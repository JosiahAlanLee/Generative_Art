"""NumPy-only terrain sampling, also usable inside Blender's Python."""
import numpy as np


def base_height(x,y):
    return (.20+.018*y+.30*np.sin(x*.19+y*.13)
            +2.3*np.exp(-((y-24-.17*x)/3.1)**2)
            +.65*np.exp(-((x+17)/4.1)**2)+.08*np.cos(x*.6-y*.3))


def sampler(state):
    gx,gy,z=state['x'],state['y'],state['height']
    def height(x,y):
        x,y=np.broadcast_arrays(np.asarray(x,float),np.asarray(y,float));shape=x.shape
        x,y=x.ravel(),y.ravel()
        if ((x<gx[0])|(x>gx[-1])|(y<gy[0])|(y>gy[-1])).any():
            raise ValueError('Terrain query outside the simulated grid')
        i=np.clip(np.searchsorted(gx,x,side='right')-1,0,len(gx)-2)
        j=np.clip(np.searchsorted(gy,y,side='right')-1,0,len(gy)-2)
        u=(x-gx[i])/(gx[i+1]-gx[i]);v=(y-gy[j])/(gy[j+1]-gy[j])
        return ((1-v)*((1-u)*z[j,i]+u*z[j,i+1])+v*((1-u)*z[j+1,i]+u*z[j+1,i+1])).reshape(shape)
    return height
