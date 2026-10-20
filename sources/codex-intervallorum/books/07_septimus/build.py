#!/usr/bin/env python3
"""Portable reading editions for the two parts of Septimus; no network at build time."""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

import fitz
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'binding'))
sys.path.insert(0,str(REPO/'common/geometry'))
import backmatter
spec=importlib.util.spec_from_file_location('sv',ROOT/'semiphoras/semiphoras.py')
sv=importlib.util.module_from_spec(spec);spec.loader.exec_module(sv)
spec=importlib.util.spec_from_file_location('matricis_cipher',REPO/'books/01_matricis/generator/cipher.py')
cipher=importlib.util.module_from_spec(spec);spec.loader.exec_module(cipher)

PW,PH=504,720
PAPER=colors.HexColor('#ede6d4');INK=colors.HexColor('#161918');RED=colors.HexColor('#a32b24');MUTE=colors.HexColor('#5a4331')
ROMAN=['I','II','III','IV','V','VI','VII']
TOKENS=['TRI','RNG','CHN','FRM','WIL','CAB','LIC']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def plain(s):return re.sub(r'\*\*(.*?)\*\*',r'\1',s)
def norm(s):return re.sub(r'[^a-z0-9]','',plain(s).lower())


def paragraphs(s):
    s=re.sub(r'<!--.*?-->','',s,flags=re.S)
    return [' '.join(p.split()) for p in s.strip().split('\n\n') if p.strip() and not p.startswith('#')]


def clavis_sections():
    parts=re.split(r'^## (.+)\n', (ROOT/'manuscript/clavis.md').read_text(),flags=re.M)
    return [(parts[i],paragraphs(parts[i+1])) for i in range(1,len(parts),2)]


def vinculis_sections():
    parts=re.split(r'^<!-- (section|operation): (.*?) -->\n',(ROOT/'manuscript/de-vinculis.md').read_text(),flags=re.M)
    out=[]
    for i in range(1,len(parts),3):
        kind,meta,body=parts[i:i+3]
        if kind=='section':
            head=re.search(r'^## (.+)$',body,re.M).group(1)
            out.append(dict(kind=kind,id=meta,title=head,paragraphs=paragraphs(body)))
        else:
            num,title,claims=[x.strip() for x in meta.split('|')]
            tab,comment=re.split(r'^### Commentarium [IVX]+\s*$',body,maxsplit=1,flags=re.M)
            out.append(dict(kind=kind,id=num,title=title,claims=claims,tabula=paragraphs(tab),commentary=paragraphs(comment)))
    return out


def all_source_blocks(kind):
    if kind=='clavis':return [p for _,ps in clavis_sections() for p in ps]
    out=[]
    for s in vinculis_sections():
        out+=s['paragraphs'] if s['kind']=='section' else s['tabula']+s['commentary']
    return out


def fonts():
    fd=REPO/'common/fonts'
    for name,file in [('SVBody','static/EBGaramond-Regular400.ttf'),('SVItalic','static/EBGaramond-Italic400.ttf'),('SVTitle','IMFeENrm28P.ttf'),('SVSmall','IMFeENsc28P.ttf'),('SVMono','IBMPlexMono-Regular.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(fd/file)))


def markup(s):
    s=html.escape(s)
    s=re.sub(r'\*\*(.*?)\*\*',r'<font name="SVSmall" color="#a32b24">\1</font>',s)
    return re.sub(r'\[(S\d+)\]',r'<link href="#ref-\1" color="#a32b24">[\1]</link>',s)


def glyph(c,text,cx,cy,size,color=INK):
    """The inherited alphabet's exact polylines, without wobble or rasterisation."""
    text=text.lower();width=sum(cipher.G[ch][0]+cipher.TRACK for ch in text)-cipher.TRACK
    x=cx-width*size/2
    c.saveState();c.setStrokeColor(color);c.setFillColor(color);c.setLineWidth(max(.45,size*.018))
    for ch in text:
        w,ops=cipher.G[ch]
        def point(p):return (x+p[0]*size,cy+(.64-p[1])*size)
        for op in ops:
            if op[0] in ('p','c'):
                ps=[point(p) for p in op[1]];path=c.beginPath();path.moveTo(*ps[0])
                for p in ps[1:]:path.lineTo(*p)
                if op[0]=='c':path.close()
                c.drawPath(path,stroke=1,fill=0)
            else:
                px,py=point((op[1],op[2]));c.circle(px,py,op[3]*size,stroke=1,fill=op[0]=='d')
        x+=(w+cipher.TRACK)*size
    c.restoreState()


def seal(c,record,cx,cy):
    c.saveState();c.setStrokeColor(INK);c.setLineWidth(.45);c.circle(cx,cy,28,stroke=1,fill=0)
    glyph(c,record['name'],cx,cy,16)
    for bit in range(7):
        a=math.pi/2-bit*math.tau/7;x=cx+35*math.cos(a);y=cy+35*math.sin(a)
        c.setStrokeColor(RED);c.setFillColor(RED if record['position']&(1<<bit) else PAPER)
        c.circle(x,y,1.7,stroke=1,fill=1)
    c.setFont('SVMono',6.7);c.setFillColor(MUTE);c.drawCentredString(cx,cy-49,record['id'])
    c.restoreState()


class Book:
    def __init__(self,path,title):
        self.path=Path(path);self.title=title;self.pages=[];self.pairs=[];self.active=False;self.y=0
        self.c=Canvas(str(path),pagesize=(PW,PH),invariant=1,pageCompression=1)
        self.c.setTitle(title);self.c.setAuthor('Josiah Alan-Lee')
        self.styles={
            'body':ParagraphStyle('body',fontName='SVBody',fontSize=12,leading=16.4,spaceAfter=11,textColor=INK),
            'small':ParagraphStyle('small',fontName='SVItalic',fontSize=10.4,leading=14,spaceAfter=10,textColor=MUTE),
            'heading':ParagraphStyle('head',fontName='SVTitle',fontSize=25,leading=29,spaceAfter=20,textColor=INK),
            'label':ParagraphStyle('label',fontName='SVSmall',fontSize=10,leading=14,spaceAfter=9,textColor=RED),
            'tabula':ParagraphStyle('tabula',fontName='SVBody',fontSize=12.4,leading=17,spaceAfter=15,textColor=INK),
            'mono':ParagraphStyle('mono',fontName='SVMono',fontSize=8,leading=12,spaceAfter=15,textColor=MUTE),
        }

    @property
    def page(self):return self.c.getPageNumber()

    def start(self,title,kind='body',key=None):
        if self.active:raise ValueError('page already open')
        self.active=True;self.running=title;self.y=638;c=self.c
        c.setFillColor(PAPER);c.rect(0,0,PW,PH,fill=1,stroke=0)
        c.setStrokeColor(colors.HexColor('#8e7b5f'));c.setLineWidth(.45);c.line(40,679,464,679)
        c.setFont('SVSmall',8);c.setFillColor(INK);c.drawString(42,690,self.title.upper())
        right=title.upper()
        size=min(8,8*230/max(230,pdfmetrics.stringWidth(right,'SVSmall',8)))
        c.setFont('SVSmall',size);c.setFillColor(RED);c.drawRightString(462,690,right)
        c.setFont('SVSmall',9);c.setFillColor(MUTE);c.drawCentredString(252,24,str(self.page))
        self.pages.append(dict(page=self.page,title=title,kind=kind))
        if key:c.bookmarkPage(key);c.addOutlineEntry(title,key,level=0)

    def end(self):
        if not self.active:raise ValueError('no page open')
        self.c.showPage();self.active=False

    def paragraph(self,text,style='body'):
        todo=Paragraph(markup(text),self.styles[style])
        while True:
            _,h=todo.wrap(400,10000)
            if self.y-h>=55:
                todo.drawOn(self.c,52,self.y-h);self.y-=h+self.styles[style].spaceAfter;return
            if style=='heading' or self.y<130:
                self.end();self.start(self.running);continue
            chunks=todo.split(400,self.y-55)
            if not chunks:self.end();self.start(self.running);continue
            if len(chunks)!=2:raise ValueError('unexpected paragraph split')
            _,height=chunks[0].wrap(400,10000);chunks[0].drawOn(self.c,52,self.y-height)
            self.end();self.start(self.running);todo=chunks[1]

    def heading(self,text):
        if self.y<190:self.end();self.start(text)
        self.paragraph(text,'heading')

    def blank(self):
        self.start('Interval','blank');self.end()

    def titlepage(self,subtitle):
        self.start('The book','title');c=self.c;c.setFont('SVSmall',34);c.setFillColor(INK);c.drawCentredString(252,478,self.title.upper())
        c.setFont('SVItalic',15);c.drawCentredString(252,444,subtitle)
        # The Clavis opens the volume; the label belongs to De Vinculis, the seventh book.
        if self.title!='Clavis':c.setFont('SVSmall',11);c.setFillColor(RED);c.drawCentredString(252,378,'SEPTIMUS')
        glyph(c,'key' if self.title=='Clavis' else 'bnd',252,278,37)
        self.end()

    def art(self,name,caption):
        self.start(caption,'illumination');self.c.drawImage(str(ROOT/'assets'/name),36,90,width=432,height=576,preserveAspectRatio=True,anchor='c')
        self.c.setFont('SVItalic',10);self.c.setFillColor(MUTE);self.c.drawCentredString(252,61,caption);self.end()

    def tabula(self,s):
        if self.page%2:self.blank()
        self.start('Tabula '+s['id'],'tabula',key='tabula-'+s['id']);page=self.page
        self.heading(s['title']);self.paragraph(s['claims']+' / proposition and opposition','label')
        c=self.c;c.setStrokeColor(colors.HexColor('#8e7b5f'));c.setLineWidth(.5);c.circle(252,456,72,stroke=1,fill=0)
        glyph(c,TOKENS[ROMAN.index(s['id'])],252,456,43)
        c.setFillColor(MUTE);c.setFont('SVMono',8);c.drawCentredString(252,363,TOKENS[ROMAN.index(s['id'])]+' / chapter mark')
        self.y=325
        for p in s['tabula']:self.paragraph(p,'tabula')
        if self.page!=page:raise ValueError('Tabula overflow: '+s['id'])
        self.end();self.pairs.append(dict(operation=s['id'],tabula_page=page,commentarium_page=self.page))
        self.start('Commentarium '+s['id'],key='commentarium-'+s['id']);self.heading('Commentarium '+s['id'])
        for p in s['commentary']:self.paragraph(p)
        self.end()

    def append_sources(self,kind):
        refs=json.loads((ROOT/'manuscript/references.json').read_text())
        used={x for p in all_source_blocks(kind) for x in re.findall(r'\[(S\d+)\]',p)}
        refs=[r for r in refs if r['id'] in used]
        notes=[dict(title='VII / preparation',paragraphs=[
            'First reading edition, 17 October 2026. Prepared for Josiah Alan-Lee. Project and text direction: Josiah Alan-Lee. Initial brief and research passes: Claude Opus 5.5. Editorial revision, Clavis and De Vinculis reading texts, native apparatus, build and opening illuminations: ChatGPT/Codex.',
            'The Clavis is a proposed entrance to the series, not personal testimony supplied by the author or a declaration of his final commitments. Both parts remain review texts. The Clavis opens the bound volume; De Vinculis follows Book VI as Book VII, before the collected bibliography. Both parts are also available as standalone reading editions. The Clavis paragraph on Book VI and its sentence on claim labels were revised by Claude on 19 October 2026, when De Potestate et Accusatione replaced the Tarot of Intervals as Book VI.',
            'The bibliography distinguishes direct passages, abstracts, indexed material and original-pass reports. The independent check is limited and no experiment was reproduced. The full research passes retain their original provenance and contested leads in the repository.',
            'The two composed raster scenes were generated with the built-in imagegen tool. On 19 October 2026, the open workshop received a furniture and instrument-support correction with the same tool; the original is retained. Prompts and image hashes are recorded with the assets. Generated imagery carries no keyed text or experimental evidence.',
            'The inner seal hand uses the inherited Matricis substitution alphabet, drawn as native vector strokes. Position carriers and identifiers are separate. The seventy-two-name arrangement is a disclosed English adaptation, with normalized-letter recovery checked by code. The three sentences first used, whose names repeat SNO, are kept in the code as a regression fixture; the printed questions repeat NEN and UND, so each seal is identified by its position as well as its name. Physical plotting has not been tested.'
        ])]
        start=self.page
        # Use the same house renderer as the opening book and current omnibus.
        apparatus=backmatter.write(self.c,refs,notes,start,REPO,local_book='VII')
        self.pages+=apparatus['pages'];self.bibliography_start=start
        return apparatus

    def finish(self):
        if self.active:self.end()
        self.c.save()


def gathering(b):
    data=sv.manifest();records=data['records']
    for first in range(0,72,20):
        b.start('Semiphoras Vinculorum','seals',key='seals-'+str(first+1));b.heading('Semiphoras Vinculorum')
        b.paragraph(f'Positions {first+1}–{min(72,first+20)} / position carrier and three-letter core','small')
        for j,r in enumerate(records[first:first+20]):seal(b.c,r,99+(j%4)*102,535-(j//4)*100)
        b.end()
    b.start('The inner hand','key',key='alphabet');b.heading('The inner hand')
    b.paragraph('The inherited Matricis alphabet. The core gives letters in order; the outer seven points on a seal give its position. Filled is one, open is zero. Read the top point first, then clockwise, least significant bit first.','small')
    for i,ch in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
        x=92+(i%5)*80;y=500-(i//5)*73
        glyph(b.c,ch,x,y,31);b.c.setFillColor(MUTE);b.c.setFont('SVMono',9);b.c.drawCentredString(x,y-31,ch)
    b.end()
    b.start('The recovery lines','key',key='recovery');b.heading('The recovery lines')
    for i,(s,line) in enumerate(zip(data['sentences'],data['normalized']),1):
        b.paragraph('Line '+str(i)+(' / reversed in the columns' if i==2 else ' / forward'),'label')
        b.paragraph(s);b.paragraph(line,'mono')
    b.paragraph('Every letter occurs once in the column arrangement. Recover first letters in order, second letters in reverse order, and third letters in order. Word boundaries and punctuation are supplied by these reading sentences, not recovered by the transposition.','small')
    b.paragraph('Active distinct trigrams: '+str(data['distinct_names'])+'. Position identifiers: 72. Equal names retain equal cores; position carriers remain distinct.','small');b.end()
    return data


def build(out):
    fonts();out=Path(out);out.mkdir(parents=True,exist_ok=True);results={}
    for kind,title,filename,subtitle in [('clavis','Clavis','Clavis_Septimus_reading.pdf','A way into the several books'),('vinculis','De Vinculis','De_Vinculis_reading.pdf','Of bonds, judgment and service')]:
        b=Book(out/filename,title);b.titlepage(subtitle);b.art('the-open-workshop-v02.png','The open workshop')
        if kind=='clavis':
            for i,(head,ps) in enumerate(clavis_sections()):
                if not b.active:b.start(head,key='clavis-'+str(i))
                b.heading(head)
                for p in ps:b.paragraph(p)
            if b.active:b.end()
        else:
            b.start('The seven operations','contents',key='contents');b.heading('The seven operations')
            b.paragraph('A Tabula faces the opening of each Commentarium. The arguments may continue across further leaves.','small')
            for s in vinculis_sections():
                if s['kind']=='operation':b.paragraph(s['id']+'. '+s['title'],'label');b.paragraph(s['claims'],'small')
            b.end();b.blank()
            for s in vinculis_sections():
                if s['kind']=='section':
                    b.start(s['title'],key=s['id']);b.heading(s['title'])
                    for p in s['paragraphs']:b.paragraph(p)
                    b.end()
                else:
                    if s['id']=='VI':
                        if b.page%2==0:b.blank()
                        b.art('the-empty-cabinet.jpg','The empty cabinet')
                    b.tabula(s)
            sealdata=gathering(b)
            (out/'semiphoras.json').write_text(json.dumps(sealdata,indent=2)+'\n')
        apparatus=b.append_sources(kind);b.finish()
        with fitz.open(out/filename) as doc:pages=len(doc)
        results[kind]=dict(pdf=filename,pages=pages,page_map=b.pages,tabula_pairs=b.pairs,bibliography_start=b.bibliography_start,reference_keys=apparatus['keys'],sha256=sha(out/filename))
    inputs=[ROOT/'build.py',ROOT/'manuscript/clavis.md',ROOT/'manuscript/de-vinculis.md',ROOT/'manuscript/references.json',ROOT/'semiphoras/semiphoras.py',REPO/'books/01_matricis/generator/cipher.py',REPO/'common/geometry/core.py',REPO/'binding/backmatter.py',*sorted((ROOT/'assets').glob('*'))]
    inputs += [REPO/'common/fonts'/x for x in ['static/EBGaramond-Regular400.ttf','static/EBGaramond-Italic400.ttf','IMFeENrm28P.ttf','IMFeENsc28P.ttf','IBMPlexMono-Regular.ttf']]
    manifest=dict(schema_version=1,books=results,input_sha256={str(p.relative_to(REPO)):sha(p) for p in inputs if p.is_file()},seal_count=72,illumination_count=2)
    (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:{x:v for x,v in r.items() if x in ('pdf','pages','bibliography_start')} for k,r in results.items()}))
    return manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=ROOT/'out');args=ap.parse_args();build(args.out)
