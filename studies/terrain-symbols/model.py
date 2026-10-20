"""Executed Blender terrain and barn; exports evaluated triangles for the ink renderer.

Run with Blender 4.5 LTS: blender -b -P model.py (or the official bpy wheel).
This script creates a new scene; it does not erase an open Blender document.
"""
from pathlib import Path
import json, math, os
import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
SC = bpy.data.scenes.new('Driftless | terrain and symbols')
bpy.context.window.scene = SC
W, H = 2100, 1575
STROKES = []
COLORS = ['#c2b594', '#c6bda4', '#646452', '#8e4937', '#7b7863', '#d6c9aa']
MATERIALS = []
for name, col in zip(['Ground', 'Limestone', 'Timber', 'Oxide', 'Roof', 'Track'], COLORS):
    mat = bpy.data.materials.new('Terrain study | ' + name)
    mat.diffuse_color = tuple(int(col[k:k+2],16)/255 for k in [1,3,5]) + (1.,)
    mat.use_nodes = True
    p = mat.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = mat.diffuse_color
    p.inputs['Roughness'].default_value = .87
    MATERIALS.append(mat)

def terrain_z(x, y):
    return (.65 + .025*y + .55*np.sin(x*.22+y*.10)
            + 2.35*np.exp(-((y-11-.24*x)/3.3)**2)
            + 1.15*np.exp(-((y-27+.18*x)/6)**2)
            + .17*np.cos(x*.55-y*.27))

def mesh(name, verts, faces, mat=1, hatch=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    SC.collection.objects.link(ob)
    ob.data.materials.append(MATERIALS[mat])
    ob['hatch'] = hatch
    return ob

def box(name, lo, hi, mat=1):
    x,y,z=lo; X,Y,Z=hi
    p=[(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)]
    f=[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    return mesh(name,p,f,mat)

def beam(name,a,b,w=.09,mat=2):
    a,b=Vector(a),Vector(b); d=b-a
    bpy.ops.mesh.primitive_cube_add(size=1,location=(a+b)/2)
    o=bpy.context.object; o.name=name; o.scale=(w,w,d.length)
    o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    o.data.materials.append(MATERIALS[mat]);o['hatch']=True
    return o

def ink(name, pts, width=.6, pen=0):
    STROKES.append({'name':name,'pts':np.asarray(pts,float).tolist(),'width':width,'ink':pen})

# One welded, consistently triangulated terrain. A real evaluated displacement
# modifier is included so the draper cannot silently use only the source formula.
GX=np.linspace(-30,30,151); GY=np.linspace(-22,49,179)
xx,yy=np.meshgrid(GX,GY); zz=terrain_z(xx,yy)
vs=np.column_stack([xx.ravel(),yy.ravel(),zz.ravel()]).tolist(); fs=[]
for j in range(len(GY)-1):
    for i in range(len(GX)-1):
        a=j*len(GX)+i;b=a+1;c=b+len(GX);d=a+len(GX)
        fs.extend([(a,b,c),(a,c,d)])
terrain=mesh('Host terrain',vs,fs,0,False)
tex=bpy.data.textures.new('Low stone undulation',type='CLOUDS')
tex.noise_scale=2.3;tex.noise_depth=1
mod=terrain.modifiers.new('Evaluated surface detail','DISPLACE')
mod.texture=tex;mod.strength=.12;mod.mid_level=.5
SC['terrain_source']='Evaluated Host terrain, including Displace modifier'

# A modest gambrel barn, with continuous wall / roof / foundation joins.
cx,cy=4.4,8.2; half=2.25; depth=4.4
base=float(terrain_z(cx,cy))-.12
z=base+.52; eave=z+2.6; shoulder=eave+1.05; ridge=eave+1.68
box('Barn limestone foundation',(cx-half-.10,cy-depth/2-.1,base-.60),(cx+half+.1,cy+depth/2+.1,z),1)
box('Barn wall',(cx-half,cy-depth/2,z),(cx+half,cy+depth/2,eave),3)
section=[(-half,eave),(-1.45,shoulder),(0,ridge),(1.45,shoulder),(half,eave)]
for y,flip in [(cy-depth/2,True),(cy+depth/2,False)]:
    ring=[(cx+x,y,h) for x,h in section]+[(cx+half,y,eave-.03),(cx-half,y,eave-.03)]
    mesh('Barn gable',ring[::-1] if flip else ring,[tuple(range(len(ring)))],3)
for (x,a),(X,b) in zip(section,section[1:]):
    mesh('Barn folded roof',[(cx+x-.02,cy-depth/2-.24,a+.04),(cx+X+.02,cy-depth/2-.24,b+.04),
         (cx+X+.02,cy+depth/2+.24,b+.04),(cx+x-.02,cy+depth/2+.24,a+.04)],[(0,1,2,3)],4)
    ink('Roof course',[(cx+x,cy-depth/2-.25,a+.065),(cx+X,cy-depth/2-.25,b+.065)],.95)
    for q in np.linspace(.1,.9,7):
        px=(1-q)*x+q*X; pz=(1-q)*a+q*b+.065
        ink('Standing seam',[(cx+px,cy-depth/2-.25,pz),(cx+px,cy+depth/2+.25,pz)],.42)
front=cy-depth/2-.015
for dx in np.arange(-half+.14,half,.21):
    ink('Barn siding',[(cx+dx,front,z+.03),(cx+dx,front,eave-.04)],.46)
for y in np.arange(cy-depth/2+.1,cy+depth/2,.23):
    ink('Barn side boards',[(cx+half+.012,y,z+.03),(cx+half+.012,y,eave-.04)],.43)
box('Double barn door',(cx-.92,front-.08,z),(cx+.92,front-.015,z+2.10),2)
for dx in [-.92,0,.92]:ink('Door upright',[(cx+dx,front-.09,z),(cx+dx,front-.09,z+2.1)],.8)
for a,b in [(-.87,-.04),(.04,.87)]:
    ink('Door diagonal',[(cx+a,front-.091,z+.08),(cx+b,front-.091,z+2.02)],.8)
box('Door lintel',(cx-1.04,front-.12,z+2.08),(cx+1.04,front-.03,z+2.22),1)
# A small open gable vent is a modeled recess facade, rather than a floating sign.
box('Gable vent',(cx-.25,front-.04,eave+.20),(cx+.25,front-.015,eave+.61),2)
for dz in [.29,.39,.49]:ink('Vent slat',[(cx-.25,front-.045,eave+dz),(cx+.25,front-.045,eave+dz)],.55)

# The fence intentionally crosses both terrain marks and upright plant symbols.
posts=[]
for x in np.arange(-12,12.01,1.6):
    y=3.4+.10*x;h=float(terrain_z(x,y))-.13
    beam('Fence post',(x,y,h),(x+.025,y,h+1.18),.12)
    posts.append(np.array([x,y,h]))
for a,b in zip(posts,posts[1:]):
    for h in [.46,.94]:beam('Fence rail',a+[0,0,h],b+[0,0,h],.075)

# Two actual stone markers emphasize depth and give ground motifs narrow blockers.
for x,y,w,h in [(-4.3,8.7,.48,1.6),(-2.5,12.2,.38,1.35)]:
    b=float(terrain_z(x,y))-.16
    box('Field stone',(x-w/2,y-.2,b),(x+w/2,y+.2,b+h),1)

CAMERAS={}
for name,eye,target,focal in [('main',(18,-30,14.5),(0,8,2.3),3000.),
                              ('low',(9,-31,8.8),(0,9,2.1),3000.)]:
    d=bpy.data.cameras.new('Terrain '+name);o=bpy.data.objects.new('Camera '+name,d);SC.collection.objects.link(o)
    o.location=eye;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    d.type='PERSP';d.sensor_fit='HORIZONTAL';d.sensor_width=36;d.lens=focal*36/W
    d.clip_start=.25;d.clip_end=300
    CAMERAS[name]={'kind':'perspective','eye':list(eye),'target':list(target),'focal_px':focal,
                   'principal_point':[W/2,H/2],'resolution':[W,H]}
SC.render.resolution_x=W;SC.render.resolution_y=H;SC.render.resolution_percentage=100
SC.render.pixel_aspect_x=SC.render.pixel_aspect_y=1
SC.camera=bpy.data.objects['Camera main']
sun_data=bpy.data.lights.new('Afternoon sun','SUN');sun_data.energy=2.1;sun_data.angle=.04
sun=bpy.data.objects.new('Afternoon sun',sun_data);SC.collection.objects.link(sun)
sun.rotation_euler=Vector((8,12,-20)).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Warm sky');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.72,.76,.83,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.48;SC.world=world
SC.render.engine='CYCLES';SC.cycles.device='CPU';SC.cycles.samples=16;SC.cycles.use_denoising=True
SC.render.threads_mode='FIXED';SC.render.threads=4
SC.view_settings.view_transform='Standard'

# Export only evaluated scene geometry. The terrain modifier changes the vertices.
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
vertices=[];faces=[];mats=[];normals=[];names=[];hatch=[];terrain_faces=[]
for ob in SC.objects:
    if ob.type!='MESH':continue
    ev=ob.evaluated_get(deps);me=ev.to_mesh();n0=len(vertices)
    vertices.extend([list(ev.matrix_world@v.co) for v in me.vertices])
    mat=MATERIALS.index(ob.data.materials[0])
    for p in me.polygons:
        k=len(faces);faces.append([n0+i for i in p.vertices]);mats.append(mat)
        normals.append(list((ev.matrix_world.to_3x3().inverted().transposed()@p.normal).normalized()))
        names.append(ob.name);hatch.append(bool(ob.get('hatch',True)))
        if ob==terrain:terrain_faces.append(k)
    ev.to_mesh_clear()
data=dict(vertices=vertices,faces=faces,materials=mats,normals=normals,names=names,hatch=hatch,
          terrain_faces=terrain_faces,strokes=STROKES,colors=COLORS,cameras=CAMERAS,
          blender=bpy.app.version_string,host='Host terrain',terrain_modifier={'type':'DISPLACE','strength':.12},
          source_grid={'x':GX.tolist(),'y':GY.tolist()})
(OUT/'scene.json').write_text(json.dumps(data,separators=(',',':')))

# Check the projected camera independently with Blender's own camera API.
errors=[]
for name,conf in CAMERAS.items():
    cam=bpy.data.objects['Camera '+name];SC.camera=cam
    eye=np.array(conf['eye']);fwd=np.array(conf['target'])-eye;fwd/=np.linalg.norm(fwd)
    right=np.cross(fwd,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,fwd)
    for p in [(-7,5,3),(3,8,5),(0,16,2),(7,-2,.5)]:
        q=np.array(p)-eye;z=q@fwd
        analytic=np.array([W/2+conf['focal_px']*(q@right)/z,H/2-conf['focal_px']*(q@up)/z])
        uv=world_to_camera_view(SC,cam,Vector(p));native=np.array([uv.x*W,(1-uv.y)*H])
        errors.append(float(np.max(abs(native-analytic))))
SC.camera=bpy.data.objects['Camera main']
(OUT/'blender-checks.json').write_text(json.dumps({'blender':bpy.app.version_string,'evaluated_faces':len(faces),
    'terrain_faces':len(terrain_faces),'native_camera_max_error_px':max(errors)},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Terrain_Symbols.blend'),compress=True)
if os.environ.get('TERRAIN_RENDER','1')!='0':
    for name in CAMERAS:
        SC.camera=bpy.data.objects['Camera '+name]
        SC.render.resolution_percentage=60
        SC.render.filepath=str(OUT/f'blender-{name}.png')
        bpy.ops.render.render(write_still=True)
print(json.dumps({'model':'Terrain_Symbols.blend','faces':len(faces),'camera_error':max(errors)}),flush=True)
