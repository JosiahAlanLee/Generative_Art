"""Scene-specific assertions supplement the common print and visibility audit."""
from pathlib import Path
import json
import numpy as np
from compile import compile_document,compile_case

from scene import output_dir
R=Path(__file__).resolve().parent;O=output_dir('spillway','incised');DRY=O.name.endswith('-dryrun')
A=compile_document(json.loads((R/'spillway-tasks.json').read_text()),'spillway')
nodes={n['id']:n for n in A['nodes']};checks={}
def check(name,ok):checks[name]=bool(ok)
check('completion_14_meets_deadline',A['result']['executable_completion']==14 and A['result']['feasible'])
check('release_wait_4_is_separate_from_duration_3',nodes['permit']['wait_duration']==4 and nodes['permit']['wait_length']==3 and nodes['permit']['bays']==3 and nodes['permit']['plinth']==0)
check('only_release_then_permit_gates_restart_are_red',
      [(e['source'],e['target']) for e in A['edges'] if e['red']]==[('permit','gates'),('gates','restart')]
      and [n['id'] for n in A['nodes'] if n['release_mark']]==['permit'])
D=json.loads((O/'scene.json').read_text());V=np.asarray(D['vertices'])
for name,n in nodes.items():
    ids={i for f,obj in zip(D['faces'],D['names']) if obj.startswith(name+' | horizontal duration bays') for i in f}
    width=float(np.ptp(V[sorted(ids),0]))
    check(name+'_horizontal_gn_extent',abs(width-(1.6*n['bays']+.08))<.002)
s=np.load(O/'terrain-state.npz');fixed=s['fixed_mask']
check('erosion_changes_ground_but_preserves_access_pads',np.array_equal(s['height'][fixed],s['initial'][fixed]) and np.max(s['initial']-s['height'])>1)
check('original_specimen_arithmetic_preserved',[compile_case(c)['result']['executable_completion'] for c in ('recorded_route','rehearsed_route','late_opening','gate_unavailable')]==[10,5,11,None])
views={};skipped={}
for v in ('main','low'):
    common=json.loads((O/f'checks-{v}.json').read_text());backend=common.get('backend','blender')
    check(v+'_common_checks',common['all_passed'])
    if backend=='blender':
        native=json.loads((O/('blender-visibility.json' if v=='main' else 'blender-visibility-low.json')).read_text())
        check(v+'_independent_blender_rays',native['visible_violations']==0)
    else:native=None;skipped[v+'_independent_blender_rays']='no Blender evaluation in a '+backend+' dry run'
    zones=common['measured']['zones']
    check(v+'_subject_framing',zones['building']['area_fraction']>=.08 and zones['sky']['area_fraction']<.30)
    views[v]=dict(backend=backend,measured=common['measured'],native=native)
result=dict(scene='spillway',all_passed=all(checks.values()),checks=checks,skipped=skipped,views=views,
            evaluator=A['result'],source_pr=23)
(R/'output'/('spillway-validation-dryrun.json' if DRY else 'spillway-validation.json')).write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
if not result['all_passed']:raise SystemExit(1)
