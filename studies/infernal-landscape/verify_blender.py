"""Check delivered points against Blender's independently evaluated scene rays."""
from pathlib import Path
import json,os
import bpy
import numpy as np
from mathutils import Vector
R=Path(__file__).resolve().parent;case=os.environ.get('INFERNAL_CASE','recorded_route');O=R/'output'/case
bpy.ops.wm.open_mainfile(filepath=str(O/('Infernal_'+case+'.blend')))
SC=bpy.context.scene;bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
view=os.environ.get('TERRAIN_VIEW','main')
D=json.loads((O/'scene.json').read_text());eye=Vector(D['cameras'][view]['eye']);checked=violations=0
for prefix in ('surface','hatch'):
    world=np.load(O/f'{prefix}-audit-{view}.npz')['world']
    for p in world[np.linspace(0,len(world)-1,min(800,len(world))).astype(int)]:
        p=Vector(p);d=eye-p;distance=d.length;d.normalize()
        hit=SC.ray_cast(deps,p+d*.006,d,distance=distance-.012)[0]
        checked+=1;violations+=int(hit)
info=dict(case=case,view=view,native_ray_samples=checked,visible_violations=violations)
(O/('blender-visibility.json' if view=='main' else f'blender-visibility-{view}.json')).write_text(json.dumps(info,indent=2));print(json.dumps(info))
if violations:raise SystemExit(1)
