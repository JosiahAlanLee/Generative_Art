"""Package this camera variant without overwriting the earlier study."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json,shutil
from PIL import Image,ImageDraw,ImageFont

R=Path(__file__).resolve().parent;O=R/'output';D=R/'dist';D.mkdir(parents=True,exist_ok=True)
checks=json.loads((O/'checks.json').read_text());assert checks['all_passed']
if (O/'00-orthographic-reference.png').is_file():
 im=Image.new('RGB',(2400,970),'#eee7d6');draw=ImageDraw.Draw(im)
 font=ImageFont.truetype(str(R/'vendor/fonts/IBMPlexMono-Regular.ttf'),22)
 for k,(f,label) in enumerate([('00-orthographic-reference.png','BEFORE / ORTHOGRAPHIC'),('03-three-gates.png','AFTER / LOWER PERSPECTIVE')]):
  draw.text((30+k*1200,20),label,font=font,fill='#5a5c4b')
  p=Image.open(O/f);p.thumbnail((1170,878),Image.Resampling.LANCZOS);im.paste(p,(15+k*1200,73))
 im.save(O/'camera-comparison.png')
PNG=D/'Three_Gates_Perspective.png';shutil.copy2(O/'03-three-gates.png',PNG)
hashes={}
for p in R.rglob('*'):
 if p.is_file() and '__pycache__' not in p.parts and 'dist' not in p.relative_to(R).parts and p.name!='files.json':hashes[str(p.relative_to(R))]=hashlib.sha256(p.read_bytes()).hexdigest()
(O/'files.json').write_text(json.dumps(hashes,indent=2))
ZIP=D/'Three_Gates_Perspective_Source.zip'
with ZipFile(ZIP,'w',ZIP_DEFLATED,compresslevel=6) as z:
 for p in R.rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and 'dist' not in p.relative_to(R).parts and p.suffix!='.log':z.write(p,Path('Three_Gates_Perspective')/p.relative_to(R))
with ZipFile(ZIP) as z:assert z.testzip() is None
print(json.dumps({'image':str(PNG),'zip':str(ZIP),'zip_bytes':ZIP.stat().st_size,'checks':len(checks['checks'])},indent=2))
