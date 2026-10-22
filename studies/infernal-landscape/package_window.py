"""Package the verified window plate and its rebuildable Blender source."""
from pathlib import Path
import json,shutil,zipfile,platform,importlib.metadata
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;O=R/'output/window-incised';D=R/'dist';D.mkdir(exist_ok=True)
valid=json.loads((O/'window-validation.json').read_text())
if not valid['all_passed']:raise SystemExit('Refusing to package failed checks')
if valid.get('backend','blender')!='blender':raise SystemExit('Refusing to package a dry run: deliver from the Blender model')
scene_record=json.loads((O/'blender-checks.json').read_text())
versions={n:importlib.metadata.version(n) for n in ('numpy','scipy','numba','pillow','contourpy','cairosvg')}
(O/'runtime.json').write_text(json.dumps({'python':platform.python_version(),'blender':scene_record['blender'],'engraving':versions},indent=2))
hero=D/'Window_onto_the_Coulee_Mill.png';shutil.copyfile(O/'Infernal_window_main.png',hero)
proof=Image.new('RGB',(2400,1040),'#ede6d4');d=ImageDraw.Draw(proof)
font_path=R/'vendor/fonts/IBMPlexMono-Regular.ttf'
f=ImageFont.truetype(str(font_path),24) if font_path.exists() else ImageFont.load_default(size=24)
sheets=[('clay.png','01 / Evaluated Blender geometry'),('Infernal_window_main.png','02 / Driftless + erosion + engraving')]
if not (O/'clay.png').exists():
    print('No clay proof (built with --no-clay): the comparison sheet shows the engraving only',flush=True)
    sheets=sheets[1:]
for i,(name,title) in enumerate(sheets):
    im=Image.open(O/name).convert('RGB');im.thumbnail((1160,880));proof.paste(im,(i*1200+20,90))
    d.text((i*1200+30,28),title,fill='#242820',font=f)
d.text((30,986),'156 x 117 mm / Solid window, shared rays / 70 erosion steps',font=f,fill='#242820')
proof.save(D/'Window_Workflow_Comparison.png')
small=Image.open(hero).convert('RGB');small.thumbnail((1600,1200));small.save(R/'output/window-preview.jpg',quality=91)
archive=D/'Window_Mill_Blender_SVG_Source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(R.rglob('*')):
        rel=p.relative_to(R)
        if p.is_file() and not any(a in ('output','dist','__pycache__') for a in rel.parts):z.write(p,Path('studies/infernal-landscape')/rel)
    for p in sorted(O.iterdir()):
        if p.suffix in ('.blend','.json','.svg','.png','.npz'):z.write(p,Path('studies/infernal-landscape/output/window-incised')/p.name)
    z.write(R/'output/window-preview.jpg','studies/infernal-landscape/output/window-preview.jpg')
    for p in (R.parents[1]/'lib/process_art').rglob('*.py'):
        if '__pycache__' not in p.parts:z.write(p,p.relative_to(R.parents[1]))
    for name in ('LICENSE','NOTICES.md','NOTICE.md','ATTRIBUTION.md'):
        p=R.parents[1]/name
        if p.exists():z.write(p,name)
for p in (hero,D/'Window_Workflow_Comparison.png',archive):print(p,p.stat().st_size)
