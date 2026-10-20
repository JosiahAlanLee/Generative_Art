"""Level sets on a triangle mesh: plane sections and interpolated contours.

Both are zero sets of a per-vertex linear function: a plane's signed distance
for hatch sections, n.v for contours. Crossing points are keyed by mesh edge,
so on the welded mesh curves join exactly where triangles share an edge.
"""
import numpy as np
from numba import njit


@njit(cache=True)
def chain_walk(seg, n_nodes):
    """Join segments (pairs of node ids) into chains. Open chains first, then loops.
    Returns (flat node ids, chain start offsets with a final end offset)."""
    m = seg.shape[0]
    deg = np.zeros(n_nodes, np.int64)
    for i in range(m):
        deg[seg[i, 0]] += 1; deg[seg[i, 1]] += 1
    ptr = np.zeros(n_nodes + 1, np.int64)
    for k in range(n_nodes):
        ptr[k + 1] = ptr[k] + deg[k]
    fill = ptr[:-1].copy(); inc = np.empty(2 * m, np.int64)
    for i in range(m):
        a = seg[i, 0]; b = seg[i, 1]
        inc[fill[a]] = i; fill[a] += 1
        inc[fill[b]] = i; fill[b] += 1
    used = np.zeros(m, np.bool_)
    out = np.empty(2 * m + 2, np.int64)
    starts = np.empty(m + 2, np.int64)
    nc = 0; w = 0
    for phase in range(2):
        for s0 in range(n_nodes if phase == 0 else m):
            while True:
                if phase == 0:
                    node = s0
                    if deg[node] == 2:
                        break
                    free = False
                    for q in range(ptr[node], ptr[node + 1]):
                        if not used[inc[q]]:
                            free = True; break
                    if not free:
                        break
                else:
                    if used[s0]:
                        break
                    node = seg[s0, 0]
                starts[nc] = w; out[w] = node; w += 1; cur = node
                while True:
                    nxt = -1
                    for q in range(ptr[cur], ptr[cur + 1]):
                        if not used[inc[q]]:
                            nxt = inc[q]; break
                    if nxt < 0:
                        break
                    used[nxt] = True
                    cur = seg[nxt, 1] if seg[nxt, 0] == cur else seg[nxt, 0]
                    out[w] = cur; w += 1
                    if cur == node:
                        break
                nc += 1
                if phase == 1:
                    break
    starts[nc] = w
    return out[:w], starts[:nc + 1]


def level_set(faces, values, n_vertices, face_mask=None):
    """Chains of the zero set of `values` (one per vertex).

    Returns (a, b, t, chains): crossing k lies on edge (a[k], b[k]) at
    p = V[a] + t*(V[b]-V[a]); chains is a list of index arrays into the
    crossings. Zero values count as positive, so each crossed face has
    exactly two crossed edges.
    """
    pos = values > 0
    F = faces if face_mask is None else faces[face_mask]
    fp = pos[F]; s = fp.sum(1)
    F = F[(s == 1) | (s == 2)]
    if len(F) == 0:
        return None
    a = F; b = np.roll(F, -1, axis=1)
    cross = pos[a] != pos[b]
    lo = np.minimum(a, b).astype(np.int64); hi = np.maximum(a, b).astype(np.int64)
    key = (lo * n_vertices + hi)[cross].reshape(-1, 2)
    uniq, inv = np.unique(key.ravel(), return_inverse=True)
    seg = inv.reshape(-1, 2).astype(np.int64)
    ea = uniq // n_vertices; eb = uniq % n_vertices
    va, vb = values[ea], values[eb]
    t = va / (va - vb)
    flat, starts = chain_walk(seg, len(uniq))
    chains = [flat[starts[i]:starts[i + 1]] for i in range(len(starts) - 1)]
    return ea, eb, t, chains


def resample(points, attrs, step):
    """Uniform arc-length resampling of a 3D polyline and its per-point attributes."""
    arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    good = np.r_[True, np.diff(arc) > 1e-10]
    points = points[good]; arc = arc[good]; attrs = [x[good] for x in attrs]
    if len(points) < 2:
        return None
    u = np.linspace(0, arc[-1], max(3, int(np.ceil(arc[-1] / step)) + 1))
    p = np.stack([np.interp(u, arc, points[:, k]) for k in range(3)], -1)
    out = []
    for x in attrs:
        if x.ndim == 1:
            out.append(np.interp(u, arc, x))
        else:
            out.append(np.stack([np.interp(u, arc, x[:, k]) for k in range(x.shape[1])], -1))
    return p, out
