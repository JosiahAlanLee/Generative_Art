"""Verify that the comparison changes terrain while retaining the task drawing."""
from pathlib import Path
import hashlib,json
import numpy as np
from terrain_height import sampler

R=Path(__file__).resolve().parent;O=R/'output';modes=('control','incised','ravined')
states={m:dict(np.load(O/('recorded_route-'+m)/'terrain-state.npz')) for m in modes}
scenes={m:json.loads((O/('recorded_route-'+m)/'scene.json').read_text()) for m in modes}
checks={}
def record(n,ok,**data):checks[n]=dict(passed=bool(ok),**data)
base=states['control'];fixed=base['fixed_mask']
record('identical_initial_height_field',all(np.array_equal(base['initial'],s['initial']) for s in states.values()))
record('zero_steps_control_is_unchanged',np.array_equal(base['height'],base['initial']))
record('protected_sites_and_edges_retained',all(np.array_equal(s['height'][s['fixed_mask']],s['initial'][s['fixed_mask']]) for s in states.values()))
record('task_program_and_cameras_unchanged',all(s['architecture']==scenes['control']['architecture'] and s['cameras']==scenes['control']['cameras'] for s in scenes.values()))
record('explicit_architecture_routes_and_detail_unchanged',all(s['strokes']==scenes['control']['strokes'] for s in scenes.values()))
differences={m:float(np.max(abs(s['height']-s['initial']))) for m,s in states.items()}
record('actual_height_changes',differences['incised']>.1 and differences['ravined']>.1,maximum_world_unit_change=differences)
runoff={}
for m,s in states.items():
    rec=s['receiver'].ravel();a=s['area'].ravel();h=s['routed_height'].ravel();active=rec>=0
    runoff[m]=dict(outlets=float(a[~active].sum()),cells=len(a))
    record(m+'_routing_descends_and_conserves_runoff',np.all(h[rec[active]]<h[active]) and np.isclose(a[~active].sum(),len(a)))
    check=json.loads((O/('recorded_route-'+m)/'checks-main.json').read_text())
    native=json.loads((O/('recorded_route-'+m)/'blender-visibility.json').read_text())
    record(m+'_visibility_and_print_checks',check['all_passed'] and native['visible_violations']==0,native=native)
summary=dict(all_passed=all(c['passed'] for c in checks.values()),checks=checks,runoff=runoff,
             native_ray_samples=sum(checks[m+'_visibility_and_print_checks']['native']['native_ray_samples'] for m in modes),
             process_tests=21,steps={m:int(s['steps']) for m,s in states.items()})
(O/'erosion-validation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if not summary['all_passed']:raise SystemExit(1)
