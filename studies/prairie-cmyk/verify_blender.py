"""Independent Blender-native point visibility, including an injected buried point."""
from pathlib import Path
import json
import numpy as np
import bpy
from mathutils import Vector
R=Path(__file__).resolve().parent;O=R/'output'
bpy.ops.wm.open_mainfile(filepath=str(O/'Prairie_Bluffs_CMYK.blend'))
SC=bpy.context.scene;deps=bpy.context.evaluated_depsgraph_get()
data=json.loads((O/'scene.json').read_text());count=0;violations=0
for name in ['main','low']:
    eye=Vector(data['cameras'][name]['eye'])
    for kind in ['surface','hatch']:
        p=np.load(O/f'{kind}-audit-{name}.npz')['world']
        ix=np.linspace(0,len(p)-1,min(1000,len(p))).astype(int)
        for q in p[ix]:
            q=Vector(q);d=eye-q;distance=d.length;d.normalize()
            violations+=int(SC.ray_cast(deps,q+d*.006,d,distance=distance-.012)[0]);count+=1
eye=Vector(data['cameras']['main']['eye']);buried=Vector((10,23,1.0));d=eye-buried;distance=d.length;d.normalize()
blocked=SC.ray_cast(deps,buried+d*.006,d,distance=distance-.012)[0]
info={'native_samples':count,'violations':violations,'buried_point_blocked':bool(blocked)}
(O/'blender-visibility.json').write_text(json.dumps(info,indent=2));print(json.dumps(info))
if violations or not blocked:raise SystemExit(1)
