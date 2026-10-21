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
# Marks behind the masonry remain hidden; the removed timber leaves open rays.
fixtures=[('left_jamb',[-4.,-6.1,6]),('right_jamb',[4.,-6.1,6]),
          ('head',[0.,-6.1,10.5]),('sill',[0.,-6.1,3.8])]
for name,q in fixtures:
    p=B.EYE+2.5*(np.asarray(q)-B.EYE)
    record('reject_mark_behind_'+name,not B.visible(p[None,:],*B.BVH[:6])[0])
for name,p in [('opening',[1.,-5.1,7.]),('former_mullion',[-1.795,-5.1,6.]),('former_transom',[1.,-5.1,8.7])]:
    record(name+'_is_open',B.visible(np.asarray([p]),*B.BVH[:6])[0])
record('timber_frame_removed',not any(n.startswith(('Window timber','Window mullion','Window transom')) for n in B.D['names']))
from window import DOOR_X,WHEEL_X,WHEEL_Y,river_y,water_z
steps=np.vstack([f['p'] for f in B.FACES if f['name'].startswith('mill approach step')])
door=np.vstack([f['p'] for f in B.FACES if f['name'].startswith('mill door')])
record('stairs_centered_on_door',abs((steps[:,0].min()+steps[:,0].max())/2-(door[:,0].min()+door[:,0].max())/2)<1e-5)
roof_ids=[i for i,n in enumerate(B.D['names']) if n=='mill porch roof']
roof_normals=np.asarray(B.D['normals'])[roof_ids]
record('porch_roof_outward_normals',len(roof_ids)==4 and roof_normals[0,1]<-.99 and (roof_normals[2:,2]>0).all())
wheel=np.vstack([f['p'] for f in B.FACES if f['name'].startswith('mill wheel rim')])
water_level=float(water_z(WHEEL_X))
record('wheel_intersects_stream',abs(float(river_y(WHEEL_X))-WHEEL_Y)<1e-5 and wheel[:,2].min()<water_level and wheel[:,2].min()>water_level-.2,immersion=float(water_level-wheel[:,2].min()))
q=np.linspace(-15,14,101);river=np.c_[q,river_y(q),water_z(q)+.02]
seen=B.visible(river,*B.BVH[:6]);record('stream_visible',int(seen.sum())>20,visible_samples=int(seen.sum()))
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
