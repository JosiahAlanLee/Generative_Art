#!/usr/bin/env python3
"""Portable book build. Adapts Intervallorum's Canvas/Paragraph, SVG and manifest pipeline."""
import argparse,base64,hashlib,html,io,json,re,sys
from pathlib import Path
from importlib.metadata import version
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generator.art import build_art,plot_export,INK,RED
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
PAPER='#f1eadb';MUTE='#706557'
FACES={'Body':'static/EBGaramond-Regular400.ttf','Italic':'static/EBGaramond-Italic400.ttf','Title':'IMFeENrm28P.ttf','TitleItalic':'IMFeENit28P.ttf','Small':'IMFeENsc28P.ttf','Mono':'IBMPlexMono-Regular.ttf'}
STYLE={}
def register():
 for n,p in FACES.items():pdfmetrics.registerFont(TTFont(n,str(ROOT/'fonts'/p)))
 pdfmetrics.registerFontFamily('Body',normal='Body',bold='Body',italic='Italic',boldItalic='Italic')
 for k,fn,sz,lh,col,after in [('body','Body',13,17,INK,12),('small','Body',11.2,14.3,INK,8),('dense','Body',10.6,13.2,INK,5),('dense-red','Body',10.6,13.2,RED,5),('small-red','Body',11.2,14.3,RED,8),('note','Italic',12.8,16.4,MUTE,10),('title','Title',28,31,INK,18),('red','Body',13,16.8,RED,8),('label','Mono',8,11,RED,7),('ref','Body',11.5,15.4,INK,11)]:
  STYLE[k]=ParagraphStyle(k,fontName=fn,fontSize=sz,leading=lh,textColor=colors.HexColor(col),spaceAfter=after,splitLongWords=True)
def esc(s):return html.escape(str(s))
def key(text):return re.sub(r'[^a-z0-9]+','-',text.lower()).strip('-')
def pages(book):
 p=[dict(kind='cover',title=book['title'],id='cover'),dict(kind='text',title=book['front'][0]['title'],paragraphs=book['front'][0]['paragraphs'],id='warrant'),dict(kind='plate',title='The twenty-one passages',art='matrix',caption='Read down the receiving stations. Each occupied cell is one handoff; the diagonal has no passage.',id='matrix'),dict(kind='text',title=book['front'][1]['title'],paragraphs=book['front'][1]['paragraphs'],id='directions',sample='seal-06')]
 for t in book['tiers']:
  i=t['id'];p += [dict(kind='plate',title=t['name']+' / '+t['office'],art=f'station-{i}',caption=f"{t['region']}. Permission enters the ornament; the office withdraws from view.",id=f'portrait-{i}'),dict(kind='office',title=t['name'],entry=t,id=f'office-{i}'),dict(kind='journey',title=t['region'],paragraphs=t['journey'],parable=t['parable'],station=i,id=f'region-{i}')]
  incoming=[h for h in book['handoffs'] if h['target']==i]
  chunks=([incoming] if len(incoming)<4 else [incoming[:2],incoming[2:]]) if len(incoming)<6 else [incoming[:1],incoming[1:4],incoming[4:]]
  for n,chunk in enumerate(chunks):
   if chunk:p.append(dict(kind='handoffs',title=f'Passages to station {i}',entries=chunk,id=f'passages-{i}-{n}'))
  after={0:['runbook','cord'],1:['clocks'],2:['vessel'],5:['crumple'],6:['gate']}.get(i,[])
  for a in after:
   it=book['interludes'][a];p.append(dict(kind='interlude',art=a,id=a,**it))
 for n,pg in enumerate(book['back']):p.append(dict(kind='text',id=f'register-{n}',**pg,style='ref' if n in [2,3,4,5] else 'body'))
 return p

class Book:
 def __init__(self,path,book):
  self.c=Canvas(str(path),pagesize=(PW,PH),invariant=1,pageCompression=1)
  self.c.setTitle(book['title']);self.c.setAuthor(book['author']);self.c.setSubject('A satirical demonology of incident escalation; third divergent grimoire')
  self.c.setCreator('Intervallorum-derived Python / ReportLab / SVG path generator')
  self.overflows=[];self.boxes=[]
 def start(self,p,n):
  c=self.c;c.setFillColor(colors.HexColor(PAPER));c.rect(0,0,PW,PH,stroke=0,fill=1)
  c.setStrokeColor(colors.HexColor(MUTE));c.setLineWidth(.4);c.line(34,680,470,680)
  c.setFillColor(colors.HexColor(INK));c.setFont('Small',8.5);c.drawString(35,692,'PSEUDOMONARCHIA ESCALATIONUM')
  c.setFillColor(colors.HexColor(RED));c.setFont('Mono',7);c.drawRightString(469,692,f'INC-0001 / {n:02d}')
  c.setFillColor(colors.HexColor(MUTE));c.setFont('Body',9);c.drawCentredString(252,22,str(n))
  c.bookmarkPage(p['id']);c.addOutlineEntry(p['title'],p['id'],0,False)
 def text(self,s,x,y,w,style='body',floor=47):
  par=Paragraph(esc(s),STYLE[style]);_,h=par.wrap(w,10000)
  self.boxes.append(dict(page=self.c.getPageNumber(),x=x,top=y,width=w,bottom=y-h,text=s[:50]))
  if y-h<floor:self.overflows.append(self.boxes[-1])
  par.drawOn(self.c,x,y-h);return y-h-STYLE[style].spaceAfter
 def heading(self,s,y=650,w=400):return self.text(s,52,y,w,'title')
 def art(self,path,x,y,w,h):
  d=svg2rlg(str(path));s=min(w/d.width,h/d.height);d.scale(s,s);d.width*=s;d.height*=s
  renderPDF.draw(d,self.c,x+(w-d.width)/2,y+(h-d.height)/2)
 def rule(self,y=260):
  c=self.c;c.setStrokeColor(colors.HexColor(RED));c.setLineWidth(.65);c.line(52,y,116,y)
 def end(self):self.c.showPage()
 def finish(self):
  if self.overflows:raise ValueError('Text overflows: '+json.dumps(self.overflows))
  self.c.save()

def fields(e):return [('Appearance',e['appearance']),('Office and powers',e['powers']),('Binding',e['binding']),('Seal',e['seal'])]
def pdf_entry(b,e,art,top=608,height=520,compact=False,dense=False):
 # The same final field is compulsory at every density.
 n=b.c.getPageNumber();c=b.c
 if compact:
  y=b.text(e['name']+' / '+e['office'],145,top,306,'small')
  y=b.text(f"{e['source']} > {e['target']} / {e['legions']} LEGIONS",145,y+2,306,'label')
  b.art(art,48,top-116,87,101)
  for f,s in fields(e):y=b.text(f+'. '+s,145,y,306,'dense' if dense else 'small')
  y=b.text('ACTUAL EFFECT. '+e['actual_effect'],145,y,306,'dense-red' if dense else 'small-red')
 else:
  y=b.text(e['office'],52,top,270,'red')
  y=b.text(str(e['legions'])+' LEGIONS'+(f" / PASSAGE {e['source']} > {e['target']}" if 'source' in e else ' / STATION '+str(e['id'])),52,y,270,'label')
  b.art(art,340,top-113,112,124)
  y=b.text('APPEARANCE',52,y-10,270,'label');y=b.text(e['appearance'],52,y,270)
  y=min(y,top-137)
  for f,s in fields(e)[1:]:
   y=b.text(f.upper(),52,y-6,400,'label');y=b.text(s,52,y,400)
  b.rule(y-3);y=b.text('WHAT THIS OFFICE ACTUALLY DID',52,y-17,400,'label');y=b.text(e['actual_effect'],52,y,400,'red')
 return y

def build_pdf(book,pp,arts,out):
 b=Book(out/'Pseudomonarchia_Escalationum.pdf',book)
 for n,p in enumerate(pp,1):
  b.start(p,n);c=b.c;k=p['kind']
  if k=='cover':
   c.setFillColor(colors.HexColor(INK));c.setFont('Title',40);c.drawCentredString(252,614,'Pseudomonarchia');c.drawCentredString(252,566,'Escalationum')
   c.setFont('TitleItalic',17);c.setFillColor(colors.HexColor(RED));c.drawCentredString(252,528,book['subtitle'])
   b.art(arts['office-seal-6'],149,210,206,260)
   b.text(book['strap'],120,181,264,'note')
   c.setFont('Small',12);c.setFillColor(colors.HexColor(INK));c.drawCentredString(252,130,book['author'])
   c.setFont('Mono',8);c.drawCentredString(252,102,'THIRD DIVERGENT GRIMOIRE / 2026')
   c.setFont('Italic',12);c.drawCentredString(252,62,'Please begin with the original fault.')
  elif k=='plate':
   b.art(arts[p['art']],28,88,448,580);b.text(p['caption'],52,83,400,'note')
  elif k=='office':
   b.heading(p['entry']['name']);pdf_entry(b,p['entry'],arts['office-seal-'+str(p['entry']['id'])])
  elif k=='journey':
   b.text('DESCENT / '+str(p['station']),52,650,400,'label');y=b.heading(p['title'],626)
   for para in p['paragraphs']:y=b.text(para,52,y,400)
   b.rule(y-13);y=b.text(p['parable'],70,y-33,363,'note')
   c.setFillColor(colors.HexColor(RED));c.setFont('Mono',8);c.drawRightString(450,71,'STATUS: ESCALATED')
  elif k=='handoffs':
   es=p['entries']
   if len(es)==1:b.heading(es[0]['name']);pdf_entry(b,es[0],arts['seal-'+es[0]['id']])
   else:
    b.text(p['title'].upper(),52,651,400,'label');y=615
    for e in es:
     y=pdf_entry(b,e,arts['seal-'+e['id']],top=y,compact=True,dense=len(es)==3)
     y-=10
     c.setStrokeColor(colors.HexColor(MUTE));c.setLineWidth(.35);c.line(52,y,452,y);y-=18
  elif k=='interlude':
   b.art(arts[p['art']],64,267,376,405)
   y=b.text(p['caption'],52,261,400,'label')
   for para in p['paragraphs']:y=b.text(para,52,y,400,'note')
  else:
   y=b.heading(p['title'])
   for para in p['paragraphs']:y=b.text(para,52,y,400,p.get('style','body'))
   if p.get('sample'):b.art(arts[p['sample']],182,49,140,146)
  b.end()
 b.finish();return b.boxes

def entry_html(e,art):
 t=('<h3>'+esc(e['name'])+'</h3><p class="office">'+esc(e['office'])+'</p><p class="meta">'+str(e['legions'])+' legions'+(f" / {e['source']} &rarr; {e['target']}" if 'source' in e else '')+'</p>')
 t+='<div class="seal" role="img" aria-label="'+esc(e['seal'])+'">'+art.read_text()+'</div><dl>'
 for f,s in fields(e):t+='<dt>'+f+'</dt><dd>'+esc(s)+'</dd>'
 t+='</dl><p class="actual"><strong>What this office actually did to the incident</strong><br>'+esc(e['actual_effect'])+'</p>'
 return '<article class="entry">'+t+'</article>'
def html_body(p,arts,book):
 k=p['kind'];t='<p class="kicker">INC-0001</p><h2>'+esc(p['title'])+'</h2>'
 if k=='cover':return '<p class="kicker">THIRD DIVERGENT GRIMOIRE</p><h1>Pseudomonarchia<br>Escalationum</h1><p class="subtitle">'+esc(book['subtitle'])+'</p><div class="coverseal">'+arts['office-seal-6'].read_text()+'</div><p>'+book['strap']+'</p><p>'+book['author']+'</p><p><em>Please begin with the original fault.</em></p>'
 if k in ['plate','interlude']:
  t='<figure role="img" aria-label="'+esc(p['caption'])+'">'+arts[p['art']].read_text()+'<figcaption>'+esc(p['caption'])+'</figcaption></figure>'
 if k=='office':return entry_html(p['entry'],arts['office-seal-'+str(p['entry']['id'])])
 if k=='handoffs':return t+''.join(entry_html(e,arts['seal-'+e['id']]) for e in p['entries'])
 if p.get('paragraphs'):t+=''.join('<p>'+esc(s)+'</p>' for s in p['paragraphs'])
 if p.get('parable'):t+='<blockquote>'+esc(p['parable'])+'</blockquote>'
 if p.get('sample'):t+='<div class="coverseal">'+arts[p['sample']].read_text()+'</div>'
 return t

def build_html(book,pp,arts,out):
 fonts=''.join('@font-face{font-family:'+k+';src:url(data:font/ttf;base64,'+base64.b64encode((ROOT/'fonts'/v).read_bytes()).decode()+') format("truetype");font-display:swap;}' for k,v in FACES.items())
 css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#25231f;color:#201d19;font-family:Body,serif;font-size:20px;line-height:1.43}nav{position:sticky;top:0;z-index:2;background:#25231f;color:#eee7d6;padding:12px 18px;display:flex;gap:14px;align-items:center;flex-wrap:wrap;font:13px Mono,monospace}nav a{color:inherit}select,input,button{font:inherit;padding:7px;background:#eee7d6;border:0;border-radius:2px;max-width:100%}input{width:160px}select{width:260px}main{max-width:730px;margin:auto}.page{background:#f1eadb;margin:18px 0;padding:50px 58px;min-height:800px;scroll-margin-top:90px;position:relative}.page[hidden]{display:none}h1,h2,h3{font-family:Title,serif;font-weight:normal;line-height:1.1}h1{font-size:52px}h2{font-size:35px;margin:10px 0 28px}h3{font-size:31px;margin:0 0 10px}.kicker,.meta,dt{font-family:Mono,monospace;font-size:11px;letter-spacing:.04em;color:#a33024}.office,.subtitle{color:#a33024;font-size:22px}.cover{text-align:center}.coverseal{width:200px;margin:20px auto}.coverseal svg,.seal svg{width:100%;height:auto}.seal{float:right;width:125px;margin:0 0 18px 20px}dl{margin:12px 0}dt{margin-top:16px}dd{margin:3px 0 12px}.actual{color:#a33024;border-top:1px solid #a33024;padding-top:16px;clear:both}.actual strong{font:10px Mono}.entry{margin:24px 0 42px}figure{margin:0}figure svg{width:100%;height:auto}figcaption{font:italic 17px Italic;line-height:1.4;margin:20px 0}blockquote{font-family:Italic;font-size:21px;margin:30px 0 0;padding:20px 22px;border-top:1px solid #a33024}p{margin:0 0 20px}.folio{font:11px Mono;color:#706557;margin-top:36px;text-align:center}#status{color:#eee7d6}@media(max-width:600px){body{font-size:19px}.page{padding:30px 25px;min-height:0;margin:10px}h1{font-size:37px}h2{font-size:31px}nav{position:relative}.seal{width:92px}.kicker{font-size:10px}}@media print{nav{display:none}body{background:white}main{max-width:none}.page{break-after:page;margin:0;min-height:0} }'''
 nav='<nav aria-label="Reader controls"><a href="#cover">Top</a><label>Go to <select id="goto">'+''.join(f'<option value="{p["id"]}">{i:02d} · {esc(p["title"])}</option>' for i,p in enumerate(pp,1))+'</select></label><label>Find <input id="query" type="search" placeholder="Name or phrase"></label><span id="status" aria-live="polite"></span></nav>'
 body=''.join(f'<section id="{p["id"]}" class="page {p["kind"]}">{html_body(p,arts,book)}<div class="folio">{i:02d}</div></section>' for i,p in enumerate(pp,1))
 # Inline SVG IDs must not collide with one another in the HTML document.
 svg_serial=[0]
 def unique_svg_ids(match):
  svg_serial[0]+=1;attr=[0]
  def unique_id(m):
   attr[0]+=1;return 'id="svg-'+str(svg_serial[0])+'-'+str(attr[0])+'-'+m.group(1)+'"'
  return re.sub(r'id="([^"]+)"',unique_id,match.group(0))
 body=re.sub(r'<svg\b.*?</svg>',unique_svg_ids,body,flags=re.S)
 js='''const pages=[...document.querySelectorAll('.page')],query=document.getElementById('query');function filter(){let n=0;let q=query.value.trim().toLowerCase();pages.forEach(p=>{p.hidden=!p.textContent.toLowerCase().includes(q);if(!p.hidden)n++});document.getElementById('status').textContent=q?n+' leaves':''}query.addEventListener('input',filter);document.getElementById('goto').addEventListener('change',e=>{query.value='';filter();location.hash=e.target.value});'''
 doc='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+book['title']+'</title><style>'+fonts+css+'</style></head><body>'+nav+'<main>'+body+'</main><script>'+js+'</script></body></html>'
 (out/'Pseudomonarchia_Escalationum.html').write_text(doc)

def markdown(book,pp,out):
 lines=['# '+book['title'],'',book['subtitle'],'',book['edition'],'',book['author'],'']
 for i,p in enumerate(pp,1):
  if p['kind']=='cover':continue
  lines+=['',f'## {i:02d}. '+p['title'],'']
  if p.get('art'):lines+=['![Plate](plates/'+p['art']+'.svg)','',p['caption'],'']
  if p.get('paragraphs'):lines+=['\n\n'.join(p['paragraphs']),'']
  if p.get('parable'):lines+=['> '+p['parable'],'']
  for e in ([p['entry']] if p.get('entry') else p.get('entries',[])):
   lines+=['### '+e['name'],'',e['office'],'',f"Legions: {e['legions']}",'']
   if 'source' in e:lines += [f"Passage: {e['source']} → {e['target']}",'']
   for label,txt in fields(e):lines += ['**'+label+'.** '+txt,'']
   lines+=['**What this office actually did to the incident.** '+e['actual_effect'],'']
 (out/'reading-edition.md').write_text('\n'.join(lines))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(out):
 out=out.resolve();out.mkdir(parents=True,exist_ok=True);register();book=json.loads((ROOT/'manuscript/catalogue.json').read_text());pp=pages(book)
 arts=build_art(book,out/'plates');boxes=build_pdf(book,pp,arts,out);build_html(book,pp,arts,out);markdown(book,pp,out)
 plot=out/'plotter-a4';plot.mkdir(exist_ok=True)
 for k,p in arts.items():plot_export(p,plot)
 (out/'specimen-results.json').write_text(json.dumps(specimen_cases(),indent=2)+'\n')
 inputs={str(p.relative_to(ROOT)):digest(p) for folder in ['generator','manuscript','fonts','tests','docs'] for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 for name in ['README.md','NOTICES.md','requirements-lock.txt']:
  inputs[name]=digest(ROOT/name)
 outputs={str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name not in ['build-manifest.json','layout-boxes.json']}
 manifest={'title':book['title'],'edition':book['edition'],'upstream_commit':book['source_commit'],'page_count':len(pp),'pages':[{'page':i,'id':p['id'],'kind':p['kind'],'title':p['title']} for i,p in enumerate(pp,1)],'input_sha256':inputs,'output_sha256':outputs,'dependencies':{x:version(x) for x in ['reportlab','svglib','fonttools','shapely','pillow']},'physical_plotter_tested':False,'counts':{'offices':7,'handoffs':21,'concept_and_portrait_plates':14,'office_seals':7,'handoff_seals':21},'reproducibility':'Deterministic build in pinned Python dependency environment; PDF invariant mode; no network needed.'}
 (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(out/'layout-boxes.json').write_text(json.dumps(boxes,indent=2)+'\n')
 print(json.dumps({'pages':len(pp),'plates_and_seals':len(arts),'text_overflow':0,'output':str(out)}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'output');args=p.parse_args();build(args.output)
