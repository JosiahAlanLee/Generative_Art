"""Test the new aperture, erosion, delivered rays and unchanged drawing engines."""
import ast,hashlib,json,xml.etree.ElementTree as ET
import numpy as np
import build as B
import occlusion as M
checks={}
def record(n,ok,**detail):checks[n]={'passed':bool(ok),**detail}
for prefix in ('surface','hatch'):
    a=np.load(B.OUT/f'{prefix}-audit-main.npz')['world'];seen=B.visible(a,*B.BVH[:6])
    record(prefix+'_visible',seen.all(),samples=len(a),violations=int((~seen).sum()))
p=np.load(B.OUT/'plants-audit-main.npz')
record('plant_ownership',not (p['nearest_depth']<p['owner_depth']-M.EPS_PLANT).any(),samples=len(p['xy']))
# Deliberately put marks behind the jamb, mullion and transom. The marks are
# on the same camera rays as those physical blockers, beyond the entire window.
fixtures=[('left_jamb',[-4.0,-6.1,6]),('right_jamb',[4.,-6.1,6]),
          ('mullion',[-1.795,-5.56,6]),('transom',[1.,-5.56,8.70])]
for name,q in fixtures:
    p=B.EYE+2.5*(np.asarray(q)-B.EYE)
    record('reject_mark_behind_'+name,not B.visible(p[None,:],*B.BVH[:6])[0])
# A sightline through the open right pane must remain open up to the landscape.
p=np.array([[1.,-5.1,7.]])
record('open_pane_is_open',B.visible(p,*B.BVH[:6])[0])
native=json.loads((B.OUT/'blender-checks.json').read_text())
record('native_camera',native['native_camera_max_error_px']<.002,error_px=native['native_camera_max_error_px'])
bridge=np.vstack([f['p'] for f in B.FACES if f['name'].startswith('Bridge stringer')])
record('bridge_reaches_exterior_sill',bridge[:,1].min()<=-5.3+1e-5 and bridge[:,1].max()>=11.2-1e-5, near_y=float(bridge[:,1].min()),far_y=float(bridge[:,1].max()))
record('geometry_nodes',len(native['geometry_nodes'])==1 and native['geometry_nodes'][0]['faces']>0)
vis=json.loads((B.OUT/'blender-visibility.json').read_text())
record('independent_blender_rays',vis['visible_violations']==0,**vis)
s=dict(np.load(B.OUT/'terrain-state.npz'))
record('erosion_changed_ground',float(s['incision_history'].sum())>0)
record('foundation_pad_preserved',np.array_equal(s['height'][s['fixed_mask']],s['initial'][s['fixed_mask']]))
text=(B.OUT/'Infernal_window_main.svg').read_text();root=ET.fromstring(text)
record('stroke_only',not any(x in text for x in ('<image','<mask','<clipPath','<rect')))
record('print_size',root.attrib['width']=='156mm' and root.attrib['height']=='117.000mm')
record('driftless_unchanged',hashlib.sha256((B.ROOT/'vendor/driftless-engine.js').read_bytes()).hexdigest()=='8ba687057284e68faf66521ec6eb543d27495fe8290095324f15201578a40020')
extract=json.loads((B.ROOT/'vendor/extraction.json').read_text());source=(B.ROOT/'vendor/claude_hatching.py').read_text()
hashes={n.name:hashlib.sha256(ast.get_source_segment(source,n).encode()).hexdigest() for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
record('nine_hatch_bodies_unchanged',all(hashes[x['name']]==x['sha256'] for x in extract['functions']))
result={'all_passed':all(x['passed'] for x in checks.values()),'checks':checks}
(B.OUT/'window-validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if not result['all_passed']:raise SystemExit(1)
