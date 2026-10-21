"""Package source, actual CMYK separations, two views and editable Blender terrain."""
from pathlib import Path
import json,zipfile
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;O=R/'output';D=R/'dist';D.mkdir(exist_ok=True)
if __name__=='__main__':
    for view in ['main','low']:
        assert json.loads((O/f'checks-{view}.json').read_text())['all_passed']
    thumb=Image.open(O/'Prairie_CMYK.png').convert('RGB');thumb.thumbnail((900,600));thumb.save(O/'preview.jpg',quality=85,optimize=True)
    comparison=Image.new('RGB',(2000,780),'#f9f4e8');draw=ImageDraw.Draw(comparison)
    font=ImageFont.truetype(str(R/'vendor/fonts/IBMPlexMono-Regular.ttf'),23)
    for k,(name,label) in enumerate([('Prairie_CMYK','PRAIRIE / THREE-QUARTER VIEW'),('Prairie_CMYK_Low','LOWER CAMERA / RIDGE OCCLUSION')]):
        draw.text((25+1000*k,22),label,font=font,fill='#363b32')
        im=Image.open(O/f'{name}.png').convert('RGB');im.thumbnail((970,647));comparison.paste(im,(15+1000*k,80))
    comparison.save(O/'Prairie_Camera_Comparison.png')
    files=[p for p in R.rglob('*') if p.is_file() and not any(x in p.parts for x in ['dist','__pycache__']) and not p.name.endswith(('.log','.blend1'))]
    target=D/'Prairie_Bluffs_CMYK_Source.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):z.write(p,'Prairie_Bluffs_CMYK/'+str(p.relative_to(R)))
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    print(json.dumps({'archive':str(target),'bytes':target.stat().st_size,'files':len(files)}))
