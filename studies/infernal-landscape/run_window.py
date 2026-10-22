"""Rebuild the window scene, engraved plate, and independent Blender ray audit."""
from pathlib import Path
import argparse,os,subprocess,sys
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--blender-python',required=False,help='Python with bpy 4.5 LTS installed (not needed with --dry-run)')
p.add_argument('--engraving-python',default=sys.executable)
p.add_argument('--no-clay',action='store_true',help='skip the Cycles clay proof (the packaged comparison sheet then omits it)')
p.add_argument('--dry-run',action='store_true',help='build the scene in NumPy instead of Blender; development only, not packaged')
a=p.parse_args()
if not a.dry_run and not a.blender_python:p.error('--blender-python is required unless --dry-run')
env={**os.environ,'INFERNAL_CASE':'window','INFERNAL_TERRAIN':'incised','INFERNAL_INPUT':str(R/'window-tasks.json'),
     'NUMBA_NUM_THREADS':'3','OPENBLAS_NUM_THREADS':'3','OMP_NUM_THREADS':'3'}
if a.no_clay:env['INFERNAL_RENDER']='0'
if a.dry_run:env['INFERNAL_DRYRUN']='1'
out=R/'output'/('window-incised-dryrun' if a.dry_run else 'window-incised');out.mkdir(parents=True,exist_ok=True)
stages=[('terrain',[a.engraving_python,'window.py']),
        ('model',[a.engraving_python,'dryrun.py'] if a.dry_run else [a.blender_python,'model.py']),
        ('patches',['node','patches.cjs']),('render-main',[a.engraving_python,'render.py'])]
if not a.dry_run:stages.append(('native-main',[a.blender_python,'verify_blender.py']))
stages.append(('window-checks',[a.engraving_python,'window_checks.py']))
if not a.dry_run:stages.append(('package',[a.engraving_python,'package_window.py']))
for label,cmd in stages:
    print(label,flush=True)
    with (out/(label+'.log')).open('w') as log:
        subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
