"""Add mapped ground marks and upright strokes as editable Blender curve layers.

These collections are hidden from the clay proof by default. They carry the
complete mapped strokes; final ink visibility is resolved by render.py. The
upright trees remain graphic symbols and are not volumetric tree models.
"""
from pathlib import Path
import json
import bpy
import numpy as np
R=Path(__file__).resolve().parent;O=R/'output'
bpy.ops.wm.open_mainfile(filepath=str(O/'Terrain_Symbols.blend'))
SC=bpy.context.scene

def collection(name):
    c=bpy.data.collections.new(name);SC.collection.children.link(c)
    c.hide_render=True;return c

def curve(name,paths,col,color,radius):
    paths=[p for p in paths if len(p)>1]
    if not paths:return
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=0
    for path in paths:
        # Preserve all ground sampling. Plants are already short / gently
        # curving and can use their original local engine vertices.
        pts=np.asarray(path,float)
        sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
        flat=np.column_stack([pts,np.ones(len(pts))]).ravel()
        sp.points.foreach_set('co',flat)
    ob=bpy.data.objects.new(name,cu);col.objects.link(ob)
    m=bpy.data.materials.get(name+' ink') or bpy.data.materials.new(name+' ink')
    m.diffuse_color=(*color,1);cu.materials.append(m)
    return ob

ground=collection('MAPPED | ground fields and rosette')
data=json.loads((O/'mapped-ground.json').read_text())
for kind,color,r in [('field',(.36,.42,.27),.007),('rosette',(.57,.20,.10),.012)]:
    paths=[]
    for row in data:
        if row['kind']!=kind:continue
        p=np.asarray(row['world']);ok=np.asarray(row['valid']);ix=np.flatnonzero(ok)
        for group in np.split(ix,np.flatnonzero(np.diff(ix)!=1)+1):
            if len(group)>1:paths.append(p[group])
    curve(kind+' | sampled on evaluated terrain',paths,ground,color,r)
plants=collection('MAPPED | upright Driftless strokes')
for i,row in enumerate(json.loads((O/'mapped-plants.json').read_text())):
    ob=curve(f"{i:03d} {row['kind']}",row['strokes'],plants,(.22,.32,.16),.007)
    if ob:ob['root']=row['root'];ob['symbol_scale']=row['scale']
SC.camera=bpy.data.objects['Camera main'];SC.render.resolution_percentage=100
SC['Mapped strokes']='Fields draped on evaluated triangles. Plants use parallel upright symbol planes. Both collections hidden in clay renders; toggle to inspect.'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Terrain_Symbols.blend'),compress=True)
print(json.dumps({'ground_curves':len(ground.objects),'upright_curve_objects':len(plants.objects)}))
