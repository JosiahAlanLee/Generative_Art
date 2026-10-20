"""Spot-check clipped strokes with Blender's independent native ray_cast."""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
R=Path(__file__).resolve().parent;O=R/'output'
bpy.ops.wm.open_mainfile(filepath=str(O/'Terrain_Symbols.blend'))
SC=bpy.context.scene
for c in bpy.data.collections:
    if c.name.startswith('MAPPED |'):c.hide_viewport=True
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
violations=0;checked=0
for name in ['main','low']:
    eye=Vector(json.loads((O/'scene.json').read_text())['cameras'][name]['eye'])
    for prefix in ['surface','hatch']:
        world=np.load(O/f'{prefix}-audit-{name}.npz')['world']
        ix=np.linspace(0,len(world)-1,min(1200,len(world))).astype(int)
        for p in world[ix]:
            p=Vector(p);d=eye-p;distance=d.length;d.normalize()
            hit=SC.ray_cast(deps,p+d*.006,d,distance=distance-.012)[0]
            violations+=int(hit);checked+=1
data=json.loads((O/'scene.json').read_text());roof=np.array([4.4,8.2,0.])
hit,pos,*_=SC.ray_cast(deps,Vector((4.4,8.2,45)),Vector((0,0,-1)))
roof_z=pos.z
hit,pos,*_=SC.ray_cast(deps,Vector((4.4,8.2,-5)),Vector((0,0,1)))
# Inside the foundation, a point is necessarily occluded along the camera ray.
p=Vector((4.4,8.2,roof_z-1.))
eye=Vector(data['cameras']['main']['eye']);d=eye-p;dist=d.length;d.normalize()
blocked=SC.ray_cast(deps,p+d*.006,d,distance=dist-.012)[0]
info={'native_ray_samples':checked,'visible_violations':violations,'buried_fixture_blocked':bool(blocked)}
(O/'blender-visibility.json').write_text(json.dumps(info,indent=2));print(json.dumps(info))
if violations or not blocked:raise SystemExit(1)
