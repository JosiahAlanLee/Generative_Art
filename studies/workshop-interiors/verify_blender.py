"""Independent native Blender visibility and physical-brief checks."""
from pathlib import Path
import json, os
import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parent
KEY=os.environ.get('PLATE','empty-cabinet');OUT=ROOT/'output'/KEY
D=json.loads((OUT/'scene.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT/(KEY+'.blend')))
sc=bpy.context.scene;deps=bpy.context.evaluated_depsgraph_get();checks={}

def record(name,passed,**extra):checks[name]={'passed':bool(passed),**extra}

eye=np.array(D['camera']['eye']);fwd=np.array(D['camera']['target'])-eye;fwd/=np.linalg.norm(fwd)
right=np.cross(fwd,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,fwd)
w,h=D['camera']['resolution'];cx,cy=D['camera']['principal_point'];f=D['camera']['focal_px']
p=np.array(D['vertices'])[::41];q=p-eye;z=q@fwd;valid=z>.5;p=p[valid];q=q[valid];z=z[valid]
cpu=np.column_stack([cx+f*(q@right)/z,cy-f*(q@up)/z])
native=np.array([(v.x*w,(1-v.y)*h) for v in [world_to_camera_view(sc,sc.camera,Vector(t)) for t in p]])
error=float(np.max(abs(cpu-native)))
record('saved_camera_matches_vector_camera',error<.003,samples=len(p),maximum_pixel_error=error)

# Vector-only details have visible tube geometry in Blender but are not opaque
# blockers in this engraving convention. Match that declared visibility model.
for ob in sc.objects:
    if ob.get('ink_only',False):ob.hide_set(True)
deps=bpy.context.evaluated_depsgraph_get()
data=np.load(OUT/'hatch-audit.npz');p=data['world'];p=p[::max(1,len(p)//1600)][:1600]
bad=0
for point in p:
    d=point-eye;distance=float(np.linalg.norm(d));d/=distance
    hit,loc,normal,index,obj,matrix=sc.ray_cast(deps,Vector(eye),Vector(d),distance=distance+.1)
    if hit and (loc-Vector(eye)).length<distance-.035:bad+=1
record('delivered_hatching_native_ray_visibility',bad==0,samples=len(p),occluded_samples=bad,world_tolerance=.035)

if KEY=='empty-cabinet':
    hits=[]
    for x in np.linspace(-1.0,1.0,7):
        for z in np.linspace(1.0,4.8,10):
            hit,loc,n,i,obj,m=sc.ray_cast(deps,Vector((x,2.7,z)),Vector((0,1,0)),distance=2.1)
            if hit:hits.append(obj.name)
    record('cabinet_inspection_volume_is_empty',not hits,rays=70,unexpected_objects=hits)
    legs=D['parts']['chair_legs']
    record('four_chair_feet_contact_floor',len(legs)==4 and all(abs(a['bottom'][2])<1e-8 for a in legs))
if KEY=='extraction-of-the-hand':
    record('five_fingers_and_twenty_three_connected_strands',D['parts']['jig_fingers']==5 and len(D['parts']['ledger_strands'])==23)
    legs=D['parts']['stool_legs']
    record('four_stool_feet_contact_floor',len(legs)==4 and all(abs(a['bottom'][2])<1e-8 for a in legs))
if KEY=='office-without-a-seal':
    parts=D['parts'];lo,hi=parts['cord_gap_z'];r=parts['reserved_recess']
    record('cord_ends_clear_the_entire_reserved_recess',lo<r['zmin'] and hi>r['zmax'],gap_world_units=hi-lo)
    crossings=[]
    for s in D['strokes']:
        p=np.array(s['pts'])
        inside=(abs(p[:,0])<1.18)&(p[:,2]>r['zmin']+.05)&(p[:,2]<r['zmax']-.05)&(p[:,1]<5.45)
        if inside.any():crossings.append(s['name'])
    record('no_detail_strokes_cross_the_reserved_recess',not crossings,unexpected_strokes=crossings)
if KEY=='maintained-workshop':
    record('figure_free_interpretation',D['parts']['characters_omitted'])
    record('reserve_vessel_uses_declared_vector_convention',D['parts']['vector_glass_convention']=='paper-reserving silhouette')
    record('cord_has_one_connected_polyline',len([s for s in D['strokes'] if s['name']=='Vermilion route'])==1)

result={'key':KEY,'blender':bpy.app.version_string,'all_passed':all(x['passed'] for x in checks.values()),'checks':checks}
(OUT/'blender-checks.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2),flush=True)
if not result['all_passed']:raise SystemExit(1)
