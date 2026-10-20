"""Adversarial visibility checks against the delivered evaluated Blender mesh."""
import ast, hashlib, json, os
from pathlib import Path
import numpy as np
import build as B
import occlusion as M

R=Path(__file__).resolve().parent;O=R/'output';tests={}
def record(name,passed,**detail):tests[name]={'passed':bool(passed),**detail}

# Independent Blender-native camera evidence is recorded during model export.
native=json.loads((O/'blender-checks.json').read_text())
record('native_blender_camera_agreement',native['native_camera_max_error_px']<.002,maximum_error_px=native['native_camera_max_error_px'])

# Host projection must hit the evaluated displacement, not the analytic source.
xy=np.array([[-7,5],[3,8],[0,16],[7,-2],[4.4,8.2],[-2.8,10],[-1,14]],float)
P,ok,hit=B.drape(xy,0)
def source_height(x,y):
    return .65+.025*y+.55*np.sin(x*.22+y*.10)+2.35*np.exp(-((y-11-.24*x)/3.3)**2)+1.15*np.exp(-((y-27+.18*x)/6)**2)+.17*np.cos(x*.55-y*.27)
error=np.abs(P[:,2]-source_height(xy[:,0],xy[:,1]))
record('drape_uses_modified_terrain',ok.all() and error.max()>.005,maximum_difference_from_unmodified_formula=float(error.max()))
# Each hit must lie on its actual returned triangle plane, not a bilinear shortcut.
res=np.abs(np.einsum('ij,ij->i',P-B.TBVH[3][hit],B.TBVH[7][hit]))
record('drape_lies_on_evaluated_triangle',ok.all() and res.max()<1e-8,max_plane_error=float(res.max()))
roofxy=np.array([[4.4,8.2]])
ground,_,_=B.drape(roofxy,0)
origins=np.column_stack([roofxy,[45.]])
t,h=B.rc.first_hits(origins,np.array([[0.,0.,-1.]]),100.,*B.BVH[:6]);top=45-t[0]
record('host_projection_never_lands_on_barn_roof',top-ground[0,2]>3,roof_z=float(top),ground_z=float(ground[0,2]))
missing,ok,_=B.drape([[500,500]])
record('host_miss_is_a_gap',not ok.any() and np.isnan(missing).all())

# Re-test delivered ground points with the model; this includes both crest
# self-occlusion and architectural blockers. Deliberately buried points fail.
a=np.load(O/f'surface-audit-{B.VIEW_NAME}.npz');world=a['world']
seen=B.visible(world,*B.BVH[:6]);record('all_delivered_ground_samples_visible',seen.all(),samples=len(world),violations=int((~seen).sum()))
injected=ground+np.array([[0,0,.006]])
record('injected_mark_behind_barn_is_rejected',not B.visible(injected,*B.BVH[:6]).any())
# Native Blender scene ray_cast results provide independent spot checks; these
# are run after mapping and are stored by verify_blender.py.
independent=json.loads((O/'blender-visibility.json').read_text())
record('blender_native_rays_agree',independent['visible_violations']==0 and independent['buried_fixture_blocked'],**independent)

hatch=np.load(O/f'hatch-audit-{B.VIEW_NAME}.npz')['world'];seen=B.visible(hatch,*B.BVH[:6])
record('delivered_hatches_respect_model',seen.all(),samples=len(hatch),violations=int((~seen).sum()))
plants=np.load(O/f'plants-audit-{B.VIEW_NAME}.npz')
bad=plants['nearest_depth']<plants['owner_depth']-M.EPS_PLANT
record('delivered_plants_respect_owner_depth',not bad.any(),samples=len(bad),violations=int(bad.sum()))

# Adversarial overlap: reversing input order must not reveal the farther owner.
def patch(pen):return {'occluders':[{'t':'rings','rings':[[-12.,-12.,12.,-12.,12.,12.,-12.,12.]]}],'strokes':[{'pts':[-10.,0.,10.,0.],'pen':pen}]}
root=B.EYE+B.FWD*25
near=M.Instance(patch(0),(0,0),root,.1,.65)
far=M.Instance(patch(2),(0,0),root+(root-B.EYE)*.04,.1,.65)
buf=np.full((B.H*M.K,B.W*M.K),np.inf);M.stamp(buf,near);M.stamp(buf,far)
one=M.plant_strokes([near,far],buf);two=M.plant_strokes([far,near],buf)
record('plant_order_does_not_reveal_far_owner',len(one[2])==len(two[2])==0 and len(one[0])>0 and len(two[0])>0)
record('illegal_owner_sample_is_detected',bool((M.lookup(buf,far.screen([[0,0]]))<far.c-M.EPS_PLANT)[0]))

# Verify a whole-view plane ordering property, and analytic camera derivatives.
screen=np.array([[0,0],[B.W,0],[B.W,B.H],[0,B.H],[B.W/2,B.H/2]],float)
origins,dirs=B.primary_rays(screen);sx,sy,z=B.project(origins+dirs*50)
record('camera_rays_roundtrip',np.max(abs(np.column_stack([sx,sy])-screen))<1e-8)
record('parallel_plant_planes_order_over_whole_frustum',(dirs@M.NORMAL>0).all())
points=np.array([[-5,0,3],[0,8,4],[6,12,7]],float)
u=np.broadcast_to([.7,.2,.3],points.shape);v=np.broadcast_to([-.2,.8,.1],points.shape)
j=B.jac(points,u,v);numeric=np.empty_like(j);eps=1e-5
for k,d in enumerate([u,v]):
    a=B.project(points+eps*d);b=B.project(points-eps*d)
    numeric[:,0,k]=(a[0]-b[0])/(2*eps);numeric[:,1,k]=(a[1]-b[1])/(2*eps)
record('perspective_hatch_spacing_jacobian',np.max(abs(j-numeric))<1e-5)

extract=json.loads((R/'vendor/extraction.json').read_text());source=(R/'vendor/claude_hatching.py').read_text()
hashes={n.name:hashlib.sha256(ast.get_source_segment(source,n).encode()).hexdigest() for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
record('unchanged_claude_hatching_bodies',all(hashes[x['name']]==x['sha256'] for x in extract['functions']))
record('unchanged_driftless_engine',hashlib.sha256((R/'vendor/driftless-engine.js').read_bytes()).hexdigest()=='8ba687057284e68faf66521ec6eb543d27495fe8290095324f15201578a40020')
s=(O/f'Terrain_{B.VIEW_NAME}.svg').read_text()
record('stroke_only_vector',all(x not in s for x in ['<image','<rect','<mask','<clipPath']) and 'fill="none"' in s)
info=json.loads((O/f'manifest-{B.VIEW_NAME}.json').read_text())
record('study_exercises_real_occlusion',all(info['surface'][k]['hidden_by_model']>100 for k in ['field','rosette']),**info['surface'])
out={'view':B.VIEW_NAME,'all_passed':all(x['passed'] for x in tests.values()),'checks':tests}
(O/f'checks-{B.VIEW_NAME}.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if not out['all_passed']:raise SystemExit(1)
