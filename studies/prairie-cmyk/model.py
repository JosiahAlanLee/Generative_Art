"""Executed Blender prairie and limestone bluffs; exports evaluated triangles for the ink renderer.

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
SC = bpy.data.scenes.new('Driftless | prairie bluffs and oaks')
bpy.context.window.scene = SC
W, H = 2400, 1600
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
    x,y=np.asarray(x),np.asarray(y)
    # Rounded Driftless summits, with steep layered limestone shoulders. The
    # host remains a single height surface so downward marks stay unambiguous.
    r=np.sqrt(((x-10)/13.5)**2+((y-23)/8.5)**2)
    r2=np.sqrt(((x+18)/10.5)**2+((y-30)/9.5)**2)
    r=r+.05*np.sin(x*.48+.6*np.sin(y*.4))+.028*np.sin(y*.87-x*.16)
    r2=r2+.045*np.sin(x*.56+y*.29)+.025*np.sin(y*.91)
    bluff=3.8/(1+np.exp(np.clip((r-1)*18,-60,60)))+1.15*np.exp(-(r/1.05)**4)
    bluff2=3.1/(1+np.exp(np.clip((r2-1)*17,-60,60)))+.90*np.exp(-(r2/1.05)**4)
    return (.55+.012*y+.46*np.sin(x*.16+y*.08)+.21*np.sin(y*.29-x*.10)
            +bluff+bluff2+.85*np.exp(-((y-45)/9)**2))

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
GX=np.linspace(-36,36,217); GY=np.linspace(-22,62,253)
xx,yy=np.meshgrid(GX,GY); zz=terrain_z(xx,yy)
vs=np.column_stack([xx.ravel(),yy.ravel(),zz.ravel()]).tolist(); fs=[]
for j in range(len(GY)-1):
    for i in range(len(GX)-1):
        a=j*len(GX)+i;b=a+1;c=b+len(GX);d=a+len(GX)
        fs.extend([(a,b,c),(a,c,d)])
terrain=mesh('Host terrain',vs,fs,0,False)
terrain.data.materials.append(MATERIALS[1])
for polygon in terrain.data.polygons:
    if polygon.normal.z<.78:polygon.material_index=1
tex=bpy.data.textures.new('Low stone undulation',type='CLOUDS')
tex.noise_scale=2.3;tex.noise_depth=1
mod=terrain.modifiers.new('Evaluated surface detail','DISPLACE')
mod.texture=tex;mod.strength=.08;mod.mid_level=.5
SC['terrain_source']='Evaluated Host terrain, including Displace modifier'

# Prairie contains no architecture. All visible stone belongs to the bluffs.
CAMERAS={}
for name,eye,target,focal in [('main',(27,-43,17),(0,18,2.9),3300.),
                              ('low',(10,-38,10.8),(0,19,2.8),3300.)]:
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
SC.render.engine='CYCLES';SC.cycles.device='CPU';SC.cycles.samples=12;SC.cycles.use_denoising=True
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
        k=len(faces);faces.append([n0+i for i in p.vertices]);mats.append(1 if ob==terrain and p.material_index==1 else mat)
        normals.append(list((ev.matrix_world.to_3x3().inverted().transposed()@p.normal).normalized()))
        names.append(ob.name);hatch.append(bool(ob.get('hatch',True)))
        if ob==terrain:terrain_faces.append(k)
    ev.to_mesh_clear()
data=dict(vertices=vertices,faces=faces,materials=mats,normals=normals,names=names,hatch=hatch,
          terrain_faces=terrain_faces,strokes=STROKES,colors=COLORS,cameras=CAMERAS,
          blender=bpy.app.version_string,host='Host terrain',terrain_modifier={'type':'DISPLACE','strength':.08},
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
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Prairie_Bluffs_CMYK.blend'),compress=True)
if os.environ.get('TERRAIN_RENDER','1')!='0':
    for name in CAMERAS:
        SC.camera=bpy.data.objects['Camera '+name]
        SC.render.resolution_percentage=60
        SC.render.filepath=str(OUT/f'blender-{name}.png')
        bpy.ops.render.render(write_still=True)
print(json.dumps({'model':'Prairie_Bluffs_CMYK.blend','faces':len(faces),'camera_error':max(errors)}),flush=True)
