#!/usr/bin/env python3
"""Build the developmental Notoria: canonical Markdown, the five computed notae from the serif
reading edition (books/05_notoria/reading/out, built by reading/build.py), the found-leaf
ornament, 7x10 PDF.

The computed notae are merged onto full leaves as Book IV merges its plates; the found leaf
remains a schematic ornament drawn here. Run from any working directory; needs the repository
requirements and fonts, and the reading edition built first.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import math
import random
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
READING = HERE.parent / 'reading' / 'out'
# art -> computed nota (the serif reading edition of the plate); 'found' stays an ornament
COMPUTED = {'vestigiorum': 'nota-i-deposit-reading', 'sense': 'nota-ii-sense-reading',
            'mutationum': 'nota-iii-decay-reading', 'sortium': 'nota-iv-follow-reading',
            'generalis': 'nota-v-generalis-reading'}
sys.path.insert(0, str(ROOT / 'common' / 'plot'))
sys.path.insert(0, str(ROOT / 'common' / 'geometry'))
from bookpage import PW, PH, PAPER, INK, RED, MM, PageHand, paper, flow_rule
from core import arc_pts, catmull
from plotkit import PlotDoc, PlotHand
import tx
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from pypdf import PdfReader


def leaves():
    text = (HERE / 'reading-edition.md').read_text()
    result = []
    cover, *sections = re.split(r'^## ', text, flags=re.M)
    result.append(dict(title='Ars Notoria Stigmatum', kind='cover', body=cover))
    for section in sections:
        title, body = section.split('\n', 1)
        meta = re.search(r'<!-- leaf: (\w+)(?:; art: (\w+); cipher: ([A-Z ]+))? -->', body)
        if not meta:
            raise ValueError(f'No leaf metadata: {title}')
        kind, art, cipher = meta.groups()
        body = re.sub(r'<!--.*?-->', '', body, flags=re.S).strip()
        result.append(dict(title=title.strip(), kind=kind, art=art, cipher=cipher, body=body))
    # Keep the bibliography last in the reading edition as well as the manuscript.
    return [p for p in result if p['kind'] != 'sources'] + [p for p in result if p['kind'] == 'sources']


class TurnedHand:
    """Rigid transform only: preserve the inherited base-mark and tally geometry."""
    def __init__(self, hand, x, y, angle):
        self.h, self.x, self.y, self.a = hand, x, y, angle

    def point(self, p):
        x, y = p
        return (self.x + x*math.cos(self.a)-y*math.sin(self.a),
                self.y + x*math.sin(self.a)+y*math.cos(self.a))

    def stroke(self, pts, weight='orn', color='ink', **kw):
        self.h.stroke([self.point(p) for p in pts], weight, color, **kw)

    def dot(self, x, y, r, color='ink'):
        self.h.dot(*self.point((x,y)), r, color)

    def ring(self, x, y, r, weight='orn', color='ink'):
        self.h.ring(*self.point((x,y)), r, weight, color)


def ring_text(hand, text):
    radius = 74
    size = min(7.5, 0.9*2*math.pi*radius / tx.width(text,1))
    cursor, audit = 0.0, []
    for wi, word in enumerate(tx.encode(text)):
        if wi:
            cursor += .55*size
        for base, tally in word:
            advance = tx.token_width(tally,size)
            angle = -math.pi/2 + (cursor+advance/2)/radius
            h = TurnedHand(hand, 105+radius*math.cos(angle), 143+radius*math.sin(angle), angle+math.pi/2)
            start = len(hand.pdoc.layers['text'])
            tx.mark(h,base,-advance/2,-size/2,size,'orn','ink')
            tx.tally(h,tally,-advance/2,-size/2,size,'ink')
            L = hand.pdoc.layers['text']
            first = L[start]
            L[start] = first[:3] + (f' data-glyph="{len(audit)}" data-word="{wi}" data-base="{base}" data-tally="{tally}"',)
            audit.append(dict(word=wi,base=base,tally=tally))
            cursor += advance
    return audit


def ornament(p, index, out):
    doc = PlotDoc()
    a = PlotHand(doc, random.Random(50100+index), 'art', amp=.045)
    t = PlotHand(doc, random.Random(50200+index), 'text', amp=.02)
    for r in (65,69,83):
        a.ring(105,143,r,'hair')
    # A physically drawn blank, kept clear of all internal constructions.
    blank = (89,132,121,154)
    a.straight([(89,132),(121,132),(121,154),(89,154)],'hair',closed=True)
    kind = p['art']
    if kind == 'found':
        a.stroke([(17,43),(159,43),(192,74),(192,247),(19,247),(17,43)],'orn')
        a.stroke([(159,43),(157,62),(175,62),(174,76),(192,74)],'orn')
        rng=random.Random(80)
        for side in (-1,1):
            for i in range(17):
                x=105+side*(23+i*2.1)
                pts=[(x,143-50), (x+side*rng.uniform(-8,5),113), (x+side*4,143), (x+side*rng.uniform(-3,8),175),(x,193)]
                a.stroke(catmull(pts,8),'hair')
        a.stroke([(171,191),(185,217),(196,237)],'core','red')
    elif kind == 'sortium':
        for i, (x0,x1) in enumerate(((70,140),(105,70),(140,105))):
            # All three deliberately skirt the reserved compartment.
            mid=66 if i%2==0 else 144
            pts=[(x0,94),(x0,112),(mid,126),(mid,161),(x1,177),(x1,192)]
            for k in range(3):
                a.stroke(catmull([(x+k*.9,y) for x,y in pts],10),'hair')
            a.ring(x0,94,2.4);a.dot(x1,192,.8)
        a.stroke(catmull([(145,151),(157,171),(173,185),(184,187)],12),'core','red')
    elif kind == 'mutationum':
        for side in (-1,1):
            x=105+side*35
            for i in range(6):
                y=113+i*12
                # Small paired registers are generic, not a named hexagram sequence.
                if (i+int(side>0))%3==0:
                    a.straight([(x-13,y),(x-3,y)],'core')
                    a.straight([(x+3,y),(x+13,y)],'core')
                else:
                    a.straight([(x-13,y),(x+13,y)],'core')
                for d in (1,2,3):
                    a.straight([(x-12,y+d),(x+12,y+d)],'hair')
        a.stroke(catmull([(82,119),(95,112),(113,112),(126,125)],12),'core','red')
    elif kind == 'vestigiorum':
        for side in (-1,1):
            stem=105+side*25
            a.stroke([(stem,105),(stem,188)],'orn')
            for i in range(5):
                y=110+i*17
                end=105+side*(43+(i%2)*6)
                a.stroke(catmull([(stem,y),(stem+side*7,y-4),(end,y)],8),'hair')
                a.straight([(end-3,y-3),(end+3,y-3),(end+3,y+3),(end-3,y+3)],'hair',closed=True)
        a.stroke(catmull([(80,161),(72,164),(65,169)],8),'core','red')
    elif kind == 'generalis':
        for i in range(9):
            angle=i*2*math.pi/9
            x,y=105+42*math.cos(angle),143+42*math.sin(angle)
            a.ring(x,y,3.2,'orn')
            for k in range(4):
                b=angle+.22+k*.03
                a.stroke(catmull([(105+58*math.cos(b),143+58*math.sin(b)),
                                  (105+51*math.cos(angle+.15),143+51*math.sin(angle+.15)),(x,y)],10),'hair')
        a.stroke(catmull([(67,105),(79,115),(81,151),(74,178),(67,190)],12),'core','red')
    else:
        raise ValueError(kind)
    for i in range(5):
        x=78+i*13.5
        a.straight([(x,233),(x,240+(i%3)*3)],'hair')
        a.dot(x,240+(i%3)*3,.5)
    audit=ring_text(t,p['cipher'])
    # Preserve fine linework when the A4 ornament is reduced into a 7x10 leaf.
    for layer, entries in doc.layers.items():
        doc.layers[layer] = [(col, weight*1.65, path, attrs) for col,weight,path,attrs in entries]
    s=doc.svg(title=p['title'].replace('&','and'),desc='Constructed schematic ornament; not a simulation or historical ritual figure. Two inks; untested on a physical plotter.')
    stem='nota-'+kind
    (out/(stem+'.svg')).write_text(s)
    # Render the very same serialized SVG in the reading PDF.
    return dict(stem=stem,cipher=p['cipher'],tokens=audit,blank_mm=blank,
                sha256=hashlib.sha256(s.encode()).hexdigest(),physical_plotter_tested=False,
                figure_status='constructed schematic ornament; no numerical field output')


def rich(s):
    s=unicodedata.normalize('NFC',s)
    s=html.escape(s)
    s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'\*(.+?)\*',r'<i>\1</i>',s)
    # URLs get break opportunities and clickable annotations without printing raw XML.
    s=re.sub(r'https://[^\s]+',lambda m:'<link href="'+m[0]+'">'+m[0].replace('/','/\u200b').replace('-','-\u200b')+'</link>',s)
    return s


def register():
    for name,path in [('Fell','IMFeENrm28P.ttf'),('FellIt','IMFeENit28P.ttf'),('FellSC','IMFeENsc28P.ttf'),('Text','Spectral-Regular.ttf'),('Mono','IBMPlexMono-Regular.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(ROOT/'common'/'fonts'/path)))
    # Preserve Spectral's diacritics in emphasized source names too.
    pdfmetrics.registerFontFamily('Text',normal='Text',bold='Text',italic='Text',boldItalic='Text')
    pdfmetrics.registerFontFamily('Fell',normal='Fell',bold='FellSC',italic='FellIt',boldItalic='FellIt')


def build(out):
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    out.mkdir(parents=True,exist_ok=True)
    register()
    pages=leaves()
    figures={}
    for i,p in enumerate(pages):
        if not p.get('art'):
            continue
        if p['art'] in COMPUTED:
            stem=COMPUTED[p['art']]
            pdf=READING/(stem+'.pdf')
            if not pdf.exists():
                raise SystemExit(f'reading edition missing: {pdf} (run books/05_notoria/reading/build.py first)')
            ed=json.loads((READING/'reading-edition.json').read_text())
            rec=next(r for r in ed['plates'] if r['stem']==stem)
            figures[p['art']]=dict(stem=stem,kind='computed',cipher=p['cipher'],pdf=str(pdf),
                                   sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),manifest_id=rec['manifest_id'],
                                   plate_validation_passed=rec['all_passed'],field=rec['field'],
                                   physical_plotter_tested=False,figure_status='computed trace field; regenerable from its run manifest')
        else:
            figures[p['art']]=ornament(p,i,out)
    merges={}   # page number -> reading pdf path, merged after the text is set
    c=Canvas(str(out/'Ars_Notoria_Stigmatum_reading.pdf'),pagesize=(PW,PH),invariant=1,pageCompression=1)
    c.setTitle('Ars Notoria Stigmatum - developmental reading edition')
    c.setAuthor('Josiah Alan-Lee; manuscript development with ChatGPT/Codex')
    layout=[]
    def start(title,kind,number,continuation=False):
        paper(c)
        c.setFillColorRGB(*INK)
        c.setFont('Mono',7)
        c.drawString(49,688,'CODEX INTERVALLORUM / V')
        c.drawRightString(455,688,'READING DRAFT / 17 OCT 2026')
        c.setStrokeColorRGB(*INK);c.setLineWidth(.35);c.line(49,678,455,678)
        c.setFont('Fell',10);c.drawCentredString(PW/2,28,str(number))
        y=646
        style=ParagraphStyle('heading',fontName='Fell',fontSize=23,leading=25,textColor=INK)
        p=Paragraph(html.escape(title+(' (continued)' if continuation else '')),style)
        w,h=p.wrap(406,100);p.drawOn(c,49,y-h);y-=h+18
        c.bookmarkPage('leaf-'+str(number));c.addOutlineEntry(title,'leaf-'+str(number),0,False)
        return y
    number=0
    for leaf in pages:
        number+=1
        kind,title=leaf['kind'],leaf['title']
        if kind=='plate' and figures[leaf['art']].get('kind')=='computed':
            # the plate takes the whole leaf (folio only); the title and its text follow on the next
            paper(c)
            c.setFont('Fell',10);c.setFillColorRGB(*INK);c.drawCentredString(PW/2,28,str(number))
            c.bookmarkPage('leaf-'+str(number));c.addOutlineEntry(title,'leaf-'+str(number),0,False)
            merges[number]=figures[leaf['art']]['pdf']
            layout.append(dict(page=number,title=title,kind='computed-plate',boxes=[]))
            c.showPage();number+=1
        y=start(title,kind,number)
        item=dict(page=number,title=title,kind=kind,boxes=[])
        if kind=='cover':
            c.setFont('FellIt',21);c.drawCentredString(PW/2,536,'Of the Figure and Its Reader')
            h=PageHand(c,PW/2-36*MM,434,random.Random(50))
            for r in (20,26,32):h.ring(36,38,r,'hair')
            h.stroke([(8,38),(21,30),(30,35)],'orn');h.stroke([(43,41),(52,50),(64,39)],'orn','red')
            h.straight([(29,30),(43,30),(43,46),(29,46)],'hair',closed=True)
            c.setFont('Fell',13);c.drawCentredString(PW/2,206,'Three arts, five computed figures, one condemnation')
            c.setFont('Mono',8);c.drawCentredString(PW/2,173,'DEVELOPMENTAL EDITION / 17 OCTOBER 2026')
            c.setFont('FellIt',11);c.drawCentredString(PW/2,126,'The last blank has been left where it was drawn.')
        else:
            if kind=='plate' and figures[leaf['art']].get('kind')=='computed':
                y=560
            elif kind=='plate':
                drawing=svg2rlg(str(out/(figures[leaf['art']]['stem']+'.svg')))
                scale=365/drawing.height
                drawing.scale(scale,scale)
                renderPDF.draw(drawing,c,(PW-drawing.width*scale)/2,218)
                y=200
            elif kind=='key':
                h=PageHand(c,57,606,random.Random(542))
                for i in range(12):
                    tx.mark(h,i+1,(i%6)*22,(i//6)*18,7,'orn','ink')
                    tx.tally(h,1,(i%6)*22,(i//6)*18,7)
                    c.setFont('Mono',7);c.drawCentredString(57+(i%6)*22*MM+12,606-((i//6)*18+12)*MM,tx.ROMAN[i])
                y=490
            font='Fell' if kind=='oration' else 'Text'
            size=13.0 if kind=='oration' else (9.7 if kind=='sources' else 11.05)
            leading=17 if kind=='oration' else (13.0 if kind=='sources' else 14.8)
            sty=ParagraphStyle('body',fontName=font,fontSize=size,leading=leading,textColor=INK,spaceAfter=9,splitLongWords=True)
            for block in leaf['body'].split('\n\n'):
                block=block.strip()
                if not block:continue
                para=Paragraph(rich(block),sty)
                w,ht=para.wrap(406,PH)
                if ht>y-65:
                    if kind=='plate':
                        raise ValueError(f'Overflow on {kind} leaf: {title}')
                    layout.append(item);c.showPage();number+=1
                    y=start(title,kind,number,True)
                    item=dict(page=number,title=title,kind=kind,boxes=[])
                if ht>y-65:raise ValueError(f'Paragraph too large: {title}')
                para.drawOn(c,49,y-ht)
                item['boxes'].append([49,round(y-ht,2),455,round(y,2)])
                y-=ht+9
            if kind not in ('plate','key') and y>105:
                flow_rule(c,51,min(y-20,160),137,number+700,n=2,red_dot=True)
        layout.append(item);c.showPage()
    c.save()
    if merges:
        from pypdf import PdfWriter, Transformation
        r=PdfReader(str(out/'Ars_Notoria_Stigmatum_reading.pdf'))
        w=PdfWriter()
        for i,page in enumerate(r.pages,start=1):
            if i in merges:
                pl=PdfReader(merges[i]).pages[0]
                pw,ph=float(pl.mediabox.width),float(pl.mediabox.height)
                sc=min((PW-0.6*72)/pw,(PH-0.9*72)/ph)
                page.merge_transformed_page(pl,Transformation().scale(sc,sc).translate((PW-pw*sc)/2,(PH-ph*sc)/2+6))
            w.add_page(page)
        for k,v in r.metadata.items():
            w.add_metadata({k:v})
        with open(out/'Ars_Notoria_Stigmatum_reading.pdf','wb') as f:
            w.write(f)
    manifest=dict(edition='developmental reading draft, 2026-10-17',trim_points=[PW,PH],page_count=number,
                  computed_plate_pages=sorted(merges),
                  manuscript_sha256=hashlib.sha256((HERE/'reading-edition.md').read_bytes()).hexdigest(),
                  figures=figures,layout=layout,bibliography_pages=[p['page'] for p in layout if p['kind']=='sources'])
    pdf=out/'Ars_Notoria_Stigmatum_reading.pdf'
    manifest['pdf_sha256']=hashlib.sha256(pdf.read_bytes()).hexdigest()
    (out/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    validate(out)
    print(json.dumps(dict(pages=number,pdf=str(pdf),bytes=pdf.stat().st_size,figures=len(figures))))


def validate(out):
    import xml.etree.ElementTree as ET
    m=json.loads((out/'build-manifest.json').read_text())
    r=PdfReader(out/'Ars_Notoria_Stigmatum_reading.pdf')
    assert len(r.pages)==m['page_count']
    for p in r.pages:
        assert list(map(float,p.mediabox[2:]))==m['trim_points']
    for name,f in m['figures'].items():
        if f.get('kind')=='computed':
            assert hashlib.sha256(Path(f['pdf']).read_bytes()).hexdigest()==f['sha256']
            assert f['plate_validation_passed'] and f['field']['all_passed']
            continue
        path=out/(f['stem']+'.svg')
        assert hashlib.sha256(path.read_bytes()).hexdigest()==f['sha256']
        root=ET.fromstring(path.read_text())
        glyphs=sorted([e for e in root.iter() if 'data-glyph' in e.attrib],key=lambda e:int(e.attrib['data-glyph']))
        words=[]
        for e in glyphs:
            wi=int(e.attrib['data-word'])
            while len(words)<=wi:words.append([])
            words[wi].append((int(e.attrib['data-base']),int(e.attrib['data-tally'])))
        assert tx.decode(words)==f['cipher']
        colors={e.attrib['stroke'] for e in root.iter() if 'stroke' in e.attrib}
        assert colors <= {'#161918','#a32b24'}
        assert not any(e.tag.endswith(('image','text')) for e in root.iter())
    for p in m['layout']:
        for x0,y0,x1,y1 in p['boxes']:
            assert 49<=x0<x1<=455 and 65<=y0<y1<678
    assert max(p['page'] for p in m['layout'] if p['kind']!='sources')<min(m['bibliography_pages'])
    assert hashlib.sha256((out/'Ars_Notoria_Stigmatum_reading.pdf').read_bytes()).hexdigest()==m['pdf_sha256']


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=HERE/'out')
    ap.add_argument('--validate',action='store_true')
    args=ap.parse_args()
    validate(args.out) if args.validate else build(args.out)

