#!/usr/bin/env python3
"""Build the book, standalone HTML, SVG plates, and an input provenance manifest.

Run from any working directory: python /path/to/repo/generator/build.py
No browser, network, hosted canvas runtime, or external PDF executable is used.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict
import hashlib
import html
import io
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generator.plates import build_plates, ROMAN, ROOT as PLATE_ROOT
from generator.reachability import specimen_cases

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

PW,PH=504,720
PAPER=colors.HexColor('#eee6d4')
INK=colors.HexColor('#28251e')
RED=colors.HexColor('#9c392d')
SEPIA=colors.HexColor('#756b57')
FACES={'Body':'static/EBGaramond-Regular400.ttf','BodyItalic':'static/EBGaramond-Italic400.ttf',
       'Title':'IMFeENrm28P.ttf','TitleItalic':'IMFeENit28P.ttf','Small':'IMFeENsc28P.ttf',
       'Mono':'IBMPlexMono-Regular.ttf','Hand':'SueEllenFrancisco-Regular.ttf'}
STYLES={}


def register_fonts():
    for name,file in FACES.items():pdfmetrics.registerFont(TTFont(name,str(ROOT/'fonts'/file)))
    pdfmetrics.registerFontFamily('Body',normal='Body',bold='Body',italic='BodyItalic',boldItalic='BodyItalic')
    STYLES.update(
        body=ParagraphStyle('Body',fontName='Body',fontSize=12.3,leading=16.7,textColor=INK,spaceAfter=13),
        small=ParagraphStyle('Small',fontName='Body',fontSize=10.1,leading=13.6,textColor=SEPIA,spaceAfter=10),
        note=ParagraphStyle('Note',fontName='BodyItalic',fontSize=11,leading=14.5,textColor=SEPIA,spaceAfter=9),
        heading=ParagraphStyle('Heading',fontName='Title',fontSize=24,leading=29,textColor=INK,spaceAfter=17),
        ref=ParagraphStyle('Reference',fontName='Body',fontSize=10.5,leading=14.1,textColor=INK,spaceAfter=10),
    )


def markup(s):
    s=html.escape(s)
    s=re.sub(r'^\[([EDHVF])\]',r'<font name="Mono" size="8" color="#9c392d">[\1]</font>',s)
    return re.sub(r'\[([A-Z][0-9])\]',r'<link href="#ref-\1" color="#9c392d">[\1]</link>',s)


class Book:
    def __init__(self,path,metadata):
        self.c=Canvas(str(path),pagesize=(PW,PH),invariant=1,pageCompression=1)
        self.c.setTitle(metadata['title']);self.c.setAuthor(metadata['author'])
        self.c.setSubject(metadata['strap']+'; first divergent edition; conditional theory and fictional plates')
        self.c.setCreator('Portable Python / ReportLab / original SVG geometry')
        self.pages=[]
        self.overflows=[]

    def start(self,title,key=None,outline=None,level=0):
        c=self.c;c.setFillColor(PAPER);c.rect(0,0,PW,PH,fill=1,stroke=0)
        c.setStrokeColor(SEPIA);c.setLineWidth(.45);c.line(36,679,468,679)
        c.setFillColor(INK);c.setFont('Small',8);c.drawString(38,690,'CLAVICULA INTERVALLORUM')
        c.setFillColor(RED);c.drawRightString(466,690,title.upper())
        c.setFillColor(SEPIA);c.setFont('Small',9);c.drawCentredString(PW/2,24,str(c.getPageNumber()))
        if key:
            c.bookmarkPage(key)
            if outline:c.addOutlineEntry(outline,key,level=level,closed=False)
        self.pages.append({'page':c.getPageNumber(),'title':title,'key':key})

    def end(self):self.c.showPage()

    def text(self,s,x,y,w,style='body'):
        p=Paragraph(markup(s),STYLES[style]);_,h=p.wrap(w,10000)
        if y-h<49:self.overflows.append({'page':self.c.getPageNumber(),'text':s[:90],'bottom':y-h})
        p.drawOn(self.c,x,y-h)
        return y-h-STYLES[style].spaceAfter

    def heading(self,s,y=631):return self.text(s,52,y,400,'heading')

    def finish(self):
        if self.overflows:raise ValueError('Page overflow: '+json.dumps(self.overflows))
        self.c.save()


def render_plate(b,path):
    # SVG lettering is reusable local outlines; PDF lettering uses embedded real
    # fonts, so it stays selectable and avoids thousands of repeated glyph paths.
    root=ET.fromstring(path.read_text())
    ns='{http://www.w3.org/2000/svg}'
    labels=json.loads(root.find(ns+'metadata').text)
    for child in list(root):
        if child.get('id')=='lettering':root.remove(child)
    d=svg2rlg(io.BytesIO(ET.tostring(root)))
    if d is None:raise ValueError(f'Cannot parse plate {path}')
    viewport=[float(v) for v in root.get('viewBox').split()]
    # SVG pixels are converted to points by svglib. The labels use original
    # viewBox coordinates, so apply that conversion as well as the page fit.
    source_to_point=d.width/viewport[2]
    s=min(486/d.width,680/d.height)
    d.scale(s,s);d.width*=s;d.height*=s
    x,y=(PW-d.width)/2,(PH-d.height)/2-2
    renderPDF.draw(d,b.c,x,y)
    c=b.c;c.saveState();c.translate(x,y);c.scale(s*source_to_point,s*source_to_point)
    faces={'roman':'Title','italic':'TitleItalic','small':'Small','mono':'Mono','hand':'Hand'}
    for label in labels:
        c.setFillColor(colors.HexColor(label['color']))
        c.setFont(faces[label['face']],label['size'])
        c.drawString(label['x'],viewport[3]-label['y'],label['text'])
    c.restoreState()


def front_matter(b,book,html_pages):
    b.start('First divergent edition','title',book['title'])
    c=b.c;c.setFont('Title',35);c.setFillColor(INK);c.drawCentredString(PW/2,568,book['title'])
    c.setFont('TitleItalic',18);c.setFillColor(RED);c.drawCentredString(PW/2,535,book['subtitle'])
    y=b.text(book['strap'],110,483,284,'note')
    # A restrained title device built from the open, branching spiral.
    c.setStrokeColor(INK);c.setLineWidth(.65);c.circle(PW/2,324,75,stroke=1,fill=0);c.circle(PW/2,324,70,stroke=1,fill=0)
    pts=[]
    for i in range(200):
        t=i/199;a=-math.pi/2+4.5*math.pi*t;r=4+48*t;pts.append((PW/2+r*math.cos(a),324+r*math.sin(a)))
    path=c.beginPath();path.moveTo(*pts[0])
    for pt in pts[1:]:path.lineTo(*pt)
    c.drawPath(path)
    c.setStrokeColor(RED);c.line(pts[-1][0],pts[-1][1],PW/2+84,363)
    c.setFont('Small',11);c.setFillColor(INK);c.drawCentredString(PW/2,193,'TWELVE TABLES WITH THEIR REASONS AND THEIR LIMITS')
    c.setFont('Body',12);c.drawCentredString(PW/2,160,book['author'])
    c.setFont('BodyItalic',10);c.drawCentredString(PW/2,133,book['edition'])
    c.setFont('BodyItalic',11);c.drawCentredString(PW/2,82,'A stored possibility is not yet an available act.')
    b.end()
    html_pages.append('<section class="page title" id="title"><p class="eyebrow">First divergent edition</p><h1>'+book['title']+'</h1><h2>'+book['subtitle']+'</h2><p>'+book['strap']+'</p><p class="device">&#x25cc;</p><p>'+book['author']+'</p><p>'+book['edition']+'</p><em>A stored possibility is not yet an available act.</em></section>')

    b.start('Index of the tables','index','Index of the Tables')
    y=b.heading('Index of the Tables',636)
    rows=[]
    for ch in book['chapters']:
        n=ch['number'];yy=554-(n-1)*37
        c.setFillColor(RED);c.setFont('Small',12);c.drawString(52,yy,ROMAN[n-1])
        c.setFillColor(INK);c.setFont('Title',14);c.drawString(94,yy,ch['title'])
        c.linkRect('',f'plate-{n}',(45,yy-8,463,yy+17),relative=0,thickness=0)
        rows.append(f'<li><a href="#plate-{n}">{ROMAN[n-1]} &nbsp; {html.escape(ch["title"])}</a></li>')
    b.text('Each table is followed by two reading leaves. The plates are newly drawn. Their quantities and cases are illustrative unless the text identifies an inspected source.',52,91,400,'small')
    b.end();html_pages.append('<section class="page" id="index"><h2>Index of the Tables</h2><ol class="index">'+''.join(rows)+'</ol></section>')

    b.start('How to read the object','reader','How to Read the Object')
    y=b.heading('An instrument with an invented history')
    paras=[
        'This is a divergent grimoire, developed from Clavicula Matricis. It removes The Borrowed Face and the Force Majeure tract. Its diagrams, voices, seals, and workshop traces are invented. Its interior argument is offered for criticism, with explicit limits on what follows from what.',
        'The organizing question is practical: what has to remain possible for a correction to be used? Slowing, storage, maintenance, dependency, authority, and revision enter as different parts of that question. No common biological, political, and mathematical mechanism is assumed.',
    ]
    for p in paras:y=b.text(p,52,y,400)
    for tag,desc in book['evidence_key'].items():y=b.text(f'[{tag}] {desc}',52,y,400,'small')
    y=b.text('Black records an arrangement; red proposes an intervention or a question. Neither color certifies a result. A blank trial field remains an absent trial.',52,y,400,'note')
    b.end();html_pages.append(html_text_page('reader','An instrument with an invented history',paras+[f'[{k}] {v}' for k,v in book['evidence_key'].items()]))

    b.start('The bounded connection','argument','The Bounded Connection')
    y=b.heading('A repertoire with a deadline')
    paras=[
        '[D] The precise link is a broken invariance. A change of clock can preserve whether an event ever occurs while changing whether it occurs before a deadline. With s=log(1+t), logical progress L requires t=exp(L)-1. Preserving every path therefore need not preserve any particular timely option. Nothing has to be forgotten for a capacity to become too late.',
        '[H] This edition proposes asking which alternatives are kept usable before a decision occurs. Maintenance can select the future repertoire without rewriting a voting rule. The further question is whether people also retain an effective way to contest that maintenance policy before a consequential capacity lapses.',
        '[D] The weak point is the bridge from a stated model to a real case. If the deadlines, needs, or actors are misdescribed, the calculation can be exact and the diagnosis wrong. If ordinary scheduling or incident review already finds the same thing more cheaply, the method adds no distinctive practical result.',
        '[V] Feasibility is not legitimacy. Care, non-domination, and affordable contestation are adopted constraints. A calculation cannot choose who deserves standing or whose burden is acceptable.',
        '[F] The grimoire stages these distinctions as rooms, vessels, gates, and keepers. The figures make the argument inspectable and the object entertaining. They do not lend it an ancient authority.',
    ]
    for p in paras:y=b.text(p,52,y,400)
    b.end();html_pages.append(html_text_page('argument','A repertoire with a deadline',paras))


def html_text_page(key,title,paras,caption=None):
    body=''.join('<p>'+markup(p)+'</p>' for p in paras)
    body=body.replace('<font name="Mono" size="8" color="#9c392d">','<span class="tag">').replace('</font>','</span>')
    body=re.sub(r'<link href="([^\"]+)" color="[^\"]+">',r'<a href="\1">',body).replace('</link>','</a>')
    if caption:body+='<aside>'+html.escape(caption)+'</aside>'
    return f'<section class="page" id="{key}"><h2>{html.escape(title)}</h2>{body}</section>'


def build_pdf(book,plate_paths,out):
    b=Book(out/'Clavicula_Intervallorum.pdf',book);hp=[]
    front_matter(b,book,hp)
    for ch,path in zip(book['chapters'],plate_paths,strict=True):
        n=ch['number']
        b.start('','plate-'+str(n),ROMAN[n-1]+' - '+ch['title'])
        render_plate(b,path);b.end()
        hp.append(f'<section class="page plate" id="plate-{n}">'+path.read_text()+'</section>')
        for j,pg in enumerate(ch['pages']):
            b.start('Table '+ROMAN[n-1]+' | Reading '+str(j+1),f'read-{n}-{j}',pg['title'],1)
            y=b.heading(pg['title'])
            for p in pg['paragraphs']:y=b.text(p,52,y,400)
            if j==0:
                cap='READING THE PLATE. '+ch['caption']
                # Anchored after prose; the build rejects any overflow.
                y=b.text(cap,52,y-5,400,'small')
            else:
                y=b.text('Source trail: '+', '.join('['+r+']' for r in ch['sources'])+'. Inspection limits follow in the reference register.',52,y-8,400,'small')
            b.end();hp.append(html_text_page(f'read-{n}-{j}',pg['title'],pg['paragraphs'],ch['caption'] if j==0 else None))
    appendices(b,book,hp)
    b.finish()
    return b.pages,hp


def appendices(b,book,hp):
    pages=[('model','The executable specimen',[
        '[D] The code evaluates one target at a time. Each task has a nonnegative duration and cost, a release time, a completion deadline, an availability flag, and AND prerequisites. Shared ancestors are counted once. Independent tasks can overlap without resource contention. A total budget is checked separately.',
        '[D] The recurrence is finish(v) = max(now, release(v), finishes of all prerequisites) + duration(v). If the earliest schedule violates a task deadline or the target deadline, no later schedule can meet that constraint under these assumptions. If a required task is unavailable, the plan is infeasible within the model.',
        '[D] Proof sketch. Induct over a topological order. No task can start before its release or any prerequisite finishes. Assuming each earlier completion is minimal, their maximum is the earliest possible start for the next task. Adding its duration yields its earliest finish. Unlimited parallel capacity makes these simultaneous earliest starts attainable. A shared prerequisite is a single task, not several charges.',
        '[D] The model omits shared resource capacity, alternative prerequisite sets, uncertainty, preemption, knowledge of unknown routes, and outputs that expire before a later use. Task valid_until means completion by that time only. It does not mean a credential or memory remains valid until every dependent finishes. Options are not jointly optimized.',
        '[D] Consequently a feasible result is a witness only for the declared model. An unavailable flag records an input judgment; it does not discover a fact. Use a richer model when omitted conditions are consequential.',
    ]),('research','The trial not yet performed',[
        '[H] Hypothesis 1: a count of procedures overstates usable alternatives when their required readers, resources, or decision routes have lapsed. Compare explicit dependency records with ordinary inventories on the same historical cases.',
        '[H] Hypothesis 2: maintenance decisions before a formal choice predict which alternatives can actually be attempted, after controlling for their original merits and the available resources. The claim fails in a case if supposedly lapsed alternatives remain equally usable, or if readiness does not affect the relevant choice.',
        '[H] Hypothesis 3: separating mission, structure, membership, capabilities, and accountability makes recovery descriptions more discriminating. Test independent coding and subsequent outcomes. Do not treat an attractive five-axis figure as evidence of measurement validity.',
        '[H] Controls: ordinary competent review, an equal-effort generic checklist, blind source-based judgment, declared exclusions, and comparable access to materials. Track unsupported allegations, missed mechanisms, effort, and whether recommendations could actually be acted on.',
        '[V] Begin with authorized operational records or documented history. Publish aggregate findings where people could be harmed by individual identification. None of the plates maps a living political network. No empirical trial is claimed for this edition.',
    ])]
    for key,title,paras in pages:
        b.start('Working notes',key,title);y=b.heading(title)
        for p in paras:y=b.text(p,52,y,400)
        b.end();hp.append(html_text_page(key,title,paras))
    # References flow across pages rather than shrinking to fit.
    b.start('Reference register','references','Reference Register');y=b.heading('Sources and inspection limits')
    y=b.text('The primary sources below support limited statements. Proposed connections are this edition’s synthesis; no priority claim is made. The supplied packet is not a verified systematic review. Further reading is listed separately from evidentiary support.',52,y,400,'small')
    for ref in book['references']:
        chunks=[f'[{ref["id"]}] '+ref['citation'],ref['status'],'Use: '+ref['use']]
        needed=sum(Paragraph(markup(s),STYLES['ref']).wrap(400,10000)[1]+10 for s in chunks)
        url=ref['url']
        if url:needed+=35
        if y-needed<62:
            b.end();b.start('Reference register');y=640
        b.c.bookmarkPage('ref-'+ref['id'])
        for k,s in enumerate(chunks):y=b.text(s,52,y,400,'ref' if k==0 else 'small')
        if url:
            # A short linked label remains readable even for long repository URLs.
            b.c.setFillColor(RED);b.c.setFont('Mono',8);b.c.drawString(52,y-7,'OPEN SOURCE / '+ref['id'])
            b.c.linkURL(url,(50,y-12,205,y+2),relative=0,thickness=0)
            y-=28
        y-=8
    b.end()
    htmlrefs=[]
    for ref in book['references']:
        htmlrefs.append(f'<article id="ref-{ref["id"]}"><h3>[{ref["id"]}] {html.escape(ref["citation"])}</h3><p>{html.escape(ref["status"])}</p><p>{html.escape(ref["use"])}</p>'+ (f'<a href="{html.escape(ref["url"],quote=True)}">Open source</a>' if ref['url'] else '')+'</article>')
    hp.append('<section class="page refs" id="references"><h2>Sources and inspection limits</h2>'+''.join(htmlrefs)+'</section>')
    b.start('Workshop record','workshop','Workshop Record');y=b.heading('How this object was made')
    paras=[
        'Derived from Josiah Alan-Lee’s Clavicula Matricis repository at commit '+book['source_commit'][:7]+', developed primarily with Claude. This edition uses the supplied Slow Clocks packet and a fresh primary-source check. It is a divergent artwork, not a replacement for the earlier edition.',
        'The earlier stroke and mark vocabulary is retained in the geometry tools. All twelve plate layouts and diagrams in this volume are new. No source-paper figure is reproduced. Curves and illustrative quantities are generated by code; typography uses bundled, locally loaded open fonts.',
        'The three voices remain distinct. The formal hand states the rule. The red hand proposes a measurement or intervention. The fiction records what the arrangement leaves unresolved. No claim acquires evidential status by appearing in a cipher or a seal.',
        'For orientation, the original bibliography also includes Argyris and Schön (1978), Organizational Learning; Pettit (1997), Republicanism; Kittay (1999), Love’s Labor; and Negarestani (2018), Intelligence and Spirit. These works are not used as freshly verified evidence for a particular empirical claim in this edition.',
        'The source distribution contains editable manuscript JSON and Markdown, portable plate generation, a standalone HTML reader, an input fingerprint manifest, the bounded scheduling specimen and its tests, and the inherited XI plotter exporter. New full-color SVG plates have not been prepared or tested as physical plotter paths.',
    ]
    for p in paras:y=b.text(p,52,y,400)
    b.end();hp.append(html_text_page('workshop','How this object was made',paras))


def write_html(book,pages,out):
    css=''
    for name,file in FACES.items():
        encoded=base64.b64encode((ROOT/'fonts'/file).read_bytes()).decode()
        css+=f"@font-face{{font-family:{name};src:url(data:font/ttf;base64,{encoded}) format('truetype');}}\n"
    css+='''
*{box-sizing:border-box}html{background:#bab4a6}body{margin:0;color:#28251e;font-family:Body,serif}
a{color:#9c392d}.page{width:7in;min-height:10in;margin:20px auto;padding:.65in .72in;background:#eee6d4;box-shadow:0 2px 15px #0003;break-after:page}
h1,h2,h3{font-family:Title,serif;font-weight:normal}h1{font-size:38px}h2{font-size:31px;line-height:1.15;margin:20px 0 25px}h3{font-size:18px}
p{font-size:16.4px;line-height:1.36;margin:0 0 17px}aside{font-size:13.5px;line-height:1.4;color:#756b57;margin-top:20px}.tag{font-family:Mono;font-size:11px;color:#9c392d}
.title{text-align:center;padding-top:1.5in}.title h2{font-size:25px;color:#9c392d}.title p{font-size:19px}.device{font-size:140px!important;margin:35px}
.plate{padding:0;display:flex;align-items:center;min-height:10in;height:10in}.plate svg{width:100%;height:100%}.index{list-style:none;padding:0}.index li{font-family:Title;font-size:20px;margin:0 0 15px}
.refs{height:auto}.refs p{font-size:14px}.refs article{break-inside:avoid;margin-bottom:26px}
@media(max-width:720px){.page{width:100%;min-height:auto;margin:0 0 12px;padding:8vw}.plate{padding:0;height:auto}.plate svg{height:auto}}
@media print{@page{size:7in 10in;margin:0}html{background:white}.page{margin:0;box-shadow:none;min-height:10in}.refs{height:auto}}
'''
    license_text='\n\n'.join(p.name+'\n'+p.read_text() for p in sorted((ROOT/'fonts/licenses').glob('*.txt')))
    notices='<details style="max-width:7in;margin:2em auto;padding:1em;background:#eee6d4"><summary>Bundled font notices</summary><pre style="white-space:pre-wrap;font-size:11px">'+html.escape(license_text)+'</pre></details>'
    doc='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+html.escape(book['title'])+'</title><style>'+css+'</style><body>'+''.join(pages)+notices+'</body></html>'
    # The markup helper produces PDF internal links; HTML requires ordinary anchors.
    doc=re.sub(r'<link href="([^\"]+)" color="[^\"]+">',r'<a href="\1">',doc).replace('</link>','</a>')
    (out/'Clavicula_Intervallorum.html').write_text(doc)


def write_markdown(book,out):
    lines=['# '+book['title'],'',book['subtitle'],'',book['strap'],'',book['edition'],'']
    for k,v in book['evidence_key'].items():lines+=['- ['+k+'] '+v]
    for ch in book['chapters']:
        lines+=['','## '+ROMAN[ch['number']-1]+'. '+ch['title'],'',ch['deck'],'',
                '*Tabula '+str(ch['number'])+' is generated at `output/plates/tabula-'+str(ch['number']).zfill(2)+'.svg` by the [plate builder](../generator/build.py).*','',
                '**Reading the plate.** '+ch['caption'],'','> '+ch['fiction']]
        for pg in ch['pages']:
            lines+=['','### '+pg['title'],'']
            for p in pg['paragraphs']:lines+=[p,'']
    lines+=['','## Reference register','']
    for ref in book['references']:
        lines+=[f'### [{ref["id"]}] '+ref['citation'],'',ref['status'],'',ref['use'],'',ref['url'],'']
    (ROOT/'manuscript/reading-edition.md').write_text('\n'.join(lines))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'output')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    book=json.loads((ROOT/'manuscript/book.json').read_text())
    register_fonts()
    # Generated plates live with each build, so alternate output does not mutate
    # the edition's committed plate files or depend on preexisting output.
    paths=build_plates(book,out/'plates')
    pages,hp=build_pdf(book,paths,out)
    write_html(book,hp,out);write_markdown(book,out)
    cases={k:asdict(v) for k,v in specimen_cases().items()}
    (out/'specimen-results.json').write_text(json.dumps(cases,indent=2)+'\n')
    inputs={}
    for folder in ['generator','manuscript','fonts']:
        for p in sorted((ROOT/folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='reading-edition.md':
                inputs[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    manifest={'title':book['title'],'edition':book['edition'],'upstream_commit':book['source_commit'],
              'page_count':len(pages),'pages':pages,'input_sha256':inputs,
              'claims':'No empirical validation claimed. All plate quantities are illustrative.',
              'dependencies':{}}
    from importlib.metadata import version
    for name in ['reportlab','svglib','fonttools','shapely']:manifest['dependencies'][name]=version(name)
    (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'pdf':str(out/'Clavicula_Intervallorum.pdf'),'pages':len(pages),
                      'plates':len(paths),'overflow':0},indent=2))


if __name__=='__main__':main()
