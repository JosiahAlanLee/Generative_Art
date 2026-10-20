"""Native stroke-only A4 plate and tagged reading/key leaves. Run python build.py."""
from pathlib import Path
import copy
import hashlib
import json
import math
import random
import subprocess
import sys
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'vendor'))
import tx
from ix_codec import CAPTION, SHIFT, LETTERS, normalize, encode, decode, codes, validate
from lettering import SerifHand

NS = 'http://www.w3.org/2000/svg'
INK = 'http://www.inkscape.org/namespaces/inkscape'
E.register_namespace('', NS)
E.register_namespace('inkscape', INK)
COLORS = {'black': '#161918', 'red': '#a32b24'}
HAND = SerifHand()
MIN_CAP_MM = 2.5
MIN_CIPHER_MM = 2.6

def f(n):
    return f'{n:.4f}'.rstrip('0').rstrip('.')

class Drawing:
    def __init__(self):
        self.paths = {'art-paths': [], 'text-outlines': []}
        self.layer = 'art-paths'
        self.color = 'black'
        self.labels=[]
        self.cipher_sizes=[]
    def path(self, pts, color=None, width=.17, closed=False, layer=None):
        pts = list(pts)
        if len(pts) < 2:
            return
        data = 'M' + ' L'.join(f'{f(x)},{f(y)}' for x,y in pts) + (' Z' if closed else '')
        element=E.Element('{'+NS+'}path', {
            'd': data, 'fill': 'none', 'stroke': COLORS[color or self.color],
            'stroke-width': f(width), 'stroke-linecap': 'round', 'stroke-linejoin': 'round'})
        self.paths[layer or self.layer].append(element)
        return element
    def line(self, x1,y1,x2,y2,color=None,width=.14):
        self.path([(x1,y1),(x2,y2)],color,width)
    def rect(self,x,y,w,h,color=None,width=.14):
        self.path([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],color,width,True)
    def circle(self,x,y,r,color=None,width=.17):
        return self.path([(x+r*math.cos(a*math.pi/40),y+r*math.sin(a*math.pi/40)) for a in range(81)],color,width,True)
    def text(self,text,x,y,s=2.5,color='black',align='left',serif=False):
        text=text.upper()
        s=max(MIN_CAP_MM,s)
        total=HAND.width(text,s)
        if align=='center': x-=total/2
        elif align=='right': x-=total
        self.labels.append({'text':text,'cap_height_mm':s,'x':x,'y':y,'width':total})
        for line in HAND.strokes(text,x,y,s):
            self.path(line,color,.18,layer='text-outlines')
        return total
    # Adapter for the retained Matricis transcription geometry.
    def stroke(self,pts,weight='orn',color='ink',closed=False,amp=0):
        self.path(pts, 'red' if color=='red' else self.color, .13 if weight=='hair' else .17, closed)
    def dot(self,x,y,r,color='ink'):
        # Filled dots in the manuscript become a two-turn pen coil; no fill.
        self.path([(x+r*(1-i/65)*math.cos(i*.22),y+r*(1-i/65)*math.sin(i*.22)) for i in range(66)],width=.15)
    def ring(self,x,y,r,weight='orn',color='ink'):
        self.circle(x,y,r)
    def glyph(self,b,t,x,y,s,color='black',tally=True):
        assert s>=MIN_CIPHER_MM
        self.cipher_sizes.append(s)
        old=(self.layer,self.color)
        self.layer='text-outlines'; self.color=color
        tx.mark(self,b,x,y,s)
        if tally: tx.tally(self,t,x,y,s)
        self.layer,self.color=old
    def cipher_word(self,word,x,y,s=MIN_CIPHER_MM,color='black',width=23):
        start=x
        for b,t in word:
            if x+tx.token_width(t,s)>start+width:
                x=start;y+=6.5
            self.glyph(b,t,x,y,s,color)
            x+=tx.token_width(t,s)
    def write(self,path,pen=None,only_layer=None):
        root=E.Element('{'+NS+'}svg',{'width':'210mm','height':'297mm','viewBox':'0 0 210 297','version':'1.1'})
        E.SubElement(root,'{'+NS+'}title').text=('Clavicula Graduum - Provisional Clavis for IX' if 'clavis' in path.name else 'Clavicula Graduum - Tabula IX - The Square Table')
        E.SubElement(root,'{'+NS+'}desc').text='Two inks, centerline serif paths (EMS Nixish), no raster or fills. Labels at least 2.5 mm nominal H cap. Cipher: base shift +3 modulo 12, tally unchanged. Red rings assign stations 0-6 to shifts 00-06. A4. Untested on a physical plotter.'
        for name,paths in self.paths.items():
            if only_layer and name!=only_layer: continue
            g=E.SubElement(root,'{'+NS+'}g',{'id':name,'{'+INK+'}groupmode':'layer','{'+INK+'}label':name.replace('-',' ').title()})
            for el in paths:
                if pen is None or el.get('stroke')==COLORS[pen]: g.append(copy.deepcopy(el))
        E.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
