"""Geometry, source identity and owner-aware occlusion regression checks."""
from pathlib import Path
import ast,hashlib,json
import numpy as np
from PIL import Image
import build as B
import occlusion as M
from render import place

R=Path(__file__).resolve().parent;O=R/'output';tests={}
def record(name,passed,**detail):tests[name]={'passed':bool(passed),**detail}

# Downward primary rays test the actual channel surface, ramp and triangulated ground.
xy=np.array([[-9.,-5.],[-8.,4.],[-9.,9.],[9.7,-3.],[0.,-6.],[0.,-1.],[0.,5.8]])
orig=np.column_stack([xy,np.full(len(xy),25.)]);dirs=np.tile([0.,0.,-1.],(len(xy),1))
t,hit=B.rc.first_hits(orig,dirs,100.,*B.BVH[:6]);got=25-t
expected=B.height(xy[:,0],xy[:,1]);expected[-3:]=B.water_height(xy[-3:,1]);err=float(np.max(abs(got-expected)))
record('terrain_pool_and_apron_intersections',np.all(hit>=0) and err<1e-6,max_height_error=err)

# The bridge spans all pier centers, with a positive vertical intersection at every support.
pier=[f for f in B.FACES if f['name']=='gate pier'];deck=[f for f in B.FACES if f['name']=='timber footbridge']
p=np.vstack([f['p'] for f in pier]);d=np.vstack([f['p'] for f in deck])
record('bridge_bears_on_piers',p[:,2].max()>=d[:,2].min() and d[:,0].min()<p[:,0].min() and d[:,0].max()>p[:,0].max(),pier_top=float(p[:,2].max()),deck_underside=float(d[:,2].min()))
record('gate_racks_connect_to_leaves',all(any(f['name']=='lifting rack' and abs(f['p'][:,0].mean()-cx)<.04 and f['p'][:,2].min()<bottom+1.6 and f['p'][:,2].max()>6.1 for f in B.FACES) for cx,bottom in zip(B.GATE_CENTERS,B.GATE_BOTTOMS)))

# Regression fixture: two distinct owners project to the same image location on different planes.
def patch(pen):return {'occluders':[{'t':'rings','rings':[[-12.,-12.,12.,-12.,12.,12.,-12.,12.]]}],'strokes':[{'pts':[-10.,0.,10.,0.],'pen':pen}]}
root=np.array([0.,-5.,6.5]);near=M.Instance(patch(0),(0.,0.),root,.1,.65);far=M.Instance(patch(2),(0.,0.),root+(root-B.EYE)*.02,.1,.65)
buf=np.full((B.H*M.K,B.W*M.K),np.inf);M.stamp(buf,near);M.stamp(buf,far)
pens=M.plant_strokes([far,near],buf)
fb=np.full_like(buf,np.inf);M.stamp(fb,far);solo=M.plant_strokes([far],fb)
record('near_plant_hides_far_owner_independent_of_input_order',len(solo[2])>0 and len(pens[2])==0 and len(pens[0])>0,far_alone_paths=len(solo[2]),far_with_near_paths=len(pens[2]))
# A deliberately illegal far-owner point MUST be detected by the owner-aware assertion.
xy=far.screen([[0.,0.]])
record('occlusion_check_detects_injected_hidden_stroke',bool((M.lookup(buf,xy)<far.c-M.EPS_PLANT)[0]))
# The analytic projective Jacobian must agree with numerical derivatives away from the near plane.
points=np.array([[-5.,0.,3.],[0.,2.,4.],[6.,5.,7.],[1.,-4.,.5]])
u=np.broadcast_to(np.array([.7,.2,.3]),points.shape);v=np.broadcast_to(np.array([-.2,.8,.1]),points.shape)
j=B.jac(points,u,v);numeric=np.empty_like(j);eps=1e-5
for k,direction in enumerate([u,v]):
 plus=B.project(points+eps*direction);minus=B.project(points-eps*direction)
 numeric[:,0,k]=(plus[0]-minus[0])/(2*eps);numeric[:,1,k]=(plus[1]-minus[1])/(2*eps)
error=float(np.max(abs(j-numeric)));record('perspective_hatch_jacobian',error<1e-5,max_error_px_per_world=error)
screen=np.array([[50.,50.],[B.W-50.,50.],[B.W*.5,B.H*.5],[50.,B.H-50.],[B.W-50.,B.H-50.]])
origins,dirs=B.primary_rays(screen);world=origins+dirs*np.array([20.,27.,40.,35.,22.])[:,None]
sx,sy,depth=B.project(world);error=float(np.max(abs(np.column_stack([sx,sy])-screen)))
record('perspective_ray_projection_roundtrip',error<1e-8,max_pixel_error=error)
record('plane_depth_orders_all_camera_rays',np.all(dirs@M.NORMAL>0),minimum_normal_dot_ray=float(np.min(dirs@M.NORMAL)))
# Perspective must shrink equal world spans when farther along the SAME image ray.
center=B.EYE+B.FWD*30.;back=B.EYE+B.FWD*60.
sx1=B.project(np.vstack([center-B.RIGHT,center+B.RIGHT]))[0];sx2=B.project(np.vstack([back-B.RIGHT,back+B.RIGHT]))[0]
ratio=float(np.diff(sx1)[0]/np.diff(sx2)[0]);record('distance_changes_projected_scale',abs(ratio-2)<1e-10,near_far_size_ratio=ratio)
audit=np.load(O/'occlusion-audit.npz')
bad=audit['nearest_depth']<audit['owner_depth']-M.EPS_PLANT
record('delivered_plant_samples_respect_owner_depth',len(bad)>1000 and not bad.any(),samples=len(bad),violations=int(bad.sum()))

# Recompute full placements, not merely their count.
patches=json.loads((O/'plants.json').read_text());a=place(patches);manifest=json.loads((O/'manifest.json').read_text())
positions=[{'kind':i.patch['kind'],'root':i.root.tolist(),'scale':i.s} for i in a]
record('all_plant_placements_reproduce',positions==manifest['plant_placements'],instances=len(positions))
root_errors=[abs(i.root[2]-float(B.height(*i.root[:2]))-.02) for i in a]
record('all_plants_rooted_on_triangle_surface',max(root_errors)<1e-9,max_root_height_error=float(max(root_errors)))

extract=json.loads((R/'vendor/extraction.json').read_text());source=(R/'vendor/claude_hatching.py').read_text()
hashes={n.name:hashlib.sha256(ast.get_source_segment(source,n).encode()).hexdigest() for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
record('unchanged_hatching_bodies',all(hashes[x['name']]==x['sha256'] for x in extract['functions']),bodies=len(extract['functions']))
record('unchanged_driftless_engine',hashlib.sha256((R/'vendor/driftless-engine.js').read_bytes()).hexdigest()==manifest['engine_sha256'])
record('stroke_only_svg',all('<image' not in (O/f).read_text() and '<rect' not in (O/f).read_text() for f in ['02-engraved.svg','03-three-gates.svg','04-landscape.svg']))
record('matched_image_frames',all(Image.open(O/f).size==(B.W,B.H) for f in ['01-massing.png','02-engraved.png','03-three-gates.png']))
record('blender_script_syntax',bool(ast.parse((R/'open_in_blender.py').read_text())))
out={'all_passed':all(t['passed'] for t in tests.values()),'checks':tests};(O/'checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if not out['all_passed']:raise SystemExit(1)
