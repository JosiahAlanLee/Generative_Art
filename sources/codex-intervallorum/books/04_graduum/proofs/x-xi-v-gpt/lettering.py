"""EMS Nixish centerline serif, calibrated by measured H rather than font metadata."""
from pathlib import Path
import xml.etree.ElementTree as ET
from fontTools.pens.basePen import BasePen
from fontTools.svgLib.path import parse_path

class PolyPen(BasePen):
    def __init__(self):
        super().__init__(None)
        self.lines=[]
    def _moveTo(self,p): self.lines.append([tuple(p)])
    def _lineTo(self,p): self.lines[-1].append(tuple(p))
    def _curveToOne(self,p1,p2,p3):
        p0=self._getCurrentPoint()
        for i in range(1,25):
            t=i/24; u=1-t
            self.lines[-1].append(tuple(u**3*p0[j]+3*u*u*t*p1[j]+3*u*t*t*p2[j]+t**3*p3[j] for j in (0,1)))
    def _closePath(self): self.lines[-1].append(self.lines[-1][0])
    def _endPath(self): pass

class SerifHand:
    def __init__(self):
        root=ET.parse(Path(__file__).parent/'fonts/EMSNixish.svg').getroot()
        font=root.find('.//{*}font')
        self.glyphs={}
        for g in font.findall('{*}glyph'):
            ch=g.get('unicode')
            if ch is None: continue
            p=PolyPen()
            if g.get('d'): parse_path(g.get('d'),p)
            self.glyphs[ch]=(float(g.get('horiz-adv-x',font.get('horiz-adv-x'))),p.lines)
        ys=[y for line in self.glyphs['H'][1] for x,y in line]
        self.top=max(ys);self.bottom=min(ys);self.cap=self.top-self.bottom
    def width(self,text,size):
        return sum(self.glyphs[ch][0] for ch in text)*size/self.cap
    def strokes(self,text,x,y,size):
        scale=size/self.cap
        for ch in text:
            advance,lines=self.glyphs[ch]
            for line in lines:
                if len(line)>1:
                    yield [(x+u*scale,y+(self.top-v)*scale) for u,v in line]
            x+=advance*scale
