"""Build a scene record without Blender, so the engraving stages run anywhere.

Same INFERNAL_CASE / INFERNAL_TERRAIN / INFERNAL_INPUT selection as model.py.
The builder instances the duration modules itself and writes the same
`scene.json` schema. What it cannot do is Blender's part: the Displace
roughening of the terrain, the Cycles clay proof, the saved .blend file and
the independent native ray audit. The record is marked `backend: numpy`;
checks skip the Blender-only audits for it, and the package scripts refuse
it. Use it to develop and test the drawing; deliver from the Blender model.
"""
import json
import geometry as G
import scene as S

if __name__ == '__main__':
    ctx = S.context(); OUT = ctx['out']
    B = G.SceneBuilder(ctx['A'], ctx['terrain_z'])
    extras = S.assemble(B, ctx)
    data = B.export(footprints=extras['footprints'], routes=extras['routes'], terrain_mode=ctx['terrain_mode'],
                    planar_trees=extras['planar_trees'], terrain_state=ctx['state'])
    (OUT / 'scene.json').write_text(json.dumps(data, separators=(',', ':')))
    audit = G.outward_audit(data)
    (OUT / 'blender-checks.json').write_text(json.dumps(dict(
        backend='numpy', blender=None, evaluated_faces=len(data['faces']), native_camera_max_error_px=None,
        geometry_nodes=data['geometry_nodes'], outward_audit=audit,
        note='NumPy dry run: no Displace, no clay render, no native Blender rays'), indent=2))
    print(json.dumps(dict(case=ctx['case'], backend='numpy', faces=len(data['faces']),
                          inward_solids=sum(v['inward'] for v in audit.values()))), flush=True)
