"""Rebuild the study without requiring matching Blender/Numba Python versions."""
from pathlib import Path
import argparse,os,subprocess,sys
from compile import CASES
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--blender-python',required=True,help='Python with bpy 4.5 LTS installed')
p.add_argument('--engraving-python',default=sys.executable,help='Python with requirements.txt')
p.add_argument('--cases',nargs='+',default=list(CASES),choices=CASES)
p.add_argument('--no-clay',action='store_true')
a=p.parse_args()
for case in a.cases:
    env=dict(os.environ,INFERNAL_CASE=case,NUMBA_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',OMP_NUM_THREADS='4')
    if a.no_clay:env['INFERNAL_RENDER']='0'
    out=R/'output'/case;out.mkdir(parents=True,exist_ok=True)
    for label,cmd in [('model',[a.blender_python,'model.py']),('patches',['node','patches.cjs']),
                      ('render',[a.engraving_python,'render.py']),('checks',[a.engraving_python,'checks.py']),
                      ('native rays',[a.blender_python,'verify_blender.py'])]:
        print(case+' / '+label,flush=True)
        with (out/(label.replace(' ','-')+'.log')).open('w') as log:
            subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
