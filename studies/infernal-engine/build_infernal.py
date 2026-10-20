"""Infernal Engine 0.1 — run from Blender's Text Editor, or with blender -b -P.
Creates two new scenes without deleting the user's existing scenes.
Native Geometry Nodes, shader nodes, cameras, lighting. No external assets.
"""
import bpy, math, random, os, sys
from mathutils import Vector
from pathlib import Path

ROOT = Path(os.environ.get('INFERNAL_OUTPUT', str(Path(__file__).resolve().parent)))
ROOT.mkdir(parents=True, exist_ok=True)
RENDER = '--render' in sys.argv or os.environ.get('INFERNAL_RENDER') == '1'
RES = int(os.environ.get('INFERNAL_RES', '1000'))
PREFIX = 'IE • '


def mat(name, color, hatch=False, metallic=0):
    m = bpy.data.materials.new(PREFIX + name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    bs = n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = .83
    bs.inputs['Metallic'].default_value = metallic
    if hatch:
        g=n.new('ShaderNodeNewGeometry'); g.location=(-700,0)
        dot=n.new('ShaderNodeVectorMath'); dot.operation='DOT_PRODUCT'; dot.location=(-500,0)
        dot.inputs[1].default_value=(1.0,.3,.8); l.new(g.outputs['Position'],dot.inputs[0])
        mul=n.new('ShaderNodeMath'); mul.operation='MULTIPLY'; mul.inputs[1].default_value=65; mul.location=(-300,0)
        l.new(dot.outputs['Value'],mul.inputs[0])
        sn=n.new('ShaderNodeMath'); sn.operation='SINE'; sn.location=(-120,0); l.new(mul.outputs[0],sn.inputs[0])
        gt=n.new('ShaderNodeMath'); gt.operation='GREATER_THAN'; gt.inputs[1].default_value=.93; gt.location=(60,0)
        l.new(sn.outputs[0],gt.inputs[0])
        mix=n.new('ShaderNodeMixRGB'); mix.location=(250,0)
        mix.inputs[1].default_value=(*color,1)
        mix.inputs[2].default_value=(*(c*.38 for c in color),1)
        l.new(gt.outputs[0],mix.inputs[0]); l.new(mix.outputs[0],bs.inputs['Base Color'])
        bs.location=(470,0); n.get('Material Output').location=(750,0)
    return m

STONE=mat('warm limestone',(.61,.55,.41),True)
PAPER=mat('chalk',(.84,.79,.65))
DARK=mat('ink',(.055,.071,.066))
BRASS=mat('tarnished brass',(.24,.23,.14),True,.15)
RUST=mat('oxide',(.32,.085,.039),True)
LEAF=mat('dark foliage',(.10,.18,.105))


def scene(name):
    s=bpy.data.scenes.new(PREFIX+name)
    bpy.context.window.scene=s
    s.render.engine='CYCLES'
    s.cycles.samples=20
    s.cycles.use_denoising=True
    s.render.resolution_x=RES
    s.render.resolution_y=int(RES*1.25)
    s.render.resolution_percentage=100
    s.render.film_transparent=True
    s.view_settings.exposure=-.35
    s.render.image_settings.file_format='PNG'
    s.render.image_settings.color_mode='RGBA'
    s.view_settings.view_transform='Standard'
    s.view_settings.look='Medium High Contrast' if 'Medium High Contrast' in [i.identifier for i in s.view_settings.bl_rna.properties['look'].enum_items] else 'None'
    s.world=bpy.data.worlds.new(PREFIX+name+' sky'); s.world.use_nodes=True
    bg=s.world.node_tree.nodes.get('Background'); bg.inputs[0].default_value=(.77,.80,.73,1); bg.inputs[1].default_value=.45
    s['Generator']='Infernal Engine 0.1'
    return s


def mesh_obj(s,name,verts,faces,material=None):
    me=bpy.data.meshes.new(PREFIX+name); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(PREFIX+name,me); s.collection.objects.link(o)
    if material: me.materials.append(material)
    return o


def cube(s,name,loc,size,material):
    v=[(x*size[0]/2,y*size[1]/2,z*size[2]/2) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    o=mesh_obj(s,name,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material); o.location=loc
    return o


def curve_obj(s,name,paths,radius,material):
    cu=bpy.data.curves.new(PREFIX+name,'CURVE'); cu.dimensions='3D'; cu.resolution_u=2; cu.bevel_depth=radius; cu.bevel_resolution=1
    for pts in paths:
        sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
        for p,co in zip(sp.points,pts): p.co=(*co,1)
    ob=bpy.data.objects.new(PREFIX+name,cu); s.collection.objects.link(ob); cu.materials.append(material)
    return ob


def camera(s,loc,target,ortho=None,lens=42):
    ca=bpy.data.cameras.new(PREFIX+'camera'); ob=bpy.data.objects.new(PREFIX+'camera',ca); s.collection.objects.link(ob)
    ob.location=loc; ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    ca.lens=lens
    if ortho: ca.type='ORTHO'; ca.ortho_scale=ortho
    s.camera=ob
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D': area.spaces.active.region_3d.view_perspective='CAMERA'


def light(s,loc,power,size):
    ld=bpy.data.lights.new(PREFIX+'softbox','AREA'); ld.energy=power; ld.shape='DISK'; ld.size=size
    ob=bpy.data.objects.new(ld.name,ld); s.collection.objects.link(ob); ob.location=loc
    ob.rotation_euler=(Vector((0,5,0))-ob.location).to_track_quat('-Z','Y').to_euler()


class Graph:
    def __init__(self,name,inputs=()):
        self.g=bpy.data.node_groups.new(PREFIX+name,'GeometryNodeTree')
        self.g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
        for name,typ,default,lo,hi,desc in inputs:
            so=self.g.interface.new_socket(name=name,in_out='INPUT',socket_type=typ)
            so.default_value=default; so.min_value=lo; so.max_value=hi; so.description=desc
        self.n=self.g.nodes; self.l=self.g.links
        self.inp=self.node('NodeGroupInput',-1000,600)
        self.out=self.node('NodeGroupOutput',1100,200)
    def node(self,typ,x=0,y=0,label=None):
        n=self.n.new(typ); n.location=(x,y)
        if label: n.label=label
        return n
    def link(self,a,out,b,inp): self.l.new(a.outputs[out],b.inputs[inp])
    def val(self,n,key,value): n.inputs[key].default_value=value; return n
    def math(self,op,a,b=None,x=0,y=0):
        n=self.node('ShaderNodeMath',x,y); n.operation=op
        if isinstance(a,tuple): self.link(a[0],a[1],n,0)
        else: n.inputs[0].default_value=a
        if b is not None:
            if isinstance(b,tuple): self.link(b[0],b[1],n,1)
            else: n.inputs[1].default_value=b
        return n
    def box(self,size,loc,material,x=-700,y=0):
        n=self.node('GeometryNodeMeshCube',x,y); n.inputs['Size'].default_value=size
        t=self.node('GeometryNodeTransform',x+190,y); t.inputs['Translation'].default_value=loc; self.link(n,'Mesh',t,'Geometry')
        return self.material(t,'Geometry',material,x+380,y)
    def material(self,source,socket,material,x=600,y=0):
        n=self.node('GeometryNodeSetMaterial',x,y); n.inputs['Material'].default_value=material; self.link(source,socket,n,'Geometry'); return n
    def join(self,parts,x=800,y=200):
        n=self.node('GeometryNodeJoinGeometry',x,y)
        for p,sock in parts: self.link(p,sock,n,'Geometry')
        return n
    def group(self,g,x,y,label=None):
        n=self.node('GeometryNodeGroup',x,y,label); n.node_tree=g.g; return n
    def finish(self,source,sock='Geometry'):
        self.link(source,sock,self.out,'Geometry')
        # Arrange by dependency depth, keeping every node readable on opening.
        levels={n:0 for n in self.n}
        for _ in range(len(self.n)):
            changed=False
            for link in self.g.links:
                target=levels[link.from_node]+1
                if levels[link.to_node]<target:
                    levels[link.to_node]=target; changed=True
            if not changed: break
        columns={}
        for n in self.n: columns.setdefault(levels[n],[]).append(n)
        for col,nodes in columns.items():
            for row,n in enumerate(nodes):
                n.location=(col*260, -row*330)
                n.width=210
        return self


def portal_module():
    g=Graph('01 Portal module')
    parts=[]
    for i,x in enumerate([-3.5,3.5]):
        for j,(size,z) in enumerate([((.48,.55,4.2),2.1),((.85,.8,.25),.125),((.8,.75,.22),4.15)]):
            p=g.box(size,(x,0,z),STONE,-900+420*i, -260*j); parts.append((p,'Geometry'))
    c=g.node('GeometryNodeCurvePrimitiveCircle',-900,-900); c.inputs['Radius'].default_value=3.5; c.inputs['Resolution'].default_value=48
    trim=g.node('GeometryNodeTrimCurve',-700,-900); trim.inputs['End'].default_value=.5; g.link(c,'Curve',trim,'Curve')
    tr=g.node('GeometryNodeTransform',-480,-900); tr.inputs['Rotation'].default_value=(math.pi/2,0,0); tr.inputs['Translation'].default_value=(0,0,4.2); g.link(trim,'Curve',tr,'Geometry')
    prof=g.node('GeometryNodeCurvePrimitiveCircle',-480,-1150); prof.inputs['Radius'].default_value=.22; prof.inputs['Resolution'].default_value=6
    m=g.node('GeometryNodeCurveToMesh',-240,-900); g.link(tr,'Geometry',m,'Curve'); g.link(prof,'Curve',m,'Profile Curve')
    ma=g.material(m,'Mesh',STONE,0,-900); parts.append((ma,'Geometry'))
    # A continuous barrel-vault panel joins the repeated ribs into an interior.
    grid=g.node('GeometryNodeMeshGrid'); grid.inputs['Size X'].default_value=math.pi; grid.inputs['Size Y'].default_value=3
    grid.inputs['Vertices X'].default_value=40; grid.inputs['Vertices Y'].default_value=2
    pos=g.node('GeometryNodeInputPosition'); xyz=g.node('ShaderNodeSeparateXYZ'); g.link(pos,'Position',xyz,'Vector')
    angle=g.math('ADD',(xyz,'X'),math.pi/2)
    cs=g.math('COSINE',(angle,0)); sn=g.math('SINE',(angle,0))
    px=g.math('MULTIPLY',(cs,0),3.72); pz=g.math('MULTIPLY_ADD',(sn,0),3.72); pz.inputs[2].default_value=4.2
    co=g.node('ShaderNodeCombineXYZ'); g.link(px,0,co,'X'); g.link(xyz,'Y',co,'Y'); g.link(pz,0,co,'Z')
    setp=g.node('GeometryNodeSetPosition'); g.link(grid,'Mesh',setp,'Geometry'); g.link(co,'Vector',setp,'Position')
    parts.append((g.material(setp,'Geometry',STONE),'Geometry'))
    return g.finish(g.join(parts))


def tower_module():
    g=Graph('02 Archive tower module')
    parts=[(g.box((1.6,1.6,1),(0,0,.5),STONE,-900,400),'Geometry')]
    for i,z in enumerate([0,.25,.5,.75,1]):
        parts.append((g.box((1.78,1.78,.035),(0,0,z),BRASS,-900,100-i*230),'Geometry'))
    # Recessed dark facade strips; side fins create legible machine architecture.
    for i,x in enumerate([-.5,0,.5]):
        parts.append((g.box((.10,.025,.86),(x,-.807,.5),DARK,-450,100-i*230),'Geometry'))
    return g.finish(g.join(parts))


def plant(s):
    rng=random.Random(491)
    paths=[]; leafverts=[]; leaffaces=[]
    def branch(start,angle,length,depth):
        x,y,z=start; pts=[]
        for k in range(7):
            t=k/6; pts.append((x+math.cos(angle)*length*.58*t,y+math.sin(angle)*length*.58*t,z+length*(t-.16*t*t)))
        paths.append(pts)
        for j in [2,3,4,5,6]:
            p=Vector(pts[j]); side=Vector((math.cos(angle+1.2),math.sin(angle+1.2),.55))*.16*length
            tip=p+side; across=Vector((-math.sin(angle),math.cos(angle),0))*.048*length
            a=len(leafverts); leafverts.extend([tuple(p),tuple((p+tip)/2+across),tuple(tip),tuple((p+tip)/2-across)]); leaffaces.append((a,a+1,a+2,a+3))
        if depth:
            for a,j in [(-1.15,3),(.9,5)]: branch(pts[j],angle+a+rng.uniform(-.3,.3),length*.59,depth-1)
    for angle in [0,1.8,3.7,5.1]: branch((0,0,0),angle,1.35,2)
    stems=curve_obj(s,'growth source stems',paths,.013,LEAF)
    leaves=mesh_obj(s,'growth source leaves',leafverts,leaffaces,LEAF)
    # Join via node Object Info; originals are hidden far below the scene.
    for ob in [stems,leaves]: ob.location.z=-100
    return stems,leaves


def exterior(s,tower):
    controls=[('Seed','NodeSocketInt',17,0,99999,'Reproducible variation of tower heights and growth'),('Height','NodeSocketFloat',7,1,12,'Maximum tower height'),('Growth','NodeSocketFloat',.58,0,1.5,'Plant density on the ground; the central avenue stays open')]
    g=Graph('EXTERIOR • common ground',controls)
    grid=g.node('GeometryNodeMeshGrid',-950,300); grid.inputs['Size X'].default_value=24; grid.inputs['Size Y'].default_value=24; grid.inputs['Vertices X'].default_value=9; grid.inputs['Vertices Y'].default_value=9
    pos=g.node('GeometryNodeInputPosition',-950,20); sep=g.node('ShaderNodeSeparateXYZ',-760,20); g.link(pos,'Position',sep,'Vector')
    ax=g.math('ABSOLUTE',(sep,'X'),x=-560,y=20); aisle=g.math('LESS_THAN',(ax,0),2.5,x=-360,y=20)
    delete=g.node('GeometryNodeDeleteGeometry',-140,300); delete.domain='POINT'; g.link(grid,'Mesh',delete,'Geometry'); g.link(aisle,0,delete,'Selection')
    randomh=g.node('FunctionNodeRandomValue',-550,650); randomh.data_type='FLOAT'; randomh.inputs['Min'].default_value=1.4; g.link(g.inp,'Height',randomh,'Max'); g.link(g.inp,'Seed',randomh,'Seed')
    scale=g.node('ShaderNodeCombineXYZ',-150,650); scale.inputs['X'].default_value=1; scale.inputs['Y'].default_value=1; g.link(randomh,'Value',scale,'Z')
    mod=g.group(tower,-140,60); inst=g.node('GeometryNodeInstanceOnPoints',120,300); g.link(delete,'Geometry',inst,'Points'); g.link(mod,'Geometry',inst,'Instance'); g.link(scale,'Vector',inst,'Scale')
    # A distinct lower density layer. Density never moves buildings or the camera.
    ground=g.node('GeometryNodeMeshGrid',-950,-450); ground.inputs['Size X'].default_value=27; ground.inputs['Size Y'].default_value=27
    dist=g.node('GeometryNodeDistributePointsOnFaces',-720,-450); g.link(ground,'Mesh',dist,'Mesh'); g.link(g.inp,'Growth',dist,'Density'); g.link(g.inp,'Seed',dist,'Seed')
    d2=g.node('GeometryNodeDeleteGeometry',-470,-450); d2.domain='POINT'; g.link(dist,'Points',d2,'Geometry'); g.link(aisle,0,d2,'Selection')
    stems,leaves=plant(s)
    infos=[]
    for i,ob in enumerate([stems,leaves]):
        n=g.node('GeometryNodeObjectInfo',-950,-850-i*260); n.inputs['Object'].default_value=ob; n.transform_space='ORIGINAL'; infos.append((n,'Geometry'))
    pj=g.join(infos,-600,-850)
    rot=g.node('FunctionNodeRandomValue',-360,-1050); rot.data_type='FLOAT_VECTOR'; rot.inputs['Min'].default_value=(0,0,-math.pi); rot.inputs['Max'].default_value=(0,0,math.pi); g.link(g.inp,'Seed',rot,'Seed')
    sz=g.node('FunctionNodeRandomValue',-360,-800); sz.data_type='FLOAT'; sz.inputs['Min'].default_value=.3; sz.inputs['Max'].default_value=1.25; g.link(g.inp,'Seed',sz,'Seed')
    pi=g.node('GeometryNodeInstanceOnPoints',0,-400); g.link(d2,'Geometry',pi,'Points'); g.link(pj,'Geometry',pi,'Instance'); g.link(sz,'Value',pi,'Scale'); g.link(rot,'Value',pi,'Rotation')
    g.finish(g.join([(inst,'Instances'),(pi,'Instances')]))
    ob=mesh_obj(s,'EXTERIOR • select to edit nodes',[],[])
    mo=ob.modifiers.new('Common ground • Geometry Nodes','NODES'); mo.node_group=g.g
    cube(s,'ground',(0,0,-.3),(29,29,.6),PAPER)
    # Central public path: a deliberate quiet interval through extraction machinery.
    cube(s,'central path',(0,-1,.025),(3.1,29,.05),PAPER)
    for x in [-1.9,1.9]:
        curve_obj(s,'distribution main', [[(x,-13,.14),(x,13,.14)]],.09,BRASS)
    for y in range(-12,13,3):
        for sign in [-1,1]: curve_obj(s,'service branch',[[(sign*1.9,y,.14),(sign*3,y,.14),(sign*3,y,.7)]],.065,RUST)
    cube(s,'collector plinth',(0,8,.6),(4.5,4.5,1.2),STONE)
    focal(s,(0,8,1.2),scale=.78)
    camera(s,(26,-33,28),(0,1,2),ortho=54)
    light(s,(-10,-12,25),6500,12); light(s,(14,14,18),4000,10)
    s['Metaphor']='An ordered extraction complex shares one collector; reclamation occupies its margins.'
    return ob


def focal(s,origin,scale=1):
    x,y,z=origin
    def p(a,b,c): return (x+a*scale,y+b*scale,z+c*scale)
    cube(s,'collector body',p(0,.3,1.8),(2.6*scale,2*scale,3.6*scale),DARK)
    cube(s,'collector cap',p(0,.3,3.7),(3*scale,2.35*scale,.22*scale),BRASS)
    paths=[]
    for r in [1.05,1.28]: paths.append([p(math.cos(t)*r,-.78,1.95+math.sin(t)*r) for t in [i*math.tau/80 for i in range(81)]])
    curve_obj(s,'collector intake rings',paths,.085*scale,RUST)
    paths=[]
    for i in range(12):
        t=i*math.tau/12; paths.append([p(math.cos(t)*.3,-.79,1.95+math.sin(t)*.3),p(math.cos(t)*.94,-.79,1.95+math.sin(t)*.94)])
    curve_obj(s,'collector spokes',paths,.035*scale,BRASS)
    # Crown ducts are physically connected to the cap.
    for sign in [-1,1]:
        curve_obj(s,'crown duct',[[p(sign*.7,.3,3.7),p(sign*.8,.3,4.6),p(sign*1.5,.3,5.35),p(sign*1.8,.3,5.85)]],.14*scale,BRASS)


def interior(s,portal,tower):
    g=Graph('INTERIOR • hall of obligations',[
        ('Seed','NodeSocketInt',23,0,99999,'Reproducible service cabinet heights'),
        ('Bays','NodeSocketInt',8,3,12,'Number of repeated arches, at fixed 3 metre spacing'),
        ('Cabinet height','NodeSocketFloat',3,1.2,4.8,'Upper height of service machines')])
    line=g.node('GeometryNodeMeshLine',-850,400); line.mode='OFFSET'; line.inputs['Start Location'].default_value=(0,0,0); line.inputs['Offset'].default_value=(0,3,0); g.link(g.inp,'Bays',line,'Count')
    pg=g.group(portal,-650,120); inst=g.node('GeometryNodeInstanceOnPoints',-400,400); g.link(line,'Mesh',inst,'Points'); g.link(pg,'Geometry',inst,'Instance')
    branches=[]
    for i,x in enumerate([-4.9,4.9]):
        tr=g.node('GeometryNodeTransform',-630,-250-i*250); tr.inputs['Translation'].default_value=(x,0,0); g.link(line,'Mesh',tr,'Geometry'); branches.append((tr,'Geometry'))
    j=g.join(branches,-380,-300)
    to=g.group(tower,-380,-650); ra=g.node('FunctionNodeRandomValue',-650,-850); ra.data_type='FLOAT'; ra.inputs['Min'].default_value=1.3; g.link(g.inp,'Cabinet height',ra,'Max'); g.link(g.inp,'Seed',ra,'Seed')
    sc=g.node('ShaderNodeCombineXYZ',-150,-650); sc.inputs['X'].default_value=1; sc.inputs['Y'].default_value=1; g.link(ra,'Value',sc,'Z')
    mi=g.node('GeometryNodeInstanceOnPoints',120,-200); g.link(j,'Geometry',mi,'Points'); g.link(to,'Geometry',mi,'Instance'); g.link(sc,'Vector',mi,'Scale')
    g.finish(g.join([(inst,'Instances'),(mi,'Instances')]))
    ob=mesh_obj(s,'INTERIOR • select to edit nodes',[],[]); mo=ob.modifiers.new('Hall of obligations • Geometry Nodes','NODES'); mo.node_group=g.g
    cube(s,'floor',(0,10,-.23),(13,29,.46),PAPER)
    # Shared manifold returns to a fixed collector; adjustable bays extend beyond it.
    for sign in [-1,1]:
        curve_obj(s,'overhead return', [[(sign*3.2,-2,4),(sign*3.2,20,4),(sign*1,20,3.7)]],.10,BRASS)
        for y in range(0,22,3):
            curve_obj(s,'connected cabinet feed',[[(sign*4.9,y,.65),(sign*3.2,y,.65),(sign*3.2,y,4)]],.06,RUST)
    cube(s,'altar plinth',(0,20,.5),(4.8,4,1),STONE); focal(s,(0,20,1))
    # Rear wall, a high slot, and buttresses. The camera side stays open.
    cube(s,'rear wall',(0,23,4),(13,.5,8),STONE)
    cube(s,'aperture',(0,22.72,4),(1.1,.035,4),DARK)
    for x in [-6,6]:
        cube(s,'side wall',(x,10,2.2),(.45,28,4.4),STONE)
        cube(s,'side aisle ceiling',(x*.82,10,4.35),(2.6,28,.22),STONE)
    camera(s,(.8,-11,4.5),(0,15,3.4),lens=32)
    light(s,(-1,3,6.3),600,4); light(s,(0,17,6.3),850,4); light(s,(1,-4,6),400,5)
    s['Metaphor']='Every service cabinet returns to a shared collector beneath repeated vaults.'
    s['Prototype limit']='Bays controls arch and cabinet repetitions; manifold, floor and collector remain fixed at the default composition.'
    return ob


def main():
    p=portal_module(); t=tower_module()
    ext=scene('01 Common ground'); eo=exterior(ext,t)
    inside=scene('02 Hall of obligations'); io=interior(inside,p,t)
    for s,ob in [(ext,eo),(inside,io)]:
        bpy.context.window.scene=s
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob
        s.render.filepath=str(ROOT / ('exterior.png' if s==ext else 'interior.png'))
        if RENDER: bpy.ops.render.render(write_still=True)
    bpy.context.window.scene=ext
    bpy.ops.object.select_all(action='DESELECT'); eo.select_set(True); bpy.context.view_layer.objects.active=eo
    text=bpy.data.texts.new('START HERE • Infernal Engine')
    text.write('Infernal Engine 0.1\nTwo scenes: Common ground / Hall of obligations.\nSelect the EXTERIOR or INTERIOR generator, then Modifiers to change seed and controls.\nOpen the Geometry Nodes workspace to inspect the native graph.\nAll materials and growth assets are embedded. No downloads or add-ons.\nPrototype: Bays changes repetitions; interior floor, collector and pipes remain fixed.\nThe growth source objects are stored at Z=-100; their Object Info nodes use original geometry.\nShader hatching is raster detail, not vector strokes. See README for export limits.\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Infernal_Engine_0_1.blend'))
    print('INFERNAL_ENGINE_SAVED',bpy.app.version_string)

if __name__=='__main__': main()
