"""Print-size page proofs: each half is one 7 x 10 inch Codex page.

The master PDF is vector; the per-scene proof-page.png is its 600 dpi binary
render beside the current diffusion selection. Large outputs remain untracked.
"""
from pathlib import Path
from io import BytesIO
import json,os,subprocess,zipfile
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader,PdfWriter,Transformation
import cairosvg
from settings_v2 import SIZES,CAPTIONS

R=Path(__file__).resolve().parent;O=R/'output/v2';REPO=R.parents[1];BOOK=Path(os.environ['BOOK_ROOT'])
KEYS=['maintained-workshop','empty-cabinet','extraction-of-the-hand','office-without-a-seal']
TITLES=['The Maintained Workshop','The Empty Cabinet','The Extraction of the Hand','The Office Without a Seal']
SOURCES=['books/01_matricis_intervallorum/assets/the-maintained-workshop.jpg','books/07_septimus/assets/the-empty-cabinet.jpg','references/raster/integrated-01/extraction-of-the-hand-v01.jpg','references/raster/integrated-01/office-without-a-seal-v01.jpg']
FONTS=REPO/'sources/codex-intervallorum/common/fonts';REG=FONTS/'static/EBGaramond-Regular400.ttf';MONO=FONTS/'IBMPlexMono-Regular.ttf';FELL=FONTS/'IMFeENsc28P.ttf'
for name,file in [('Body',REG),('Mono',MONO),('Fell',FELL)]:pdfmetrics.registerFont(TTFont(name,str(file)))
PW,PH=504,720;MM=72/25.4;PAPER='#ede6d4';INK='#242820';RED='#a32b24'
writer=PdfWriter();summary={}

def caption(c,text,x,y,w,size=9.6):
    style=ParagraphStyle('caption',fontName='Body',fontSize=size,leading=size*1.30,textColor=HexColor(INK))
    p=Paragraph(text,style);_,h=p.wrap(w,500);p.drawOn(c,x,y-h)

for key,title,source in zip(KEYS,TITLES,SOURCES):
    d=O/key;checks=json.loads((d/'checks.json').read_text());native=json.loads((d/'blender-checks.json').read_text());replay=json.loads((d/'regeneration-check.json').read_text())
    assert checks['all_passed'] and native['all_passed'] and replay['passed'],key
    summary[key]={'print_checks':checks,'native_checks':native,'regeneration':replay,'manifest':json.loads((d/'manifest.json').read_text())}
    buffer=BytesIO();c=canvas.Canvas(buffer,pagesize=(PW*2,PH),invariant=1,pageCompression=1)
    c.setTitle('Workshop interiors / revised briefs / exact-size page proofs')
    for side,label in enumerate(['CURRENT SELECTION','SECOND PASS / TWO INKS']):
        off=side*PW;c.setFillColor(HexColor(PAPER));c.rect(off,0,PW,PH,fill=1,stroke=0)
        c.setFont('Mono',6.3);c.setFillColor(HexColor(RED));c.drawString(off+36,707,label)
        c.setStrokeColor(HexColor('#8e7b5f'));c.setLineWidth(.4);c.line(off+36,680,off+468,680)
        c.setFillColor(HexColor(INK));c.setFont('Fell',8)
        header='MATRICIS ET INTERVALLORUM' if key=='maintained-workshop' else 'DE VINCULIS' if key=='empty-cabinet' else 'PSEUDOMONARCHIA ESCALATIONUM'
        c.drawString(off+36,691,header)
        width,height=SIZES[key];w,h=width*MM,height*MM
        if key=='maintained-workshop':
            x,y=31,80;caption(c,'[F] '+CAPTIONS[key],off+63,65,378)
        elif key=='empty-cabinet':
            x,y=36,90;c.setFont('Body',10);c.drawCentredString(off+252,61,'The empty cabinet')
        else:
            x,y=(PW-w)/2,278;c.setFont('Fell',14);c.drawCentredString(off+252,650,title.upper())
            c.setFont('Mono',6.3);c.drawCentredString(off+252,632,'COPY / ORDER / REMOVE' if key=='extraction-of-the-hand' else 'STOP WORK AUTHORITY / UNISSUED')
            caption(c,CAPTIONS[key],off+52,248,400,10.0)
        if side==0:c.drawImage(ImageReader(Image.open(BOOK/source)),off+x,y,w,h,preserveAspectRatio=False,mask='auto')
        else:placement=(off+x,y,w,h)
        c.setFillColor(HexColor('#62594a'));c.setFont('Mono',6.2)
        c.drawString(off+36,36,f'{width} x {height} mm / 100% placement / 7 x 10 inch page')
        c.drawCentredString(off+252,21,'Placement study; no book asset selection changed')
    c.save();buffer.seek(0);page=PdfReader(buffer).pages[0]
    vector=PdfReader(BytesIO(cairosvg.svg2pdf(bytestring=(d/(key+'.svg')).read_bytes()))).pages[0]
    x,y,w,h=placement;vw,vh=float(vector.mediabox.width),float(vector.mediabox.height)
    page.merge_transformed_page(vector,Transformation().scale(w/vw,h/vh).translate(x,y))
    writer.add_page(page);writer.pages[-1].compress_content_streams()

pdf=O/'Workshop_Interiors_v2_Page_Proofs.pdf'
writer.add_metadata({'/Title':'Workshop interiors v2 / print-size page proofs','/Author':'Josiah Alan-Lee; scenes and engraving prepared with ChatGPT/Codex','/Subject':'Current selections beside revised two-ink Blender/SVG plates at 156, 152 and 95 mm print widths'})
with pdf.open('wb') as f:writer.write(f)

# Render each 14 x 10 inch pair at 600 dpi, with no screen-size rescaling.
tmp=O/'page-proof-renders';tmp.mkdir(exist_ok=True)
subprocess.run(['pdftoppm','-r','600','-mono',str(pdf),str(tmp/'page')],check=True,stdout=subprocess.DEVNULL)
pages=sorted(tmp.glob('page-*.pbm'));assert len(pages)==4
for key,p in zip(KEYS,pages):
    im=Image.open(p);assert im.size==(8400,6000),im.size
    im.convert('1').save(O/key/'proof-page.png')
    record={'dpi':600,'page_pair_inches':[14,10],'page_inches':[7,10],'raster_pixels':[8400,6000],'plate_mm':list(SIZES[key]),'mode':'binary','caption':CAPTIONS[key]}
    (O/key/'page-proof-record.json').write_text(json.dumps(record,indent=2))

# The colour contact sheet is convenient for browsing, not the size proof.
sheet=Image.new('RGB',(1800,2420),'#f0e9da');draw=ImageDraw.Draw(sheet)
tf=ImageFont.truetype(str(REG),49);nf=ImageFont.truetype(str(REG),31);sf=ImageFont.truetype(str(MONO),16)
draw.text((44,23),'Workshop interiors / second pass',font=tf,fill=INK)
draw.text((46,88),'BLACK + VERMILION / ENGRAVED AT THE BOOK\'S PRINTED SIZES',font=sf,fill=RED)
for i,(key,title) in enumerate(zip(KEYS,TITLES)):
    x=(i%2)*900;y=140+(i//2)*1120
    draw.text((x+34,y),title,font=nf,fill=INK);draw.text((x+35,y+39),f'{SIZES[key][0]} x {SIZES[key][1]} mm',font=sf,fill='#685d4c')
    im=Image.open(O/key/(key+'.png')).convert('RGB');im.thumbnail((840,1010),Image.Resampling.LANCZOS);sheet.paste(im,(x+(900-im.width)//2,y+78+(1010-im.height)//2))
sheet.save(O/'Workshop_Interiors_v2.png');small=sheet.copy();small.thumbnail((900,1210));small.save(R/'preview.jpg',quality=87)
(R/'validation-v2.json').write_text(json.dumps(summary,indent=2))
archive=O/'Workshop_Interiors_v2_Models_and_SVGs.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.writestr('README.txt','Workshop interiors / second pass / 21 October 2026\n\nEditable Blender models, two-ink stroke-only SVGs, exact print dimensions and 600 dpi page comparisons.\n\nGenerator and instructions:\nhttps://github.com/JosiahAlanLee/Generative_Art/tree/studies/workshop-interiors-v2/studies/workshop-interiors\n\nEach proof-page.png is a 14 x 10 inch pair at 600 dpi: current diffusion selection on the left, revised plate on the right. Each half is a 7 x 10 inch book page.\n\nThe PDF is the colour vector proof. The page PNGs are binary legibility proofs.\nF12 renders the Blender scene; regenerate the SVG with the separate engraving stage.\nThese are print masters. No plot master or physical pen plot test is claimed.\nFirst-pass files remain unchanged and are identified in baseline-v1.json in the source repository.\n')
    for key in KEYS:
        for name in [key+'.blend',key+'.svg',key+'.png','blender-proof.png','scene.json','manifest.json','checks.json','blender-checks.json','hatch-audit.npz','stroke-audit.json','halo-mask.png','print-600dpi.png','proof-page.png','page-proof-record.json','regeneration-check.json']:
            z.write(O/key/name,key+'/'+name)
print(json.dumps({'pdf':str(pdf),'contact_sheet':str(O/'Workshop_Interiors_v2.png'),'assets':str(archive),'all_checks_passed':True,'page_pairs':4},indent=2),flush=True)
