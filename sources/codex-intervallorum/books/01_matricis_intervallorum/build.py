#!/usr/bin/env python3
"""Build the consolidated opening book from editable JSON and local assets.

The two earlier books remain source editions. This is the active reading text.
No browser, network, or development-workspace paths are needed.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import importlib.util
import io
import json
import math
from pathlib import Path
import random
import re
import sys
import xml.etree.ElementTree as ET

import fitz
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
INTER=REPO/'books/02_intervallorum'
sys.path.insert(0,str(INTER))
sys.path.insert(0,str(REPO/'common/illum'))
import generator.build as ib
import generator.plates as ip
import furniture as fu

spec=importlib.util.spec_from_file_location('inherited_illustration',INTER/'illustrated/build.py')
ill=importlib.util.module_from_spec(spec);spec.loader.exec_module(ill)
spec=importlib.util.spec_from_file_location('matricis_cipher',REPO/'books/01_matricis/generator/cipher.py')
cipher=importlib.util.module_from_spec(spec);spec.loader.exec_module(cipher)

ROMAN=['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII','XIII','XIV','XV','XVI','XVII']
ip.ROMAN=ROMAN
PW,PH=504,720
PAPER=colors.HexColor('#ede6d4');INK=colors.HexColor('#161918');RED=colors.HexColor('#a32b24')
ASSETS={e['name']:e for e in json.loads((ROOT/'assets/figures.json').read_text())}
INSCRIPTIONS=[
    'who may change the instruction', 'name the invariant before the trial',
    'the substrate still spends time', 'record the fire beneath the vessel',
    'two copies may preserve one omission', 'a stored route is not a passage',
    'follow the bypass to its destination', 'the clock does not name the cause',
    'who maintains the refuge', 'the decision precedes the vote',
    'the bell preserves only its hour', 'the measure enters the measured room',
    'the added question must earn its place', 'visibility is not delegation',
    'care is not earned by contribution', 'no final keeper is entered',
    'the inventory may itself be revised']
ill.R=lambda name:str(ROOT/'assets'/ASSETS[name]['asset'])
PDF_NAME='Clavicula_Matricis_et_Intervallorum.pdf'
STYLES={}

# Plates restored from the Matricis source edition are mounted, not redrawn: the
# drawn board and its own labels are taken from the e-reader leaf as vector or
# raster objects, clipped below that leaf's running head and title. Clips are in
# the source page's top-down points; the combined furniture supplies the rest.
MATRICIS_PDF=REPO/'books/01_matricis/pdf/Clavicula_Matricis_ereader.pdf'
MOUNTS={
    'matricis-i':dict(page=4,clip=(40,96,406,500),dark=False,source='Clavicula Matricis, Tabula I'),
    'matricis-vii':dict(page=30,clip=(40,96,406,500),dark=False,source='Clavicula Matricis, Tabula VII'),
    'matricis-viii':dict(page=32,clip=(40,108,406,478),dark=False,source='Clavicula Matricis, Tabula VIII'),
    'matricis-x':dict(page=44,clip=(52,74,395,488),dark=False,source='Clavicula Matricis, Tabula X'),
    'matricis-xiii':dict(page=55,clip=(47,72,399,575),dark=True,source='Clavicula Matricis, Tabula XIII'),
}
MOUNT_AREA=(40,150,464,598)   # top-down page points between the inscription and the plate rule
# The inherited renderer fits a 750 x 1050 pt plate (1000 x 1400 units) to the page.
_S=min(486/750,680/1050);_UNIT=.75*_S;_OX=(PW-750*_S)/2;_OY=PH-((PH-1050*_S)/2-2)-1050*_S


def mount_rect(spec):
    x0,y0,x1,y1=spec['clip'];ax0,ay0,ax1,ay1=MOUNT_AREA
    s=min((ax1-ax0)/(x1-x0),(ay1-ay0)/(y1-y0));w,h=(x1-x0)*s,(y1-y0)*s
    left=(ax0+ax1-w)/2;top=(ay0+ay1-h)/2
    return fitz.Rect(left,top,left+w,top+h)


def mount_frame(p,spec):
    # A hairline mount, drawn in plate units, three points outside the leaf.
    r=mount_rect(spec);u=lambda x,y:((x-_OX)/_UNIT,(y-_OY)/_UNIT)
    (a,b),(c,d)=u(r.x0-3,r.y0-3),u(r.x1+3,r.y1+3)
    p.path([(a,b),(c,b),(c,d),(a,d)],weight='hair',closed=True)


def mount_originals(pdf,placements):
    """Lay each restored Matricis board onto its plate page."""
    src=fitz.open(MATRICIS_PDF);doc=fitz.open(pdf);records=[]
    for page,plate in placements:
        spec=MOUNTS[plate];r=mount_rect(spec)
        doc[page-1].show_pdf_page(r,src,spec['page']-1,clip=fitz.Rect(spec['clip']))
        records.append(dict(page=page,plate=plate,source=spec['source'],source_page=spec['page'],clip=list(spec['clip']),rect=[round(v,2) for v in r]))
    tmp=Path(str(pdf)+'.tmp');doc.save(tmp,garbage=3,deflate=True,no_new_id=True);doc.close();src.close()
    tmp.replace(pdf)
    return records


def fonts():
    ib.register_fonts();fu.fonts()
    STYLES.update(
        body=ParagraphStyle('CombinedBody',fontName='Body',fontSize=12.1,leading=16.3,textColor=INK,spaceAfter=13),
        note=ParagraphStyle('CombinedNote',fontName='BodyItalic',fontSize=10.8,leading=14.4,textColor=colors.HexColor('#5a4331'),spaceAfter=11),
        small=ParagraphStyle('CombinedSmall',fontName='Body',fontSize=9.6,leading=12.6,textColor=colors.HexColor('#5a4331'),spaceAfter=10),
        ref=ParagraphStyle('CombinedReference',fontName='Body',fontSize=10.5,leading=14.1,textColor=INK,spaceAfter=9),
        heading=ParagraphStyle('CombinedHeading',fontName='Title',fontSize=25,leading=29,textColor=INK,spaceAfter=20))


def markup(s):
    s=html.escape(s)
    s=re.sub(r'^\[([EDHVF])\]',r'<font name="Mono" size="7.5" color="#a32b24">[\1]</font>',s)
    return re.sub(r'\[([A-Z]\d+)\]',r'<link href="#ref-\1" color="#a32b24">[\1]</link>',s)


class Book:
    def __init__(self,path,book):
        self.c=Canvas(str(path),pagesize=(PW,PH),invariant=1,pageCompression=1)
        self.c.setTitle(book['title']);self.c.setAuthor(book['author'])
        self.c.setSubject(book['strap']+'; combined reading edition')
        self.pages=[];self.overflows=[];self.bounds=[]

    def start(self,title,key=None,outline=None,level=0):
        c=self.c;c.setFillColor(PAPER);c.rect(0,0,PW,PH,fill=1,stroke=0)
        fu.specks(c,PW,PH,'combined-'+str(c.getPageNumber()),n=36,color=(221,207,178))
        c.setStrokeColor(colors.HexColor('#8e7b5f'));c.setLineWidth(.45);c.line(38,679,466,679)
        c.setFont('Small',8);c.setFillColor(INK);c.drawString(40,690,'MATRICIS ET INTERVALLORUM')
        c.setFont('Small',8);c.setFillColor(RED);c.drawRightString(464,690,title.upper())
        c.setFont('Small',9);c.setFillColor(colors.HexColor('#756b57'));c.drawCentredString(PW/2,24,str(c.getPageNumber()))
        if key:
            c.bookmarkPage(key)
            if outline:c.addOutlineEntry(outline,key,level=level,closed=False)
        self.pages.append(dict(page=c.getPageNumber(),title=title,key=key))

    def text(self,s,x,y,w,style='body'):
        p=Paragraph(markup(s),STYLES[style]);_,h=p.wrap(w,10000)
        bottom=y-h
        if bottom<49:self.overflows.append(dict(page=self.c.getPageNumber(),bottom=bottom,text=s[:70]))
        p.drawOn(self.c,x,bottom)
        self.bounds.append(dict(page=self.c.getPageNumber(),box=[x,bottom,x+w,y],kind=style))
        return bottom-STYLES[style].spaceAfter

    def heading(self,s,y=631):return self.text(s,52,y,400,'heading')
    def end(self):self.c.showPage()
    def finish(self):
        if self.overflows:raise ValueError(json.dumps(self.overflows,indent=2))
        self.c.save()


class Plate(ip.Plate):
    def __init__(self,ch,unnumbered=False):
        self.combined_number=ch['number'];self.unnumbered=unnumbered
        mount=MOUNTS.get(ch['plate']) if isinstance(ch['plate'],str) else None
        self.source_number=ch['plate'] if isinstance(ch['plate'],int) else 1
        source=copy.deepcopy(ch);source['number']=self.source_number
        super().__init__(source,dark=ch['plate']==12 or bool(mount and mount['dark']))
        if unnumbered:return   # an unnumbered plate carries no table inscription
        s=INSCRIPTIONS[self.combined_number-1];size=12
        cipher.write(self.hand,s,(1000-cipher.measure(s,size))/2,240,size,rail=True,jit=False)

    def text(self,x,y,text,size=20,face='roman',color='ink',align='left'):
        if text=='Clavicula Intervallorum':text='Matricis et Intervallorum'
        if self.unnumbered:
            if y==36 and text.startswith('Tabula '):text='Sine numero'
            if y==1347:return
        elif y==36 and text.startswith('Tabula '):text='Tabula '+ROMAN[self.combined_number-1]
        if y==1347:text=ROMAN[self.combined_number-1].lower()
        if y==145:
            size=min(size,820/max(1,len(text))/.44)
        if self.source_number==4 and y==1135:return
        return super().text(x,y,text,size,face,color,align)


def question(p):
    for x,head,lines,mark in [(200,'INFERENCE',['within the model'],1),(500,'CRITICISM',['about the model'],7),(800,'CONSTITUTION',['goals / membership'],11)]:
        p.seal(x,350,48,mark);p.text(x,445,head,23,'small',align='center')
        p.lines(x,485,lines,21,'italic',align='center')
        p.arrow([(x,525),(x,600),(500,700)])
    p.circle(500,756,55);p.text(500,763,'?',42,align='center')
    p.text(500,870,'WHO CAN CHANGE THE INSTRUCTION?',28,'small',align='center')
    for x,head in [(230,'BENEFIT'),(500,'BURDEN'),(770,'STANDING')]:
        p.box(x-105,948,210,86);p.text(x,999,head,24,'small',align='center')
    p.text(500,1120,'THE CENTRE IS NOT A FINAL JUDGE',22,'italic',color='red',align='center')


def outage(p):
    stages=[(325,'DIAGNOSIS'),(520,'AUTHORIZATION'),(740,'DISPATCH'),(965,'REPAIR')]
    for y,label in stages:
        p.box(360,y-34,280,68,double=label=='AUTHORIZATION')
        p.text(500,y+9,label,25,'small',align='center')
    for (y,_),(nxt,_) in zip(stages,stages[1:]):p.arrow([(500,y+38),(500,nxt-42)])
    p.lines(180,508,['disputed','instruction'],24,'italic',align='center')
    p.dash([(280,520),(345,520)])
    p.arrow([(650,325),(805,325),(805,740),(650,740)],'red')
    p.lines(805,545,['proposed','standing','dispatch'],23,'hand','red',align='center')
    p.text(500,1082,'ACCESS / STAFF / EQUIPMENT / SAFE WORK',22,'small',align='center')
    p.box(335,1110,330,62);p.text(500,1150,'TRIAL NOT YET ENTERED',21,'small',align='center')


def measure(p):
    nodes=[(240,370,'MEASURE'),(760,370,'DECISION'),(760,660,'BEHAVIOR'),(240,660,'OBSERVATION')]
    for x,y,label in nodes:p.box(x-140,y-40,280,80);p.text(x,y+9,label,25,'small',align='center')
    p.arrow([(390,370),(610,370)],'red');p.arrow([(760,420),(760,610)],'red')
    p.arrow([(610,660),(390,660)],'red');p.arrow([(240,610),(240,420)],'red')
    p.lines(500,510,['the next observation','has a changed setting'],24,'italic',align='center')
    for y,label in [(850,'CONSEQUENTIAL POWER'),(1010,'EFFECTIVE CORRECTION')]:
        p.text(120,y,label,24,'small');p.line(120,y+55,880,y+55,weight='hair')
        for x in range(120,881,95):p.line(x,y+47,x,y+63,weight='hair')
        p.text(880,y+103,'separate units / no quotient',19,'italic',align='right')
    p.text(500,1163,'REGISTER A CLAIM; DO NOT INVENT A SCORE',22,'small',color='red',align='center')


def bindings(p):
    for n in range(10):
        a=-math.pi/2+n*2*math.pi/10;x=500+300*math.cos(a);y=610+280*math.sin(a)
        p.circle(x,y,39);p.text(x,y+8,str(n+1),24,'small',align='center')
        p.dash([(x+(500-x)*.17,y+(610-y)*.17),(500+(x-500)*.36,610+(y-610)*.36)],'sep')
    p.lines(500,587,['NO STANDING','EARNED BY UTILITY'],27,'small',align='center')
    for x,label in [(230,'REBUILD IN TIME'),(500,'IMPOSED LOSS'),(770,'SUBSTITUTE')]:
        p.circle(x,1012,45);p.line(x,1012,x+25,980,'red')
        p.text(x,1094,label,21,'small',align='center')
    p.text(500,1160,'THREE QUESTIONS / NO COMMON UNIT',22,'italic',color='red',align='center')


def questions(p):
    rows=['ACCOUNTABLE RECEPTION','REPRESENTATION','RETENTION','OWNERSHIP','ALLOCATION']
    for i,label in enumerate(rows):
        y=335+i*164;p.text(95,y,label,22,'small')
        p.arrow([(95,y+34),(575,y+34)],'ink')
        p.box(620,y-9,260,86);p.text(750,y+45,'?',36,align='center')
    p.text(500,1166,'NO FINAL KEEPER IS ENTERED',24,'italic',color='red',align='center')


DRAWERS={'question':question,'outage':outage,'measure':measure,'bindings':bindings,'questions':questions}


def interleaf_chapter(il):
    return dict(number=il['after'],title=il['title'],deck=il['deck'],fiction='',caption=il['caption'],plate=il['plate'])


def interleaf_paths(book,out):
    paths={}
    for il in book.get('interleaves',[]):
        p=Plate(interleaf_chapter(il),unnumbered=True);mount_frame(p,MOUNTS[il['plate']])
        path=out/f'interleaf-{il["key"]}.svg';p.finish(path);paths[il['key']]=path
    return paths


def plate_paths(book,out):
    out.mkdir(parents=True,exist_ok=True);paths=[]
    for ch in book['chapters']:
        p=Plate(ch);source=ch['plate']
        if source in MOUNTS:mount_frame(p,MOUNTS[source])
        else:(ip.DRAWERS[source-1] if isinstance(source,int) else DRAWERS[source])(p)
        if ch['title']=='Of the Second Copy':
            # An omission passed between copies, outside the memory network.
            p.box(170,1080,170,55);p.box(660,1080,170,55);p.arrow([(370,1107),(630,1107)],'red')
            p.text(500,1170,'THE UNCHECKED BLANK PASSES BETWEEN COPIES',19,'italic',align='center')
        p.n=ch['number'];p.chapter=ch
        path=out/f'tabula-{ch["number"]:02d}.svg';p.finish(path);paths.append(path)
    return paths


def render_plate(b,path,ch):
    # The inherited PDF renderer preserves precise vector geometry and real type.
    ib.render_plate=ib_render
    ib_render(b,path)
    source=ch['plate']
    if source not in ill.FIGURES:return
    f=ill.FIGURES[source];name=Path(f['src']).stem
    meta=ASSETS[name];src=ROOT/'assets'/meta['asset']
    # Same 1000 x 1400 transform as the inherited renderer, whose SVG is 750 x 1050 pt.
    k=min(486/1000,680/1400);x=(PW-1000*k)/2;y=(PH-1400*k)/2-2
    X=lambda a:x+a*k;Y=lambda a:y+(1400-a)*k
    c=b.c
    if f['vignette']:
        x0,y0,x1,y1=f['vignette'];c.setFillColor(PAPER);c.roundRect(X(x0),Y(y1),(x1-x0)*k,(y1-y0)*k,4,fill=1,stroke=0)
    x0,y0,x1,y1=f['box'];bx0,by0,bx1,by1=meta['figure_bbox_px'];W,H=meta['size']
    s=min((x1-x0)*k/(bx1-bx0+1),(y1-y0)*k/(by1-by0+1))
    fx=X(x0)+((x1-x0)*k-(bx1-bx0+1)*s)/2
    fy=Y(y1)+((y1-y0)*k-(by1-by0+1)*s)/2
    c.saveState();c.setBlendMode('Multiply')
    c.drawImage(str(src),fx-bx0*s,fy-(H-1-by1)*s,W*s,H*s)
    c.restoreState()


# The illustration module installs its renderer; load the original explicitly so
# figure boxes are placed once, after the vector drawer has reserved their space.
spec=importlib.util.spec_from_file_location('plain_intervallorum_build',INTER/'generator/build.py')
plain=importlib.util.module_from_spec(spec);spec.loader.exec_module(plain)
ib_render=plain.render_plate


def front(b,book):
    b.start('The work and its intervals','title',book['title']);c=b.c
    c.setFillColor(INK);c.setFont('Title',38);c.drawCentredString(PW/2,555,'Clavicula Matricis')
    c.setFont('TitleItalic',30);c.drawCentredString(PW/2,513,'et Intervallorum')
    b.text(book['subtitle'],106,465,292,'note')
    fu.rope_frame(fu.Hand(c,random.Random(410),amp=.1),90,205,414,403,gap=3,corner=7,hatch=2)
    # One open device in the inherited hand, never a closed seal of agreement.
    h=fu.Hand(c,random.Random(411),amp=.12)
    fu.marks.sig_mark(h,PW/2,310,44,'ink','orn')
    b.text('Seventeen tables of correction, maintenance,\nand contested purpose',121,170,262,'note')
    b.end()

    b.start('The maintained workshop','frontispiece','The Maintained Workshop')
    c.drawImage(str(ROOT/'assets/the-maintained-workshop.jpg'),31,80,442,589.33,preserveAspectRatio=True,anchor='c')
    b.text('[F] One hand checks the instrument. Another keeps the room warm.',63,65,378,'small');b.end()

    for part in range(2):
        b.start('Index of the tables','index' if part==0 else None,'Index of the Tables' if part==0 else None)
        y=b.heading('Index of the Tables' if part==0 else 'The Tables, continued')
        for ch in book['chapters'][part*9:(part+1)*9]:
            c.setFillColor(RED);c.setFont('Small',12);c.drawString(52,y-12,ROMAN[ch['number']-1])
            c.setFillColor(INK);c.setFont('Title',14);c.drawString(103,y-12,ch['title'])
            c.linkRect('',f'plate-{ch["number"]}',(49,y-23,462,y+5),thickness=0)
            y=b.text(ch['deck'],103,y-24,349,'small')-9
        if part==1:b.text('Each table has two reading leaves. An unnumbered plate, Of an Analogy Taken to Its Limit, stands with one leaf before Table XVII. Source keys resolve in one register at the end. The earlier volumes remain as source editions; this is their consolidated reading text.',52,126,400,'note')
        b.end()

    b.start('Proem','proem','Proem');y=b.heading('The work and the interval')
    for s in [
        'The keeper receives two instructions: make the instrument answer when it is wrong; keep enough of the workshop alive for an answer to matter. These instructions can compete. A room preserved against change can prevent correction. A correction that spends every reserve can leave no one able to continue.',
        'The tables investigate who knows enough to act, who may authorize action, who can challenge a decision, and who bears its consequences. Clocks, gates, vessels and offices give those questions a form. Their invented history belongs to the artwork; their resemblance does not establish one mechanism across the domains compared.',
        'The first question concerns purpose and the authority to revise it. The next tables ask what preservation keeps, what waiting costs, and which routes remain usable. Later tables follow a report toward a decision, inspect the effect of measures, and record the commitments and disagreements a calculation cannot settle.',
        'Existing safety, maintenance and governance practices supply many of the questions here. The proposed instruments have not demonstrated an advantage over competent review. Their hypotheses remain open; the historical arguments, ethical commitments and artwork require their own grounds. A shared binding does not turn them into one validated theory.',
        'Read a plate as a proposed account. Read its two leaves for the claim, the limits, and the observation that could change it. Where no receiving authority, workable alternative, or agreed measure is known, the book leaves the absence visible.'
    ]:y=b.text(s,52,y,400)
    b.end()

    b.start('The hands and their limits','reader','The Hands and Their Limits');y=b.heading('Reading the hands')
    for k,v in book['evidence_key'].items():y=b.text(f'[{k}] {v}',52,y,400)
    for s in [
        'Black records an arrangement. Red marks an intervention or a question. Neither color certifies an outcome. The plate quantities are illustrative unless a source is identified; no copied experimental data are concealed in ornament.',
        'The twelve-mark hand names diagram questions. Matricis and Intervallorum named its signs differently; each plate writes the name it uses, and the sheet mounted at Table XVII keys the Matricis readings. Tables I, VIII, XV and XVII and the unnumbered plate are mounted from the Matricis edition. The separate Matricis cipher is a substitution alphabet; its key and literal readings appear after the tables. Neither alphabet is a revealed language. A reserved blank contains no omitted answer.',
        'Inspection notes distinguish inherited accounts from newly read sources. The six-case exercise and expanded follow-up were retrospective development work; neither executed the independent three-arm comparison. Their overlap with ordinary review establishes no added advantage, and their unrun comparison establishes no measured null effect.'
    ]:y=b.text(s,52,y,400,'note')
    b.end()


def glyph_key(b):
    b.start('Cipher key','cipher','The Cipher and Its Readings');y=b.heading('The cipher hand')
    y=b.text('The legacy Matricis alphabet is retained without a new mapping. Each base sign below has its Latin reading. These signs are separate from the twelve diagram marks. This edition writes only lowercase letters and spaces in its two inscriptions.',52,y,400,'note')
    for i,ch in enumerate('abcdefghijklmnopqrstuvwxyz'):
        col=i%13;row=i//13;x=57+col*30;y0=493-row*90
        h=fu.Hand(b.c,random.Random(720+i),amp=.04)
        # Original cipher uses a y-down drawing hand. Mirror its local coordinates
        # into the PDF so terminals, descenders, and word rails stay intact.
        b.c.saveState();b.c.translate(0,y0*2);b.c.scale(1,-1)
        cipher.glyph_only(h,ch,x,y0,18,'orn','ink');b.c.restoreState()
        b.c.setFont('BodyItalic',10);b.c.setFillColor(INK);b.c.drawCentredString(x+6,y0-27,ch)
    sentences=['a sketch prompts a claim and never replaces one','a stored possibility is not yet an available act']
    records=[]
    for i,s in enumerate(sentences):
        baseline=300-i*92;size=min(10,394/cipher.measure(s,1));h=fu.Hand(b.c,random.Random(840+i),amp=.03)
        b.c.saveState();b.c.translate(0,baseline*2);b.c.scale(1,-1)
        cipher.write(h,s,55,baseline,size,weight='orn',color='ink',rail=True,jit=False)
        b.c.restoreState();b.text(s,55,baseline-24,394,'note')
        records.append(dict(plaintext=s,normalized=cipher.clean(s),advance=cipher.measure(s,size),size=size))
    b.text('The literal readings are supplied beside the inscriptions. No digit, punctuation mark, or terminal is required to carry an unstated claim.',52,105,400,'small');b.end()
    b.start('Inscriptions of the tables','inscriptions','Inscriptions of the Tables')
    y=b.heading('The table inscriptions')
    y=b.text('The line above each plate is written in the legacy cipher. These are its literal readings, in table order. The Latin words are the reading key; they add no hidden operational instruction.',52,y,400,'note')
    for i,s in enumerate(INSCRIPTIONS):
        y=b.text(ROMAN[i]+'. '+s,52,y,400,'ref')-2
        records.append(dict(table=i+1,plaintext=s,normalized=cipher.clean(s),advance=cipher.measure(s,12),size=12,plate_units=True))
    b.end()
    return records


def appendices(b,book):
    b.start('The executable specimen','model','The Executable Specimen');y=b.heading('A small exact model')
    for s in [
        '[D] The inherited specimen evaluates one target at a time in a finite acyclic task graph. Tasks have nonnegative duration and cost, release time, completion deadline, availability, and AND prerequisites. Shared ancestors count once. Independent tasks may overlap with unlimited parallel capacity. A total budget is checked separately.',
        '[D] Earliest finish equals the latest of now, release, and prerequisite finishes, plus duration. Induction over the graph gives the earliest attainable completion under these assumptions. If it misses a deadline, a later schedule cannot meet it. This arithmetic does not discover the tasks or establish their real-world necessity.',
        '[D] Reading for two units and staffing for three may overlap. Approval taking six after reading, followed by two for restoration, finishes at ten. Shorten approval to one and the finish is five. Release approval only at time eight and the finish is eleven, missing a deadline of ten.',
        '[D] The model omits resource contention, OR prerequisites, uncertainty, preemption, and outputs that expire before a dependent use. Completion by a credential deadline does not establish its later validity. A feasible output is a witness for this model alone.',
        '[H] Run the existing reachability tests and compare the model with the case before using its output. Unknown is not unavailable. A well-defined calculation can remain the wrong description.'
    ]:y=b.text(s,52,y,400)
    b.end()
    guide=book['notation_guide']
    b.start('The notation guide','notation-guide','The Notation Guide');y=b.heading(guide['title'])
    for s in guide['paragraphs']:y=b.text(s,52,y,400)
    b.end()
    cipher_records=glyph_key(b)
    sys.path.insert(0,str(REPO/'binding'))
    import backmatter
    records=backmatter.opening_records(book)
    notes=[dict(title='Preparation and authorship',paragraphs=[book['edition']+'.',*book['production_notes']])]
    apparatus=backmatter.write(b.c,records,notes,b.c.getPageNumber(),REPO,local_book='I-II')
    b.pages.extend(apparatus['pages'])
    return cipher_records



def markdown(book,out):
    rows=['# '+book['title'],'',book['subtitle'],'']
    for ch in book['chapters']:
        rows+=['## '+ROMAN[ch['number']-1]+'. '+ch['title'],'',ch['deck'],'','> '+ch['fiction'],'','**Reading the plate.** '+ch['caption'],'']
        for pg in ch['pages']:
            rows+=['### '+pg['title'],'']
            for s in pg['paragraphs']:rows+=[s,'']
        for il in book.get('interleaves',[]):
            if il['after']!=ch['number']:continue
            rows+=['## Unnumbered plate. '+il['title'],'',il['deck'],'','**Reading the plate.** '+il['caption'],'','### '+il['reading_title'],'']
            for s in il['paragraphs']:rows+=[s,'']
    rows+=['## '+book['notation_guide']['title'],'']
    for s in book['notation_guide']['paragraphs']:rows += [s,'']
    rows+=['## Reference register','']
    for ref in book['references']:rows += ['### ['+ref['id']+'] '+ref['citation'],'',ref['status'],'',ref['use'],'',ref['url'],'']
    rows+=['## Further reading carried forward','']+sum(([s,''] for s in book['further_reading']),[])
    rows+=['## Production and preparation notes','',book['edition'],'']+sum(([s,''] for s in book['production_notes']),[])
    (ROOT/'manuscript/reading-edition.md').write_text('\n'.join(rows))


def validate(path,manifest):
    d=fitz.open(path);assert len(d)==len(manifest['pages'])
    assert len(manifest['chapters'])==17
    for p in d:
        assert p.rect.width==504 and p.rect.height==720
        for block in p.get_text('dict')['blocks']:
            for line in block.get('lines',[]):assert p.rect.contains(fitz.Rect(line['bbox'])),(p.number,line)
    text='\n'.join(p.get_text() for p in d)
    normalized=lambda s:re.sub(r'[^a-z0-9]','',s.lower())
    for paragraph in json.loads((ROOT/'manuscript/book.json').read_text())['notation_guide']['paragraphs']:
        assert normalized(paragraph) in normalized(text),'lost notation guide paragraph'
    assert 'Of the Borrowed Face' not in text and 'Vis Maior\nor' not in text
    for ch in manifest['chapters']:
        assert ch['title'] in d[ch['plate_page']-1].get_text()
        for n in ch['reading_pages']:assert d[n-1].get_text().strip()
    assert sum(len(p.get_images())>0 for p in d)>=6
    # Each restored board is present on its page with the labels it carried.
    src=fitz.open(MATRICIS_PDF)
    for m in manifest['mounts']:
        want=' '.join(src[m['source_page']-1].get_textbox(fitz.Rect(m['clip'])).split())
        got=' '.join(d[m['page']-1].get_text().split())
        assert want and want[:40] in got,(m['page'],want[:40])
    assert {m['plate'] for m in manifest['mounts']}==set(MOUNTS)
    for il in manifest['interleaves']:
        assert il['title'] in d[il['plate_page']-1].get_text()
    refs=[p.number+1 for p in d if 'BIBLIOGRAPHY' in p.get_text() or 'PRODUCTION NOTES' in p.get_text()]
    assert refs and refs==list(range(min(refs),len(d)+1))
    for r in manifest['cipher_readings']:
        assert r['plaintext']==r['normalized'] and r['advance']<=(800 if r.get('plate_units') else 394)
        assert set(r['normalized']) <= set(cipher.G)|{' '}
    return dict(pages=len(d),tables=17,trim=[504,720],overflow=0,cipher_readings=len(manifest['cipher_readings']),source_register_at_end=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=ROOT/'out');args=p.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    book=json.loads((ROOT/'manuscript/book.json').read_text());fonts()
    caps=json.loads((INTER/'illustrated/captions.json').read_text())
    for ch in book['chapters']:
        if str(ch['plate']) in caps:ch['caption']=caps[str(ch['plate'])]
    paths=plate_paths(book,out/'plates');leaves=interleaf_paths(book,out/'plates')
    b=Book(out/PDF_NAME,book);front(b,book);chapters=[];interleaves=[];placements=[]
    for ch,path in zip(book['chapters'],paths,strict=True):
        n=ch['number'];plate_page=b.c.getPageNumber()
        b.start('',f'plate-{n}',ROMAN[n-1]+' - '+ch['title']);render_plate(b,path,ch);b.end();read=[]
        if ch['plate'] in MOUNTS:placements.append((plate_page,ch['plate']))
        for j,pg in enumerate(ch['pages']):
            read.append(b.c.getPageNumber());b.start('Table '+ROMAN[n-1]+' / Reading '+str(j+1),f'read-{n}-{j}',pg['title'],1)
            y=b.heading(pg['title'])
            for s in pg['paragraphs']:y=b.text(s,52,y,400)
            if j==0:y=b.text('READING THE PLATE. '+ch['caption'],52,y-4,400,'small')
            else:y=b.text('Source trail: '+', '.join('['+r+']' for r in ch['sources'])+'. Limits are recorded at the end.',52,y-5,400,'small')
            b.end()
        chapters.append(dict(number=n,title=ch['title'],plate_page=plate_page,reading_pages=read))
        for il in book.get('interleaves',[]):
            if il['after']!=n:continue
            # An unnumbered plate and one reading leaf; the following table keeps its place.
            page=b.c.getPageNumber();k=il['key']
            b.start('',f'plate-{k}','Unnumbered plate - '+il['title']);render_plate(b,leaves[k],interleaf_chapter(il));b.end()
            placements.append((page,il['plate']));reading=b.c.getPageNumber()
            b.start('Unnumbered plate / Reading',f'read-{k}',il['reading_title'],1);y=b.heading(il['reading_title'])
            for s in il['paragraphs']:y=b.text(s,52,y,400)
            y=b.text('READING THE PLATE. '+il['caption'],52,y-4,400,'small')
            y=b.text('Source trail: '+', '.join('['+r+']' for r in il['sources'])+'. Limits are recorded at the end.',52,y-5,400,'small')
            b.end();interleaves.append(dict(key=k,title=il['title'],plate_page=page,reading_pages=[reading]))
    cipher_readings=appendices(b,book);b.finish();mounts=mount_originals(out/PDF_NAME,placements);markdown(book,out)
    dependencies={Path(__file__),ROOT/'manuscript/book.json',INTER/'illustrated/captions.json',MATRICIS_PDF,*sorted((ROOT/'assets').glob('*'))}
    for module in list(sys.modules.values()):
        path=getattr(module,'__file__',None)
        if path:
            path=Path(path).resolve()
            if path.is_relative_to(REPO) and path.suffix=='.py':dependencies.add(path)
    dependencies.update(INTER/'fonts'/name for name in ib.FACES.values())
    dependencies.update(p for p in (REPO/'common/fonts').glob('*.ttf'))
    inputs={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dependencies) if p.is_file()}
    manifest=dict(title=book['title'],source_commit=book['source_commit'],pages=b.pages,chapters=chapters,interleaves=interleaves,mounts=mounts,
                  cipher_readings=cipher_readings,input_sha256=inputs,pdf_sha256=hashlib.sha256((out/PDF_NAME).read_bytes()).hexdigest())
    result=validate(out/PDF_NAME,manifest);manifest['validation']=result
    (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
