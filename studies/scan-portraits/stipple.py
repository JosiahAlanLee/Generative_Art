"""Stippled half-tones: dots for the light flesh tones, between the drawn lines.

An engraver models the lights of a face with dots and short flicks, and keeps
the long lines for the shadows. Here the darkness that the hatching would have
carried in the light half-tones is split: `dot_share` of it goes to dots,
fading to none by `dots_until`.

The dots are placed by the collection's Poisson-disc sampler,
`lib/halftone/poisson.py` (after thi.ng's `poisson`), with an exclusion radius
read at each candidate from a raster of the dot coverage the light asks for.
That raster is ray cast through the plate's camera, so a dot only lands on the
visible scan. Candidates within a dot's width of any drawn line are refused,
so the dots sit between the hatch lines instead of on them.
"""
import hashlib
import math
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

REPO = Path(__file__).resolve().parents[2]
STATUE = Path(__file__).resolve().parents[1] / 'scanned-statue-v2'
for p in (REPO, STATUE):
    if str(p) not in sys.path:
        sys.path.append(str(p))
import raycore                         # noqa: E402  Scanned Statue v2, unchanged
from lib.halftone import poisson_sample  # noqa: E402  the thi.ng port, unchanged

# Dart throwing to saturation reaches about this many points per r^2 (r the exclusion radius):
# random sequential adsorption fills ~0.55 of the plane with discs of radius r/2, i.e. 0.70 / r^2;
# the sampler's quality limit stops a little short. checks.py measures it on a uniform field.
# Between hatch lines the open ground is a set of narrow strips, and in a strip narrower than the
# radius the sampler packs tighter than on open paper. So dots() compares the count it got with
# the count the light asked for and, while they differ by more than 4 %, samples again (up to four
# times) with the packing scaled by that ratio.
PACKING = .64


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def dot_share(d, tone):
    """Fraction of the darkness carried by dots: `dots` in the lights, none from `dots_until` on."""
    return tone['dots'] * (1 - smoothstep(tone['dots_from'], tone['dots_until'], d))


def dot_ink_radius(pen, tone):
    """Radius of the inked disc a dot leaves: its drawn ring plus half the pen."""
    return tone['dot_ring_mm'] + .5 * pen


def surface_raster(cam, bvh, scan, region, res):
    """First hit of a ray through every cell centre: (hit mask, face index, barycentrics) on a grid."""
    x0, y0, x1, y1 = region
    nx, ny = int(math.ceil((x1 - x0) / res)), int(math.ceil((y1 - y0) / res))
    gx, gy = np.meshgrid(x0 + (np.arange(nx) + .5) * res, y0 + (np.arange(ny) + .5) * res)
    xy = np.stack([gx.ravel(), gy.ravel()], 1)
    hit = np.zeros(len(xy), bool); face = np.zeros(len(xy), np.int64); bary = np.zeros((len(xy), 3))
    order = bvh[8]
    for s in range(0, len(xy), 400000):
        sl = slice(s, s + 400000)
        d = cam.rays(xy[sl, 0], xy[sl, 1])
        T, H = raycore.first_hits(np.tile(cam.eye, (len(d), 1)), d, 1e3, *bvh[:3], *bvh[3:6])
        h = H >= 0
        f = order[H[h]]
        P = cam.eye + d[h] * T[h, None]
        tri = scan.V[scan.F[f]]
        v0 = tri[:, 1] - tri[:, 0]; v1 = tri[:, 2] - tri[:, 0]; v2 = P - tri[:, 0]
        d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
        d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1); den = d00 * d11 - d01 * d01
        b1 = (d11 * d20 - d01 * d21) / den; b2 = (d00 * d21 - d01 * d20) / den
        idx = np.flatnonzero(h) + s
        hit[idx] = True; face[idx] = f; bary[idx] = np.stack([1 - b1 - b2, b1, b2], 1)
    return xy, hit, face, bary, (ny, nx)


def line_clearance(paths, region, res):
    """Distance in mm from every cell centre to the nearest drawn line's centre.

    Each path is walked at half a cell and its cells marked, then a distance transform taken. (A
    wide-line rasteriser is not used: PIL draws a 2-pixel line about one pixel wide, with gaps.)"""
    x0, y0, x1, y1 = region
    nx, ny = int(math.ceil((x1 - x0) / res)), int(math.ceil((y1 - y0) / res))
    ink = np.zeros((ny, nx), bool)
    for p in paths:
        seg = np.diff(p, axis=0); n = np.maximum(1, np.ceil(np.linalg.norm(seg, axis=1) / (.5 * res)).astype(int))
        t = np.concatenate([np.arange(k) / k for k in n])
        a = np.repeat(p[:-1], n, axis=0); b = np.repeat(p[1:], n, axis=0)
        q = np.vstack([a + (b - a) * t[:, None], p[-1:]])
        ix = np.clip(((q[:, 0] - x0) / res).astype(int), 0, nx - 1); iy = np.clip(((q[:, 1] - y0) / res).astype(int), 0, ny - 1)
        ink[iy, ix] = True
    return distance_transform_edt(~ink) * res


def dots(cam, bvh, scan, vlight, albedo_at_uv, head_paths, region, fade_fn, darkness_fn, pen, tone, key):
    """Dot centres in sheet millimetres (camera placement), and a record of what was placed.

    darkness_fn(light, albedo) -> (d, desired coverage before the fade); fade_fn(xy) -> [0, 1].
    """
    res = tone['dot_raster_mm']
    xy, hit, face, bary, shape = surface_raster(cam, bvh, scan, region, res)
    F = scan.F[face[hit]]
    light = (bary[hit] * vlight[F]).sum(1)
    if albedo_at_uv is not None:
        uv = (bary[hit][:, :, None] * scan.UV[scan.Fu[face[hit]]]).sum(1)
        albedo = albedo_at_uv(uv)
    else:
        albedo = np.ones(len(light))
    d, desired = darkness_fn(light, albedo)
    cover = np.zeros(len(xy))
    cover[hit] = desired * fade_fn(xy[hit]) * dot_share(d, tone) * tone['dot_gain']
    cover = cover.reshape(shape)
    # A dot's ink must clear a line's ink by dot_gap_mm; half a cell more covers the raster's rounding.
    clear = line_clearance(head_paths, region, res) >= .5 * pen + dot_ink_radius(pen, tone) + tone['dot_gap_mm'] + .5 * res
    area = math.pi * dot_ink_radius(pen, tone) ** 2
    r_min, r_max = tone['dot_r_min_mm'], tone['dot_r_max_mm']
    c_min = PACKING * area / r_max ** 2            # lighter than this asks for dots farther apart than r_max
    allowed = clear & (cover >= c_min)
    x0, y0 = region[:2]
    # Dots the light asks for at this dot size; where r_min caps the radius it asks for fewer.
    asked = float((np.minimum(cover, PACKING * area / r_min ** 2)[allowed]).sum() * res * res / area)

    def cell(p):
        return (min(shape[0] - 1, max(0, int((p[1] - y0) / res))), min(shape[1] - 1, max(0, int((p[0] - x0) / res))))

    def mask(p):
        return bool(allowed[cell(p)])

    seed = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)
    packing = PACKING; passes = []
    for attempt in range(4):
        def radius(p, k=packing):
            # r_max decides where dots may go (allowed, above); capping the radius at it as well would
            # pack the faintest cells tighter than asked as the packing is corrected upward.
            c = cover[cell(p)]
            return min(2 * r_max, max(r_min, math.sqrt(k * area / c))) if c > 0 else 2 * r_max
        rng = np.random.default_rng(seed)
        pts = poisson_sample(region, radius, rng, min_radius=r_min, quality=tone['dot_quality'], iterations=3,
                             mask=mask)
        passes.append(dict(packing=round(packing, 4), dots=int(len(pts))))
        ratio = len(pts) / max(asked, 1.)
        if abs(ratio - 1) <= .04 or attempt == 3:
            break
        packing *= ratio
    return pts, dict(dots=int(len(pts)), asked=round(asked), passes=passes, seed=seed, raster_mm=res,
                     ink_radius_mm=round(dot_ink_radius(pen, tone), 4),
                     allowed_mm2=round(float(allowed.sum()) * res * res, 1))


def ring(x, y, r, n=10):
    """A dot for a pen: a closed ring of radius r, small enough that the pen fills it."""
    t = np.linspace(0, 2 * np.pi, n + 1)
    return np.column_stack([x + r * np.cos(t), y + r * np.sin(t)])
