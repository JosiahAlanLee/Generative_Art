"""Check the delivered vector plates, inherited renderer and book-specific limits."""
import ast, hashlib, json, os, re, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from PIL import Image
import engrave as E

O=E.OUT;tests={}
def record(name,passed,**extra):tests[name]={'passed':bool(passed),**extra}
root=ET.parse(O/(E.KEY+'.svg')).getroot();ns='{http://www.w3.org/2000/svg}'
ink='{http://www.inkscape.org/namespaces/inkscape}'
groups=root.findall(ns+'g');points=[];red=[]
for g in groups:
    for path in g.findall(ns+'path'):
        q=np.array([float(v) for v in re.findall(r'-?\d+(?:\.\d+)?',path.attrib['d'])]).reshape(-1,2)
        points.append(q)
        if g.attrib[ink+'label'].startswith('04 '):red.append(q)
record('stroke_only_svg_without_raster_or_opaque_masks',all(x.tag in [ns+'svg',ns+'title',ns+'g',ns+'path'] for x in root.iter()),layers=len(groups),paths=len(points))
p=np.vstack(points)
record('all_vector_coordinates_finite',np.isfinite(p).all())
record('printer_margin_clear',np.all((p[:,0]>=44)&(p[:,0]<=E.W-44)&(p[:,1]>=44)&(p[:,1]<=E.H-44)))
record('vermilion_accents_delivered',len(red)>0,paths=len(red),length_pixels=round(float(sum(np.linalg.norm(np.diff(q,axis=0),axis=1).sum() for q in red)),2))
if E.KEY in ['extraction-of-the-hand','office-without-a-seal']:
    record('no_border_in_original_borderless_brief',len(groups[-1])==0)
record('png_matches_exported_camera',Image.open(O/(E.KEY+'.png')).size==(E.W,E.H))
extract=json.loads((E.ROOT/'vendor/extraction.json').read_text());source=(E.ROOT/'vendor/claude_hatching.py').read_text()
hashes={n.name:hashlib.sha256(ast.get_source_segment(source,n).encode()).hexdigest() for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
record('nine_upstream_hatching_bodies_unchanged',all(hashes[x['name']]==x['sha256'] for x in extract['functions']),bodies=len(extract['functions']))
native=json.loads((O/'blender-checks.json').read_text())
record('independent_native_blender_checks',native['all_passed'],checks=len(native['checks']))
result={'plate':E.KEY,'all_passed':all(t['passed'] for t in tests.values()),'checks':tests}
(O/'checks.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if not result['all_passed']:raise SystemExit(1)
