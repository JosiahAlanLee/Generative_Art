"""Rebuild the study without requiring matching Blender/Numba Python versions."""
from pathlib import Path
import argparse,os,subprocess,sys
from compile import CASES
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--blender-python',required=False,help='Python with bpy 4.5 LTS installed (not needed with --dry-run)')
p.add_argument('--engraving-python',default=sys.executable,help='Python with requirements.txt')
p.add_argument('--cases',nargs='+',default=list(CASES),choices=CASES)
p.add_argument('--views',nargs='+',default=None,choices=['main','low','tower','barn'],
               help='default main (main tower barn with --plates); package.py needs the low view of recorded_route as well')
p.add_argument('--no-clay',action='store_true')
p.add_argument('--dry-run',action='store_true',help='build the scenes in NumPy instead of Blender; development only, not packaged')
p.add_argument('--face-patterns',action='store_true',help='add strata and a barn quilt to flat walls (FACE-PATTERNS.md); writes output/<case>-face-patterns')
p.add_argument('--plates',action='store_true',help='the plate studies (PLATES.md): farmstead, flora, face patterns and the tower and barn cameras; writes output/<case>-plates')
a=p.parse_args()
if not a.dry_run and not a.blender_python:p.error('--blender-python is required unless --dry-run')
if a.plates and a.face_patterns:p.error('--plates already includes the face patterns')
views=a.views or (['main','tower','barn'] if a.plates else ['main'])
if not a.plates and set(views)-{'main','low'}:p.error('the tower and barn views exist only with --plates')
for case in a.cases:
    env=dict(os.environ,INFERNAL_CASE=case,NUMBA_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',OMP_NUM_THREADS='4')
    if a.no_clay:env['INFERNAL_RENDER']='0'
    if a.dry_run:env['INFERNAL_DRYRUN']='1'
    if a.face_patterns:env['INFERNAL_FACE_PATTERNS']='1'
    if a.plates:env['INFERNAL_PLATES']='1'
    variant='-plates' if a.plates else '-face-patterns' if a.face_patterns else ''
    out=R/'output'/(case+variant+('-dryrun' if a.dry_run else ''));out.mkdir(parents=True,exist_ok=True)
    stages=[('model',[a.engraving_python,'dryrun.py'] if a.dry_run else [a.blender_python,'model.py'],'main'),
            ('patches',['node','patches.cjs'],'main')]
    for view in views:
        stages+=[('render-'+view,[a.engraving_python,'render.py'],view),('checks-'+view,[a.engraving_python,'checks.py'],view)]
        if not a.dry_run:stages.append(('native-rays-'+view,[a.blender_python,'verify_blender.py'],view))
    for label,cmd,view in stages:
        print(case+' / '+label,flush=True)
        with (out/(label+'.log')).open('w') as log:
            subprocess.run(cmd,cwd=R,env={**env,'TERRAIN_VIEW':view},stdout=log,stderr=subprocess.STDOUT,check=True)
