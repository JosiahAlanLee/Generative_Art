"""Execute engraving again from unchanged scene.json and compare exact SVG bytes."""
from pathlib import Path
import os,sys,json,subprocess,hashlib
R=Path(__file__).resolve().parent;key=os.environ.get('PLATE','empty-cabinet');O=R/'output/v2'/key
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
before=digest(O/(key+'.svg'));scene=digest(O/'scene.json')
with (O/'regeneration.log').open('w') as log:
    subprocess.run([sys.executable,str(R/'engrave.py')],check=True,env=os.environ.copy(),stdout=log,stderr=subprocess.STDOUT)
after=digest(O/(key+'.svg'));scene_after=digest(O/'scene.json')
result={'passed':before==after and scene==scene_after,'svg_before_sha256':before,'svg_after_sha256':after,'scene_sha256':scene,'scene_unchanged':scene==scene_after,'renderer_sha256':digest(R/'render_v2.py')}
(O/'regeneration-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if not result['passed']:raise SystemExit(1)
