"""Package the two-camera drawing, editable model and reproducible source."""
from pathlib import Path
import json,shutil,zipfile
from PIL import Image,ImageDraw,ImageFont

R=Path(__file__).resolve().parent;O=R/'output/spillway-incised';D=R/'dist';D.mkdir(exist_ok=True)
validation=json.loads((R/'output/spillway-validation.json').read_text())
if not validation['all_passed']:raise SystemExit('Refusing to package failed checks')
hero=D/'Infernal_Spillway.png';shutil.copyfile(O/'Infernal_spillway_main.png',hero)
paper='#ede6d4';sheet=Image.new('RGB',(2400,1080),paper);draw=ImageDraw.Draw(sheet)
font_path=R/'vendor/IBMPlexMono-Regular.ttf'
font=ImageFont.truetype(str(font_path),24) if font_path.exists() else ImageFont.load_default(size=24)
for i,(v,title) in enumerate((('main','01 / Spillway works'),('low','02 / Lower camera'))):
    im=Image.open(O/f'Infernal_spillway_{v}.png').convert('RGB');im.thumbnail((1160,920))
    sheet.paste(im,(i*1200+20,75));draw.text((i*1200+30,25),title,font=font,fill='#242820')
draw.text((30,1005),'Duration: horizontal bays. Release wait: access passage. Red: critical path.',font=font,fill='#242820')
sheet.save(D/'Infernal_Spillway_Views.png')
preview=sheet.copy();preview.thumbnail((1800,810));preview.save(R/'output/spillway-preview.jpg',quality=89)
archive=D/'Infernal_Spillway_Source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(R.rglob('*')):
        rel=p.relative_to(R)
        if p.is_file() and not any(a in ('output','dist','__pycache__') for a in rel.parts):
            z.write(p,Path('studies/infernal-landscape')/rel)
    for p in sorted(O.iterdir()):
        if p.is_file() and p.suffix not in ('.log','.blend1'):
            z.write(p,Path('studies/infernal-landscape/output/spillway-incised')/p.name)
    for name in ('spillway-validation.json','spillway-preview.jpg'):
        z.write(R/'output'/name,Path('studies/infernal-landscape/output')/name)
    for name in ('__init__.py','models.py','terrain.py','tests/test_terrain.py'):
        p=R.parents[1]/'lib/process_art'/name
        if p.exists():z.write(p,Path('lib/process_art')/name)
    for name in ('LICENSE','NOTICES.md','NOTICE.md','ATTRIBUTION.md'):
        p=R.parents[1]/name
        if p.exists():z.write(p,name)
for p in (hero,D/'Infernal_Spillway_Views.png',archive):print(p,p.stat().st_size)
