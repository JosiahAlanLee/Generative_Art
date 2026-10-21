"""Existing D8 incision adapted to supplied height fields and protected sites.

Dimensionless illustration model. This extends the catchment construction in
models.py without changing the original generator or its committed outputs.
"""
import numpy as np
from scipy.ndimage import laplace
from .models import drainage, flood


def erode_heightfield(initial, *, steps=48, incision=.08, diffusion=.035,
                      fixed_mask=None):
    """Incise and diffuse a caller-supplied grid; keep edges and fixed sites.

    All edges are open outlets at their supplied elevation. Protected sites
    remain at the supplied elevation on every iteration. Depression filling
    affects routing, not the exported physical height. There is no deposition,
    calibrated time scale, or model of building/soil mechanics.
    """
    h=np.array(initial,dtype=float,copy=True)
    if h.ndim!=2 or min(h.shape)<8 or not np.isfinite(h).all():
        raise ValueError('Finite 2D grid with both dimensions >= 8 required')
    if not isinstance(steps,(int,np.integer)) or not 0<=steps<=300:
        raise ValueError('steps must be an integer in 0..300')
    if not 0<=incision<=.15 or not 0<=diffusion<=.20:
        raise ValueError('incision 0..0.15 and diffusion 0..0.20 required')
    fixed=np.zeros(h.shape,bool) if fixed_mask is None else np.asarray(fixed_mask,bool).copy()
    if fixed.shape!=h.shape:raise ValueError('fixed_mask must match the grid')
    fixed[[0,-1],:]=True;fixed[:,[0,-1]]=True
    original=h.copy();history=[]
    for _ in range(steps):
        routed=flood(h);rec,area,slope=drainage(routed)
        drop=np.zeros(h.size);r=rec.ravel();valid=r>=0
        drop[valid]=routed.ravel()[valid]-routed.ravel()[r[valid]]
        loss=np.minimum(incision*np.sqrt(area)*slope,.30*drop.reshape(h.shape))
        loss[fixed]=0
        h=h-loss+diffusion*laplace(h,mode='nearest')
        h[fixed]=original[fixed]
        history.append(float(loss.sum()))
    routed=flood(h);rec,area,slope=drainage(routed)
    return dict(height=h,initial=original,routed_height=routed,receiver=rec,
                area=area,slope=slope,fixed_mask=fixed,incision_history=np.asarray(history))
