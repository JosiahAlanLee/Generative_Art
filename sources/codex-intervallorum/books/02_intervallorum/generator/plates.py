"""Twelve original, deterministic SVG plates. Lettering is local font outlines.

The inherited stroke and mark vocabulary is retained from Clavicula Matricis.
Diagram layouts, drawings, and their stated illustrative quantities are new.
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path
import random
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

# The inherited geometry modules use sibling imports. Resolve that directory
# from this file rather than from a development machine or the working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import Doc, arc_pts, bezier
from marks import Hand, asterisk, band_x, sig_mark, ring_x
import tx

ROOT = Path(__file__).resolve().parents[1]
W, H = 1000, 1400
INK, RED, GOLD, PAPER = '#28251e', '#9c392d', '#cdbd93', '#eee6d4'
ROMAN = ['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII']
FONTS = {'roman':'IMFeENrm28P.ttf','italic':'IMFeENit28P.ttf',
         'small':'IMFeENsc28P.ttf','mono':'IBMPlexMono-Regular.ttf',
         'hand':'SueEllenFrancisco-Regular.ttf'}


class Plate:
    def __init__(self, chapter, *, dark=False, grid=False):
        self.chapter = chapter
        self.n = chapter['number']
        self.dark = dark
        self.ink = GOLD if dark else INK
        self.red = '#e89c7f' if dark else RED
        self.bg = '#282720' if dark else PAPER
        self.rng = random.Random(5000 + self.n)
        styles = {}
        for name, col in [('ink',self.ink),('red',self.red),('sep','#8d8167')]:
            for weight,width in [('hair',.85),('orn',1.5),('core',2.6),('cip',1.3)]:
                styles[f'{name}_{weight}']={'fill':'none','stroke':col,'stroke-width':str(width),
                    'stroke-linecap':'round','stroke-linejoin':'round'}
            styles[f'{name}_fill']={'fill':col,'stroke':'none'}
        styles['fox_fill']={'fill':'#b19b72','opacity':'.12','stroke':'none'}
        self.doc=Doc(W,H,styles,order=['fox_fill']+[k for k in styles if k!='fox_fill'],bg=self.bg)
        self.hand=Hand(self.doc,self.rng,amp=.22)
        self.fonts={}
        self.glyphs={}
        self.labels=[]
        self.label_bounds=[]
        for _ in range(140):
            self.doc.circle('fox_fill',self.rng.uniform(12,988),self.rng.uniform(12,1388),self.rng.uniform(.4,1.8))
        if grid:
            for x in range(70,950,40):self.line(x,270,x,1150,color='sep',weight='hair')
            for y in range(270,1170,40):self.line(70,y,930,y,color='sep',weight='hair')
        self.line(45,54,955,54)
        self.line(45,58,955,58,weight='hair')
        self.text(48,36,'Clavicula Intervallorum',16,'small')
        self.text(952,36,f'Tabula {ROMAN[self.n-1]}',16,'small',color='red',align='right')
        self.text(500,145,chapter['title'],43,'roman',align='center')
        self.text(500,188,chapter['deck'],21,'italic',align='center')
        band_x(self.hand,(405,218),(595,218),8,11,'hair','ink')
        # Engraved furniture remains separate from every meaningful connection.
        # The corner hatching and pin rings have no dependency semantics.
        for x,sgn in [(49,1),(951,-1)]:
            for y,sy in [(246,1),(1185,-1)]:
                self.path([(x,y+sy*70),(x,y),(x+sgn*70,y)],weight='orn')
                self.path([(x+sgn*5,y+sy*60),(x+sgn*5,y+sy*5),(x+sgn*60,y+sy*5)],weight='hair')
                for d in range(12,53,7):
                    self.line(x+sgn*7,y+sy*d,x+sgn*d,y+sy*7,weight='hair')
                self.circle(x,y,6)
        self.line(62,1200,938,1200,weight='hair')
        self.text(500,1347,ROMAN[self.n-1].lower(),18,'small',align='center')
        sig_mark(self.hand,500,1378,8,'ink','orn')

    def line(self,x1,y1,x2,y2,color='ink',weight='orn'):
        self.doc.line(f'{color}_{weight}',x1,y1,x2,y2)

    def path(self,pts,color='ink',weight='orn',closed=False,wobble=False):
        if wobble:self.hand.stroke(pts,weight,color,closed=closed)
        else:self.doc.poly(f'{color}_{weight}',pts,closed=closed)

    def circle(self,x,y,r,color='ink',weight='orn'):
        self.doc.circle(f'{color}_{weight}',x,y,r)

    def dot(self,x,y,r=3,color='ink'):
        self.doc.circle(f'{color}_fill',x,y,r)

    def box(self,x,y,w,h,color='ink',double=False):
        self.path([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],color,closed=True)
        if double:self.path([(x+5,y+5),(x+w-5,y+5),(x+w-5,y+h-5),(x+5,y+h-5)],color,'hair',closed=True)

    def arrow(self,pts,color='ink',weight='orn',size=10):
        self.path(pts,color,weight)
        a,b=pts[-2:];angle=math.atan2(b[1]-a[1],b[0]-a[0])
        self.path([(b[0]-size*math.cos(angle-.42),b[1]-size*math.sin(angle-.42)),b,
                   (b[0]-size*math.cos(angle+.42),b[1]-size*math.sin(angle+.42))],color,weight)

    def dash(self,pts,color='ink',step=12):
        for a,b in zip(pts,pts[1:]):
            length=math.dist(a,b)
            n=max(1,math.ceil(length/step))
            for i in range(0,n,2):
                t0=i/n;t1=min(1,(i+1)/n)
                self.line(a[0]+(b[0]-a[0])*t0,a[1]+(b[1]-a[1])*t0,
                          a[0]+(b[0]-a[0])*t1,a[1]+(b[1]-a[1])*t1,color,'hair')

    def text(self,x,y,text,size=20,face='roman',color='ink',align='left'):
        # Font outlines make each SVG portable without an installed font or a URL.
        if face not in self.fonts:self.fonts[face]=TTFont(ROOT/'fonts'/FONTS[face])
        font=self.fonts[face];gs=font.getGlyphSet();cmap=font.getBestCmap();s=size/font['head'].unitsPerEm
        if any(ord(ch) not in cmap for ch in text):raise ValueError(f'Font cannot render {text!r}')
        width=sum(gs[cmap[ord(ch)]].width for ch in text)*s
        x-=width/2 if align=='center' else width if align=='right' else 0
        self.label_bounds.append((x,y-size,x+width,y+size*.3,text))
        col={'ink':self.ink,'red':self.red,'sep':'#8d8167'}[color]
        self.labels.append(dict(x=x,y=y,text=text,size=size,face=face,color=col))
        for ch in text:
            glyph=gs[cmap[ord(ch)]]
            key=f'g-{face}-{ord(ch)}'
            if key not in self.glyphs:
                pen=SVGPathPen(gs);glyph.draw(pen)
                self.glyphs[key]=pen.getCommands()
            if self.glyphs[key]:
                self.doc.extra_after.append(f'<use xlink:href="#{key}" fill="{col}" transform="matrix({s},0,0,{-s},{x},{y})"/>')
            x+=glyph.width*s

    def lines(self,x,y,lines,size=20,face='roman',color='ink',align='left',leading=None):
        for i,line in enumerate(lines):self.text(x,y+i*(leading or size*1.4),line,size,face,color,align)

    def note(self,text):
        # Story fragment, deliberately short enough to remain readable on the plate.
        words=text.split();lines=[];line=''
        for w in words:
            candidate=(line+' '+w).strip()
            if len(candidate)>102:lines.append(line);line=w
            else:line=candidate
        if line:lines.append(line)
        self.lines(82,1241,lines,21,'italic',leading=27)

    def hatch(self,x,y,w,h,spacing=10,color='ink'):
        for xx in range(int(x),int(x+w),spacing):self.line(xx,y,xx,y+h,color,'hair')

    def seal(self,x,y,r,mark=7,color='ink'):
        self.circle(x,y,r,color)
        self.circle(x,y,r-5,color,'hair')
        ring_x(self.hand,x,y,r-7,r-13,max(14,int(r/3)),'hair',color)
        tx.mark(self.hand,mark,x-r*.55,y-r*.55,r*1.1,'orn',color)

    def finish(self,path):
        self.note(self.chapter['fiction'])
        for x0,y0,x1,y1,text in self.label_bounds:
            if x0<20 or x1>980 or y0<5 or y1>1400:
                raise ValueError(f'Lettering outside plate: {text}')
        svg=self.doc.svg()
        defs='<defs>'+''.join(f'<path id="{key}" d="{d}"/>' for key,d in self.glyphs.items() if d)+'</defs>'
        lettering='\n'.join(self.doc.extra_after)
        svg=svg.replace(lettering, '<g id="lettering">'+lettering+'</g>')
        svg=svg.replace('xmlns="http://www.w3.org/2000/svg"','xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"')
        title=html.escape(f'Tabula {ROMAN[self.n-1]}: '+self.chapter['title'])
        desc=html.escape(self.chapter['caption']+' Fiction: '+self.chapter['fiction'])
        at=svg.index('>')+1
        metadata=html.escape(json.dumps(self.labels,separators=(',',':')))
        svg=svg[:at]+f'\n<title>{title}</title>\n<desc>{desc}</desc>\n<metadata id="label-data">{metadata}</metadata>\n'+defs+svg[at:]
        path.write_text(svg)
        for f in self.fonts.values():f.close()


def plate_1(p):
    p.seal(500,335,61,3)
    p.text(500,433,'What is to remain possible?',28,align='center')
    for x,word,mark in [(220,'STATE',1),(500,'FUNCTION',2),(780,'REPERTOIRE',7)]:
        p.arrow([(500,465),(x,520),(x,570)])
        p.seal(x,660,75,mark)
        p.text(x,786,word,23,'small',align='center')
    p.lines(220,835,['same arrangement','checksum / configuration'],20,align='center')
    p.lines(500,835,['specified work continues','service / task outcome'],20,align='center')
    p.lines(780,835,['several acts remain usable','dependencies / windows'],20,align='center')
    p.box(95,938,810,171,double=True)
    p.lines(500,980,['NAME THE INVARIANT BEFORE THE TRIAL',
        'An intact vessel may hold an unusable record.',
        'A changed vessel may continue the work.',
        'More alternatives may consume the reserve.'],22,align='center',leading=32)
    for x in [155,845]:asterisk(p.hand,x,350,17,8,weight='hair')


def plate_2(p):
    for x,title,kind in [(250,'s = t',0),(750,'s = log(1+t)',1)]:
        p.circle(x,360,83);p.circle(x,360,76,weight='hair')
        for i in range(24):
            a=i*math.pi/12
            p.line(x+66*math.cos(a),360+66*math.sin(a),x+75*math.cos(a),360+75*math.sin(a),weight='hair')
        p.arrow([(x,360),(x+48,330 if kind==0 else 354)],size=8)
        p.dot(x,360);p.text(x,485,title,26,'mono',align='center')
    x0,y0,w,h=130,1030,740,400
    p.arrow([(x0,y0),(x0+w+25,y0)]);p.arrow([(x0,y0),(x0,y0-h-30)])
    for n in range(6):
        xx=x0+w*n/5;yy=y0-h*n/5
        p.line(xx,y0,xx,y0+8);p.text(xx,y0+35,str(n),18,'mono',align='center')
        if n:p.line(x0-8,yy,x0,yy);p.text(x0-20,yy+5,str(n),18,'mono',align='right')
    p.text(500,1120,'physical time t (normalized)',21,align='center')
    p.text(130,582,'logical progress s',21)
    p.dash([(x0+w*4/5,y0-h),(x0+w*4/5,y0)],'red',step=10)
    p.text(x0+w*4/5,609,'H=4',18,'mono','red',align='center')
    p.path([(x0+w*t/5,y0-h*t/5) for t in [i/50 for i in range(251)]])
    p.path([(x0+w*t/5,y0-h*math.log1p(t)/5) for t in [i/50 for i in range(251)]],'red','core')
    step=[(0,0),(1,0),(1,1),(2.3,1),(2.3,2),(4,2),(4,3),(5,3)]
    p.dash([(x0+w*t/5,y0-h*s/5) for t,s in step],step=8)
    p.text(780,670,'continuous',19,align='right')
    p.text(800,818,'bursts / gaps',19,align='right')
    p.text(850,935,'slowed',19,color='red',align='right')
    p.lines(500,535,['A finite deadline allows only finite progress.'],22,'italic',align='center')


def plate_3(p):
    p.box(335,330,330,410,double=True)
    p.path([(370,330),(370,290),(630,290),(630,330)])
    for y in range(520,720,12):p.line(352,y,648,y,'red','hair')
    p.line(352,520,648,520,'red','core')
    p.text(500,457,'R(t)',40,'italic',align='center')
    p.arrow([(500,245),(500,285)],color='red')
    p.text(250,280,'renewal q',22,color='red')
    for x,word in [(380,'loss'),(500,'upkeep'),(620,'restart')]:
        p.arrow([(x,742),(x,810)])
        p.text(x,850,word,20,align='center')
    p.lines(150,400,['internal','reserve'],23,align='center')
    p.lines(840,400,['external','shelter'],23,align='center')
    p.dash([(240,300),(240,780),(760,780),(760,300)],'sep')
    p.arrow([(785,415),(700,415)],'red')
    x0,y0=130,1120
    p.arrow([(x0,y0),(890,y0)]);p.arrow([(x0,y0),(x0,895)])
    p.text(150,910,'illustrative reserve',19)
    pts=[(130,960),(310,1030),(310,950),(490,1020),(490,940),(670,1010),(670,930),(850,1000)]
    p.path(pts,'red','core')
    p.dash([(130,1048),(850,1048)]);p.text(860,1054,'restart',17,align='right')
    p.dash([(130,1088),(850,1088)],'sep');p.text(860,1110,'storage',17,align='right')


def network(p,cx,cy,weighted=False):
    nodes=[(-155,0),(-75,-110),(45,-100),(155,-20),(80,115),(-65,115),(0,0)]
    edges=[(0,1),(1,2),(2,3),(3,4),(4,5),(5,0),(0,6),(1,6),(2,6),(3,6),(4,6),(5,6)]
    for i,(a,b) in enumerate(edges):
        x,y=nodes[a];xx,yy=nodes[b]
        weight='core' if weighted and i in (2,8,9) else 'hair'
        p.line(cx+x,cy+y,cx+xx,cy+yy,'red' if weighted and i in (2,8,9) else 'ink',weight)
        if weighted and i in (2,8,9):
            dx,dy=xx-x,yy-y;l=math.hypot(dx,dy);nx,ny=-dy/l*4,dx/l*4
            for sign in [-1,1]:p.line(cx+x+sign*nx,cy+y+sign*ny,cx+xx+sign*nx,cy+yy+sign*ny,'red')
    for x,y in nodes:p.circle(cx+x,cy+y,8)


def plate_4(p):
    network(p,270,480);network(p,730,480,True)
    p.lines(270,685,['before allocation','same topology'],23,align='center')
    p.lines(730,685,['after allocation','unequal capacity'],23,align='center',color='red')
    p.arrow([(445,480),(550,480)])
    p.text(500,300,'A SCHEMATIC, NOT EXPERIMENTAL DATA',18,'small',align='center')
    ys=[810,895,980]
    for y,label,words in zip(ys,['DESCRIBED','MAINTAINED','SELECTABLE'],
                             ['what the archive lists','what receives upkeep','what can be used now']):
        p.box(110,y,780,66,double=True)
        p.text(135,y+42,label,21,'small')
        p.text(865,y+42,words,21,align='right')
    p.text(500,1135,'Observed agreement may inherit an earlier allocation.',24,'italic',align='center')


def plate_5(p):
    p.box(125,300,260,100,double=True);p.box(615,300,260,100,double=True)
    p.lines(255,340,['READ','2 units'],23,align='center');p.lines(745,340,['STAFF','3 units'],23,align='center')
    p.box(125,475,260,100,double=True);p.lines(255,515,['APPROVAL','6 after reading'],23,align='center')
    p.arrow([(255,405),(255,470)])
    p.arrow([(745,405),(745,640),(525,640)])
    p.arrow([(255,580),(255,640),(475,640)])
    p.circle(500,640,23);p.text(500,648,'&',25,align='center')
    p.arrow([(500,665),(500,715)])
    p.box(350,720,300,90,double=True);p.text(500,775,'RESTORE: 2 units',24,align='center')
    p.text(500,875,'EARLIEST-COMPLETION SPECIMEN',22,'small',align='center')
    for j,(label,start,end,col) in enumerate([('read',0,2,'ink'),('staff',0,3,'ink'),('approval',2,8,'red'),('restore',8,10,'ink')]):
        y=930+j*53;p.text(200,y+6,label,20,align='right')
        for xx in range(int(250+start*54),int(250+end*54),8):p.line(xx,y-10,xx,y+10,col,'hair')
        p.box(250+start*54,y-12,(end-start)*54,24,col)
    for n in range(11):p.text(250+n*54,1170,str(n),17,'mono',align='center')


def gate(p,cx,cy,s=1,label='A',color='ink'):
    pts=[(-135,-130),(135,-130),(13,-5),(13,5),(135,130),(-135,130),(-13,5),(-13,-5)]
    p.path([(cx+x*s,cy+y*s) for x,y in pts],color,'core',closed=True)
    for y in range(-110,111,13):
        width=max(12,abs(y)*.93)
        p.line(cx-width*s,cy+y*s,cx+width*s,cy+y*s,color,'hair')
    p.text(cx+155*s,cy+6,label,24,'small',color)


def plate_6(p):
    for x in (300,700):p.seal(x,310,34,1)
    p.arrow([(300,346),(300,390),(500,445)]);p.arrow([(700,346),(700,390),(500,445)])
    p.dot(500,445);p.line(500,445,500,1040)
    gate(p,500,645,1,'A');gate(p,500,1010,.52,'B')
    p.arrow(bezier((500,445),(920,500),(920,840),(500,890),55),'red','core')
    p.text(850,686,'bypasses A',21,'hand','red',align='center')
    p.text(850,718,'retains B',21,'hand','red',align='center')
    p.dash(bezier((500,890),(185,880),(160,1130),(500,1130),45),'red')
    p.text(232,1030,'proposed',20,'hand','red',align='center')
    p.text(232,1062,'untried',20,'hand','red',align='center')
    p.box(90,1110,120,60);p.text(150,1150,'TRIAL',17,'small',align='center')
    p.text(650,1168,'THE BLANK IS NOT A SUCCESS',18,'small',align='center')


def plate_7(p):
    p.path([(130,430),(500,265),(870,430)],weight='core')
    p.path([(145,435),(145,970),(855,970),(855,435)],weight='core')
    p.path([(200,415),(500,290),(800,415)],weight='hair')
    p.circle(500,365,34);tx.mark(p.hand,3,475,340,50)
    for i,(word,mark,support) in enumerate([('RECORDS',1,'read / verify'),('SKILLS',5,'practice / teach'),
                                            ('RELATIONS',11,'contact / repair'),('RULES',4,'review / amend')]):
        x=230+i*180
        p.box(x-65,490,130,320,double=True);p.seal(x,570,37,mark)
        p.text(x,695,word,18,'small',align='center')
        p.text(x,755,support,17,align='center')
        p.line(x,815,x,950)
        p.text(x,1008,['premises','income','care','standing'][i],20,align='center')
        p.arrow([(x,1065),(x,1025)],'red')
    p.dash([(95,260),(95,1090),(905,1090),(905,260)],'sep')
    p.text(500,1150,'WHO MAINTAINS THE REFUGE?',26,'small',align='center')


def plate_8(p):
    rows=[('PUBLIC TRACE',.27,'visibility'),('RETAINED LESSON',.8,'usable description'),
          ('IDENTITY LINK',.45,'re-identification'),('ACTING CAPACITY',.62,'resources / access')]
    for i,(label,end,sub) in enumerate(rows):
        y=340+i*180
        p.text(100,y,label,21,'small')
        p.text(900,y,sub,19,'italic',align='right')
        p.line(100,y+50,900,y+50,weight='hair')
        p.line(100,y+50,100+800*end,y+50,'red','core')
        p.circle(100+800*end,y+50,12,'red')
        for j in range(9):p.line(100+j*100,y+44,100+j*100,y+56,weight='hair')
        p.circle(930,y+50,18);p.line(916,y+63,944,y+37)
        p.text(100,y+98,'keeper / renewal rule / residual copies or dependencies',17,'mono')
    p.box(100,1095,800,73,double=True)
    p.text(500,1140,'ILLUSTRATIVE WINDOWS: NO COMMON UNIT',21,'small',align='center')


def plate_9(p):
    cx,cy,r=500,650,270
    labels=['MISSION','STRUCTURE','MEMBERSHIP','CAPABILITIES','ACCOUNTABILITY']
    vals=[.28,.68,.45,.9,.35]
    angles=[-math.pi/2+i*2*math.pi/5 for i in range(5)]
    for j in range(1,5):
        p.path([(cx+r*j/4*math.cos(a),cy+r*j/4*math.sin(a)) for a in angles],weight='hair',closed=True)
    for a,label in zip(angles,labels):
        p.line(cx,cy,cx+r*math.cos(a),cy+r*math.sin(a))
        p.text(cx+(r+82)*math.cos(a),cy+(r+82)*math.sin(a)+7,label,20,'small',align='center')
    pts=[(cx+r*v*math.cos(a),cy+r*v*math.sin(a)) for a,v in zip(angles,vals)]
    p.path(pts,'red','core',closed=True)
    for x,y in pts:p.circle(x,y,7,'red')
    p.lines(500,1060,['invented case / ordinal descriptions',
                      'Do not sum the axes. No overall score is supplied.',
                      'More capacity can coexist with less accountability.'],23,align='center',leading=35)


def plate_10(p):
    p.box(340,275,320,85,double=True);p.text(500,328,'MATCHED CASE PACKETS',22,'small',align='center')
    xs=[210,500,790]
    for x in xs:p.arrow([(500,365),(x,425),(x,480)])
    for x,lines,mark in zip(xs,[['competent','review'],['review +','this practice'],['review +','generic checklist']],[1,7,5]):
        p.box(x-120,490,240,230,double=True);p.seal(x,555,30,mark)
        p.lines(x,630,lines,24,align='center')
        p.arrow([(x,725),(x,800),(500,845)])
    p.box(325,855,350,82,double=True);p.text(500,907,'INDEPENDENT JUDGES',24,'small',align='center')
    p.lines(500,1000,['supported findings / unsupported claims',
        'actionability / effort / missed mechanisms',
        'A proposed study. No outcomes entered.'],23,align='center',leading=37)
    p.dash([(90,1150),(910,1150)],'red')


def plate_11(p):
    for x in [220,500,780]:
        p.seal(x,310,34,11)
        p.arrow([(x,350),(500,475)])
    p.box(330,485,340,90,double=True);p.text(500,542,'ONE SHARED RECIPIENT',23,'small',align='center')
    p.line(500,575,500,660)
    p.path([(475,610),(525,660)],'red','core');p.path([(525,610),(475,660)],'red','core')
    p.text(500,710,'three entries / one disabling dependency',23,'italic',align='center')
    p.line(100,770,900,770,weight='hair')
    p.seal(220,900,40,11)
    p.arrow([(265,900),(445,900)],'red')
    p.box(455,850,330,100,'red',double=True)
    p.lines(620,891,['ACTING RECIPIENT','resources / power / review'],22,color='red',align='center')
    p.arrow([(620,955),(620,1030)])
    p.box(480,1040,280,80);p.text(620,1088,'CHALLENGE TO RECIPIENT',19,'small',align='center')
    p.dash([(475,1080),(140,1080),(140,945)],'red')
    p.text(500,1163,'Who cannot enter either arrangement?',24,'italic',align='center')


def plate_12(p):
    labels=['STATE','FUNCTION','REPERTOIRE','CLOCK','RESERVE','CARRIER',
            'PREREQUISITE','OPENING','KEEPER','TRIAL','STANDING','REVISION']
    for i,label in enumerate(labels):
        col,row=i%4,i//4;x=170+220*col;y=360+220*row
        p.seal(x,y,58,i+1)
        p.text(x,y+98,label,19,'small',align='center')
        p.text(x,y-79,ROMAN[i],17,'small',align='center')
    sig_mark(p.hand,500,1100,65,'red','core')
    p.text(185,1100,'AN INVENTED KEY',20,'small')
    p.text(835,1100,'NO FINAL SEAL',20,'small',align='right')


DRAWERS=[plate_1,plate_2,plate_3,plate_4,plate_5,plate_6,plate_7,plate_8,plate_9,plate_10,plate_11,plate_12]


def build_plates(book, out: Path) -> list[Path]:
    out.mkdir(parents=True,exist_ok=True)
    result=[]
    for ch,draw in zip(book['chapters'],DRAWERS,strict=True):
        p=Plate(ch,dark=ch['number'] in (4,12),grid=False)
        draw(p)
        path=out/f"tabula-{ch['number']:02d}.svg"
        p.finish(path);result.append(path)
    return result
