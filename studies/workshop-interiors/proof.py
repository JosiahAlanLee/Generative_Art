"""Make the comparison PDF, contact sheet and editable-asset archive.

BOOK_ROOT points at a checkout with the original four reference rasters.
Large deliverables stay in output/; only a small preview is committed.
"""
from pathlib import Path
from io import BytesIO
import json, os, zipfile
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter, Transformation
import cairosvg

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
REPO=ROOT.parents[1]
BOOK=Path(os.environ['BOOK_ROOT'])
FONTS=REPO/'sources/codex-intervallorum/common/fonts'
REGULAR=FONTS/'static/EBGaramond-Regular400.ttf'
MONO=FONTS/'IBMPlexMono-Regular.ttf'
pdfmetrics.registerFont(TTFont('Garamond',str(REGULAR)))
pdfmetrics.registerFont(TTFont('Plex',str(MONO)))
KEYS=['maintained-workshop','empty-cabinet','extraction-of-the-hand','office-without-a-seal']
TITLES=['The Maintained Workshop','The Empty Cabinet','The Extraction of the Hand','The Office Without a Seal']
REFS=[
 'books/01_matricis_intervallorum/assets/the-maintained-workshop.jpg',
 'books/07_septimus/assets/the-empty-cabinet.jpg',
 'references/raster/integrated-01/extraction-of-the-hand-v01.jpg',
 'references/raster/integrated-01/office-without-a-seal-v01.jpg',
]
NOTES=[
 'The observation wheel and removable ruler face a suspended reserve vessel over a stove. A red route passes through an open gate and stops on an unfinished shelf. Access stairs and a service bay keep the maintenance visible. The two clerks are omitted for this pass.',
 'The front doors and side inspection hatches stand open. Pulleys, bearings and a crank sit around an empty central volume. A closed folded chessboard rests above it; a ruled ledger, spool and detached drive belt occupy the workshop foreground.',
 'Five wooden fingers rise from a clamped repair jig. Twenty-three strands leave its tips and continue onto the ruled pages of an open ledger. The stool is empty. The hand is an instrument attached to the bench, rather than a character.',
 'The upper bracket and lower pull ring have separate cords. Their endpoints stop above and below the entire untouched recess. Side shelves and cellular tracery surround the blank centre; no detail stroke crosses the reserved rectangle.',
]
LIMITS=[
 'Glass reserves paper inside its silhouette in the engraving; the Blender material remains transparent. This is a drawing convention for legibility.',
 'Seventy native Blender rays pass through the inspection volume without meeting a cabinet component. The chair has four floor contacts.',
 'The modeled jig has five fingers and 23 strands. Four stool legs meet the floor. The partial room has no page border.',
 'The cord gap spans 3.64 world units, clearing the complete recess. The partial alcove has no page border.',
]
CREAM='#f0e9da';INK='#252b25';BRASS='#8b6c36';RED='#a32b24'

def image_in(c,path,x,y,w,h):
    im=Image.open(path);iw,ih=im.size;scale=min(w/iw,h/ih)
    c.drawImage(ImageReader(im),x+(w-iw*scale)/2,y+(h-ih*scale)/2,iw*scale,ih*scale,mask='auto')

def paragraph(c,text,x,y,width,size=13,leading=16):
    c.setFont('Garamond',size);c.setFillColor(HexColor(INK));line=''
    for word in text.split():
        proposed=(line+' '+word).strip()
        if pdfmetrics.stringWidth(proposed,'Garamond',size)>width and line:
            c.drawString(x,y,line);y-=leading;line=word
        else:line=proposed
    if line:c.drawString(x,y,line);y-=leading
    return y

# A compact two-by-two contact sheet works on a phone as well as a large screen.
sheet=Image.new('RGB',(1600,2200),CREAM);draw=ImageDraw.Draw(sheet)
titlefont=ImageFont.truetype(str(REGULAR),48)
namefont=ImageFont.truetype(str(REGULAR),31)
smallfont=ImageFont.truetype(str(MONO),16)
draw.text((42,25),'Workshop interiors',font=titlefont,fill=INK)
draw.text((44,83),'BLENDER GEOMETRY / HATCHED SVG / 21 OCTOBER 2026',font=smallfont,fill=BRASS)
for i,(key,title) in enumerate(zip(KEYS,TITLES)):
    x=24+(i%2)*800;y=139+(i//2)*1018
    draw.text((x+18,y),f'{i+1:02d}  {title}',font=namefont,fill=INK)
    im=Image.open(OUT/key/(key+'.png')).convert('RGB');im.thumbnail((752,936),Image.Resampling.LANCZOS)
    sheet.paste(im,(x+(776-im.width)//2,y+45+(936-im.height)//2))
sheet.save(OUT/'Workshop_Interiors.png')
small=sheet.copy();small.thumbnail((960,1320),Image.Resampling.LANCZOS);small.save(ROOT/'preview.jpg',quality=88)

# Background page, then the SVG's genuine vector PDF is overlaid on its right.
writer=PdfWriter();PW,PH=1008,720
for i,(key,title,ref,note,limit) in enumerate(zip(KEYS,TITLES,REFS,NOTES,LIMITS)):
    target=OUT/key
    native=json.loads((target/'blender-checks.json').read_text())
    vector=json.loads((target/'checks.json').read_text())
    assert native['all_passed'] and vector['all_passed'],key
    buffer=BytesIO();c=canvas.Canvas(buffer,pagesize=(PW,PH))
    c.setTitle('Workshop interiors - original images, Blender reconstructions and vector proofs')
    c.setFillColor(HexColor(CREAM));c.rect(0,0,PW,PH,fill=1,stroke=0)
    c.setFont('Garamond',29);c.setFillColor(HexColor(INK));c.drawString(32,679,f'{i+1:02d}  {title}')
    c.setFont('Plex',8);c.setFillColor(HexColor(BRASS));c.drawString(34,657,'CODEX INTERVALLORUM / INTERIOR STUDIES / 21 OCTOBER 2026')
    c.setStrokeColor(HexColor(BRASS));c.setLineWidth(.35);c.line(32,646,976,646)
    for x,label in [(32,'ORIGINAL DIFFUSION IMAGE'),(270,'EXECUTED BLENDER PROOF'),(520,'STROKE-ONLY VECTOR PLATE')]:
        c.setFont('Plex',7.6);c.setFillColor(HexColor(INK));c.drawString(x,629,label)
    image_in(c,BOOK/ref,32,328,214,286)
    image_in(c,target/'blender-proof.png',270,328,214,286)
    y=paragraph(c,note,34,302,450,14,18)
    c.setStrokeColor(HexColor(RED));c.line(34,y-7,90,y-7)
    y=paragraph(c,limit,34,y-30,450,12.5,16)
    y=paragraph(c,'All four scenes use evaluated Blender geometry and the same perspective camera for their final engraving. Each delivered plate passed 1,600 independent native visibility rays, plus checks of its SVG paths, margins and brief-specific structure.',34,y-15,450,11.5,15)
    c.setFillColor(HexColor(BRASS));c.setFont('Plex',7)
    c.drawString(34,53,'Source book: 02e1155 / New geometry and adapter: ChatGPT/Codex')
    c.drawString(34,41,'Hatching bodies and CPU ray core: Claude / No physical plot test')
    c.setFont('Plex',7.4);c.drawRightString(976,24,f'REVIEW PROOF  {i+1} / 4')
    c.save();buffer.seek(0);page=PdfReader(buffer).pages[0]
    vector_bytes=cairosvg.svg2pdf(bytestring=(target/(key+'.svg')).read_bytes())
    vector_page=PdfReader(BytesIO(vector_bytes)).pages[0]
    vw,vh=float(vector_page.mediabox.width),float(vector_page.mediabox.height)
    scale=min(456/vw,574/vh);x=520+(456-vw*scale)/2;y=54+(574-vh*scale)/2
    page.merge_transformed_page(vector_page,Transformation().scale(scale).translate(x,y))
    writer.add_page(page)
    writer.pages[-1].compress_content_streams()
writer.add_metadata({'/Title':'Workshop interiors - Blender and hatched SVG studies','/Author':'Josiah Alan-Lee; prepared with ChatGPT/Codex','/Subject':'Four workshop plates reconstructed from recorded briefs; original images, native Blender proofs and vector engravings'})
with (OUT/'Workshop_Interiors_Comparison.pdf').open('wb') as f:writer.write(f)

summary={key:{'native':json.loads((OUT/key/'blender-checks.json').read_text()),'vector':json.loads((OUT/key/'checks.json').read_text()),'manifest':json.loads((OUT/key/'manifest.json').read_text())} for key in KEYS}
(ROOT/'validation.json').write_text(json.dumps(summary,indent=2))
archive=OUT/'Workshop_Interiors_Models_and_SVGs.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.writestr('README.txt','Four editable Blender scenes and their hatched SVG plates.\n\nGenerator, original briefs, attribution and rebuild instructions:\nhttps://github.com/JosiahAlanLee/Generative_Art/tree/studies/workshop-interiors/studies/workshop-interiors\n\nThese are review studies; the book selection has not been changed.\nOpen each .blend in Blender 4.5 LTS. F12 makes a shaded render; rebuilding the SVG requires the separate engraving stage.\nSVGs contain vector paths with transparent backgrounds. PNGs use warm paper.\nGlass reserves paper in the maintained-workshop SVG and remains transparent in Cycles. Fine decorative curves do not occlude other vector strokes.\n')
    for key in KEYS:
        for name in [key+'.blend',key+'.svg',key+'.png','blender-proof.png','manifest.json','scene.json','hatch-audit.npz','checks.json','blender-checks.json','camera-check.json']:
            z.write(OUT/key/name,key+'/'+name)
print(json.dumps({'pdf':str(OUT/'Workshop_Interiors_Comparison.pdf'),'contact_sheet':str(OUT/'Workshop_Interiors.png'),'models_and_svgs':str(archive),'pages':len(writer.pages),'checks_passed':all(d['native']['all_passed'] and d['vector']['all_passed'] for d in summary.values())},indent=2))
