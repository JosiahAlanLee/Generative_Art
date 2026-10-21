"""Blender exterior architecture, volume foliage, evaluated geometry and cameras.

Run with Blender 4.5 LTS or the official bpy wheel. INFERNAL_CASE selects a
compiled specimen. Native Geometry Nodes repeats a whole architectural storey.
"""
from pathlib import Path
import json, math, os
import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
from compile import compile_case,compile_document
from terrain_height import base_height as terrain_z,sampler

ROOT = Path(__file__).resolve().parent
CASE = os.environ.get('INFERNAL_CASE', 'recorded_route')
TERRAIN_MODE = os.environ.get('INFERNAL_TERRAIN','original')
OUT = ROOT/'output'/(CASE if TERRAIN_MODE=='original' else CASE+'-'+TERRAIN_MODE)
OUT.mkdir(parents=True, exist_ok=True)
A = (compile_document(json.loads(Path(os.environ['INFERNAL_INPUT']).read_text()),CASE)
     if os.environ.get('INFERNAL_INPUT') else compile_case(CASE))
(OUT/'architecture.json').write_text(json.dumps(A, indent=2))
SC = bpy.data.scenes.new('Infernal Engine | '+CASE)
bpy.context.window.scene = SC
W, H = 3120, 2340
STROKES, MATERIALS = [], []
COLORS = ['#bfb79d', '#bcb29b', '#716b53', '#8d4e39', '#6e7165', '#dbceb2', '#4e6450']
for name, col in zip(['Ground','Limestone','Timber','Oxide','Roof','Paper','Foliage'], COLORS):
    m = bpy.data.materials.new('IE | '+name)
    m.diffuse_color = tuple(int(col[k:k+2],16)/255 for k in (1,3,5))+(1.,)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = m.diffuse_color
    p.inputs['Roughness'].default_value = .88
    MATERIALS.append(m)


EROSION_STATE=None
if TERRAIN_MODE!='original':
    source=OUT/'terrain-state.npz'
    if not source.exists():raise FileNotFoundError('Prepare terrain with the engraving Python: python erosion.py')
    EROSION_STATE=dict(np.load(source));terrain_z=sampler(EROSION_STATE)


def mesh(name,verts,faces,mat=1,hatch=True,link=True):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me)
    if link:SC.collection.objects.link(o)
    o.data.materials.append(MATERIALS[mat]);o['hatch']=hatch;o['material_id']=mat
    return o


def box(name,lo,hi,mat=1,link=True):
    x,y,z=lo;X,Y,Z=hi
    return mesh(name,[(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],
                [(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat,link=link)


def beam(name,a,b,r=.08,mat=2,sides=6):
    a,b=np.asarray(a,float),np.asarray(b,float);n=b-a;n/=np.linalg.norm(n)
    u=np.cross(n,[0,0,1]) if abs(n[2])<.95 else np.cross(n,[0,1,0])
    u/=np.linalg.norm(u);v=np.cross(n,u)
    ring=np.array([u*np.cos(t)+v*np.sin(t) for t in np.arange(sides)*2*np.pi/sides])*r
    p=np.vstack([a+ring,b+ring]);f=[tuple(range(sides-1,-1,-1)),tuple(range(sides,2*sides))]
    f += [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
    return mesh(name,p,f,mat)


def ink(name,pts,mm=.12,pen=0):
    STROKES.append(dict(name=name,pts=np.asarray(pts,float).tolist(),width=mm*20,ink=pen))


def roof(name,x,y,z,w,d,rise=.9):
    p=[(x-w/2,y-d/2,z),(x+w/2,y-d/2,z),(x,y-d/2,z+rise),
       (x-w/2,y+d/2,z),(x+w/2,y+d/2,z),(x,y+d/2,z+rise)]
    o=mesh(name,p,[(0,2,1),(3,4,5),(0,3,5,2),(1,2,5,4)],4)
    for q in np.linspace(-d/2+.13,d/2-.13,max(3,int(d/.30))):
        ink('Standing roof seam',[(x-w/2,y+q,z+.018),(x,y+q,z+rise+.018),(x+w/2,y+q,z+.018)],.10)
    return o


def arch(name,x,y,z,w,h,depth=.20):
    # Real masonry around an empty opening. No white image masks.
    spring=z+h-w/2
    for side in (-1,1):box(name+' jamb',(x+side*w/2-.12,y-depth/2,z),(x+side*w/2+.12,y+depth/2,spring),1)
    for t in np.linspace(0,np.pi,11)[:-1]:
        ts=np.linspace(t,t+np.pi/10,2)
        vs=[]
        for yy in (y-depth/2,y+depth/2):
            for r in (w/2-.12,w/2+.12):
                vs.extend([(x+r*np.cos(a),yy,spring+r*np.sin(a)) for a in ts])
        mesh(name+' voussoir',vs,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)],1)


# Evaluated, displaced host. All plants and marks subsequently project onto it.
gx=np.linspace(-30,30,101) if EROSION_STATE is None else EROSION_STATE['x']
gy=np.linspace(-20,44,105) if EROSION_STATE is None else EROSION_STATE['y']
xx,yy=np.meshgrid(gx,gy);zz=terrain_z(xx,yy);fs=[]
for j in range(len(gy)-1):
    for i in range(len(gx)-1):
        a=j*len(gx)+i;fs.extend([(a,a+1,a+len(gx)+1),(a,a+len(gx)+1,a+len(gx))])
terrain=mesh('Host terrain',np.c_[xx.ravel(),yy.ravel(),zz.ravel()],fs,0,False)
tex=bpy.data.textures.new('Stone undulation',type='CLOUDS');tex.noise_scale=2.3;tex.noise_depth=1
mod=terrain.modifiers.new('Evaluated ground detail','DISPLACE');mod.texture=tex;mod.strength=.08;mod.mid_level=.5


def story_nodes(name,cx,cy,z,w,d,count):
    """One repeatable body, with its windows and cornice, realised by GN."""
    parts=[]
    def component(n,lo,hi,mat=1):parts.append(box(name+' module '+n,lo,hi,mat,False))
    component('body',(-w/2,-d/2,0),(w/2,d/2,.92))
    component('cornice',(-w/2-.12,-d/2-.12,.86),(w/2+.12,d/2+.12,1.03))
    for x in np.linspace(-w/2+.43,w/2-.43,3):
        if abs(x)<.1:continue  # keep the portal axis free of a superposed window
        component('front window',(x-.20,-d/2-.027,.24),(x+.20,-d/2-.014,.69),2)
        component('back window',(x-.20,d/2+.014,.24),(x+.20,d/2+.027,.69),2)
    for y in np.linspace(-d/2+.42,d/2-.42,3):
        component('side window',(w/2+.014,y-.19,.24),(w/2+.027,y+.19,.69),2)
    # Build a local mesh carrying per-face material slots from its parts.
    vs=[];faces=[];mi=[]
    for ob in parts:
        off=len(vs);vs.extend([tuple(v.co) for v in ob.data.vertices])
        faces.extend([tuple(off+i for i in p.vertices) for p in ob.data.polygons])
        mi.extend([ob['material_id']]*len(ob.data.polygons))
    me=bpy.data.meshes.new(name+' complete bay');me.from_pydata(vs,[],faces);me.update()
    for m in MATERIALS:me.materials.append(m)
    for p,i in zip(me.polygons,mi):p.material_index=i
    module=bpy.data.objects.new(name+' | unlinked bay source',me)
    for ob in parts:bpy.data.objects.remove(ob)
    host=mesh(name+' | duration bays',[],[],1);host.location=(cx,cy,z)
    g=bpy.data.node_groups.new('IE | '+name+' | duration repetition','GeometryNodeTree')
    s=g.interface.new_socket(name='Bays',in_out='INPUT',socket_type='NodeSocketInt');s.default_value=count;s.min_value=1;s.max_value=24
    g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    n=g.nodes;l=g.links;i=n.new('NodeGroupInput');i.location=(-600,100)
    line=n.new('GeometryNodeMeshLine');line.mode='OFFSET';line.location=(-380,100)
    line.inputs['Offset'].default_value=(0,0,1.04);l.new(i.outputs['Bays'],line.inputs['Count'])
    info=n.new('GeometryNodeObjectInfo');info.location=(-380,-150);info.inputs['Object'].default_value=module
    inst=n.new('GeometryNodeInstanceOnPoints');inst.location=(-100,100)
    l.new(line.outputs['Mesh'],inst.inputs['Points']);l.new(info.outputs['Geometry'],inst.inputs['Instance'])
    real=n.new('GeometryNodeRealizeInstances');real.location=(150,100);l.new(inst.outputs['Instances'],real.inputs['Geometry'])
    out=n.new('NodeGroupOutput');out.location=(400,100);l.new(real.outputs['Geometry'],out.inputs['Geometry'])
    m=host.modifiers.new('Task duration / repeated bays','NODES');m.node_group=g
    host['task_id']=name;host['duration']=count
    return count*1.04


TOP={};BASE={};FOOTPRINTS=[]
for node in A['nodes']:
    name=node['id'];x,y=node['x'],node['y'];z=float(terrain_z(x,y))+.14+node['plinth']
    w,d=(3.3,3.0) if name=='approval' else (4.1,3.6) if name=='staff' else (3.6,3.2)
    BASE[name]=(x,y,z);FOOTPRINTS.append([x-w/2-.55,y-d/2-.5,x+w/2+.55,y+d/2+.5])
    box(name+' foundation',(x-w/2-.2,y-d/2-.2,float(terrain_z(x,y))-.8),(x+w/2+.2,y+d/2+.2,z))
    # A grounded 0.8-unit entrance base gives the one-bay building a portal
    # taller than its windows without pushing the portcullis through its roof.
    box(name+' entrance base',(x-w/2,y-d/2,z),(x+w/2,y+d/2,z+.8))
    h=.8+story_nodes(name,x,y,z+.8,w,d,node['bays']);TOP[name]=z+h
    roof(name+' roof',x,y,z+h+.02,w+.65,d+.60,1.0 if name=='approval' else .7)
    arch(name+' portal',x,y-d/2-.12,z,1.15,1.75)
    # Foundation courses remain fixed to the building; surface marks are separate.
    for dz in np.arange(float(terrain_z(x,y))-.1,z,.24):
        ink('Rusticated foundation',[(x-w/2-.21,y-d/2-.21,dz),(x+w/2+.21,y-d/2-.21,dz),(x+w/2+.21,y+d/2+.21,dz)],.10)
    if node['release_at']:
        # Late release is drawn as a real lift tower, not extra duration bays.
        for dx in (-.9,.9):beam('Release lift upright',(x+dx,y-d/2-.5,float(terrain_z(x,y))),(x+dx,y-d/2-.5,z+.3),.09)
        for dz in np.arange(float(terrain_z(x,y)),z,.55):
            beam('Release lift bracing',(x-.9,y-d/2-.5,dz),(x+.9,y-d/2-.5,dz+.5),.04)
        box('Release lift landing',(x-1,y-d/2-.75,z-.12),(x+1,y-d/2+.1,z),2)
    if not node['available']:
        for dx in np.linspace(-.48,.48,7):beam('Unavailable portcullis',(x+dx,y-d/2-.27,z),(x+dx,y-d/2-.27,z+1.5),.035)

# Two prerequisites join at restore: two independent supported service routes.
ROUTES=[]
for k,e in enumerate(A['edges']):
    a,b=e['source'],e['target'];x,y,z=BASE[a];X,Y,Z=BASE[b]
    # A raised cable tray leaves a separate socket on the right of each facade.
    p=np.array([(x+1.2,y,z+.75),(x+2.3,y,z+.75),(x+2.3,y,Z+.75),(X+2.3,Y,Z+.75),(X+1.2,Y,Z+.75)])
    p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-5]]
    for j,(u,v) in enumerate(zip(p,p[1:])):
        beam('Service tray '+str(k),u+[0,0,-.10],v+[0,0,-.10],.055,2)
        if np.linalg.norm((v-u)[:2])>.3:
            for t in np.linspace(0,1,max(2,int(np.linalg.norm(v-u)/1.8))):
                q=u*(1-t)+v*t
                beam('Service support',q+[0,0,-.15],[q[0],q[1],float(terrain_z(q[0],q[1]))-.10],.045)
    # Ink-only lifted centerline, so the tray does not swallow its own route.
    ink('Dependency '+a+' to '+b,p+[0,0,.035],.32,2)
    ROUTES.append(dict(source=a,target=b,pts=p.tolist()))

# Restoration powerhouse: a grounded chimney, fluted vat and flywheel.
x,y,z=BASE[A['target']]
beam('Powerhouse chimney',(x+.8,y+.6,z),(x+.8,y+.6,TOP[A['target']]+2.4),.34,3,10)
for r in (.76,.94):
    t=np.linspace(0,2*np.pi,97)
    ink('External flywheel',np.c_[x+np.cos(t)*r,np.full(len(t),y-1.88),z+1.05+np.sin(t)*r],.16)
for t in np.arange(8)*np.pi/4:
    ink('Flywheel spoke',[(x,y-1.88,z+1.05),(x+np.cos(t)*.76,y-1.88,z+1.05+np.sin(t)*.76)],.12)
beam('Wheel pedestal',(x,y-1.88,float(terrain_z(x,y))),(x,y-1.88,z+.35),.18)

# Open field gateway: masonry and threshold give plant occlusion thin blockers.
for x in (-1.9,1.9):
    z=float(terrain_z(x,-.3));box('Entry pier',(x-.22,-.6,z-.2),(x+.22,-.1,z+2.3))
arch('Open approach arch',0,-.35,float(terrain_z(0,-.35)),3.8,4.1,.30)

# Fence rooted independently along an undulating contour.
posts=[]
for x in np.arange(-15,15.1,1.7):
    if abs(x)<2.5:posts.append(None);continue
    y=-.1+.10*x;z=float(terrain_z(x,y))-.08
    beam('Meadow fence post',(x,y,z),(x,y,z+1.0),.07);posts.append(np.array([x,y,z]))
for a,b in zip(posts,posts[1:]):
    if a is None or b is None:continue
    for h in (.40,.79):beam('Meadow fence rail',a+[0,0,h],b+[0,0,h],.035)


def oak(name,x,y,height,seed):
    """A branching volume tree with leaf diamonds distributed in 3D crowns."""
    rng=np.random.default_rng((seed+int(A['seed'])-314159)%(2**32));root=np.array([x,y,float(terrain_z(x,y))-.07]);tips=[]
    def branch(a,d,length,r,level):
        b=a+d/np.linalg.norm(d)*length
        ob=beam(name+' branch',a,b,r,2,5);ob['hatch']=False
        if level==0:tips.append(b);return
        for j in range(3 if level>1 else 2):
            angle=(j*2*np.pi/3)+rng.uniform(-.5,.5)
            q=np.array([np.cos(angle),np.sin(angle),rng.uniform(.4,1.3)])
            branch(b,.42*d+q,length*rng.uniform(.55,.70),r*.55,level-1)
    branch(root,np.array([.03,.01,1]),height*.33,height*.035,3)
    vs=[];fs=[]
    for tip in tips:
        for _ in range(21):
            c=tip+rng.normal(0,[height*.10,height*.10,height*.06])
            normal=rng.normal(size=3);normal/=np.linalg.norm(normal)
            u=np.cross(normal,[0,0,1]);u/=max(np.linalg.norm(u),1e-8);v=np.cross(normal,u)
            length=rng.uniform(.16,.29);width=length*.54
            off=len(vs)
            # Eight-sided leaf outline softens the diamond-card prototype.
            ts=np.arange(8)*np.pi/4
            vs.extend([c+u*np.cos(t)*length+v*np.sin(t)*width for t in ts])
            fs.append(tuple(range(off,off+8)))
    mesh(name+' leaf volume',vs,fs,6,False)

oak('Volume oak near',10.3,9.5,6.7,371)
oak('Volume oak far',-11.8,20,6.5,521)
for i,(x,y,h) in enumerate([(-20,27,4.6),(-15,29,4.4),(-7,31,4.5),(0,31,5.2),(8,30,4.8),(16,29,5.1)]):
    oak('Ridge oak '+str(i),x,y,h,900+i)

# Limestone bluff slabs, their strata give the field a recognisable region.
for j in range(3):
    # Every exposed stratum follows the ridge, with its lower edge buried.
    xs=np.linspace(-25,-8,20);ys=23+.17*xs+j*.65
    zs=terrain_z(xs,ys)-.10
    vs=np.vstack([np.c_[xs,ys,zs],np.c_[xs,ys+.22,zs+.28]])
    mesh('Limestone ledge '+str(j),vs,[(i,i+1,i+21,i+20) for i in range(19)],1)

CAMERAS={}
for name,eye,target,focal in [('main',(27,-38,23),(0,9.5,3),3500.),('low',(30,-38,13),(0,9,3),3500.)]:
    d=bpy.data.cameras.new('IE '+name);ob=bpy.data.objects.new('Camera '+name,d);SC.collection.objects.link(ob)
    ob.location=eye;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    d.type='PERSP';d.sensor_fit='HORIZONTAL';d.sensor_width=36;d.lens=focal*36/W;d.clip_start=.25;d.clip_end=300
    CAMERAS[name]=dict(kind='perspective',eye=list(eye),target=list(target),focal_px=focal,principal_point=[W/2,H/2],resolution=[W,H])
SC.render.resolution_x=W;SC.render.resolution_y=H;SC.render.resolution_percentage=100
SC.render.pixel_aspect_x=SC.render.pixel_aspect_y=1;SC.camera=bpy.data.objects['Camera main']
sun_data=bpy.data.lights.new('Low afternoon sun','SUN');sun_data.energy=2.1;sun_data.angle=.035
sun=bpy.data.objects.new('Low afternoon sun',sun_data);SC.collection.objects.link(sun)
sun.rotation_euler=Vector((10,8,-9)).to_track_quat('-Z','Y').to_euler()
world=bpy.data.worlds.new('Warm sky');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.73,.77,.85,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.5;SC.world=world
SC.render.engine='CYCLES';SC.cycles.device='CPU';SC.cycles.samples=12;SC.cycles.use_denoising=True
SC.render.threads_mode='FIXED';SC.render.threads=4;SC.view_settings.view_transform='Standard'

# Export evaluated meshes, including Geometry Nodes and Displace, once.
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
vertices=[];faces=[];mats=[];normals=[];names=[];hatch=[];terrain_faces=[];gn_objects=[]
for ob in SC.objects:
    if ob.type!='MESH':continue
    ev=ob.evaluated_get(deps);me=ev.to_mesh();off=len(vertices)
    vertices.extend([list(ev.matrix_world@v.co) for v in me.vertices])
    for p in me.polygons:
        k=len(faces);faces.append([off+i for i in p.vertices])
        mat=me.materials[p.material_index] if len(me.materials) else ob.data.materials[0]
        mats.append([m.name for m in MATERIALS].index(mat.name))
        normals.append(list((ev.matrix_world.to_3x3().inverted().transposed()@p.normal).normalized()))
        names.append(ob.name);hatch.append(bool(ob.get('hatch',True)))
        if ob==terrain:terrain_faces.append(k)
    if any(m.type=='NODES' for m in ob.modifiers):gn_objects.append(dict(name=ob.name,faces=len(me.polygons)))
    ev.to_mesh_clear()
data=dict(vertices=vertices,faces=faces,materials=mats,normals=normals,names=names,hatch=hatch,
          terrain_faces=terrain_faces,strokes=STROKES,colors=COLORS,cameras=CAMERAS,
          blender=bpy.app.version_string,host='Host terrain',architecture=A,footprints=FOOTPRINTS,
          routes=ROUTES,terrain_modifier=dict(type='DISPLACE',strength=.08),geometry_nodes=gn_objects)
data['terrain_mode']=TERRAIN_MODE
if EROSION_STATE is not None:
    data['terrain_state']={k:EROSION_STATE[k].tolist() for k in ('x','y','height','area','receiver','fixed_mask')}
(OUT/'scene.json').write_text(json.dumps(data,separators=(',',':')))
errors=[]
for name,c in CAMERAS.items():
    cam=bpy.data.objects['Camera '+name];eye=np.array(c['eye'],float);fwd=np.array(c['target'],float)-eye;fwd/=np.linalg.norm(fwd)
    right=np.cross(fwd,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,fwd)
    for p in [(-7,5,3),(3,8,5),(0,16,2),(7,-2,.5)]:
        q=np.array(p)-eye;z=q@fwd
        xy=np.array([W/2+c['focal_px']*(q@right)/z,H/2-c['focal_px']*(q@up)/z])
        uv=world_to_camera_view(SC,cam,Vector(p));errors.append(float(np.max(abs(np.array([uv.x*W,(1-uv.y)*H])-xy))))
(OUT/'blender-checks.json').write_text(json.dumps(dict(blender=bpy.app.version_string,evaluated_faces=len(faces),
      native_camera_max_error_px=max(errors),geometry_nodes=gn_objects),indent=2))
SC['architecture_json']=json.dumps(A);SC['printed_width_mm']=156
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('Infernal_'+CASE+'.blend')),compress=True)
if os.environ.get('INFERNAL_RENDER','1')!='0':
    SC.render.resolution_percentage=38;SC.render.filepath=str(OUT/'clay.png');bpy.ops.render.render(write_still=True)
print(json.dumps(dict(case=CASE,faces=len(faces),native_camera_max_error=max(errors))),flush=True)
