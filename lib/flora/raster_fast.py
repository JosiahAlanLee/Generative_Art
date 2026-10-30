"""Optional accelerated triangle kernel; same depth/owner contract as render.py."""
import numpy as np
from numba import njit

@njit(cache=True)
def raster_triangle(buf, owners, triangle, owner):
    a,b,c=triangle[0],triangle[1],triangle[2]
    x0=max(0,int(np.floor(min(a[0],b[0],c[0]))));x1=min(buf.shape[1]-1,int(np.ceil(max(a[0],b[0],c[0]))))
    y0=max(0,int(np.floor(min(a[1],b[1],c[1]))));y1=min(buf.shape[0]-1,int(np.ceil(max(a[1],b[1],c[1]))))
    den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-12:return
    for y in range(y0,y1+1):
        for x in range(x0,x1+1):
            u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
            v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den
            w=1-u-v;z=u*a[2]+v*b[2]+w*c[2]
            if u>=-1e-8 and v>=-1e-8 and w>=-1e-8 and z>buf[y,x]:
                buf[y,x]=z;owners[y,x]=owner
