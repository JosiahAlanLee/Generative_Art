"""A BVH and ray queries for scenes that have none of their own (the garden) and for
object-only queries (the skull's surface map). Same median-split construction and
ray/triangle test as Sol's hallway and Memento engines."""
import numpy as np
from numba import njit, prange


def build(tris):
    """tris (n, 3, 3) -> (blo, bhi, nodes, ordered tris, order, unit normals)."""
    tris = np.asarray(tris, float)
    lo, hi = tris.min(1), tris.max(1)
    cent = (lo + hi) / 2
    nodes, order = [], []

    def rec(ix):
        index = len(nodes)
        node = [lo[ix].min(0), hi[ix].max(0), -1, -1, 0, 0]
        nodes.append(node)
        if len(ix) <= 8:
            node[4], node[5] = len(order), len(ix)
            order.extend(ix.tolist())
        else:
            axis = int(np.argmax(np.ptp(cent[ix], axis=0)))
            ix = ix[np.argsort(cent[ix, axis], kind='stable')]
            mid = len(ix) // 2
            node[2] = rec(ix[:mid])
            node[3] = rec(ix[mid:])
        return index

    import sys
    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))
    rec(np.arange(len(tris)))
    order = np.array(order)
    t = tris[order]
    normal = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    return (np.array([n[0] for n in nodes]), np.array([n[1] for n in nodes]),
            np.array([n[2:] for n in nodes], np.int32), np.ascontiguousarray(t), order, normal)


@njit(cache=True)
def cast(o, d, tmax, blo, bhi, nodes, tris):
    stack = np.empty(96, np.int32)
    stack[0] = 0
    sp = 1
    best = tmax
    hit = -1
    while sp:
        sp -= 1
        ni = stack[sp]
        tn = .0001
        tf = best
        ok = True
        for k in range(3):
            if abs(d[k]) < 1e-12:
                if o[k] < blo[ni, k] or o[k] > bhi[ni, k]:
                    ok = False
                    break
            else:
                a = (blo[ni, k] - o[k]) / d[k]
                b = (bhi[ni, k] - o[k]) / d[k]
                if a > b:
                    a, b = b, a
                tn = max(tn, a)
                tf = min(tf, b)
                if tn > tf:
                    ok = False
                    break
        if not ok:
            continue
        if nodes[ni, 3] > 0:
            start, count = nodes[ni, 2], nodes[ni, 3]
            for j in range(start, start + count):
                v0 = tris[j, 0]
                e1 = tris[j, 1] - v0
                e2 = tris[j, 2] - v0
                pv = np.cross(d, e2)
                det = np.dot(e1, pv)
                if abs(det) < 1e-10:
                    continue
                inv = 1 / det
                tv = o - v0
                u = np.dot(tv, pv) * inv
                if u < 0 or u > 1:
                    continue
                qv = np.cross(tv, e1)
                v = np.dot(d, qv) * inv
                if v < 0 or u + v > 1:
                    continue
                tt = np.dot(e2, qv) * inv
                if .0001 < tt < best:
                    best = tt
                    hit = j
        else:
            stack[sp] = nodes[ni, 0]
            stack[sp + 1] = nodes[ni, 1]
            sp += 2
    return best, hit


@njit(cache=True, parallel=True)
def first_hits(origins, dirs, tmax, blo, bhi, nodes, tris):
    n = origins.shape[0]
    dist = np.full(n, np.inf)
    hit = np.full(n, -1, np.int64)
    for i in prange(n):
        t, h = cast(origins[i], dirs[i], tmax, blo, bhi, nodes, tris)
        if h >= 0:
            dist[i] = t
            hit[i] = h
    return dist, hit


@njit(cache=True, parallel=True)
def visibility(points, eye, skip, blo, bhi, nodes, tris):
    """Is each point seen from the eye? Occluders closer than `skip` along the ray
    (the point's own surface) are ignored."""
    vis = np.zeros(points.shape[0], np.bool_)
    for i in prange(points.shape[0]):
        d = eye - points[i]
        dist = np.sqrt(np.dot(d, d))
        d /= dist
        if dist <= 2 * skip:
            vis[i] = True
            continue
        _, h = cast(points[i] + d * skip, d, dist - skip - .01, blo, bhi, nodes, tris)
        vis[i] = h < 0
    return vis
