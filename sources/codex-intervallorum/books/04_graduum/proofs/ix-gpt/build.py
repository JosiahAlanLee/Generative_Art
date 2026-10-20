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
from codec import CAPTION, SHIFT, LETTERS, normalize, encode, decode, codes, validate
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

def plate():
    d=Drawing()
    d.rect(8,10,194,278,width=.18)
    d.line(12,31,198,31)
    d.text('CLAVICULA GRADUUM',105,18,4.1,align='center')
    d.text('THE SQUARE TABLE / FIRST KEY',105,26,2.5,align='center')
    # Drawn reserved blank, with no encoded data or paths in its interior.
    d.rect(82,42,46,24,width=.18)
    d.text('RESERVED',105,69,2.5,align='center')
    d.text('SHIFT +03',47,46,2.8,align='center')
    d.text('TALLY HELD',47,53,2.5,align='center')
    d.text('WHAT IS LOST?',162,46,2.5,'red',align='center')
    d.text('NOT MEASURED HERE',162,53,2.5,'red',align='center')
    d.text('RED RINGS: STATIONS 0-6',105,74,2.5,'red',align='center')
    x0,y0,cell=44,92,122/12
    d.text('INPUT BASE',105,79,2.5,align='center')
    d.text('K',40,86,2.5,align='center')
    for c in range(12):
        d.text(str(c+1),x0+(c+.5)*cell,86,2.5,align='center')
    for r in range(13): d.line(x0,y0+r*cell,x0+122,y0+r*cell,width=.10)
    for c in range(13): d.line(x0+c*cell,y0,x0+c*cell,y0+122,width=.10)
    for r in range(12):
        d.text(f'{r:02d}',40,y0+(r+.5)*cell-1.25,2.5,align='center')
        if r<7: d.circle(40,y0+(r+.5)*cell,2.5,'red',.20).set('data-station',str(r))
        for c in range(12):
            b=(c+r)%12+1
            d.glyph(b,1,x0+c*cell+2.4,y0+r*cell+2.3,5.2,tally=False)
    # Red brackets select row 03; the black arrangement remains legible.
    ry=y0+3*cell
    d.path([(167,ry),(168,ry),(168,ry+cell),(167,ry+cell)],'red',.22)
    d.line(x0+7*cell+1.7,ry+cell-1.4,x0+8*cell-1.7,ry+cell-1.4,'red',.26)
    # Cipher caption split in two ordered side registers.
    words=encode(CAPTION)
    for side, subset in enumerate((words[:4],words[4:])):
        sx=11 if side==0 else 175
        d.text('A' if side==0 else 'B',sx,87,2.5)
        for wi,word in enumerate(subset):
            yy=104+wi*26
            d.line(sx,yy-3,sx+23,yy-3,width=.10)
            d.cipher_word(word,sx,yy,MIN_CIPHER_MM,width=23)
        d.text('DOWN',sx,208,2.5)
    d.text('REVERSE THE SHIFT BEFORE READING THE LETTER',105,218,2.5,align='center')
    # Worked encryption: literal THE, numeric tokens, and actual cipher hand.
    d.line(12,226,198,226,width=.18)
    d.text('SPECIMEN / THE / SHIFT +03',105,230,2.5,align='center')
    for i,(letter,plain,cipher) in enumerate(zip('THE',encode('THE',0)[0],encode('THE')[0])):
        xx=49+i*56
        d.text(letter,xx-15,239,3,align='center')
        d.glyph(*plain,xx-9,237.5,4)
        d.text('+3',xx+1,240,2.5,'red')
        d.glyph(*cipher,xx+10,237.5,4)
        d.text(f'{plain[0]:02d}:{plain[1]} / {cipher[0]:02d}:{cipher[1]}',xx,249,2.5,align='center')
    # Full plaintext lookup on the plate, not just on the separate Clavis.
    d.text('BASE',53,257,2.5,align='right')
    d.text('TALLY',22,266,2.5)
    for b in range(1,13):
        xx=63+(b-1)*10
        d.text(str(b),xx,257,2.5,align='center')
        for t in range(1,4):
            d.text(tx.INV.get((b,t),'-'),xx,261+(t-1)*5,2.5,align='center')
    for t in range(1,4): d.text(str(t),53,261+(t-1)*5,2.5,align='right')
    d.line(12,278,198,278,width=.14)
    d.text('TABULA IX',105,279.5,2.5,align='center')
    d.text('THE SQUARE TABLE',105,283.3,3,align='center')
    return d

def key_leaf():
    d=Drawing(); d.rect(12,12,186,273)
    d.text('CLAVIS / IX',105,22,3.6,align='center',serif=True)
    d.text('THE MATRICIS TRANSCRIPTION HAND',105,32,2,align='center')
    d.text('TWELVE BASE MARKS / THREE TALLY ROWS',105,39,1.55,align='center')
    for b in range(1,13):
        x=19+(b-1)*14.5
        d.text(str(b),x+5,51,1.7,align='center')
        for t in range(1,4):
            y=60+(t-1)*33
            ch=tx.INV.get((b,t))
            if ch:
                d.glyph(b,t,x,y,6)
                d.text(ch,x+4,y+12,2.3,align='center')
            else:
                d.text('-',x+4,y+3,2.3,align='center')
    for text,y,color in [
      ('DASHES ARE RESERVED IN PLAINTEXT',161,'black'),
      ('CIPHER TOKENS MAY OCCUPY THOSE CELLS',169,'red'),
      ('FIRST UNSHIFT THE BASE / THEN READ A LETTER',177,'black'),
      ('IX: SHIFT +03 / MODULO 12 / TALLY UNCHANGED',191,'black'),
      ('ADD 03 TO BASE / WRAP AFTER XII',199,'black'),
      ('DECRYPT: SUBTRACT 03 IN THE SAME CYCLE',207,'black'),
      ('SPACES SURVIVE / PUNCTUATION IS OMITTED',215,'black'),
      ('READ PLATE MARGIN A BEFORE MARGIN B',223,'black'),
      ('THIS LEAF SETTLES IX ONLY',242,'red'),
      ('AVE MARIA TABLE AND XII KEY STATUS PENDING',250,'black'),
      ('SEVEN APPEARS FOUR TIMES IN THIS BOOK',265,'black'),
      ('THE COINCIDENCE CARRIES NO ARGUMENT',273,'black'),
    ]: d.text(text,105,y,1.55,color,align='center')
    return d

def make_reading(manifest):
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    fontroot=ROOT/'fonts'
    pdfmetrics.registerFont(TTFont('Fell',str(fontroot/'IMFeENrm28P.ttf')))
    pdfmetrics.registerFont(TTFont('Mono',str(fontroot/'IBMPlexMono-Regular.ttf')))
    c=canvas.Canvas(str(ROOT/'ix-reading-and-key.pdf'),pagesize=(595.276,841.89))
    c.setTitle('Clavicula Graduum - IX - Reading and key')
    sections=[
      ('[E]', 'Matricis supplies twelve base marks and one, two, or three tally strokes: A-L, M-X, then Y-Z. Ten combinations in the third row are reserved. Its proof sheet omits punctuation and separates words by wider intervals. The local transcription geometry and proof-sheet text were inspected [M]. Escalationum numbers its seven stations 0-6 by permission, not competence [S].'),
      ('[D]', 'IX adds a reversible operation: c = 1 + ((b - 1 + k) mod 12), with tally t unchanged. Here k = 3. Decryption subtracts 3 before consulting the plaintext key. All 26 letters round-trip at all 12 shifts. The table shows base marks only; the margin supplies each mark with its tally.'),
      ('[H]', 'The twelve rows are arithmetic shifts K=0-11. Red rings select Escalationum stations S0-S6 [S], with the editorial assignment K=S. Other rows complete the cipher cycle. This assignment supplies no measure of context loss: the arithmetic preserves every normalized letter.'),
      ('[V]', 'Print the key and keep the decoded sentence beside the plate in the manuscript record. This edition chooses inspectability over secrecy. A reader can check the operation without accepting an office or an interpretation.'),
      ('[F]', CAPTION),
      ('READING THE PLATE', 'Begin at the input base column and the numbered shift row K. Retain the letter\'s tally strokes. Seven red rings map stations S0-S6 to shifts 00-06. The right bracket selects shift +03; the underline selects the H base there. The bottom specimen works THE. Read margin A downward, then B. A word wrapped within one ruled strip remains one word. The upper rectangle is a drawn reserved blank. Black records the table; red selects passages and asks what it cannot measure.'),
      ('DOES NOT CLAIM', 'Recovering the normalized signs does not recover the situation in which they were written.'),
      ('SOURCE TRAIL', '[M] Clavicula Matricis, transcription proof sheet (PDF p. 21), and retained generator/tx.py plus core.py from Clavicula Intervallorum. The twelve-mark geometry and tally mapping were read; the filled dots are rendered here as pen coils. [I] Clavicula Intervallorum, How to Read the Object (PDF p. 3), inspected for the five tags and the two-ink convention. [S] Pseudomonarchia Escalationum, Directions for descending (PDF p. 4), inspected for station numbering and its stated ordering. [B] Josiah Alan-Lee / Claude, supplied production brief and feedback, read in full. [T] Wellcome Collection catalogue ukbqdd75, Polygraphiae libri sex (1518), bibliographic metadata inspected. No historical table page was inspected in this run; the modular construction here is a new adaptation, not a diplomatic reconstruction.'),
    ]
    def page_header(title,num):
        c.setFillColor(HexColor('#161918'));c.setStrokeColor(HexColor('#161918'))
        c.setFont('Mono',8);c.drawString(43,806,'CLAVICULA GRADUUM');c.drawRightString(552,806,'IX / '+title)
        c.setLineWidth(.35);c.line(43,795,552,795)
        c.setFont('Mono',8);c.drawCentredString(297.6,27,str(num))
    def block(label,text,y,size=10.6):
        c.setFillColor(HexColor('#a32b24') if label in ('[F]','DOES NOT CLAIM') else HexColor('#161918'))
        c.setFont('Mono',8.5);c.drawString(43,y,label);y-=16
        c.setFillColor(HexColor('#161918'));c.setFont('Fell',size)
        lines=simpleSplit(text,'Fell',size,509)
        for line in lines:c.drawString(43,y,line);y-=size*1.28
        return y-13
    page_header('READING LEAF',1)
    c.setFont('Fell',25);c.drawString(43,759,'The signs and the room')
    y=727
    for label,text in sections[:7]: y=block(label,text,y)
    assert y>45, y
    c.showPage();page_header('KEY AND WORKED ENCRYPTION',2)
    c.setFont('Fell',25);c.drawString(43,759,'Keep the tally. Reverse the shift.')
    y=block('NORMALIZATION','ASCII A-Z only; lowercase becomes uppercase. Listed punctuation is omitted, whitespace collapses, and word boundaries survive. Digits, non-ASCII letters, and unsupported characters are rejected. Original punctuation remains in the manuscript JSON.',727)
    for row,label in ((1,'ONE TALLY'),(2,'TWO TALLIES'),(3,'THREE TALLIES')):
        c.setFont('Mono',8);c.drawString(43,y,label);y-=18
        c.setFont('Mono',9)
        c.drawString(43,y,' '.join(f'{b:02d}' for b in range(1,13)));y-=15
        c.drawString(43,y,'  '.join(tx.INV.get((b,row),'-') for b in range(1,13)));y-=27
    y=block('WORKED SPECIMEN','THE -> 08:2 08:1 05:1 -> shift bases +3 -> 11:2 11:1 08:1. The tally is unchanged. KEY -> 02:1 08:1 04:3. The final 04:3 is legal ciphertext; subtract 3 to obtain 01:3 = Y. Never read ciphertext through the plaintext alphabet first.',y)
    y=block('FULL CAPTION',normalize(CAPTION),y)
    c.setFont('Mono',8.0)
    for line in simpleSplit(codes(encode(CAPTION)),'Mono',8,509):c.drawString(43,y,line);y-=12
    y-=18
    y=block('SOURCE TRAIL',sections[-1][1],y,9.2)
    y=block('HISTORICAL CATALOGUE','https://wellcomecollection.org/works/ukbqdd75',y,9.0)
    y=block('PRODUCTION STATUS','A4, black/red, two SVG layers, stroke paths only. EMS Nixish centerlines: minimum nominal H cap 2.5 mm; cipher base 2.6 mm. Untested on a physical plotter, including 0.3 mm gel pens. Ave Maria and XII remain pending. The four thematic occurrences of seven are not yet audited.',y,9.2)
    assert y>35,y
    c.save()
    text='# IX - The Square Table\n\n'+'\n\n'.join(label+' '+text for label,text in sections)
    text+='\n\nCiphertext: '+codes(encode(CAPTION))+'\n\nNormalization: '+normalize(CAPTION)+'\n\nUntested on a physical plotter.\n'
    (ROOT/'ix-reading-leaf.md').write_text(text)

def main():
    check=validate()
    manifest={'title':'Clavicula Graduum','status':'IX revised proof: serif hand, seven station markers, no ornament; later plates pending',
      'plate':{'number':'IX','title':'The Square Table','second_text_plain':CAPTION,
       'second_text_normalized':normalize(CAPTION),'second_text_source':'this plate\'s [F] sentence',
       'ciphertext':encode(CAPTION),'ciphertext_codes':codes(encode(CAPTION)),
       'does_not_claim':'Recovering the normalized signs does not recover the situation in which they were written.',
       'reserved_blank_mm':{'x':82,'y':42,'width':46,'height':24}},
      'codec':{'base_marks':12,'plaintext_letters':26,'caption_shift':SHIFT,'station_to_shift':{str(i):i for i in range(7)},'station_to_shift_status':'editorial assignment; not a context-loss measurement','modulus':12,
        'tally':'unchanged','row_zero':'identity','ciphertext_space':'36 base/tally combinations; unshift before plaintext lookup',
        'normalization':'ASCII letters; uppercase; omit listed punctuation; collapse whitespace; reject other characters',
        'plaintext_key':LETTERS,'caption_register_order':['A top to bottom','B top to bottom']},
      'plot':{'width_mm':210,'height_mm':297,'physical_plotter_tested':False,'inks':COLORS,'layers':['art-paths','text-outlines'],'lettering':'EMS Nixish centerline serif','minimum_nominal_H_cap_mm':MIN_CAP_MM,'minimum_cipher_base_mm':MIN_CIPHER_MM,'ornament':False},
      'production_order':['IX','X','XI','V','VII','I','II','III','IV','VI','VIII','XII'],
      'open_decisions':{'XI':'SVG order is controllable; a letter delimiter and protected export protocol remain to be specified.',
        'X':'Ave Maria table and actual Foras effect line must be inspected before production.',
        'books':'The brief does not allocate the twelve plates among the three books.',
        'XII':'Withheld-key mechanism remains to be designed after the other keys exist.',
        'seven':'Four thematic occurrences asserted by brief; audit pending, no evidentiary argument.'},
      'validation':check,
      'source_hashes':{f:hashlib.sha256((ROOT/'vendor'/f).read_bytes()).hexdigest() for f in ('tx.py','core.py')}}
    (ROOT/'manuscript.json').write_text(json.dumps(manifest,indent=2)+'\n')
    d=plate()
    for name,pen,layer in [('ix-square-table.svg',None,None),('ix-black-a4.svg','black',None),
        ('ix-red-a4.svg','red',None),('ix-art-only.svg',None,'art-paths'),('ix-text-only.svg',None,'text-outlines')]:
        d.write(ROOT/name,pen,layer)
    key=key_leaf()
    key.write(ROOT/'clavis-ix-provisional.svg')
    make_reading(manifest)
    for name in ('ix-square-table','clavis-ix-provisional'):
        subprocess.run(['inkscape','--app-id-tag=graduum-'+name,'--batch-process',str(ROOT/(name+'.svg')),
          '--export-background=#f6f0e4','--export-background-opacity=1','--export-width=1500',
          '--export-filename='+str(ROOT/(name+'.png'))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for file in ROOT.glob('*.svg'):
        root=E.parse(file).getroot()
        assert len(root.findall('{'+NS+'}g')) in (1,2)
        for el in root.iter():
            assert el.tag.split('}')[-1] in ('svg','title','desc','g','path')
            if el.tag.endswith('}path'):
                assert el.get('fill')=='none' and el.get('stroke') in COLORS.values()
    # All paths are polylines, so checking their line segments also checks the
    # entire drawn blank. The frame's boundary may touch, never cross, it.
    import re
    from shapely.geometry import LineString, box
    blank=box(82.001,42.001,127.999,65.999)
    for paths in d.paths.values():
        for el in paths:
            nums=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',el.get('d'))))
            pts=list(zip(nums[::2],nums[1::2]))
            assert all(7.9<=x<=202.1 and 9.9<=y<=288.1 for x,y in pts)
            assert not LineString(pts).intersects(blank), 'Reserved blank crossed'
    check['svg_structure']='passed: stroke-only paths, declared layers, two inks'
    check['counts']={k:len(v) for k,v in d.paths.items()}
    check['reserved_blank_and_page_bounds']='passed'
    check['typography']={'face':'EMS Nixish','min_plate_cap_mm':min(x['cap_height_mm'] for x in d.labels),'min_clavis_cap_mm':min(x['cap_height_mm'] for x in key.labels),'min_cipher_base_mm':min(d.cipher_sizes)}
    check['station_mapping']={str(i):i for i in range(7)}
    assert sorted(el.get('data-station') for el in d.paths['art-paths'] if el.get('data-station') is not None)==list('0123456')
    check['physical_plotter_test']='not performed'
    (ROOT/'type-audit.json').write_text(json.dumps({'plate':d.labels,'clavis':key.labels},indent=2)+'\n')
    (ROOT/'validation.json').write_text(json.dumps(check,indent=2)+'\n')
    print(json.dumps(check,indent=2))

if __name__=='__main__': main()
