"""Next production batch: X, XI, V. Native paths, two inks, exact second texts."""
from pathlib import Path
import copy
import hashlib
import json
import math
import re
import subprocess
import xml.etree.ElementTree as E
from fontTools.svgLib.path import parse_path
from shapely.geometry import LineString,Point,box
from sheet import Drawing, HAND, NS, COLORS, f, tx
from lettering import PolyPen
from ix_codec import normalize
from ciphers import *

ROOT=Path(__file__).resolve().parent
MANUSCRIPT={}

def pts(data):
    pen=PolyPen();parse_path(data,pen)
    return [p for p in pen.lines if len(p)>1]

def arc(cx,cy,rx,ry=None,start=0,stop=360,n=120):
    ry=ry or rx
    return [(cx+rx*math.cos(math.radians(start+(stop-start)*i/n)),cy+ry*math.sin(math.radians(start+(stop-start)*i/n))) for i in range(n+1)]

def bez(p0,p1,p2,p3,n=48):
    return [tuple((1-t)**3*p0[k]+3*(1-t)**2*t*p1[k]+3*(1-t)*t*t*p2[k]+t**3*p3[k] for k in (0,1)) for t in (i/n for i in range(n+1))]

def base(number,title,sub):
    d=Drawing();d.rect(8,10,194,278,width=.18);d.line(12,31,198,31)
    d.text('CLAVICULA GRADUUM',105,18,4.1,align='center')
    d.text(sub,105,26,2.5,align='center')
    d.line(12,277,198,277)
    d.text('TABULA '+number,105,279,2.5,align='center')
    d.text(title,105,283.5,2.9,align='center')
    return d

def blank(d,x,y,w,h,label=True):
    el=d.rect(x,y,w,h,width=.18)
    if label:d.text('RESERVED',x+w/2,y+h+2.6,2.5,align='center')

def finish(d,number,slug,title,plain,blank_box,extra):
    files=[]
    for suffix,pen,layer in [('',None,None),('-black-a4','black',None),('-red-a4','red',None),('-art-only',None,'art-paths'),('-text-only',None,'text-outlines')]:
        p=ROOT/(slug+suffix+'.svg');d.write(p,pen,layer)
        r=E.parse(p).getroot()
        r.find('{'+NS+'}title').text=f'Clavicula Graduum - Tabula {number} - {title}'
        r.find('{'+NS+'}desc').text='Two inks. Stroke paths only. A4. EMS Nixish. Untested on a physical plotter. '+extra.get('description','')
        E.ElementTree(r).write(p,encoding='utf-8',xml_declaration=True)
        files.append(p.name)
    record={'number':number,'title':title,'second_text_plain':plain,'second_text_normalized':normalize(plain),
      'reserved_blank_mm':blank_box,'files':files,'physical_plotter_tested':False,**extra}
    MANUSCRIPT[number]=record
    (ROOT/(slug+'-type-audit.json')).write_text(json.dumps(d.labels,indent=2)+'\n')
    # Verify drawn blank and page bounds. Paths are line segments except the
    # deliberately retained M/L/Q carrier, which is flattened solely for QA.
    x,y,w,h=blank_box
    interior=(Point(x+w/2,y+h/2).buffer(w/2-.01) if extra.get('blank_shape')=='ring' else box(x+.01,y+.01,x+w-.01,y+h-.01))
    for layer,paths in d.paths.items():
        for el in paths:
            assert el.get('fill')=='none' and el.get('stroke') in COLORS.values()
            for line in pts(el.get('d')):
                assert all(7.8<=a<=202.2 and 9.8<=b<=288.2 for a,b in line),(slug,min(line),max(line))
                assert not LineString(line).intersects(interior),(slug,'reserved blank crossed')
    assert min(label['cap_height_mm'] for label in d.labels)>=2.5
    subprocess.run(['inkscape','--app-id-tag=graduum-'+slug,'--batch-process',str(ROOT/(slug+'.svg')),
      '--export-background=#f6f0e4','--export-background-opacity=1','--export-width=1500','--export-filename='+str(ROOT/(slug+'.png'))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    record['path_counts']={k:len(v) for k,v in d.paths.items()}
    return record

def prayer():
    d=base('X','THE PRAYER OF THE OFFICE','FORAS / STATION 0')
    # Retain the actual six-handed Foras portrait; remove old titles, tick
    # registers and the old name cipher. Every imported body strand is black.
    src=E.parse(ROOT/'source/foras.svg').getroot()
    for el in src.findall('{'+NS+'}path'):
        for line in pts(el.get('d','')):
            if min(y for x,y in line)>78 and max(y for x,y in line)<635:
                d.path([(105+(x-300)*.27,52+(y-95)*.29) for x,y in line],width=max(.12,min(.24,float(el.get('stroke-width','.6'))*.27)))
    # Sparse explicit facial anatomy sits in the source's clear face aperture.
    face=[[(290,248),(285,266),(287,286),(300,303),(312,286),(315,266),(310,248)],
          [(301,260),(298,275),(302,279),(307,277)],[(294,288),(300,286),(307,288)],
          [(296,292),(303,294),(308,291)]]
    for line in face:d.path([(105+(x-300)*.27,52+(y-95)*.29) for x,y in line],width=.18)
    # Five small instruments make the work of the source's six hands legible;
    # the lowest right hand has only the uncompleted permission request.
    for x,y in ((54,119),(154,119),(154,135)):
        d.rect(x-3,y-3,6,6,width=.14)
        d.path([(x-1.8,y),(x-.4,y+1.4),(x+2,y-1.6)],width=.14)
    d.circle(54,135,2.8,width=.14)
    for a in range(0,360,60):
        d.line(54+2.8*math.cos(math.radians(a)),135+2.8*math.sin(math.radians(a)),54+4*math.cos(math.radians(a)),135+4*math.sin(math.radians(a)),width=.14)
    d.path([(52,145),(56,151),(52,152),(52,145)],width=.14)
    # The incident remains in motion while the request stops outside the field.
    d.path(bez((151,155),(169,176),(160,214),(132,231)),'red',.23)
    d.line(132,231,130,242,'red',.23)
    blank(d,82,244,46,23,label=False)
    d.text('PERMISSION',105,270,2.5,align='center')
    for r in (5.4,7.4):d.circle(43,255,r,width=.16)
    d.line(35,255,51,255);d.line(43,247,43,263)
    d.text('04 MIN',43,269,2.5,align='center')
    d.path([(157+i*.3,255+3*math.sin(i*.22)) for i in range(70)],'red',.20)
    d.text('RUNNING',168,269,2.5,align='center')
    # Split at an actual English word boundary, represented by AMEN. Each
    # printed token is a cipher word; no pseudo-writing is retained.
    tokens=prayer_encode(FORAS_EFFECT)
    split=min((i+1 for i,t in enumerate(tokens) if t==BOUNDARY),key=lambda i:abs(i-len(tokens)/2))
    halves=(tokens[:split],tokens[split:])
    for i,words in enumerate(halves):
        x=11 if i==0 else 168
        d.text('A' if i==0 else 'B',x,42,2.5)
        step=min(4.4,178/(len(words)-1))
        for j,word in enumerate(words):
            assert HAND.width(word,2.5)<31
            d.text(word,x,51+j*step,2.5,'black')
    return finish(d,'X','x-prayer-of-the-office','The Prayer of the Office',FORAS_EFFECT,[82,244,46,23],{
       'carrier':'new 26-word office litany; fixed-column Ave Maria-style adaptation',
       'table':TABLE,'word_boundary':BOUNDARY,'cipher_tokens':tokens,'register_order':['A downward','B downward'],
       'source_effect':'Pseudomonarchia Escalationum, Foras, PDF p. 6',
       'does_not_claim':'A prayer-shaped record is neither an authorization nor evidence that a repair occurred.',
       'description':'The original Foras effect line is encoded as an office litany. The table is a new adaptation, not a historical transcription.'})

def litany_leaf():
    d=base('X','THE OFFICE LITANY / KEY','CLAVIS / NEW ADAPTATION')
    d.text('A-Z / ONE WORD PER LETTER',105,40,2.8,align='center')
    for i,(letter,word) in enumerate(TABLE.items()):
        col=i//13;row=i%13;x=27+col*90;y=56+row*10.3
        d.text(letter,x,y,3);d.text(word,x+12,y,2.8)
    d.text('AMEN = WORD BOUNDARY',105,204,2.8,'red',align='center')
    d.text('READ A DOWNWARD / THEN B DOWNWARD',105,217,2.5,align='center')
    d.text('THIS TABLE IS AN EDITORIAL CONSTRUCTION',105,231,2.5,align='center')
    d.text('NOT A TRANSCRIPTION OF TRITHEMIUS',105,239,2.5,align='center')
    d.text('PUNCTUATION IS KEPT IN THE MANUSCRIPT RECORD',105,252,2.5,align='center')
    d.text('THE EFFECT LINE MUST ACCOMPANY A COPY',105,263,2.5,'red',align='center')
    d.write(ROOT/'x-office-litany-key.svg')
    r=E.parse(ROOT/'x-office-litany-key.svg');r.getroot().find('{'+NS+'}title').text='Clavicula Graduum - office litany key'
    r.getroot().find('{'+NS+'}desc').text='New 26-word office litany, fixed-column Ave Maria-style adaptation. AMEN marks a word boundary. Not a historical transcription. Two inks, stroke paths only, A4. Untested on a physical plotter.'
    r.write(ROOT/'x-office-litany-key.svg',encoding='utf-8',xml_declaration=True)
    subprocess.run(['inkscape','--app-id-tag=graduum-litany-key','--batch-process',str(ROOT/'x-office-litany-key.svg'),'--export-background=#f6f0e4','--export-background-opacity=1','--export-width=1500','--export-filename='+str(ROOT/'x-office-litany-key.png')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def lifted_pen():
    d=base('XI','THE LIFTED PEN','THE ORDERED SPECIMEN')
    # The reserved ring remains completely clear. Red marks a question at its
    # rim; it contributes no hidden letter.
    d.circle(105,50,12,width=.18)
    d.path([(119,40),(122,40),(122,60),(119,60)],'red',.20)
    words=normalize(LIFT_TEXT).split()
    radii=[39,49,59,69,79]
    # Each word is exactly one continuous pen-down path. A straight letter run
    # is subdivided into L commands: these collinear divisions leave no visible
    # marks on paper. A Q corner terminates a letter without lifting the pen.
    for wi,(word,r) in enumerate(zip(words,radii)):
        n=len(word);phase=-math.pi/2+wi*.37
        vertices=[(105+r*math.cos(phase+2*math.pi*j/n),156+r*math.sin(phase+2*math.pi*j/n)) for j in range(n)]
        starts=[];ends=[]
        for j in range(n):
            a=vertices[j];b=vertices[(j+1)%n]
            starts.append((a[0]*.9+b[0]*.1,a[1]*.9+b[1]*.1))
            ends.append((a[0]*.1+b[0]*.9,a[1]*.1+b[1]*.9))
        data='M'+f(starts[0][0])+','+f(starts[0][1])
        for j,ch in enumerate(word):
            count=ord(ch)-64
            for k in range(1,count+1):
                a=starts[j];b=ends[j];t=k/count
                data+=' L'+f(a[0]+t*(b[0]-a[0]))+','+f(a[1]+t*(b[1]-a[1]))
            control=vertices[(j+1)%n];target=starts[(j+1)%n]
            data+=' Q'+','.join(f(v) for v in (*control,*target))
        el=E.Element('{'+NS+'}path',{'d':data,'fill':'none','stroke':COLORS['black'],'stroke-width':'.20',
             'stroke-linecap':'round','stroke-linejoin':'round','data-channel':'lifted-pen'})
        d.paths['art-paths'].append(el)
    # A restrained orbit and registration lines belong to the arrangement,
    # outside the carrier. No second readable sentence is printed here.
    for side in (-1,1):
        for y in (106,156,206):
            d.line(105+side*88,y-5,105+side*88,y+5)
            d.line(105+side*85,y,105+side*91,y)
    # Three equal printed specimens retain different source subdivision counts.
    d.line(12,245,198,245)
    for i,count in enumerate((1,13,26)):
        left=23+i*62
        d.path([(left+40*j/count,259) for j in range(count+1)],width=.20)
        d.text(('I','II','III')[i],left+20,265,2.5,align='center')
    record=finish(d,'XI','xi-lifted-pen','The Lifted Pen',LIFT_TEXT,[93,38,24,24],{
        'carrier':'document-order SVG paths; each carrier path is one word','blank_shape':'ring',
        'letter_boundary':'Q curve; count preceding L commands modulo 26, zero is Z',
        'word_boundary':'next M path; one physical pen lift between carrier word paths',
        'path_order':'SVG document order among data-channel=lifted-pen paths',
        'does_not_claim':'The plate does not claim that rasterization or arbitrary reordering preserves its second text.',
        'description':'Preserve raw M/L/Q commands and carrier path order. Collinear subdivisions are invisible on paper.'})
    # Decode the delivered master and black sheet, not an in-memory token list.
    assert ordered_decode(ROOT/'xi-lifted-pen.svg')==normalize(LIFT_TEXT)
    assert ordered_decode(ROOT/'xi-lifted-pen-black-a4.svg')==normalize(LIFT_TEXT)
    return record

def keeper_dial():
    d=base('V','THE DIAL OF SEVEN KEEPERS','TWO SCALES / NO ALIGNMENT IMPOSED')
    blank(d,17,42,40,24)
    # Reuse the reconstructed Keeper and its projected face. The crescent,
    # old typography, margins and studies are excluded, leaving the body.
    names={'black-native-chest-aperture','red-native-chest-aperture','black-native-interval-guides',
       'red-native-interval-guides','black-reconstructed-anatomy-anchors','black-native-thread',
       'red-native-thread','black-face-surface-artwork','teal-face-surface-artwork','black-face-mesh-silhouette',
       'black-source-derived-tissue-contours','black-generated-body-strands','teal-generated-body-strands'}
    # Make real line-free clearances around two lower scale labels; no white
    # filled rectangles are used to cover the Keeper's paths.
    label_clearances=box(77,109,93,117).union(box(108,126,122,133))
    source=E.parse(ROOT/'source/keeper-face-plot.svg').getroot()
    for group in source.findall('.//{'+NS+'}g'):
        if group.get('id') not in names:continue
        for el in group.findall('{'+NS+'}path'):
            for line in pts(el.get('d')):
                clipped=LineString(line).intersection(box(180,350,870,1248))
                parts=list(clipped.geoms) if hasattr(clipped,'geoms') else [clipped]
                for part in parts:
                    if part.geom_type!='LineString' or part.length<.5:continue
                    color='red' if group.get('id','').startswith('red-') else 'black'
                    shape=LineString([(105+(x-520)*.16,109+(y-350)*.145) for x,y in part.coords]).difference(label_clearances)
                    visible=list(shape.geoms) if hasattr(shape,'geoms') else [shape]
                    for v in visible:
                        if v.geom_type=='LineString':d.path(v.coords,color,max(.12,min(.20,float(el.get('stroke-width','1'))*.16)))
    cx,cy=125,82
    face_clearance=box(123,107.5,139,121)
    for r in (27,32,39,42):
        shape=LineString(arc(cx,cy,r)).difference(face_clearance)
        parts=list(shape.geoms) if hasattr(shape,'geoms') else [shape]
        for part in parts:
            if part.geom_type=='LineString':d.path(part.coords,width=.16)
    for i in range(7):
        a=math.radians(-90+i*360/7)
        d.circle(cx+32*math.cos(a),cy+32*math.sin(a),1.1,width=.16)
        d.text(str(i+1),cx+24*math.cos(a),cy+24*math.sin(a)-1.25,2.5,align='center')
    spans=[.25,1,2,5,10,20,50]
    labels=['3M','1Y','2Y','5Y','10Y','20Y','50Y']
    # An open 340-degree log scale prevents first and last boundaries coinciding.
    for value,label in zip(spans,labels):
        a=math.radians(-90+340*math.log(value/.25)/math.log(200))
        d.line(cx+39*math.cos(a),cy+39*math.sin(a),cx+42*math.cos(a),cy+42*math.sin(a))
        d.text(label,cx+48*math.cos(a),cy+48*math.sin(a)-1.25,2.5,align='center')
    phases=[]
    for i,value in enumerate(spans):
        theta=-math.pi/2+i*2*math.pi/7+2*math.pi*.37/value
        phases.append(theta)
        r=26-i*1.7
        color='red' if i==3 else 'black'
        d.line(cx,cy,cx+r*math.cos(theta),cy+r*math.sin(theta),color,.23 if i==3 else .16)
        d.circle(cx+r*math.cos(theta),cy+r*math.sin(theta),.8,color,.16)
    d.circle(cx,cy,1.4,width=.18)
    d.text('JAQUES',18,94,2.5)
    for i,label in enumerate(['III M','I Y','II Y','V Y','X Y','XX Y','L Y']):d.text(label,18,107+i*13,2.5)
    d.text('REIGN',178,138,2.5)
    d.text('354 Y',178,151,2.5)
    d.text('04 M',178,164,2.5)
    d.text('EACH',178,177,2.5)
    d.line(12,241,198,241)
    d.text('BOUNDARIES / ROMAN NUMERALS',105,246,2.5,align='center')
    # Exactly the [F] instruction, with Roman numerals and unit letters retained
    # in the existing A-Z transcription hand.
    words=tx.encode(DIAL_TEXT);x=18;y=255;s=2.6
    for word in words:
        width=sum(tx.token_width(t,s) for b,t in word)
        if x+width>192:x=18;y+=8
        d.cipher_word(word,x,y,s,width=180);x+=width+2.8
    return finish(d,'V','v-dial-of-seven-keepers','The Dial of Seven Keepers',DIAL_TEXT,[17,42,40,24],{
      'carrier':'Matricis twelve-mark hand; Roman numerals and M/Y unit letters',
      'cipher_tokens':tx.encode(DIAL_TEXT),'cipher_codes':tx.codes(DIAL_TEXT),
      'Jaques_upper_boundaries_years':spans,'Jaques_labels':labels,'Trithemius_reign_years':354+4/12,
      'dial_geometry':'inner seven equal stations; outer open 340-degree logarithmic boundary scale',
      'hands':'seven invented hands with periods equal to the listed Jaques spans; arbitrary phase offsets; snapshot t=.37 years',
      'hand_phases_radians':phases,'does_not_claim':'The plate does not claim that sharing the number seven establishes a common mechanism or validates either hierarchy.',
      'description':'Keeper body and projected face reused. The dial replaces the crescent. 354 years and four months per Trithemius reign; seven Jaques upper boundaries remain mismatched.'})

def readings():
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.utils import simpleSplit
    from reportlab.lib.colors import HexColor
    pdfmetrics.registerFont(TTFont('Fell',str(ROOT/'fonts/IMFeENrm28P.ttf')))
    pdfmetrics.registerFont(TTFont('Mono',str(ROOT/'fonts/IBMPlexMono-Regular.ttf')))
    contents={
      'X':[
       ('[E]','Foras\'s actual effect line in Escalationum is the plaintext encoded on this plate [S]. His six-handed portrait is retained, with sparse explicit facial contours added. This is a fictional office and an artwork, not an observed service incident.'),
       ('[D]','A fixed table assigns one unique Latin office word to each letter A-Z. AMEN marks a plaintext word boundary. ASCII normalization omits punctuation; the manuscript preserves the original sentence. The printed words decode to: '+FORAS_EFFECT),
       ('[H]','The plate asks what happens when an account of an office\'s effect is copied as an invocation of its powers. Recasting a report as a prayer does not itself change the reported action. The reuse trap is an interpretive proposal, not a claim about every ritual or organization.'),
       ('[V]','Keep the actual effect line attached to a copy, and supply the substitution key. That is this edition\'s editorial commitment; decipherability is not a claim to institutional authority.'),
       ('[F]',FORAS_EFFECT),
       ('READING THE PLATE','Read register A downward, then B. Every office word stands for one letter; AMEN separates English words. The printed key is a separate leaf. Five hands are occupied with the arrangement while the sixth waits. The red request stops outside the drawn permission field. The left specimen records four minutes; the right trace continues running.'),
       ('DOES NOT CLAIM',MANUSCRIPT['X']['does_not_claim']),
       ('SOURCE TRAIL','[S] Pseudomonarchia Escalationum, pp. 4-6 and local station-0 vector portrait, inspected for numbering, appearance, and exact actual-effect line. [B] Supplied Graduum brief. [C] The new executable word table and its round-trip checks. An Ave Maria-style mechanism is adapted; no historical Latin table is transcribed or claimed. Historical facsimile links are identified in sources.md with inspection limits.')],
      'XI':[
       ('[E]','The delivered SVG and its black pen sheet were parsed in document order. Both recover the same sentence [C]. No physical pen movement has been measured; the file is the inspected specimen.'),
       ('[D]','Each carrier path begins with one M and contains one word. Count consecutive L commands up to a Q corner: 1-25 gives A-Y and 0 modulo 26 gives Z. Q terminates a letter without lifting the pen. The next carrier path is the next word. Letter runs contain collinear subdivisions, which do not appear as separate marks when rendered.'),
       ('[H]','The image can remain unchanged after a change that destroys the record. This is a concrete property of the chosen file encoding, not a theory that all meaning resides in execution order. Printed geometry may reveal word lengths and structure; it does not retain the invisible subdivision counts.'),
       ('[V]','Preserve carrier command types and document order when this sentence matters. Keep the decoded sentence in the manuscript record. Ordinary optimization may be useful for plotting, but such an export must not be represented as the unchanged cipher specimen.'),
       ('[F]',LIFT_TEXT),
       ('READING THE PLATE','The rosette is ordinary abstract linework on paper. In the file, each continuous rounded polygon is one carrier word. A carrier word has no internal pen lift. Read only paths marked data-channel=lifted-pen, in document order; this marker supplies no plaintext letters. The three lower specimens have equal printed lengths and 1, 13, or 26 source subdivisions. Frame, lettering and those specimens are outside the channel. The upper ring is reserved.'),
       ('DOES NOT CLAIM',MANUSCRIPT['XI']['does_not_claim']),
       ('SOURCE TRAIL','[B] Supplied Graduum brief. [C] This batch\'s native generator, raw SVG command stream, decoder, and counterexamples inspected. This is a new framing contract: Q is the added letter separator. No historical steganographic source is offered as evidence for this invented mechanism.')],
      'V':[
       ('[E]','Trithemius assigns a reign of 354 years and four months to each planetary governor in the dedication and opening reign [T]. The organization publishing the Requisite Organization FAQ lists the boundaries used here: 3 months, 1, 2, 5, 10, 20, and 50 years [J]. These are textual attributions, not validation of their respective theories.'),
       ('[D]','The inner ring has seven equally spaced stations. The outer ring places the selected upper boundaries on an open logarithmic scale. Its unequal intervals are intentional. The hands have invented periods equal to the selected Jaques boundaries and arbitrary phase offsets at a snapshot of 0.37 years; these are design choices, not measured institutional rates.'),
       ('[H]','Sharing the number seven may invite comparison while failing to supply a common variable. A planetary reign and the time span of discretion of a work role answer different questions. The dial stages that mismatch without correcting it or deriving either theory from the other.'),
       ('[V]','Keep the units, inspection limits, and disagreement visible. Do not use either a longer horizon or a more elaborate diagram as a warrant for greater moral worth or unreviewable authority.'),
       ('[F]',DIAL_TEXT),
       ('READING THE PLATE','The reconstructed Keeper and projected face remain; the crescent is replaced by the dial. Read the inner ring as seven successive reign stations, each with the same historical duration. Read the outer labels as seven selected Jaques upper boundaries, not seven planetary dates. The red hand selects a timing question. In the caption, M is months and Y is years; Roman numeral letters preserve the original A-Z cipher alphabet. The drawn upper-left field is reserved.'),
       ('DOES NOT CLAIM',MANUSCRIPT['V']['does_not_claim']),
       ('SOURCE TRAIL','[T] Trithemius, De septem secundeis: Peterson\'s Latin transcription of the 1545 dedication and first reign, and Lilly\'s 1647 English excerpt, retrieved through indexed source excerpts; full-page retrieval failed. Only the duration is used here. https://www.esotericarchives.com/tritheim/tritem.htm [J] Global Organization Design Society, Requisite Organization FAQ, section on strata and time-span, inspected. Empirical claims were not audited; Jaques\'s full books were not read. https://globalro.org/article/frequently-asked-questions-faq-about-requisite-organization/2360 [A] Earlier Keeper wireframe-face vector study, inspected and reused. [B] Supplied brief.')]
    }
    c=canvas.Canvas(str(ROOT/'graduum-x-xi-v-reading-leaves.pdf'),pagesize=(595.276,841.89));c.setTitle('Clavicula Graduum - X, XI, V - Reading leaves')
    page=0
    def header(number,title,continued=False):
        nonlocal page
        page+=1;c.setFillColor(HexColor('#161918'));c.setStrokeColor(HexColor('#161918'))
        c.setFont('Mono',8);c.drawString(43,806,'CLAVICULA GRADUUM');c.drawRightString(552,806,'TABULA '+number+(' / CONTINUED' if continued else ' / READING'))
        c.setLineWidth(.35);c.line(43,795,552,795);c.setFont('Fell',24);c.drawString(43,759,title)
        c.setFont('Mono',8);c.drawCentredString(297.6,27,str(page));return 725
    for number in ('X','XI','V'):
        title=MANUSCRIPT[number]['title'];y=header(number,title)
        for tag,text in contents[number]:
            size=10.7;lines=simpleSplit(text,'Fell',size,509);need=29+len(lines)*14
            if y-need<57:c.showPage();y=header(number,title,True)
            c.setFillColor(HexColor('#a32b24') if tag in ('[F]','DOES NOT CLAIM') else HexColor('#161918'))
            c.setFont('Mono',8.5);c.drawString(43,y,tag);y-=17
            c.setFillColor(HexColor('#161918'));c.setFont('Fell',size)
            for line in lines:c.drawString(43,y,line);y-=14
            y-=13
        c.showPage()
        text='# '+number+' - '+title+'\n\n'+'\n\n'.join(tag+' '+text for tag,text in contents[number])+'\n'
        (ROOT/(number.lower()+'-reading-leaf.md')).write_text(text)
    c.save()

def main():
    checks=validate()
    prayer();litany_leaf();lifted_pen();keeper_dial()
    # Command-preserving black export is verified. Reversal changes the reading
    # while preserving all plotted marks; collinear simplification erases it.
    original=E.parse(ROOT/'xi-lifted-pen.svg');root=original.getroot()
    group=root.find('{'+NS+'}g');channel=[p for p in group if p.get('data-channel')=='lifted-pen']
    for p in channel:group.remove(p)
    for p in reversed(channel):group.append(p)
    tmp=ROOT/'tests';tmp.mkdir(exist_ok=True);original.write(tmp/'xi-reversed.svg')
    assert ordered_decode(tmp/'xi-reversed.svg')==' '.join(reversed(normalize(LIFT_TEXT).split()))
    checks['XI_master_and_black_sheet']='passed: decoded delivered SVGs'
    checks['XI_same_appearance_different_order']='passed: reversing paths reverses decoded words'
    # Collapse each line run to its last endpoint. Geometry is identical, but
    # every letter then reads A. Keep this counterexample outside the master.
    tree=E.parse(ROOT/'xi-lifted-pen.svg')
    for el in tree.getroot().iter('{'+NS+'}path'):
        if el.get('data-channel')!='lifted-pen':continue
        reduced=[];pending=None
        for cmd in re.findall(r'[MLQ][^MLQ]+',el.get('d')):
            if cmd.startswith('L'):pending=cmd
            else:
                if pending is not None:reduced.append(pending);pending=None
                reduced.append(cmd)
        if pending is not None:reduced.append(pending)
        el.set('d',' '.join(reduced))
    tree.write(tmp/'xi-simplified.svg')
    assert ordered_decode(tmp/'xi-simplified.svg')!=normalize(LIFT_TEXT)
    checks['XI_collinear_simplification']='passed: same line geometry destroys letter counts'
    from PIL import Image,ImageChops,ImageStat
    comparisons={}
    master=Image.open(ROOT/'xi-lifted-pen.png').convert('RGB')
    for name in ('xi-reversed','xi-simplified'):
        subprocess.run(['inkscape','--app-id-tag=graduum-test-'+name,'--batch-process',str(tmp/(name+'.svg')),
          '--export-background=#f6f0e4','--export-background-opacity=1','--export-width=1500',
          '--export-filename='+str(tmp/(name+'.png'))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        test=Image.open(tmp/(name+'.png')).convert('RGB')
        diff=ImageChops.difference(master,test)
        mean=sum(ImageStat.Stat(diff).mean)/3
        assert mean<.02,(name,mean)
        comparisons[name]={'mean_pixel_difference_0_to_255':mean,'threshold':.02,'decoded':ordered_decode(tmp/(name+'.svg'))}
    checks['XI_rendered_counterexamples']=comparisons
    assert tx.decode(tx.encode(DIAL_TEXT))==normalize(DIAL_TEXT)
    checks['V_Roman_caption_round_trip']='passed'
    checks['physical_plotter_tested']=False
    readings()
    (ROOT/'manuscript.json').write_text(json.dumps({'title':'Clavicula Graduum','batch':['X','XI','V'],'plates':MANUSCRIPT,
      'production_status':{'IX':'revised proof in previous package','X':'first proof','XI':'ordered SVG proof; physical plot untested','V':'first proof','remaining':['VII','I','II','III','IV','VI','VIII','XII']},
      'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'source').glob('*.svg')},
      'validation':checks},indent=2)+'\n')
    import csv
    with (ROOT/'office-litany.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['plaintext','carrier_word']);writer.writerows(TABLE.items());writer.writerow(['SPACE',BOUNDARY])
    (ROOT/'office-litany.json').write_text(json.dumps({'alphabet':TABLE,'word_boundary':BOUNDARY,'status':'new adaptation, not historical transcription'},indent=2)+'\n')
    (ROOT/'validation.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
