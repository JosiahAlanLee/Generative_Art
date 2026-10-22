"""Rebuild the new scene, both engraved cameras, and their native ray checks."""
from pathlib import Path
import argparse,json,os,subprocess,sys

R=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blender-python',required=False,help='Python with bpy 4.5 LTS installed (not needed with --dry-run)')
    p.add_argument('--engraving-python',default=sys.executable)
    p.add_argument('--no-clay',action='store_true')
    p.add_argument('--dry-run',action='store_true',help='build the scene in NumPy instead of Blender; development only, not packaged')
    a=p.parse_args()
    if not a.dry_run and not a.blender_python:p.error('--blender-python is required unless --dry-run')
    env=dict(os.environ,INFERNAL_CASE='spillway',INFERNAL_TERRAIN='incised',
             INFERNAL_INPUT=str(R/'spillway-tasks.json'),NUMBA_NUM_THREADS='3',OPENBLAS_NUM_THREADS='3',OMP_NUM_THREADS='3')
    if a.no_clay:env['INFERNAL_RENDER']='0'
    if a.dry_run:env['INFERNAL_DRYRUN']='1'
    out=R/'output'/('spillway-incised-dryrun' if a.dry_run else 'spillway-incised');out.mkdir(parents=True,exist_ok=True)
    def run(label,cmd,view='main'):
        print(label,flush=True)
        with (out/(label+'.log')).open('w') as log:
            subprocess.run(cmd,cwd=R,env={**env,'TERRAIN_VIEW':view},stdout=log,stderr=subprocess.STDOUT,check=True)
    run('terrain',[a.engraving_python,'-c',
        "import json,numpy as np; from pathlib import Path; from compile import compile_document; "
        "from erosion import make_terrain; from terrain_height import base_height; "
        "a=compile_document(json.loads(Path('spillway-tasks.json').read_text()),'spillway'); "
        "from scene import output_dir; s,_=make_terrain('incised',a,base_height); out=output_dir('spillway','incised'); out.mkdir(parents=True,exist_ok=True); "
        "np.savez_compressed(out/'terrain-state.npz',**s)"])
    run('model',[a.engraving_python,'dryrun.py'] if a.dry_run else [a.blender_python,'model.py'])
    run('patches',['node','patches.cjs'])
    for view in ('main','low'):
        run('render-'+view,[a.engraving_python,'render.py'],view)
        run('checks-'+view,[a.engraving_python,'checks.py'],view)
        if not a.dry_run:run('native-'+view,[a.blender_python,'verify_blender.py'],view)
    run('spillway-checks',[a.engraving_python,'spillway_checks.py'])
    if not a.dry_run:run('package',[a.engraving_python,'package_spillway.py'])


if __name__=='__main__':main()
