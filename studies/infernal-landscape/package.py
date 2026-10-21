"""Five-page vector proof, a compact preview, and the reproducible study pack."""
from pathlib import Path
import hashlib,json,zipfile
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
import cairosvg
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader,PdfWriter,Transformation
from compile import CASES,compile_case

R=Path(__file__).resolve().parent;O=R/'output';D=R/'dist';D.mkdir(exist_ok=True)
PAPER='#ede6d4';INK='#242820';RED='#a32b24';MUTE='#5f5b4e';PT=72/25.4
FONT=R/'vendor/fonts/IBMPlexMono-Regular.ttf'
pdfmetrics.registerFont(TTFont('Plex',str(FONT)))
SERI='/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf'
if Path(SERI).exists():pdfmetrics.registerFont(TTFont('Serif',SERI))
else: pdfmetrics.registerFont(TTFont('Serif',str(FONT)))

TITLES={'recorded_route':'The estate of prerequisites', 'rehearsed_route':'The gate brought within reach',
        'late_opening':'The office opens after the window', 'gate_unavailable':'The gate without an answer'}
CAPTIONS={
'recorded_route':'Reading takes 2 units; staffing takes 3. Approval follows reading and takes 6. Restoration needs both staffing and approval, then takes 2. The earliest completion is 10, meeting the deadline of 10. The six-storey approval tower is an artistic scale for the six-unit task.',
'rehearsed_route':'Approval takes 1 unit instead of 6. Reading and staffing remain unchanged, as do the dependency edges. The earliest completion falls to 5. One approval storey replaces six; the smaller building is a rendering of the changed input, not evidence that small organisations work better.',
'late_opening':'Approval still takes only 1 unit, but it cannot start until time 8. It finishes at 9; restoration finishes at 11 and misses the deadline of 10. The raised foundation and access frame signify the release time. They do not add a second delay to the calculation.',
'gate_unavailable':'The approval task is unavailable. Its gate closes. The source evaluator still calculates 5 under the duration assumptions, while reporting infeasibility. This adapter keeps that arithmetic separately and reports no executable completion. The visible conduits record prerequisites; they do not imply that the circuit can operate.'}


def wrap(c,text,x,y,width,size=10,leading=14,font='Serif'):
    c.setFont(font,size);line=''
    for word in text.split():
        q=(line+' '+word).strip()
        if pdfmetrics.stringWidth(q,font,size)>width and line:
            c.drawString(x,y,line);y-=leading;line=word
        else:line=q
    if line:c.drawString(x,y,line);y-=leading
    return y


def page_base(c,num,kicker,title):
    c.setFillColor(HexColor(PAPER));c.rect(0,0,504,720,fill=1,stroke=0)
    c.setFillColor(HexColor(RED));c.setFont('Plex',8);c.drawString(31,678,kicker)
    c.setFillColor(HexColor(INK));c.setFont('Serif',22);c.drawString(31,647,title)
    c.setStrokeColor(HexColor(INK));c.setLineWidth(.4);c.line(31,632,473,632)
    c.setFillColor(HexColor(MUTE));c.setFont('Plex',7)
    c.drawString(31,27,'INFERNAL ENGINE 0.2  /  EXTERIOR STUDIES')
    c.drawRightString(473,27,str(num))


def proof_pdf():
    buf=BytesIO();c=canvas.Canvas(buf,pagesize=(504,720),pageCompression=1)
    c.setTitle('Infernal Engine 0.2 - exterior studies')
    c.setAuthor('Josiah Alan-Lee / ChatGPT Codex')
    for i,case in enumerate(CASES):
        page_base(c,i+1,f'PLATE {i+1:02d}  /  '+case.replace('_',' ').upper(),TITLES[case])
        # Vector plate is merged at exact physical size after reportlab draws text.
        c.setFillColor(HexColor(INK));y=wrap(c,CAPTIONS[case],43,220,418,10.5,15)
        y-=12;wrap(c,'156 x 117 mm / black and vermilion / shared evaluated geometry',43,y,418,7.5,11,'Plex')
        c.showPage()
    page_base(c,5,'MODEL / MATERIAL / LIMIT','A grammar that can be changed')
    c.setFillColor(HexColor(INK));y=590
    rows=[('DURATION','ceil(duration / bay_unit) complete bays'),('PREREQUISITE','supported red service route'),
          ('RELEASE','raised foundation and access frame'),('UNAVAILABLE','closed gate; no executable completion')]
    for label,text in rows:
        c.setFont('Plex',8);c.setFillColor(HexColor(RED));c.drawString(43,y,label)
        c.setFillColor(HexColor(INK));y=wrap(c,text,156,y,300,9.5,13);y-=14
    y=wrap(c,'A lower camera tests the same scene. Branching 3D oaks turn and cast shadows; Driftless symbols keep their drawn silhouettes. Both share the model visibility.',43,y-6,418,10,14)
    c.setFillColor(HexColor(INK))
    wrap(c,'Synthetic scheduling artwork. The mapping is an artistic choice, not a validation of institutional claims. The model omits shared-resource contention, uncertain durations and human incentives. Source, editable scenes, SVG layers and audits accompany the pack. Right of reply: invited; no objection.',43,117,418,9.5,13)
    c.showPage();c.save();buf.seek(0)
    reader=PdfReader(buf);writer=PdfWriter()
    for i,page in enumerate(reader.pages):
        if i<4:
            case=CASES[i];svg=O/case/f'Infernal_{case}_main.svg';y=267
        else:svg=O/'recorded_route'/'Infernal_recorded_route_low.svg';y=131
        v=PdfReader(BytesIO(cairosvg.svg2pdf(url=str(svg)))).pages[0]
        # The SVG declares 156 x 117 mm; Cairo preserves that point geometry.
        assert abs(float(v.mediabox.width)-156*PT)<.02
        page.merge_transformed_page(v,Transformation().translate(tx=(504-156*PT)/2,ty=y))
        writer.add_page(page)
        writer.pages[-1].compress_content_streams()
    writer.add_metadata({'/Title':'Infernal Engine 0.2 - Exterior Studies','/Author':'Josiah Alan-Lee / ChatGPT Codex'})
    with (D/'Infernal_Engine_Exterior_Proof.pdf').open('wb') as f:writer.write(f)


def preview():
    im=Image.new('RGB',(2000,1740),PAPER);d=ImageDraw.Draw(im)
    head=ImageFont.truetype(str(FONT),31);small=ImageFont.truetype(str(FONT),18)
    d.text((44,26),'INFERNAL ENGINE / THE ESTATE OF PREREQUISITES',fill=INK,font=head)
    d.text((44,80),'One task graph. Four arrangements. Driftless fields + evaluated Blender architecture + 3D oaks.',fill=MUTE,font=small)
    labels=['10 / MEETS DEADLINE','5 / MEETS DEADLINE','11 / MISSES DEADLINE','NO EXECUTABLE COMPLETION']
    for i,case in enumerate(CASES):
        x=35+(i%2)*1000;y=143+(i//2)*772
        d.text((x,y),f'{i+1:02d}  '+case.replace('_',' ').upper(),font=small,fill=INK)
        d.text((x,y+30),labels[i],font=small,fill=RED)
        q=Image.open(O/case/f'Infernal_{case}_main.png').convert('RGB')
        q=q.resize((930,698),Image.Resampling.LANCZOS);im.paste(q,(x,y+54))
    d.text((44,1694),'Synthetic scheduling specimen; architectural scales are artistic choices. Master width: 156 mm.',font=small,fill=MUTE)
    im.save(D/'Infernal_Engine_Exterior_Studies.png')
    q=im.copy();q.thumbnail((1200,1044));q.save(O/'preview.jpg',quality=88,optimize=True)


def package():
    summaries=[]
    for case in CASES:
        checks=json.loads((O/case/'checks-main.json').read_text())
        native=json.loads((O/case/'blender-visibility.json').read_text())
        scene=json.loads((O/case/'scene.json').read_text())
        rendered=json.loads((O/case/'manifest-main.json').read_text())
        if len(scene['faces'])!=rendered['faces']:raise RuntimeError('Stale engraving: '+case)
        if not checks['all_passed'] or native['visible_violations']:raise RuntimeError('Checks failed: '+case)
        summaries.append(dict(case=case,checks=checks,native=native))
    low=json.loads((O/'recorded_route'/'checks-low.json').read_text())
    native_low=json.loads((O/'recorded_route'/'blender-visibility-low.json').read_text())
    if not low['all_passed'] or native_low['visible_violations']:raise RuntimeError('Lower camera checks failed')
    summaries.append(dict(case='recorded_route',view='low',checks=low,native=native_low))
    (O/'validation.json').write_text(json.dumps(summaries,indent=2))
    (O/'architecture-cases.json').write_text(json.dumps({x:compile_case(x) for x in CASES},indent=2))
    files=[p for p in R.rglob('*') if p.is_file() and not any(t in p.parts for t in ('__pycache__','dist'))
           and not p.name.endswith(('.log','.blend1','.pyc','.nbc','.nbi'))]
    manifest={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    (D/'manifest.json').write_text(json.dumps(manifest,indent=2))
    with zipfile.ZipFile(D/'Infernal_Engine_0_2_Source_and_Scenes.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):z.write(p,'Infernal_Engine_0_2/'+str(p.relative_to(R)))
        for name in ('manifest.json','Infernal_Engine_Exterior_Proof.pdf','Infernal_Engine_Exterior_Studies.png'):
            z.write(D/name,'Infernal_Engine_0_2/'+name)
    with zipfile.ZipFile(D/'Infernal_Engine_0_2_Source_and_Scenes.zip') as z:
        assert z.testzip() is None
    print(json.dumps(dict(files=len(files),archive_bytes=(D/'Infernal_Engine_0_2_Source_and_Scenes.zip').stat().st_size)))


if __name__=='__main__':
    preview();proof_pdf();package()
