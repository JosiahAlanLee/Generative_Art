"""Rebuild the window scene, engraved plate, and independent Blender ray audit."""
from pathlib import Path
import argparse,os,subprocess,sys
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--blender-python',required=True)
p.add_argument('--engraving-python',default=sys.executable)
a=p.parse_args()
env={**os.environ,'INFERNAL_CASE':'window','INFERNAL_TERRAIN':'incised','INFERNAL_INPUT':str(R/'window-tasks.json'),
     'NUMBA_NUM_THREADS':'3','OPENBLAS_NUM_THREADS':'3','OMP_NUM_THREADS':'3'}
out=R/'output/window-incised';out.mkdir(parents=True,exist_ok=True)
for label,cmd in [('terrain',[a.engraving_python,'window.py']),('model',[a.blender_python,'model.py']),
                  ('patches',['node','patches.cjs']),('render-main',[a.engraving_python,'render.py']),
                  ('native-main',[a.blender_python,'verify_blender.py']),('window-checks',[a.engraving_python,'window_checks.py']),('package',[a.engraving_python,'package_window.py'])]:
    print(label,flush=True)
    with (out/(label+'.log')).open('w') as log:
        subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
