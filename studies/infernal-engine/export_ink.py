"""Camera-aware SVG line and hatch export for Infernal Engine.
Run inside Blender after opening the supplied .blend. No add-on required.
Hidden lines are clipped by ray tests, sampled at approximately 1.4 SVG units.
This is a drawing export, not a physically based lighting reconstruction.
"""
import bpy, math, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path

ROOT=Path(os.environ.get('INFERNAL_OUTPUT',str(Path(__file__).resolve().parent)))
W,H=1600,2000
INK='#252a23'


def export(s,path):
    bpy.context.window.scene=s
    # Temporarily realize node instances to expose their faces to the exporter.
    edits=[]
    for ob in s.objects:
        for mod in ob.modifiers:
            if mod.type=='NODES' and mod.node_group:
                g=mod.node_group
                out=next(n for n in g.nodes if n.type=='GROUP_OUTPUT')
                links=list(out.inputs['Geometry'].links)
                if links:
                    source=links[0].from_socket
                    real=g.nodes.new('GeometryNodeRealizeInstances')
                    g.links.new(source,real.inputs['Geometry']); g.links.new(real.outputs['Geometry'],out.inputs['Geometry'])
                    edits.append((g,out,source,real))
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    verts=[]; polygons=[]; edges=[]; hatchfaces=[]
    camera=s.camera.evaluated_get(dg)
    eye=camera.matrix_world.translation
    forward=camera.matrix_world.to_quaternion() @ Vector((0,0,-1))
    view=camera.matrix_world.inverted()
    frame=camera.data.view_frame(scene=s)
    if camera.data.type=='PERSP':
        xs=[v.x/-v.z for v in frame]; ys=[v.y/-v.z for v in frame]
    else:
        xs=[v.x for v in frame]; ys=[v.y for v in frame]
    left,right,bottom,top=min(xs),max(xs),min(ys),max(ys)
    light=Vector((-.4,-.5,1)).normalized()
    try:
        for ob in s.objects:
            if ob.type not in {'MESH','CURVE','SURFACE','FONT'} or ob.location.z < -50: continue
            ev=ob.evaluated_get(dg); me=ev.to_mesh()
            if not me: continue
            try:
                me.calc_loop_triangles()
                coords=[ev.matrix_world@v.co for v in me.vertices]
                base=len(verts); verts.extend(coords)
                polygons.extend(tuple(base+i for i in tri.vertices) for tri in me.loop_triangles)
                adjacency={}
                for f in me.polygons:
                    pts=[coords[i] for i in f.vertices]
                    if len(pts)<3: continue
                    normal=(pts[1]-pts[0]).cross(pts[2]-pts[0])
                    if normal.length < 1e-10: continue
                    normal.normalize(); center=sum(pts,Vector())/len(pts)
                    facing=normal.dot(eye-center) if camera.data.type=='PERSP' else normal.dot(-forward)
                    for k in f.edge_keys: adjacency.setdefault(tuple(sorted(k)),[]).append((normal,facing))
                    # Only broad, planar surfaces receive hatch marks.
                    # Leaves and curved pipe sections keep their outlines.
                    if ob.type=='MESH' and f.area>.35 and facing>0 and not any(t in ob.name for t in ['ground','floor','path']):
                        shade=normal.dot(light)
                        if shade<.65: hatchfaces.append((pts,.15 if shade>.05 else .10))
                for e in me.edges:
                    adj=adjacency.get(tuple(sorted(e.vertices)),[])
                    draw=len(adj)<2
                    if len(adj)>=2:
                        n1,f1=adj[0]; n2,f2=adj[1]
                        draw=(f1*f2<0) or (n1.dot(n2)<.45 and max(f1,f2)>0)
                    if draw: edges.append((coords[e.vertices[0]],coords[e.vertices[1]]))
            finally: ev.to_mesh_clear()
        tree=BVHTree.FromPolygons(verts,polygons,all_triangles=True,epsilon=.00001)
        def project(p):
            v=view@p; depth=-v.z
            if camera.data.type=='PERSP':
                if depth<=1e-6: return (0,0,depth)
                xx,yy=v.x/depth,v.y/depth
            else: xx,yy=v.x,v.y
            return ((xx-left)/(right-left)*W,(top-yy)/(top-bottom)*H,depth)
        def visible(p):
            if camera.data.type=='ORTHO':
                origin=p-forward*150; ray=forward; dist=150
            else:
                origin=eye; ray=p-eye; dist=ray.length
                if dist<1e-6: return False
                ray=ray/dist
            hit,_,_,distance=tree.ray_cast(origin,ray,dist+.02)
            return hit is None or distance>=dist-.012
        def stroke(a,b):
            p,q=project(a),project(b)
            if min(p[2],q[2])<=.01: return []
            if max(p[0],q[0])<0 or min(p[0],q[0])>W or max(p[1],q[1])<0 or min(p[1],q[1])>H: return []
            length=math.hypot(p[0]-q[0],p[1]-q[1])
            if length<.45: return []
            steps=min(1600,max(2,math.ceil(length/1.4)))
            runs=[]; active=[]
            for i in range(steps+1):
                t=i/steps; v=a.lerp(b,t); pp=project(v)
                ok=(-1<=pp[0]<=W+1 and -1<=pp[1]<=H+1 and visible(v))
                if ok: active.append(pp)
                elif active:
                    if len(active)>1: runs.append((active[0],active[-1]))
                    active=[]
            if len(active)>1: runs.append((active[0],active[-1]))
            return [f'M {u[0]:.2f},{u[1]:.2f} L {v[0]:.2f},{v[1]:.2f}' for u,v in runs]
        outline=[]; hatches=[]
        for a,b in edges: outline.extend(stroke(a,b))
        axis=Vector((1,.27,.73)).normalized()
        for pts,spacing in hatchfaces:
            vals=[p.dot(axis) for p in pts]
            first=math.ceil(min(vals)/spacing); last=math.floor(max(vals)/spacing)
            for k in range(first,last+1):
                level=k*spacing; hits=[]
                for i,a in enumerate(pts):
                    b=pts[(i+1)%len(pts)]; da=vals[i]-level; db=vals[(i+1)%len(pts)]-level
                    if da*db<0: hits.append(a.lerp(b,da/(da-db)))
                if len(hits)==2: hatches.extend(stroke(*hits))
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="177.8mm" height="222.25mm" viewBox="0 0 {W} {H}">',
             '<title>Infernal Engine — camera-visible ink study</title>',
             '<desc>Original procedural architecture. Occlusion sampled at 1.4 SVG units. Surface hatching uses face orientation, not Cycles illumination.</desc>',
             f'<g fill="none" stroke="{INK}" stroke-linecap="round" stroke-linejoin="round">',
             '<g id="hatching" stroke-width=".65">']
        svg.extend(f'<path d="{d}"/>' for d in hatches)
        svg.append('</g><g id="outlines" stroke-width="1.05">')
        svg.extend(f'<path d="{d}"/>' for d in outline)
        svg.extend(['</g></g></svg>'])
        path.write_text('\n'.join(svg))
        print('INK_EXPORT',s.name,len(outline),'outlines',len(hatches),'hatches',flush=True)
    finally:
        for g,out,source,real in edits:
            g.links.new(source,out.inputs['Geometry']); g.nodes.remove(real)
        bpy.context.view_layer.update()

if __name__=='__main__':
    if not any(s.name.startswith('IE •') for s in bpy.data.scenes):
        bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Infernal_Engine_0_1.blend'))
    for s in list(bpy.data.scenes):
        if s.name.startswith('IE •'):
            export(s,ROOT/('exterior_ink.svg' if '01 Common' in s.name else 'interior_ink.svg'))
