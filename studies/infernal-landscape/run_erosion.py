"""Build the three matched terrain exposures with separate Blender/ink Pythons."""
from pathlib import Path
import argparse,os,subprocess,sys

R=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--blender-python',required=False,help='Python with bpy 4.5 LTS installed (not needed with --dry-run)')
p.add_argument('--engraving-python',default=sys.executable)
p.add_argument('--no-clay',action='store_true')
p.add_argument('--dry-run',action='store_true',help='build the scenes in NumPy instead of Blender; development only, not packaged')
a=p.parse_args()
if not a.dry_run and not a.blender_python:p.error('--blender-python is required unless --dry-run')
env=dict(os.environ,INFERNAL_CASE='recorded_route',NUMBA_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',OMP_NUM_THREADS='4')
if a.dry_run:env['INFERNAL_DRYRUN']='1'
subprocess.run([a.engraving_python,'erosion.py'],cwd=R,env=env,check=True)
for mode in ('control','incised','ravined'):
    env['INFERNAL_TERRAIN']=mode
    if a.no_clay:env['INFERNAL_RENDER']='0'
    out=R/'output'/('recorded_route-'+mode+('-dryrun' if a.dry_run else ''))
    stages=[('model',[a.engraving_python,'dryrun.py'] if a.dry_run else [a.blender_python,'model.py']),('patches',['node','patches.cjs']),
            ('render',[a.engraving_python,'render.py']),('checks',[a.engraving_python,'checks.py'])]
    if not a.dry_run:stages.append(('native',[a.blender_python,'verify_blender.py']))
    for label,cmd in stages:
        print(mode+' / '+label,flush=True)
        with (out/(label+'.log')).open('w') as f:subprocess.run(cmd,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
env.pop('INFERNAL_TERRAIN',None)
subprocess.run([a.engraving_python,'erosion_checks.py'],cwd=R,env=env,check=True)
if not a.dry_run:subprocess.run([a.engraving_python,'package_erosion.py'],cwd=R,env=env,check=True)
