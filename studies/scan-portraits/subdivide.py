"""Loop subdivision that keeps a seam-split UV layout aligned with the mesh.

Positions are refined on the welded mesh with Loop's rules (Loop 1987):
edge points 3/8 + 3/8 + 1/8 + 1/8, vertices reweighted by valence, and the
cubic B-spline rules on any open boundary. The UV layout lives on the source's
seam-split records, so it is refined separately and linearly. Both refinements
emit a triangle's four children in the same order, so triangle i of one is
triangle i of the other at every level.
"""
import numpy as np


def _edges(F, n):
    """Unique edges, and for each triangle the edge id leaving each corner."""
    a = F.astype(np.int64); b = np.roll(a, -1, axis=1)
    key = np.minimum(a, b) * n + np.maximum(a, b)
    uniq, inv = np.unique(key.ravel(), return_inverse=True)
    return np.stack([uniq // n, uniq % n], 1), inv.reshape(-1, 3)


def _children(F, fe, n):
    a, b, c = F[:, 0], F[:, 1], F[:, 2]
    ab, bc, ca = n + fe[:, 0], n + fe[:, 1], n + fe[:, 2]
    return np.concatenate([np.stack(t, 1) for t in ((a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca))])


def _loop_positions(V, F):
    n = len(V)
    E, fe = _edges(F, n)
    ne = len(E)
    opposite = F[:, [2, 0, 1]]                      # corner opposite each corner's outgoing edge
    osum = np.zeros((ne, 3)); ocount = np.zeros(ne)
    np.add.at(osum, fe.ravel(), V[opposite.ravel()])
    np.add.at(ocount, fe.ravel(), 1)
    inner = ocount == 2
    mid = V[E[:, 0]] + V[E[:, 1]]
    edge_points = np.where(inner[:, None], .375 * mid + .125 * osum, .5 * mid)
    nsum = np.zeros_like(V); valence = np.zeros(n)
    np.add.at(nsum, E[:, 0], V[E[:, 1]]); np.add.at(nsum, E[:, 1], V[E[:, 0]])
    np.add.at(valence, E[:, 0], 1); np.add.at(valence, E[:, 1], 1)
    beta = (.625 - (.375 + .25 * np.cos(2 * np.pi / np.maximum(valence, 3))) ** 2) / np.maximum(valence, 1)
    moved = (1 - valence * beta)[:, None] * V + beta[:, None] * nsum
    bE = E[~inner]
    if len(bE):
        bsum = np.zeros_like(V); bcount = np.zeros(n)
        np.add.at(bsum, bE[:, 0], V[bE[:, 1]]); np.add.at(bsum, bE[:, 1], V[bE[:, 0]])
        np.add.at(bcount, bE[:, 0], 1); np.add.at(bcount, bE[:, 1], 1)
        on = bcount == 2
        moved[on] = .75 * V[on] + .125 * bsum[on]
    return np.concatenate([moved, edge_points]), _children(F, fe, n)


def _linear(UV, Fu):
    n = len(UV)
    E, fe = _edges(Fu, n)
    return np.concatenate([UV, .5 * (UV[E[:, 0]] + UV[E[:, 1]])]), _children(Fu, fe, n)


def loop(V, F, levels, Fu=None, UV=None):
    """`levels` rounds of Loop subdivision. Returns (V, F, Fu, UV)."""
    for _ in range(levels):
        V, F = _loop_positions(np.asarray(V, float), np.asarray(F))
        if Fu is not None:
            UV, Fu = _linear(np.asarray(UV, float), np.asarray(Fu))
    return V, F, Fu, UV
