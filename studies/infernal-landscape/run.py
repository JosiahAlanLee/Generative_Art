"""Rebuild the study without requiring matching Blender/Numba Python versions."""
from pathlib import Path
import argparse,os,subprocess,sys
from compile import CASES
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--blender-python',required=False,help='Python with bpy 4.5 LTS installed (not needed with --dry-run)')
p.add_argument('--engraving-python',default=sys.executable,help='Python with requirements.txt')
p.add_argument('--cases',nargs='+',default=list(CASES),choices=CASES)
p.add_argument('--views',nargs='+',default=['main'],choices=['main','low'],help='package.py needs the low view of recorded_route as well')
p.add_argument('--no-clay',action='store_true')
p.add_argument('--dry-run',action='store_true',help='build the scenes in NumPy instead of Blender; development only, not packaged')
a=p.parse_args()
if not a.dry_run and not a.blender_python:p.error('--blender-python is required unless --dry-run')
for case in a.cases:
    env=dict(os.environ,INFERNAL_CASE=case,NUMBA_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',OMP_NUM_THREADS='4')
    if a.no_clay:env['INFERNAL_RENDER']='0'
    if a.dry_run:env['INFERNAL_DRYRUN']='1'
    out=R/'output'/(case+'-dryrun' if a.dry_run else case);out.mkdir(parents=True,exist_ok=True)
    stages=[('model',[a.engraving_python,'dryrun.py'] if a.dry_run else [a.blender_python,'model.py'],'main'),
            ('patches',['node','patches.cjs'],'main')]
    for view in a.views:
        stages+=[('render-'+view,[a.engraving_python,'render.py'],view),('checks-'+view,[a.engraving_python,'checks.py'],view)]
        if not a.dry_run:stages.append(('native-rays-'+view,[a.blender_python,'verify_blender.py'],view))
    for label,cmd,view in stages:
        print(case+' / '+label,flush=True)
        with (out/(label+'.log')).open('w') as log:
            subprocess.run(cmd,cwd=R,env={**env,'TERRAIN_VIEW':view},stdout=log,stderr=subprocess.STDOUT,check=True)
