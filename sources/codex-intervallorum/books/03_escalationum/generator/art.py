"""Deterministic path-only art, retaining Intervallorum's geometry and twelve marks."""
import math, random, json, re
from pathlib import Path
from xml.etree import ElementTree as ET
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from .core import Doc,arc_pts,bezier,spiral_pts,curl_pts
from .marks import Hand
from . import tx
ROOT=Path(__file__).resolve().parents[1]
INK='#201d19'; RED='#b43628'; MUTE='#746858'
FONTS={}
def font(which='roman'):
 if which not in FONTS:
  p={'roman':'IMFeENrm28P.ttf','mono':'IBMPlexMono-Regular.ttf','italic':'IMFeENit28P.ttf'}[which]
  FONTS[which]=TTFont(ROOT/'fonts'/p)
 return FONTS[which]
def label(text,x,y,size=13,face='mono',color=INK,center=False):
 f=font(face); gs=f.getGlyphSet(); cm=f.getBestCmap(); scale=size/f['head'].unitsPerEm
 width=sum(f['hmtx'][cm.get(ord(ch),'.notdef')][0]*scale for ch in text)
 if center:x-=width/2
 pen=SVGPathPen(gs)
 for ch in text:
  gn=cm.get(ord(ch),'.notdef');gs[gn].draw(TransformPen(pen,(scale,0,0,-scale,x,y)))
  x+=f['hmtx'][gn][0]*scale
 return f'<path fill="{color}" stroke="none" d="{pen.getCommands()}"/>'
def doc(w=600,h=760):
 styles={}
 for color,code in [('ink',INK),('red',RED),('muted',MUTE)]:
  for weight,sw in [('core',1.6),('orn',.95),('hair',.52),('fill',.8)]:
   styles[color+'_'+weight]={'stroke':code,'stroke-width':sw,'fill':'none','stroke-linecap':'round','stroke-linejoin':'round'}
 return Doc(w,h,styles)
def hand(d,seed=0):return Hand(d,random.Random(seed),mode='plotter',amp=0)
def l(d,a,b,key='ink_orn'):d.line(key,*a,*b)
def rect(d,x,y,w,h,key='ink_orn'):d.poly(key,[(x,y),(x+w,y),(x+w,y+h),(x,y+h)],True)
def arrow(d,a,b,key='red_orn'):
 l(d,a,b,key);ang=math.atan2(b[1]-a[1],b[0]-a[0]);s=7
 d.poly(key,[(b[0]-s*math.cos(ang-.5),b[1]-s*math.sin(ang-.5)),b,(b[0]-s*math.cos(ang+.5),b[1]-s*math.sin(ang+.5))])
def title(d,t,sub=''):
 d.extra_after.append('<g id="lettering">'+label(t,300,36,23,'roman',center=True)+(label(sub,300,58,9,center=True) if sub else '')+'</g>')
def annotate(d,labels):d.extra_after.append('<g id="lettering">'+''.join(label(*args) for args in labels)+'</g>')
def cipher(d,text,x,y,s=9):tx.write(hand(d,41),text,x,y,s,color='red')
def anchor(i,cx=150,cy=142,r=92):
 a=math.radians(-90+i*360/7);return cx+r*math.cos(a),cy+r*math.sin(a)
def seal(i,j,name,small=False,core=None):
 d=doc(300,330);h=hand(d,100+i*7+j)
 for t in range(7):
  a=anchor(t);o=anchor(t,r=104);l(d,a,o,'muted_orn')
  # the same seven stations remain visible even when not traversed
  d.circle('muted_hair',*a,1.5)
 a=anchor(i);b=anchor(j)
 p1=(a[0]*.45+150*.55,a[1]*.45+142*.55)
 p2=(b[0]*.45+150*.55,b[1]*.45+142*.55)
 d.poly('ink_core',bezier(a,p1,p2,b,50))
 # the defect uses the inherited Revision 3 core vocabulary
 core=core or (i*7+j)%12+1
 tx.mark(h,core,118,113,65,'core','red')
 # horned side returns, strictly subordinate to endpoint coding
 for side in [-1,1]:
  d.poly('ink_orn',bezier((150+side*27,182),(150+side*93,220),(150+side*115,144),(150+side*105,127),45))
  d.poly('ink_hair',curl_pts(150+side*105,127,-90,18,14,1.1,side))
 # departure and receipt are separate named groups, decodable from geometry
 for key,p,radii in [('departure',a,[7]),('receipt',b,[5,10])]:
  dd=doc();
  for rad in radii:dd.circle('ink_core',*p,rad)
  d.extra_after.append(f'<g id="{key}">'+dd.body()+'</g>')
 for idx,(v,x0) in enumerate([(i,106),(j,166)]):
  for k in range(v+1):l(d,(x0+k*4,263),(x0+k*4,275),'ink_orn')
 l(d,(148,259),(148,280),'red_orn')
 s=min(10,245/max(1,tx.width(name,1)))
 cipher(d,name,(300-tx.width(name,s))/2,294,s)
 d.extra_before.append('<metadata>'+json.dumps({'source':i,'target':j,'name':name,'core':core,'alphabet':'Revision 3','plotter_tested':False})+'</metadata>')
 return d

def portrait(t):
 i=t['id'];rng=random.Random(3200+i);d=doc();title(d,t['name'],f"STATION {i} / {t['office'].upper()}")
 cx=300;bottom=610;top=143;wid=[94,114,142,126,128,170,130][i]
 def strands(cx,cy,w,length,count=180,face=True):
  for k in range(count):
   u=-1+2*k/(count-1);x=cx+u*w
   y0=cy+65*abs(u)**1.6+rng.uniform(-9,12);y1=cy+length+rng.uniform(-17,18)-22*abs(u)
   pts=[]
   for n in range(60):
    v=n/59;y=y0+(y1-y0)*v;xx=x+u*25*math.sin(v*math.pi)+math.sin(v*16+u*5)*6+math.sin(v*31+k*.8)*1.7
    if face:
     dist=abs(y-(cy+109))
     if dist<62 and abs(x-cx)<49:xx+=(-1 if u<0 else 1)*(54-abs(x-cx))*math.cos(dist/62*math.pi/2)
    pts.append((xx,y))
   d.poly('red_hair' if k%19==0 else 'ink_hair',pts)
 def eyes(x,y):
  for side in [-1,1]:
   d.poly('ink_core',arc_pts(x+side*22,y,9,-155,155,28,ry=4));d.circle('red_orn',x+side*22,y,1.3)
 def horn(x,y,side,size=1):
  for k in range(8):d.poly('ink_hair',bezier((x,y+k*.7),(x+side*95*size,y-45),(x+side*81*size,y-120*size),(x+side*72*size,y-109*size+k),60))
 if i==0:
  strands(300,150,94,440);eyes(300,257);horn(260,201,-1,.8);horn(340,201,1,.8)
  for q in range(6):
   side=-1 if q<3 else 1;yy=345+(q%3)*53
   d.poly('ink_orn',bezier((300+side*70,yy),(300+side*130,yy-30),(300+side*145,yy+15),(300+side*166,yy-12),40))
   for f in range(4):l(d,(300+side*166,yy-12),(300+side*(175+f*4),yy-32+f*8),'ink_hair')
 elif i==1:
  # two heads joined to a single narrow robe; the second face is already wiped
  strands(254,142,59,442,130);strands(349,193,55,392,120);eyes(254,251)
  for r in [28,32]:d.poly('ink_orn',arc_pts(349,302,r,0,360,80,ry=44))
  horn(232,180,-1,.7);horn(375,220,1,.7)
  for k in range(16):
   y=400+k*10;d.poly('red_hair',bezier((147,y),(240,y-50),(380,y+50),(455,y),70))
 elif i==2:
  # roof protects the official view; the lower body swells into a conservatory
  strands(300,211,143,383,230);eyes(300,320)
  for k in range(24):
   d.poly('ink_hair',[(85,210+k*.6),(300,110+k*.9),(515,210+k*.6)])
  for x in range(100,506,7):
   l(d,(x,89),(x-8,128),'red_hair')
  for k in range(12):
   y=433+k*11;d.poly('red_hair',bezier((144,y),(220,y+25),(380,y-25),(456,y),70))
  for x in [152,448]:l(d,(x,212),(x,589),'ink_core')
 elif i==3:
  strands(300,144,126,452,235);horn(256,189,-1,.8);horn(344,189,1,.8)
  # three contractual mouths: promise, interpretation, renewal
  for yy in [226,252,278]:
   d.poly('red_orn',arc_pts(300,yy,25,0,360,60,ry=7))
   for k in range(9):l(d,(281+k*4,yy-4),(281+k*4,yy+4),'ink_hair')
  for k in range(5):
   y=397+k*35;d.poly('ink_orn',bezier((139,y),(250,y+70),(350,y-70),(461,y),65))
   for r in [7,10,13]:d.circle('red_hair',300,y,r)
 elif i==4:
  # horse-front and bureaucratic missing half divided at the vertical boundary
  for k in range(155):
   u=k/154;x=137+u*150
   d.poly('ink_hair',bezier((x,210+u*60),(x-60,320),(x+53,480),(x+20,600+9*math.sin(k)),65))
  # elongated profile and a mane of nested contours
  for k in range(14):
   d.poly('ink_hair',[(227+k,207),(242+k,143),(262+k,160),(290+k,140),(302+k,216),(330+k,292),(305+k,318),(269+k,270),(241+k,287)])
  d.circle('red_orn',281,219,4)
  for k in range(5):
   x=356+k*21;rect(d,x,222+k*28,38,315-k*31,'red_hair')
  l(d,(335,103),(335,617),'red_orn')
  for k in range(15):l(d,(324,121+k*32),(346,121+k*32),'red_hair')
 elif i==5:
  # an office is concealed by the dispatch curtain; narrow unprinted aperture
  for k in range(210):
   x=95+k*1.95;y0=128+rng.randrange(14);y1=610-rng.randrange(65)
   cut=278+50*math.sin(k*.05)
   if 273<x<328:
    l(d,(x,y0),(x,cut-28),'ink_hair');l(d,(x,cut+53),(x,y1),'ink_hair')
   else:
    d.poly('red_orn' if k%13 in [0,1] else 'ink_hair',[(x,y0),(x+math.sin(k)*3,280),(x+math.sin(k)*3,y1)])
  for k in range(12):
   y=360+k*18;l(d,(103,y),(501,y),'red_hair')
  # theatre rigging and a speaker, the body has become its report
  for yy in [111,118,125]:l(d,(74,yy),(524,yy),'ink_orn')
  for r in range(5,27,4):d.circle('ink_hair',300,304,r)
 elif i==6:
  # empty throne. Permission ornaments the perimeter; the centre remains vacant.
  for k in range(29):
   o=k*1.25;rect(d,176-o,143-o,248+2*o,346+2*o,'ink_hair')
  for k in range(20):
   o=k*.8;d.poly('red_hair',[(146-o,506+o),(300,558+o),(454+o,506+o),(300,463+o),(146-o,506+o)])
  for side in [-1,1]:
   for k in range(18):
    x=300+side*(109+k*1.2);d.poly('ink_hair',[(x,536),(x+side*13,608),(x+side*24,620)])
   horn(300+side*93,177,side,.75)
  for k in range(13):
   y=245+k*16;d.poly('red_hair',bezier((76,y),(165,y-25),(165,511),(300,541),90))
   d.poly('red_hair',bezier((524,y),(435,y-25),(435,511),(300,541),90))
  for r in [35,40]:d.circle('muted_orn',300,308,r)
  # seven keys, none entering the lock
  for k in range(7):
   x=219+k*27;d.circle('ink_orn',x,194,4);l(d,(x,198),(x,222),'ink_orn');l(d,(x,214),(x+6,214),'ink_orn')
 # ordinal marks; deliberately no empirical metric scale
 for col,val in enumerate([i,6-i,6-i]):
  x=220+col*80
  for k in range(val+1):l(d,(x+k*4,661),(x+k*4,678),'red_orn' if col==0 else 'ink_orn')
 annotate(d,[('AUTH',220,699,9,'mono',RED),('KNOW',300,699,9),('BLAME',380,699,9)])
 cipher(d,t['name'],(600-tx.width(t['name'],12))/2,718,12)
 return d

def matrix(book):
 d=doc();title(d,'The twenty-one passages','ONE SPIRIT FOR EVERY PAIR / i < j')
 # triangular seals under station axes
 for j in range(1,7):
  y=140+(j-1)*82
  annotate(d,[(str(j),50,y+5,15,'mono',RED)])
  for i in range(j):
   x=103+i*77;rect(d,x-32,y-32,64,64,'muted_hair')
   entry=next(h for h in book['handoffs'] if h['id']==f'{i}{j}')
   sd=seal(i,j,entry['name'],core=entry['mark'])
   d.extra_before.append(f'<g transform="translate({x-27},{y-31}) scale(.18)">'+sd.body()+'</g>')
 for i in range(6):annotate(d,[(str(i),103+i*77,95,13,'mono',INK,True)])
 annotate(d,[('DEPARTURE',300,76,9,'mono',INK,True),('RECEIPT',50,664,9),('7 x 6 / 2 = 21',300,700,14,'mono',RED,True)])
 return d

def vessel():
 d=doc();title(d,'The reserve of patience','ONE VESSEL / SIX RESTARTS')
 # nested jar contours with gaps / red escaping water
 for off in range(9):
  d.poly('ink_hair',bezier((245-off,130),(240-off,230),(155-off,235),(160-off,505),60)+bezier((160-off,505),(166-off,605),(434+off,605),(440+off,505),60)+bezier((440+off,505),(445+off,235),(360+off,230),(355+off,130),60))
 for y in range(305,548,5):
  xspan=133-abs(y-430)*.06
  d.poly('ink_hair',[(300-xspan+t*xspan*2/70,y+2*math.sin(t/4+y)) for t in range(71)])
 for k in range(6):
  y=300+k*43;x=440
  d.circle('red_orn',x,y,7)
  d.poly('red_orn',bezier((x,y),(530,y),(480,610+k*8),(530,641+k*8),70))
  annotate(d,[(str(k+1),462,y-9,11,'mono',RED)])
 d.poly('red_orn',[(120,670),(494,670)])
 annotate(d,[('REPEAT THE WHOLE ACCOUNT',300,725,11,'mono',RED,True)])
 return d

def clocks():
 d=doc();title(d,'The hours retained and cancelled','THE WOUND / THE RECEIPT')
 for idx,cy in enumerate([260,550]):
  cx=300
  for r in [110,115,124]:d.circle('ink_orn',cx,cy,r)
  for k in range(60):
   a=math.radians(k*6-90);r0=100 if k%5==0 else 106
   l(d,(cx+r0*math.cos(a),cy+r0*math.sin(a)),(cx+110*math.cos(a),cy+110*math.sin(a)),'ink_orn')
  for k in range(12):
   a=math.radians(k*30-90);annotate(d,[(str(k*5),cx+88*math.cos(a),cy+88*math.sin(a)+4,10,'mono',INK,True)])
  angle=(52 if idx==0 else 0)*6-90;a=math.radians(angle)
  arrow(d,(cx,cy),(cx+77*math.cos(a),cy+77*math.sin(a)))
  if idx==1:
   for rad in [136,144,152]:d.poly('red_hair',arc_pts(cx,cy,rad,-80,252,110))
  annotate(d,[('ELAPSED: 52' if idx==0 else 'NEW RECEIPT: 00',300,cy+151+(24 if idx else 0),12,'mono',RED,True)])
 arrow(d,(445,269),(445,487),'ink_orn')
 return d

def gate():
 d=doc();title(d,'Five roads through one neck','TECHNICAL READINESS AND EXECUTIVE PERMISSION')
 for k in range(5):
  x=85+k*107;d.circle('ink_orn',x,140,18);annotate(d,[(str(k+1),x,145,12,'mono',INK,True)])
  yy=320+k*20
  d.poly('red_orn' if k==4 else 'ink_orn',bezier((x,158),(x,yy),(300,yy),(300,405),80))
 rect(d,245,405,110,58);annotate(d,[('BAEL',300,440,18,'roman',INK,True),('AVAILABLE AT 90',300,489,12,'mono',RED,True)])
 # explicit AND with independent technical readiness
 rect(d,92,513,135,48);annotate(d,[('READY AT 4',160,542,11,'mono',INK,True)])
 arrow(d,(300,463),(300,546));arrow(d,(227,537),(266,566),'ink_orn')
 d.poly('ink_orn',[(270,540),(310,540)]+arc_pts(310,570,30,-90,90,30)+[(270,600),(270,540)])
 annotate(d,[('AND',301,574,11,'mono',RED,True)])
 arrow(d,(305,605),(305,664));annotate(d,[('REPAIR: 95-103',305,696,12,'mono',RED,True)])
 return d

def crumple():
 d=doc();title(d,'The return of responsibility','THE ONE WHO KNEW / THE ONES WHO COULD')
 for k in range(7):
  y=127+k*68;x=110+k*52
  rect(d,x-34,y-16,68,32);annotate(d,[(str(k),x,y+4,12,'mono',INK,True)])
  if k:arrow(d,(x-52,y-48),(x,y-18),'ink_orn')
  for z in range(k+1):
   d.poly('red_hair',bezier((x+34,y),(565+z*2,y),(555-z*4,658),(143+z*3,658),100))
 # recipient with folded compression field
 for k in range(26):
  y=606+k*3;d.poly('ink_hair',[(55,y),(94,y-4),(110,y+4),(127,y-5),(151,y)])
 l(d,(110,143),(110,599),'ink_orn');arrow(d,(150,658),(115,658))
 annotate(d,[('0',110,704,20,'roman',RED,True),('ACCOUNTABLE OWNER',300,731,12,'mono',RED,True)])
 return d

def cord():
 d=doc();title(d,'The office without a seal','STOP WORK AUTHORITY / UNISSUED')
 rect(d,118,180,364,408,'muted_orn')
 for y in range(186,584,9):l(d,(120,y),(128,y),'muted_hair');l(d,(472,y),(480,y),'muted_hair')
 d.circle('ink_orn',300,206,7);l(d,(300,213),(300,270),'ink_orn')
 l(d,(300,479),(300,560),'ink_orn');d.circle('ink_orn',300,568,8)
 # deliberate disconnected ends. No connecting dashed line.
 annotate(d,[('SEAL NOT ISSUED',300,394,14,'mono',RED,True),('POSITION RESERVED',300,639,11,'mono',INK,True)])
 return d

def runbook():
 d=doc();title(d,'The extraction of the hand','COPY / ORDER / REMOVE')
 rng=random.Random(92)
 # rich analogue bundle transforms into sorted rule strips
 for k in range(140):
  x=70+k*3.2;yy=125+rng.randrange(35)
  d.poly('ink_hair',bezier((x,yy),(x+80*math.sin(k),270),(80+k*3.15,320),(80+k*3.15,380),60))
 for k in range(13):
  y=407+k*15
  rect(d,80,y,440,10,'red_hair');
  for j in range(5):l(d,(90+j*83,y+4),(143+j*83,y+4),'ink_hair')
 # bottom retained absence hand socket, template without worker
 for k in range(5):
  x=210+k*36;l(d,(x,624),(x,681),'ink_orn');d.poly('ink_orn',arc_pts(x+9,624,9,180,360,16))
 l(d,(210,681),(363,681),'ink_orn')
 annotate(d,[('THE READER HAS LEFT',300,724,12,'mono',RED,True)])
 return d

def office_seal(t):
 d=doc(300,330);h=hand(d,88+t['id'])
 for r in [91,97]:d.circle('ink_orn',150,145,r)
 core=[2,6,3,9,7,11,12][t['id']]
 tx.mark(h,core,102,97,96,'core','ink')
 for k in range(t['id']+1):l(d,(130+k*7,255),(130+k*7,274),'red_orn')
 s=min(12,240/tx.width(t['name'],1));cipher(d,t['name'],(300-tx.width(t['name'],s))/2,297,s)
 return d


def build_art(book,out):
 out.mkdir(parents=True,exist_ok=True);results={}
 plates={'matrix':matrix(book),'vessel':vessel(),'clocks':clocks(),'gate':gate(),'crumple':crumple(),'cord':cord(),'runbook':runbook()}
 for t in book['tiers']:plates['station-'+str(t['id'])]=portrait(t)
 for key,d in plates.items():
  path=out/(key+'.svg');path.write_text(d.svg());results[key]=path
 for t in book['tiers']:
  path=out/('office-seal-'+str(t['id'])+'.svg');path.write_text(office_seal(t).svg());results['office-seal-'+str(t['id'])]=path
 for h in book['handoffs']:
  path=out/('seal-'+h['id']+'.svg');path.write_text(seal(h['source'],h['target'],h['name'],core=h['mark']).svg());results['seal-'+h['id']]=path
 return results

def plot_export(path,out):
 """A4 physical sheet, no filled font outlines or decorative background."""
 root=ET.fromstring(path.read_text());ns='{http://www.w3.org/2000/svg}'
 # nested lettering group may occur several times
 for par in root.iter():
  for c in list(par):
   if c.get('id')=='lettering':par.remove(c)
 w,h=map(float,root.get('viewBox').split()[2:]);s=min(190/w,277/h)
 for color in ['black','red','combined']:
  copy=ET.fromstring(ET.tostring(root))
  for par in copy.iter():
   for c in list(par):
    if c.tag==ns+'path' and ((color=='red' and c.get('stroke')!=RED) or (color=='black' and c.get('stroke')==RED)):par.remove(c)
  inner=''.join(ET.tostring(c,encoding='unicode') for c in copy)
  svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297"><g transform="translate({(210-w*s)/2},{(297-h*s)/2}) scale({s})">{inner}</g></svg>'
  (out/(path.stem+'-'+color+'.svg')).write_text(svg)
