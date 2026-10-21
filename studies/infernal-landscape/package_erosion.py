"""Matched preview, standalone plate, and a reproducible erosion source pack."""
from pathlib import Path
import hashlib,json,shutil,zipfile
import numpy as np
from PIL import Image,ImageDraw,ImageFont

R=Path(__file__).resolve().parent;O=R/'output';D=R/'dist';D.mkdir(exist_ok=True)
REPO=R.parents[1];MODES=('control','incised','ravined');PAPER='#ede6d4';INK='#242820';RED='#a32b24'


def comparison():
    images={m:Image.open(O/('recorded_route-'+m)/'Infernal_recorded_route_main.png').convert('RGB') for m in MODES}
    background=np.asarray([237,230,212]);bounds=[]
    for im in images.values():
        a=np.asarray(im,dtype=int);y,x=np.nonzero(np.max(abs(a-background),axis=2)>45)
        bounds.append((x.min(),y.min(),x.max()+1,y.max()+1))
    # The same crop and same scale preserve the matched camera comparison.
    crop=(max(0,min(b[0] for b in bounds)-35),max(0,min(b[1] for b in bounds)-35),
          min(3120,max(b[2] for b in bounds)+35),min(2340,max(b[3] for b in bounds)+35))
    tilew=1020;tileh=round(tilew*(crop[3]-crop[1])/(crop[2]-crop[0]))
    out=Image.new('RGB',(3180,tileh+255),PAPER);draw=ImageDraw.Draw(out)
    font=R/'vendor/fonts/IBMPlexMono-Regular.ttf';head=ImageFont.truetype(str(font),35);small=ImageFont.truetype(str(font),21)
    draw.text((38,24),'INFERNAL ENGINE / EROSION EXPOSURES',font=head,fill=INK)
    draw.text((38,80),'One initial terrain, task graph, camera and light. Black: land and drainage. Red: dependencies.',font=small,fill=INK)
    for i,m in enumerate(MODES):
        x=30+1055*i;steps={'control':0,'incised':36,'ravined':110}[m]
        draw.text((x,139),f'{i+1:02d}  {m.upper()} / {steps} ITERATIONS',font=small,fill=RED)
        out.paste(images[m].crop(crop).resize((tilew,tileh),Image.Resampling.LANCZOS),(x,183))
    draw.text((38,tileh+205),'Protected building pads; actual terrain incision. Iterations are dimensionless, not geological dates.',font=small,fill=INK)
    out.save(D/'Infernal_Erosion_Comparison.png')
    preview=out.copy();preview.thumbnail((1800,1100));preview.save(O/'erosion-preview.jpg',quality=88,optimize=True)
    images['incised'].crop(crop).save(D/'Infernal_Eroded_Estate.png')
    (D/'erosion-preview-settings.json').write_text(json.dumps(dict(common_crop=list(map(int,crop)),hero='incised',master_print_mm=[156,117]),indent=2))


def package():
    checks=json.loads((O/'erosion-validation.json').read_text())
    if not checks['all_passed']:raise RuntimeError('Comparison checks failed')
    files=[]
    for p in R.rglob('*'):
        if not p.is_file() or any(x in p.parts for x in ('__pycache__','dist')):continue
        if p.name.endswith(('.log','.blend1','.pyc','.nbc','.nbi')):continue
        relative=p.relative_to(R)
        if relative.parts[0]=='output' and len(relative.parts)>1:
            if relative.parts[1] not in ['recorded_route-'+m for m in MODES] and p.name not in ('erosion-preview.jpg','erosion-validation.json'):continue
        files.append((p,'studies/infernal-landscape/'+str(relative)))
    for name in ('__init__.py','models.py','terrain.py'):
        p=REPO/'lib/process_art'/name;files.append((p,'lib/process_art/'+name))
    p=REPO/'lib/process_art/tests/test_terrain.py';files.append((p,'lib/process_art/tests/test_terrain.py'))
    for name in ('NOTICES.md','requirements-process-art.txt'):
        p=REPO/name
        if p.exists():files.append((p,name))
    for p in D.glob('Infernal_Ero*.png'):files.append((p,p.name))
    files.append((D/'erosion-preview-settings.json','erosion-preview-settings.json'))
    manifest={name:hashlib.sha256(p.read_bytes()).hexdigest() for p,name in files}
    (D/'erosion-manifest.json').write_text(json.dumps(manifest,indent=2))
    target=D/'Infernal_Erosion_Study_Source.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,name in sorted(files,key=lambda q:q[1]):z.write(p,'Infernal_Erosion/'+name)
        z.write(D/'erosion-manifest.json','Infernal_Erosion/manifest.json')
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
    print(json.dumps(dict(archive=str(target),bytes=target.stat().st_size,files=len(files)+1)))


if __name__=='__main__':comparison();package()
