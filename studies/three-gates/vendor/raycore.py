"""Ray queries and light transport for the v2 engraving.

Everything the kernels need is passed in as an argument. The v1 kernels read
the camera from module globals, which Numba freezes into its on-disk cache;
changing the camera there could silently reuse a stale compiled function.
"""
import math
import numpy as np
from numba import njit, prange, config as numba_config, set_num_threads

set_num_threads(min(4, numba_config.NUMBA_NUM_THREADS))

# Material ids, as in v1: 0 = setting, 6 = scan.
ALBEDO = 0.72          # v1 surface albedo for materials 0 and 6
BOUNCE_ALBEDO = 0.70   # v1 albedo of the surface a bounce ray lands on
AMBIENT = 0.10
EXPOSURE = 1.6


def build_bvh(tris, mats, leaf=4):
    """Median-split BVH over an (N,3,3) triangle array.

    Returns (blo, bhi, nodes, v0, e1, e2, mats, normals) with triangles in leaf
    order. nodes[i] = [left, right, start, count]; count > 0 marks a leaf.
    """
    tris = np.asarray(tris, np.float64)
    lo = tris.min(1); hi = tris.max(1); cent = (lo + hi) / 2
    nodes = []; order = []

    def build(ix):
        index = len(nodes)
        node = [lo[ix].min(0), hi[ix].max(0), -1, -1, 0, 0]; nodes.append(node)
        if len(ix) <= leaf:
            node[4] = len(order); node[5] = len(ix); order.extend(ix.tolist())
        else:
            axis = int(np.argmax(np.ptp(cent[ix], axis=0)))
            ix = ix[np.argsort(cent[ix, axis], kind='stable')]
            mid = len(ix) // 2
            node[2] = build(ix[:mid]); node[3] = build(ix[mid:])
        return index

    import sys
    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))
    build(np.arange(len(tris)))
    order = np.asarray(order)
    t = tris[order]
    normal = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    return (np.array([n[0] for n in nodes]), np.array([n[1] for n in nodes]),
            np.array([n[2:] for n in nodes], np.int32),
            np.ascontiguousarray(t[:, 0]), np.ascontiguousarray(t[:, 1] - t[:, 0]),
            np.ascontiguousarray(t[:, 2] - t[:, 0]), np.asarray(mats, np.int32)[order], normal, order)


@njit(cache=True, fastmath=False)
def _box(ox, oy, oz, ix, iy, iz, blo, bhi, ni, tmin, tmax):
    a = (blo[ni, 0] - ox) * ix; b = (bhi[ni, 0] - ox) * ix
    t0 = min(a, b); t1 = max(a, b)
    a = (blo[ni, 1] - oy) * iy; b = (bhi[ni, 1] - oy) * iy
    t0 = max(t0, min(a, b)); t1 = min(t1, max(a, b))
    a = (blo[ni, 2] - oz) * iz; b = (bhi[ni, 2] - oz) * iz
    t0 = max(t0, min(a, b)); t1 = min(t1, max(a, b))
    t0 = max(t0, tmin); t1 = min(t1, tmax)
    return t0, t1


@njit(cache=True)
def trace(o, d, tmin, tmax, anyhit, blo, bhi, nodes, v0, e1, e2):
    """Closest (or any) hit with t in (tmin, tmax). Returns (t, triangle index or -1)."""
    ox, oy, oz = o[0], o[1], o[2]; dx, dy, dz = d[0], d[1], d[2]
    ix = 1.0 / dx if abs(dx) > 1e-15 else 1e30
    iy = 1.0 / dy if abs(dy) > 1e-15 else 1e30
    iz = 1.0 / dz if abs(dz) > 1e-15 else 1e30
    stack = np.empty(96, np.int32); sp = 1; stack[0] = 0
    best = tmax; hit = -1
    while sp > 0:
        sp -= 1; ni = stack[sp]
        t0, t1 = _box(ox, oy, oz, ix, iy, iz, blo, bhi, ni, tmin, best)
        if t0 > t1:
            continue
        count = nodes[ni, 3]
        if count > 0:
            start = nodes[ni, 2]
            for j in range(start, start + count):
                ax, ay, az = e1[j, 0], e1[j, 1], e1[j, 2]
                bx, by, bz = e2[j, 0], e2[j, 1], e2[j, 2]
                px = dy * bz - dz * by; py = dz * bx - dx * bz; pz = dx * by - dy * bx
                det = ax * px + ay * py + az * pz
                if abs(det) < 1e-14:
                    continue
                inv = 1.0 / det
                tx = ox - v0[j, 0]; ty = oy - v0[j, 1]; tz = oz - v0[j, 2]
                u = (tx * px + ty * py + tz * pz) * inv
                if u < 0.0 or u > 1.0:
                    continue
                qx = ty * az - tz * ay; qy = tz * ax - tx * az; qz = tx * ay - ty * ax
                v = (dx * qx + dy * qy + dz * qz) * inv
                if v < 0.0 or u + v > 1.0:
                    continue
                t = (bx * qx + by * qy + bz * qz) * inv
                if t > tmin and t < best:
                    best = t; hit = j
                    if anyhit:
                        return best, hit
        else:
            l = nodes[ni, 0]; r = nodes[ni, 1]
            la, lb = _box(ox, oy, oz, ix, iy, iz, blo, bhi, l, tmin, best)
            ra, rb = _box(ox, oy, oz, ix, iy, iz, blo, bhi, r, tmin, best)
            lok = la <= lb; rok = ra <= rb
            # Push the farther child first so the nearer one is searched first.
            if lok and rok:
                if la < ra:
                    stack[sp] = r; stack[sp + 1] = l
                else:
                    stack[sp] = l; stack[sp + 1] = r
                sp += 2
            elif lok:
                stack[sp] = l; sp += 1
            elif rok:
                stack[sp] = r; sp += 1
    return best, hit


@njit(cache=True, parallel=True)
def first_hits(origins, dirs, tmax, blo, bhi, nodes, v0, e1, e2):
    n = len(origins); T = np.empty(n); H = np.empty(n, np.int64)
    for i in prange(n):
        t, h = trace(origins[i], dirs[i], 1e-6, tmax, False, blo, bhi, nodes, v0, e1, e2)
        T[i] = t; H[i] = h
    return T, H


@njit(cache=True, parallel=True)
def visible_from(points, lift, eye, blo, bhi, nodes, v0, e1, e2):
    """Point-to-eye visibility. `lift` (N,3) is a small offset added to each
    point first: along the viewer-facing normal for surface samples, outward
    for contour samples, so grazing rays do not clip the point's own facets."""
    out = np.zeros(len(points), np.bool_)
    for i in prange(len(points)):
        o = points[i] + lift[i]
        d = eye - o; dist = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]); d = d / dist
        _, h = trace(o, d, 1e-5, dist - 1e-3, True, blo, bhi, nodes, v0, e1, e2)
        out[i] = h < 0
    return out


@njit(cache=True)
def _frame(n):
    ax = np.array([0., 0., 1.])
    if abs(n[2]) > .9:
        ax = np.array([1., 0., 0.])
    t = np.cross(ax, n); t /= math.sqrt(t[0] ** 2 + t[1] ** 2 + t[2] ** 2); b = np.cross(n, t)
    return t, b


@njit(cache=True)
def _direct(p, n, light, shadow, blo, bhi, nodes, v0, e1, e2):
    d = light - p; dist = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]); d = d / dist
    c = n[0] * d[0] + n[1] * d[1] + n[2] * d[2]
    if c <= 0.0:
        return 0.0
    if shadow:
        _, h = trace(p + n * .001, d, 1e-5, dist - .003, True, blo, bhi, nodes, v0, e1, e2)
        if h >= 0:
            return 0.0
    return 20.0 * c / (dist * dist)


@njit(cache=True, parallel=True)
def shade(P, N, lights, light_center, ao_uv, bounce_uv, blo, bhi, nodes, v0, e1, e2, tri_n):
    """v1's shading model, evaluated at arbitrary points with given normals.

    illum = .10*(1 - .95*ao) + (direct + .70*bounce) * .72 * 1.6, clipped to [0,1]
    direct: mean over area-light samples, shadowed. ao: mean of (1 - d/.35) over
    cosine-weighted rays that hit within .35. bounce: mean over cosine-weighted
    rays of light arriving at the first surface hit, times its albedo.
    Returns (illum, ao, direct, bounce).
    """
    n_pts = len(P)
    out = np.zeros((n_pts, 4))
    for i in prange(n_pts):
        p = P[i]; n = N[i]
        dl = 0.0
        for j in range(len(lights)):
            dl += _direct(p, n, lights[j], True, blo, bhi, nodes, v0, e1, e2)
        dl /= len(lights)
        t, b = _frame(n)
        ao = 0.0
        org = p + n * .0015
        for j in range(len(ao_uv)):
            r = math.sqrt(ao_uv[j, 0]); th = 2 * math.pi * ao_uv[j, 1]
            hd = r * math.cos(th) * t + r * math.sin(th) * b + math.sqrt(1 - ao_uv[j, 0]) * n
            dd, hh = trace(org, hd, 1e-5, .35, False, blo, bhi, nodes, v0, e1, e2)
            if hh >= 0:
                ao += 1 - dd / .35
        ao /= len(ao_uv)
        bounce = 0.0
        for j in range(len(bounce_uv)):
            r = math.sqrt(bounce_uv[j, 0]); th = 2 * math.pi * bounce_uv[j, 1]
            hd = r * math.cos(th) * t + r * math.sin(th) * b + math.sqrt(1 - bounce_uv[j, 0]) * n
            dd, hh = trace(org, hd, 1e-5, 8.0, False, blo, bhi, nodes, v0, e1, e2)
            if hh >= 0:
                q = org + hd * dd; nn = tri_n[hh].copy()
                if nn[0] * hd[0] + nn[1] * hd[1] + nn[2] * hd[2] > 0:
                    nn = -nn
                bounce += _direct(q, nn, light_center, True, blo, bhi, nodes, v0, e1, e2) * BOUNCE_ALBEDO
        bounce /= max(1, len(bounce_uv))
        illum = AMBIENT * (1 - .95 * ao) + (dl + .70 * bounce) * ALBEDO * EXPOSURE
        out[i, 0] = min(1.0, max(0.0, illum)); out[i, 1] = ao; out[i, 2] = dl; out[i, 3] = bounce
    return out


def light_grid(center, size_x, size_z, k):
    """k x k cell-centred samples over v1's rectangular area light."""
    c = (np.arange(k) + .5) / k - .5
    return np.array([center + [dx * size_x, 0., dz * size_z] for dx in c for dz in c])


def hemi_pattern(k):
    """Deterministic stratified (u, v) pairs for cosine-weighted directions."""
    return np.column_stack([(np.arange(k) + .5) / k, (np.arange(k) * .61803398875) % 1])
