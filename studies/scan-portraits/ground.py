"""A ruled ground behind the head, held off it by a halo.

The engraved-portrait convention: an oval of ruled lines behind the sitter,
darkest beside the lit side of the face so that edge carries, lighter beside
the shadowed side, and stopped short of the outline by a band of bare paper.
The lines are candidates spaced in pen widths, kept by the same nested 64-step
order as the hatching, so the ground's tone and the head's are on one scale.
"""
import math
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, gaussian_filter1d, map_coordinates

STATUE = Path(__file__).resolve().parents[1] / 'scanned-statue-v2'
if str(STATUE) not in sys.path:
    sys.path.append(str(STATUE))
import raycore  # noqa: E402


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def rank_of(k, bits=6):
    n = 1 << bits
    return int(f'{k % n:0{bits}b}'[::-1], 2) / n + .5 / n


def subject_mask(cam, bvh, region, res):
    """True where a ray through the cell centre hits the scan; region is (x0, y0, x1, y1) in mm."""
    rx0, ry0, rx1, ry1 = region
    nx, ny = int(math.ceil((rx1 - rx0) / res)), int(math.ceil((ry1 - ry0) / res))
    xs = rx0 + (np.arange(nx) + .5) * res; ys = ry0 + (np.arange(ny) + .5) * res
    mask = np.zeros((ny, nx), bool)
    for r0 in range(0, ny, 200):
        rows = ys[r0:r0 + 200]
        gx, gy = np.meshgrid(xs, rows)
        d = cam.rays(gx.ravel(), gy.ravel())
        _, H = raycore.first_hits(np.tile(cam.eye, (len(d), 1)), d, 1e3, *bvh[:3], *bvh[3:6])
        mask[r0:r0 + len(rows)] = (H >= 0).reshape(len(rows), nx)
    return mask


def ruled(cam, bvh, sheet, pen, head_xy, head_mm, spec, fade):
    """Ruled ground paths in sheet millimetres, and a short record of what was drawn."""
    if spec.get('kind', 'none') == 'none':
        return [], dict(kind='none')
    res = spec.get('res', .25)
    # Work over the sheet and a quarter of it again on every side: the drawing is centred on the
    # sheet afterwards, so the plotting extent only clips it then.
    w, h = sheet['size']; region = (-.25 * w, -.25 * h, 1.25 * w, 1.25 * h)
    mask = subject_mask(cam, bvh, region, res)
    ny, nx = mask.shape
    gx, gy = np.meshgrid(region[0] + (np.arange(nx) + .5) * res, region[1] + (np.arange(ny) + .5) * res)
    # The subject is only "there" where the drawing keeps it: inside the vignette.
    r = np.hypot((gx - fade['cx']) / fade['rx'], (gy - fade['cy']) / fade['ry'])
    drawn = mask & (r < 1 - .5 * fade['soft'])
    dist = distance_transform_edt(~drawn) * res
    cx = head_xy[0] + spec['dx'] * head_mm; cy = head_xy[1] + spec['dy'] * head_mm
    rx = spec['rx'] * head_mm; ry = spec['ry'] * head_mm
    ro = np.hypot((gx - cx) / rx, (gy - cy) / ry)
    oval = 1 - smoothstep(1 - spec['soft'], 1, ro)
    halo = smoothstep(spec['halo_mm'], spec['halo_mm'] + spec['halo_soft_mm'], dist)
    # Where the vignette has faded the head out, the ground may come closer, but never onto it.
    clear = smoothstep(spec.get('clear_mm', .8), 2 * spec.get('clear_mm', .8), distance_transform_edt(~mask) * res)
    side = 1 + spec['gradient'] * np.clip((gx - cx) / rx, -1, 1) * spec['dark_side']
    coverage = np.clip(spec['tone'] * oval * halo * clear * side, 0, 1) * ~mask
    blocked = binary_dilation(mask, iterations=max(1, int(math.ceil(spec.get('clear_mm', .8) / res))))
    gap = spec['spacing_pens'] * pen
    angle = math.radians(spec.get('angle', 0.)); d = np.array([math.cos(angle), math.sin(angle)])
    nrm = np.array([-d[1], d[0]])
    corners = np.array([[cx - rx, cy - ry], [cx + rx, cy - ry], [cx + rx, cy + ry], [cx - rx, cy + ry]])
    offs = corners @ nrm; along = corners @ d
    paths = []; drawn_len = 0.
    for k, o in enumerate(np.arange(offs.min(), offs.max(), gap)):
        t = np.arange(along.min(), along.max(), spec.get('sample_mm', .3))
        xy = t[:, None] * d + o * nrm
        cov = map_coordinates(coverage, [(xy[:, 1] - region[1]) / res - .5, (xy[:, 0] - region[0]) / res - .5],
                              order=1, mode='constant')
        prob = np.clip(cov * gap / pen, 0, 1)
        prob = gaussian_filter1d(prob, 3., mode='nearest')
        on = map_coordinates(blocked.astype(float), [(xy[:, 1] - region[1]) / res - .5,
                                                     (xy[:, 0] - region[0]) / res - .5], order=0, mode='constant')
        keep = (prob > rank_of(k)) & (on < .5)      # smoothing must not carry a line onto the head
        ch = np.diff(np.r_[0, keep.astype(np.int8), 0])
        for a, b in zip(np.flatnonzero(ch == 1), np.flatnonzero(ch == -1)):
            if (b - a) * spec.get('sample_mm', .3) >= spec.get('min_mm', 1.5):
                paths.append(xy[[a, b - 1]] if spec.get('straight', True) else xy[a:b])
                drawn_len += np.linalg.norm(xy[b - 1] - xy[a])
    return paths, dict(kind=spec['kind'], lines=len(paths), metres=round(drawn_len / 1000, 2),
                       spacing_mm=round(gap, 4), halo_mm=spec['halo_mm'])
