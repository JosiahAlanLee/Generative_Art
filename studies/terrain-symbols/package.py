"""Create a compact visual comparison and a self-contained study archive."""
from pathlib import Path
import json,shutil,zipfile
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;O=R/'output';DIST=R/'dist';DIST.mkdir(exist_ok=True)

def make_comparison():
    paper='#eee7d6';im=Image.new('RGB',(1800,1510),paper);d=ImageDraw.Draw(im)
    font=str(R/'vendor/fonts/IBMPlexMono-Regular.ttf')
    f=ImageFont.truetype(font,19);title=ImageFont.truetype(font,29)
    d.text((38,24),'DRIFTLESS / EVALUATED BLENDER TERRAIN',font=title,fill='#3d4235')
    d.text((38,70),'Two cameras, one terrain host. Ground symbols fold; upright symbols keep their silhouettes.',font=f,fill='#625f4f')
    for i,name in enumerate(['main','low']):
        x=30+900*i
        d.text((x,120),'01  THREE-QUARTER VIEW' if i==0 else '02  LOWER CAMERA / MORE RIDGE OCCLUSION',font=f,fill='#3d4235')
        clay=Image.open(O/f'blender-{name}.png').convert('RGB').resize((840,630),Image.Resampling.LANCZOS)
        plate=Image.open(O/f'Terrain_{name}.png').convert('RGB').resize((840,630),Image.Resampling.LANCZOS)
        im.paste(clay,(x,158));im.paste(plate,(x,812))
    d.text((38,1465),'Cycles proof above / stroke-only engraving below. Native Blender ray audit: 4,800 samples, zero violations.',font=f,fill='#625f4f')
    im.save(DIST/'Terrain_Camera_Comparison.png')
    thumb=Image.open(O/'Terrain_main.png').convert('RGB');thumb.thumbnail((900,675))
    thumb.save(O/'preview.jpg',quality=85,optimize=True)

if __name__=='__main__':
    make_comparison()
    for name in ['main','low']:
        check=json.loads((O/f'checks-{name}.json').read_text())
        if not check['all_passed']:raise RuntimeError(f'{name} checks did not pass')
    sources=[p for p in R.rglob('*') if p.is_file() and not any(x in p.parts for x in ['__pycache__','dist','.git'])
             and not p.name.endswith(('.log','.blend1'))
             and p.name not in ['mapped-ground.json','mapped-plants.json']]
    archive=DIST/'Terrain_Symbols_Source.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(sources):z.write(p,'Terrain_Symbols/'+str(p.relative_to(R)))
        z.write(DIST/'Terrain_Camera_Comparison.png','Terrain_Symbols/output/Terrain_Camera_Comparison.png')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise RuntimeError('Archive verification failed')
    print(json.dumps({'archive':str(archive),'size':archive.stat().st_size,'files':len(sources)+1}))
