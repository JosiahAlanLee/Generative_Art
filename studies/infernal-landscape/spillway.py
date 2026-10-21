"""A second architectural grammar: sawtooth works beside an incised coulee.

The scheduling evaluator and hatch bodies stay shared. Duration occupies the
horizontal axis; release wait occupies a separate approach passage.
"""
import numpy as np

BAY=1.6


def dimensions(node):
    return BAY*node['bays'],3.6 if node['id']=='crew' else 3.2


def build_scene(A,T):
    import bpy
    box,beam,ink,mesh,arch,ground,oak=(T[k] for k in ('box','beam','ink','mesh','arch','terrain_z','oak'))
    SC,MATERIALS=T['SC'],T['MATERIALS']
    base={};top={};footprints=[];routes=[]

    def factory(n,x,y,z,w,d):
        # A complete hall bay, including its sawtooth roof and front light.
        name=n['id'];parts=[]
        def part(label,lo,hi,mat=1):parts.append(box(name+' module '+label,lo,hi,mat,False))
        height=3.4 if name=='restart' else 2.65
        part('body',(0,-d/2,0),(BAY,d/2,height))
        part('front pier',(0,-d/2-.07,0),(.13,-d/2-.01,height+.08))
        part('front window',(.29,-d/2-.035,.85),(BAY-.27,-d/2-.018,1.9),2)
        part('sill',(.21,-d/2-.10,.75),(BAY-.20,-d/2, .85))
        part('cornice',(-.04,-d/2-.13,height-.08),(BAY+.04,d/2+.13,height+.05))
        vertices=[];faces=[];mats=[]
        for ob in parts:
            off=len(vertices);vertices.extend([tuple(v.co) for v in ob.data.vertices])
            faces.extend([tuple(off+i for i in p.vertices) for p in ob.data.polygons])
            mats.extend([ob['material_id']]*len(ob.data.polygons))
        # Sloped roof with a short, vertical northlight at the high end.
        off=len(vertices)
        vertices.extend([(0,-d/2-.16,height+.05),(BAY,-d/2-.16,height+.75),
                         (BAY,-d/2-.16,height+.05),(0,d/2+.16,height+.05),
                         (BAY,d/2+.16,height+.75),(BAY,d/2+.16,height+.05)])
        faces.extend([tuple(off+i for i in f) for f in ((0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4))]);mats.extend([1,1,4,2])
        me=bpy.data.meshes.new(name+' horizontal bay source');me.from_pydata(vertices,[],faces);me.update()
        for m in MATERIALS:me.materials.append(m)
        for p,i in zip(me.polygons,mats):p.material_index=i
        module=bpy.data.objects.new(name+' | unlinked horizontal bay',me)
        for ob in parts:bpy.data.objects.remove(ob)
        host=mesh(name+' | horizontal duration bays',[],[]);host.location=(x-w/2,y,z)
        g=bpy.data.node_groups.new('IE | '+name+' | horizontal duration','GeometryNodeTree')
        s=g.interface.new_socket(name='Bays',in_out='INPUT',socket_type='NodeSocketInt');s.default_value=n['bays'];s.min_value=1;s.max_value=24
        g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
        nodes,links=g.nodes,g.links
        inp=nodes.new('NodeGroupInput');inp.location=(-600,100)
        line=nodes.new('GeometryNodeMeshLine');line.mode='OFFSET';line.location=(-380,100)
        line.inputs['Offset'].default_value=(BAY,0,0);links.new(inp.outputs['Bays'],line.inputs['Count'])
        info=nodes.new('GeometryNodeObjectInfo');info.location=(-380,-150);info.inputs['Object'].default_value=module
        inst=nodes.new('GeometryNodeInstanceOnPoints');inst.location=(-100,100)
        links.new(line.outputs['Mesh'],inst.inputs['Points']);links.new(info.outputs['Geometry'],inst.inputs['Instance'])
        real=nodes.new('GeometryNodeRealizeInstances');real.location=(150,100);links.new(inst.outputs['Instances'],real.inputs['Geometry'])
        out=nodes.new('NodeGroupOutput');out.location=(400,100);links.new(real.outputs['Geometry'],out.inputs['Geometry'])
        host.modifiers.new('Task duration / horizontal bays','NODES').node_group=g
        host['task_id']=name;host['duration']=n['duration'];host['bay_count']=n['bays']
        return height+.75

    for n in A['nodes']:
        name=n['id'];x,y=n['x'],n['y'];w,d=dimensions(n);z=float(ground(x,y))+.24
        base[name]=(x,y,z);footprints.append([x-w/2-.6,y-d/2-.6,x+w/2+.6,y+d/2+.6])
        box(name+' foundation',(x-w/2-.18,y-d/2-.18,z-.95),(x+w/2+.18,y+d/2+.18,z))
        top[name]=z+factory(n,x,y,z,w,d)
        arch(name+' portal',x-w/2+.80,y-d/2-.16,z,1.15,2.25)
        for dz in np.arange(z-.6,z,.24):
            ink('Rusticated foundation',[(x-w/2-.19,y-d/2-.19,dz),(x+w/2+.19,y-d/2-.19,dz)],.1)
        if n['wait_length']:
            a=y-d/2-n['wait_length'];b=y-d/2-.20
            box(name+' waiting passage',(x-.68,a,z-.14),(x+.68,b,z+.03))
            footprints.append([x-.9,a-.3,x+.9,b+.3])
            for yy in np.arange(a,b+.01,.75):
                arch(name+' waiting frame',x,yy,z,1.25,2.2,.12)
                beam('Service support waiting rail',(x+.86,yy,z),(x+.86,yy,z+.9),.025)
            # Keep the release trace on an exposed rail, clear of both the
            # terrain and the masonry frames, rather than on a hidden floor.
            beam('Service tray waiting rail',(x+.86,a,z+.82),(x+.86,b,z+.82),.035)
            ink('Release wait '+name,[(x+.86,a,z+.94),(x+.86,b,z+.94)],.32,2)
        if not n['available']:
            for dx in np.linspace(-.48,.48,7):beam('Unavailable portcullis',(x-w/2+.8+dx,y-d/2-.30,z),(x-w/2+.8+dx,y-d/2-.30,z+1.9),.035)

    nodes={n['id']:n for n in A['nodes']}
    for k,e in enumerate(A['edges']):
        a,b=e['source'],e['target'];x,y,z=base[a];X,Y,Z=base[b]
        w,d=dimensions(nodes[a]);W,D=dimensions(nodes[b])
        sx,sy=x+w/2-.28,y-d/2-.36;tx,ty=X+W/2-.28,Y-D/2-.36
        bus=min(sy,ty)-1.05-k*.26
        level=max(z,Z)+1.0
        p=np.array([(sx,sy,z+1.0),(sx,sy,level),(sx,bus,level),(tx,bus,level),(tx,ty,level),(tx,ty,Z+1.0)])
        p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-5]]
        for u,v in zip(p,p[1:]):
            beam('Service tray '+str(k),u+[0,0,-.11],v+[0,0,-.11],.055)
            if np.linalg.norm((v-u)[:2])>.3:
                for t in np.linspace(0,1,max(2,int(np.linalg.norm(v-u)/2.1))):
                    q=u*(1-t)+v*t
                    beam('Service support',q+[0,0,-.18],[q[0],q[1],float(ground(q[0],q[1]))-.12],.035)
        ink('Dependency '+a+' to '+b,p+[0,0,.055],.32,2)
        routes.append(dict(source=a,target=b,pts=p.tolist()))

    x,y,z=base[A['target']]
    beam('restart chimney',(x+1.5,y+1.05,z),(x+1.5,y+1.05,top[A['target']]+3.0),.30,3,10)
    for r in (.65,.83):
        t=np.linspace(0,2*np.pi,97)
        ink('External flywheel',np.c_[x+np.cos(t)*r,np.full(len(t),y-1.94),z+1.1+np.sin(t)*r],.16)
    for t in np.arange(8)*np.pi/4:
        ink('Flywheel spoke',[(x,y-1.94,z+1.1),(x+np.cos(t)*.65,y-1.94,z+1.1+np.sin(t)*.65)],.12)
    # Revetments reveal the eroded bank, rather than concealing it under a plinth.
    for x in np.arange(-14,14,1.6):
        y=1.8+.025*x*x;z=float(ground(x,y))
        beam('Service support revetment',(x,y,z-.3),(x,y,z+.75),.075)
        ink('Bank coping',[(x,y,z+.8),(x+1.25,y,z+.8)],.1)
    oak('Volume oak west',-15.8,13,6.2,812)
    oak('Volume oak east',14.8,22,5.0,813)
    oak('Volume oak ridge',-18,26,5.0,814)
    return top,base,footprints,routes


CAMERAS=[('main',(21,-30,17),(0,11,1.2),4100.),
         ('low',(23,-31,11),(0,11,.8),4100.)]
PLANAR_TREES=[(-17,-.8,6.5),(-15,27,4.0),(-9,29,4.4),(-2,30,4.0),(6,30,4.5),(13,28,4.1)]
