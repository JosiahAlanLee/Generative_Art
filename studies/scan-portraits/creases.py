"""Ridge and valley lines (Ohtake, Belyaev & Seidel 2004), for the features a
contour or a fold misses on a face seen nearly head-on: eyelid margins, the
line between the lips, the wings of the nose, the hollows between curls.

A valley is where the more concave principal curvature k2 is at a minimum
along its own direction t2: e2 = grad(k2) . t2 crosses zero, k2 is strongly
negative and dominates k1. A ridge is the same for k1 at a maximum. Both are
view-independent; the drawing keeps only their visible stretches.

Curvature comes from the per-face shape operators of suggestive.py (Rusinkiewicz
2004) on smoothed normals, averaged to vertices. Principal directions carry no
sign, so each mesh edge orients its far end's direction to its near end's
before testing for a crossing; both triangles on an edge therefore agree.
"""
import sys
from pathlib import Path

import numpy as np

STATUE = Path(__file__).resolve().parents[1] / 'scanned-statue-v2'
if str(STATUE) not in sys.path:
    sys.path.append(str(STATUE))
import meshlines   # noqa: E402  Scanned Statue v2, unchanged
import suggestive  # noqa: E402  Scanned Statue v2, unchanged


def _ring_average(F, n):
    import scipy.sparse as sp
    ed = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    A = sp.coo_matrix((np.ones(len(ed)), (ed[:, 0], ed[:, 1])), shape=(n, n)).tocsr()
    A = (((A + A.T) > 0).astype(float) + sp.eye(n)).tocsr()
    return sp.diags(1 / np.asarray(A.sum(1)).ravel()) @ A


def vertex_curvature(V, F, vn, smooth=0):
    """Principal curvatures k1 >= k2 and unit directions t1, t2 at every vertex.
    `smooth` averages the curvature tensor over 1-rings that many times; the
    lines are third-order quantities, so scan noise breaks them up without it."""
    abc, e1, e2, fn, area = suggestive.face_shape_operators(V, F, vn)
    a, b, c = abc[:, 0], abc[:, 1], abc[:, 2]
    S = (a[:, None, None] * e1[:, :, None] * e1[:, None, :]
         + b[:, None, None] * (e1[:, :, None] * e2[:, None, :] + e2[:, :, None] * e1[:, None, :])
         + c[:, None, None] * e2[:, :, None] * e2[:, None, :])
    nv = len(V)
    Sv = np.zeros((nv, 3, 3)); w = np.zeros(nv)
    for k in range(3):
        np.add.at(Sv, F[:, k], S * area[:, None, None]); np.add.at(w, F[:, k], area)
    Sv /= np.maximum(w, 1e-15)[:, None, None]
    if smooth:
        R = _ring_average(F, nv); flat = Sv.reshape(nv, 9)
        for _ in range(smooth):
            flat = R @ flat
        Sv = flat.reshape(nv, 3, 3)
    ref = np.where(np.abs(vn[:, 2:3]) < .9, [[0., 0., 1.]], [[1., 0., 0.]])
    t = np.cross(ref, vn); t /= np.linalg.norm(t, axis=1)[:, None]; s = np.cross(vn, t)
    m00 = np.einsum('ni,nij,nj->n', t, Sv, t); m01 = np.einsum('ni,nij,nj->n', t, Sv, s)
    m11 = np.einsum('ni,nij,nj->n', s, Sv, s)
    half = .5 * (m00 + m11); r = np.sqrt(.25 * (m00 - m11) ** 2 + m01 ** 2)
    k1 = half + r; k2 = half - r
    ang = .5 * np.arctan2(2 * m01, m00 - m11)          # direction of k1 in (t, s)
    t1 = np.cos(ang)[:, None] * t + np.sin(ang)[:, None] * s
    t2 = np.cross(vn, t1)
    return k1, k2, t1, t2, fn, area


def _vertex_gradient(V, F, f, fn, area):
    """Gradient of a piecewise-linear vertex field, per face, area-averaged to vertices."""
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    g = (f[F[:, 0]][:, None] * np.cross(fn, p2 - p1) + f[F[:, 1]][:, None] * np.cross(fn, p0 - p2)
         + f[F[:, 2]][:, None] * np.cross(fn, p1 - p0)) / np.maximum(2 * area[:, None], 1e-15)
    gv = np.zeros_like(V); w = np.zeros(len(V))
    for k in range(3):
        np.add.at(gv, F[:, k], g * area[:, None]); np.add.at(w, F[:, k], area)
    return gv / np.maximum(w, 1e-15)[:, None]


def crease_lines(V, F, vn, kind, threshold, scale, smooth=0, field=None):
    """Chains of ridge ('ridge') or valley ('valley') points.

    threshold: minimum |k| times `scale` (a length, the head's height) at a
    crossing; the curvature must also dominate the other principal curvature.
    Returns a list of (points, normals, |k| * scale, field) arrays and a summary; `field` is an
    optional per-vertex value (the light, say) interpolated to each point.
    """
    k1, k2, t1, t2, fn, area = vertex_curvature(V, F, vn, smooth)
    if kind == 'ridge':
        k, other, td, sign = k1, k2, t1, 1.
    else:
        k, other, td, sign = k2, k1, t2, -1.
    g = _vertex_gradient(V, F, k, fn, area)
    e = (g * td).sum(1)
    strong = (sign * k * scale > threshold) & (sign * k > np.abs(other))
    n = len(V)
    a = F.astype(np.int64); b = np.roll(a, -1, axis=1)
    key = (np.minimum(a, b) * n + np.maximum(a, b)).ravel()
    uniq, inv = np.unique(key, return_inverse=True)
    ea = uniq // n; eb = uniq % n
    flip = np.sign((td[ea] * td[eb]).sum(1)); flip[flip == 0] = 1
    ga, gb = e[ea], (g[eb] * td[eb]).sum(1) * flip
    along = ((V[eb] - V[ea]) * td[ea]).sum(1)
    if kind == 'ridge':          # a maximum: e runs + to - along +t
        extremum = (ga - gb) * along > 0
    else:                        # a minimum: e runs - to + along +t
        extremum = (gb - ga) * along > 0
    cross = (np.sign(ga) != np.sign(gb)) & (strong[ea] | strong[eb]) & extremum
    tt = np.where(cross, ga / np.where(cross, ga - gb, 1.), 0.)
    fe = inv.reshape(-1, 3)
    hits = cross[fe]
    two = hits.sum(1) == 2
    pairs = fe[two][hits[two]].reshape(-1, 2)
    used = np.unique(pairs)
    node = np.full(len(uniq), -1, np.int64); node[used] = np.arange(len(used))
    seg = node[pairs]
    if len(seg) == 0:
        return [], dict(kind=kind, chains=0)
    flat, starts = meshlines.chain_walk(seg, len(used))
    ue, ut = used, tt[used]
    P = V[ea[ue]] + ut[:, None] * (V[eb[ue]] - V[ea[ue]])
    N = vn[ea[ue]] + ut[:, None] * (vn[eb[ue]] - vn[ea[ue]]); N /= np.linalg.norm(N, axis=1)[:, None]
    K = np.abs(k[ea[ue]] + ut * (k[eb[ue]] - k[ea[ue]])) * scale
    G = np.zeros(len(ue)) if field is None else field[ea[ue]] + ut * (field[eb[ue]] - field[ea[ue]])
    out = []
    for i in range(len(starts) - 1):
        c = flat[starts[i]:starts[i + 1]]
        if len(c) >= 2:
            out.append((P[c], N[c], K[c], G[c]))
    return out, dict(kind=kind, chains=len(out), crossings=int(len(used)),
                     k_scaled_pct=[float(np.percentile(np.abs(k) * scale, q)) for q in (50, 90, 99)])
