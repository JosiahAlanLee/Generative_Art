"""One shared terrain seed, three erosion exposures, unchanged task architecture."""
from pathlib import Path
import sys
import numpy as np
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]))
from lib.process_art.models import noise
from lib.process_art.terrain import erode_heightfield
from terrain_height import sampler,base_height

PRESETS={'control':0,'incised':36,'ravined':110}


def make_terrain(mode,architecture,base_height):
    if mode not in PRESETS:raise ValueError('terrain mode must be control, incised or ravined')
    gx=np.linspace(-30,30,129);gy=np.linspace(-20,44,137)
    xx,yy=np.meshgrid(gx,gy)
    rng=np.random.default_rng(783)
    # Shared microrelief seeds branching; all three exposures start identically.
    rough=.30*noise(xx.shape,rng)+.10*gaussian_filter(rng.normal(size=xx.shape),1.2)
    fixed=np.zeros(xx.shape,bool)
    for n in architecture['nodes']:
        if architecture.get('scene_profile')=='spillway':
            from spillway import dimensions
            w,d=dimensions(n)
            fixed|=(abs(xx-n['x'])<.95)&(yy>n['y']-d/2-n['wait_length']-.35)&(yy<n['y']-d/2)
        else:w,d=(3.3,3.0) if n['id']=='approval' else (4.1,3.6) if n['id']=='staff' else (3.6,3.2)
        fixed|=(abs(xx-n['x'])<w/2+.85)&(abs(yy-n['y'])<d/2+.85)
    fixed|=(abs(xx)<2.4)&(yy> -1.2)&(yy<1.2)
    # Fade the perturbation into service pads; their original level is retained.
    rough[fixed]=0
    # A broad raised site shelf gives the process relief to cut at book scale.
    # This is declared initial composition, shared by every exposure.
    shelf=3.6*np.exp(-((xx+1)/14)**8-((yy-6)/14)**8)
    initial=base_height(xx,yy)+shelf+rough
    s=erode_heightfield(initial,steps=PRESETS[mode],incision=.12,diffusion=.028,fixed_mask=fixed)
    s.update(x=gx,y=gy,steps=np.asarray(PRESETS[mode]),seed=np.asarray(783))
    return s,sampler(s)


def channels(state,threshold=55):
    """Read chain segments from the actual receiver graph; no random fractal."""
    r=state['receiver'].ravel();a=state['area'].ravel();ny,nx=state['height'].shape
    active=(a>=threshold)&(r>=0);incoming=np.zeros(len(r),int)
    np.add.at(incoming,r[active],1)
    result=[]
    for i in np.flatnonzero(active&(incoming!=1)):
        path=[int(i)];j=int(r[i])
        while j>=0:
            path.append(j)
            if not active[j] or incoming[j]!=1:break
            j=int(r[j])
        if len(path)<3:continue
        p=np.asarray(path);result.append(np.c_[state['x'][p%nx],state['y'][p//nx]])
    return result


if __name__=='__main__':
    import os,json
    from compile import compile_case,compile_document
    case=os.environ.get('INFERNAL_CASE','recorded_route')
    architecture=(compile_document(json.loads(Path(os.environ['INFERNAL_INPUT']).read_text()),case)
                  if os.environ.get('INFERNAL_INPUT') else compile_case(case))
    for mode in PRESETS:
        out=ROOT/'output'/(case+'-'+mode);out.mkdir(parents=True,exist_ok=True)
        state,_=make_terrain(mode,architecture,base_height)
        np.savez_compressed(out/'terrain-state.npz',**state)
        print(mode,'steps',PRESETS[mode],'cut total',float(state['incision_history'].sum()),flush=True)
