"""Checks of model arithmetic, print dimensions, provenance and delivered rays."""
from pathlib import Path
import ast,hashlib,json,xml.etree.ElementTree as ET
import numpy as np
import build as B
from compile import compile_case,CASES
import occlusion as M

checks={}
def record(name,ok,**detail):checks[name]=dict(passed=bool(ok),**detail)

expected={'recorded_route':10,'rehearsed_route':5,'late_opening':11,'gate_unavailable':None}
record('specimen_arithmetic_preserved',all(compile_case(k)['result']['executable_completion']==v for k,v in expected.items()))
record('unavailability_not_reported_as_late_execution',compile_case('gate_unavailable')['result']['executable_completion'] is None)
record('release_time_not_added_to_duration',next(n for n in compile_case('late_opening')['nodes'] if n['id']=='approval')['bays']==1 and compile_case('late_opening')['result']['arithmetic_completion']==11)
native=json.loads((B.OUT/'blender-checks.json').read_text())
record('native_blender_camera',native['native_camera_max_error_px']<.002,maximum_error_px=native['native_camera_max_error_px'])
record('geometry_nodes_executed',all(x['faces']>0 for x in native['geometry_nodes']),objects=native['geometry_nodes'])
gate=[f['p'] for f in B.FACES if 'Unavailable portcullis' in f['name']]
roof=[f['p'] for f in B.FACES if 'approval roof' in f['name']]
record('closed_gate_fits_beneath_roof',not gate or max(p[:,2].max() for p in gate)<min(p[:,2].min() for p in roof))
for prefix in ('surface','hatch'):
    a=np.load(B.OUT/f'{prefix}-audit-{B.VIEW_NAME}.npz')['world'];seen=B.visible(a,*B.BVH[:6])
    record(prefix+'_delivered_samples_visible',seen.all(),samples=len(a),violations=int((~seen).sum()))
p=np.load(B.OUT/f'plants-audit-{B.VIEW_NAME}.npz')
record('plant_owners_respected',not (p['nearest_depth']<p['owner_depth']-M.EPS_PLANT).any(),samples=len(p['xy']))
# Adversarial fixture: place a mark at ground level beneath the approval tower.
n=next(n for n in B.D['architecture']['nodes'] if n['id']=='approval')
ground,ok,hit=B.drape([[n['x'],n['y']]])
record('injected_mark_under_building_rejected',ok.all() and not B.visible(ground,*B.BVH[:6]).any())
record('terrain_host_independent_of_architecture',B.height(n['x'],n['y'])<B.FACES[next(i for i,f in enumerate(B.FACES) if 'approval roof' in f['name'])]['p'][:,2].min())
extract=json.loads((B.ROOT/'vendor/extraction.json').read_text());s=(B.ROOT/'vendor/claude_hatching.py').read_text()
hashes={n.name:hashlib.sha256(ast.get_source_segment(s,n).encode()).hexdigest() for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
record('nine_hatching_bodies_unchanged',all(hashes[x['name']]==x['sha256'] for x in extract['functions']))
record('driftless_unchanged',hashlib.sha256((B.ROOT/'vendor/driftless-engine.js').read_bytes()).hexdigest()=='8ba687057284e68faf66521ec6eb543d27495fe8290095324f15201578a40020')
svg=B.OUT/f'Infernal_{B.CASE}_{B.VIEW_NAME}.svg';root=ET.parse(svg).getroot();text=svg.read_text()
record('stroke_only_svg',not any(x in text for x in ('<image','<mask','<clipPath','<rect')) and 'fill="none"' in text)
record('print_size_mm',root.attrib['width']=='156mm' and root.attrib['height']=='117.000mm')
manifest=json.loads((B.OUT/f'manifest-{B.VIEW_NAME}.json').read_text())
record('red_is_heaviest_line',manifest['red_heavier_than_black'])
record('shared_volume_and_planar_plants',manifest['plants']>20 and manifest['volume_leaf_faces']>1000,
       planar_instances=manifest['plants'],volume_leaf_faces=manifest['volume_leaf_faces'])
result=dict(case=B.CASE,view=B.VIEW_NAME,all_passed=all(x['passed'] for x in checks.values()),checks=checks)
(B.OUT/f'checks-{B.VIEW_NAME}.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if not result['all_passed']:raise SystemExit(1)
