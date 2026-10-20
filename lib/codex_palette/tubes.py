"""Flux-adapted tube networks after Tero, Kobayashi and Nakagaki.

Tero, A., Kobayashi, R. and Nakagaki, T. (2007), "A mathematical model for
adaptive transport network in path finding by true slime mold", Journal of
Theoretical Biology 244(4), 553–564, doi:10.1016/j.jtbi.2006.07.015; and
Tero, A. et al. (2010), "Rules for biologically inspired adaptive network
design", Science 327(5964), 439–442, doi:10.1126/science.1177894.

This is a different model from the book's Notoria fields, which follow Jones
(2010) with sensing agents and a diffusing trail. Here there are no agents.
A mesh of tubes joins the arena; each step one food source is chosen as the
source and another as the sink, Kirchhoff's law gives the pressures, and each
tube's conductivity relaxes toward a saturating function of the flux it
carried:

    sum_j (D_ij / L_ij) (p_i - p_j) = +I0 at the source, -I0 at the sink, 0 elsewhere
    Q_ij = D_ij (p_i - p_j) / L_ij
    D_ij <- (D_ij + dt * f(|Q_ij|)) / (1 + dt),   f(q) = q**gamma / (1 + q**gamma)

The update is the semi-implicit form of dD/dt = f(|Q|) - D. The 2010 paper's
sigmoidal f, random source/sink choice and fine random mesh are followed; its
illumination mask (sea and lakes) is replaced by the disc the arena is given.
Nothing here is calibrated to an organism or a city.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from scipy.spatial import Delaunay

__all__ = ["disc_mesh", "adapt", "tube_graph", "chains"]


def disc_mesh(nodes, centre, radius, spacing, rng, jitter=.32):
    """Jittered triangular lattice inside a disc, with the food nodes as vertices.

    Returns ``points`` (N×2), ``edges`` (E×2, i<j), ``lengths`` (E,) and the
    indices of the food nodes in ``points``.
    """
    cx, cy = centre
    rows = np.arange(-radius, radius + spacing, spacing * np.sqrt(3) / 2)
    pts = []
    for k, y in enumerate(rows):
        xs = np.arange(-radius, radius + spacing, spacing) + (spacing / 2 if k % 2 else 0)
        pts.extend((x, y) for x in xs)
    pts = np.asarray(pts) + rng.uniform(-jitter, jitter, (len(pts), 2)) * spacing
    pts = pts[np.hypot(*pts.T) < radius - spacing * .4] + [cx, cy]
    food = np.asarray(nodes, float)[:, :2]
    # Keep lattice points clear of the food nodes, then add the nodes themselves.
    clear = np.min(np.hypot(*(pts[:, None, :] - food[None]).transpose(2, 0, 1)), axis=1) > spacing * .55
    pts = np.vstack([pts[clear], food])
    food_index = np.arange(len(pts) - len(food), len(pts))
    tri = Delaunay(pts).simplices
    e = np.vstack([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [0, 2]]])
    e = np.unique(np.sort(e, axis=1), axis=0)
    lengths = np.hypot(*(pts[e[:, 0]] - pts[e[:, 1]]).T)
    keep = lengths < spacing * 2.2          # drop long hull edges across the rim
    return pts, e[keep], lengths[keep], food_index


def adapt(points, edges, lengths, food, rng, steps=2400, flux=2.0, gamma=1.8, dt=.05,
          record=(), d0=(.5, 1.0)):
    """Run the source/sink adaptation; return final D, snapshots and the last flux."""
    n = len(points)
    i, j = edges[:, 0], edges[:, 1]
    D = rng.uniform(*d0, len(edges))
    snapshots, Q = {}, np.zeros(len(edges))
    for step in range(1, steps + 1):
        s, t = rng.choice(food, 2, replace=False)
        g = D / lengths
        # Graph Laplacian; ground the sink by deleting its row and column.
        L = coo_matrix((np.concatenate([g, g, -g, -g]),
                        (np.concatenate([i, j, i, j]), np.concatenate([i, j, j, i]))),
                       shape=(n, n)).tocsr()
        keep = np.ones(n, bool)
        keep[t] = False
        b = np.zeros(n)
        b[s] = flux
        p = np.zeros(n)
        p[keep] = spsolve(L[keep][:, keep].tocsc(), b[keep])
        Q = g * (p[i] - p[j])
        q = np.abs(Q) ** gamma
        D = (D + dt * q / (1 + q)) / (1 + dt)
        if step in record:
            snapshots[step] = D.copy()
    return D, snapshots, Q


def tube_graph(edges, D, threshold):
    """Edges whose conductivity stays above ``threshold``."""
    return edges[D > threshold], D[D > threshold]


def chains(edges, weights):
    """Merge a graph's degree-2 runs into polylines of vertex indices.

    Returns [(vertex_list, mean_weight)]. Junctions and ends stay as chain ends,
    so each drawn stroke stops where the network branches.
    """
    from collections import defaultdict
    adj = defaultdict(list)
    for k, (a, b) in enumerate(edges):
        adj[a].append((b, k))
        adj[b].append((a, k))
    used = np.zeros(len(edges), bool)
    out = []
    def walk(start, nxt, k):
        path, ws = [start, nxt], [weights[k]]
        used[k] = True
        prev, cur = start, nxt
        while len(adj[cur]) == 2:
            step, kk = adj[cur][0] if adj[cur][0][1] != k else adj[cur][1]
            if used[kk]:
                break
            used[kk] = True
            path.append(step)
            ws.append(weights[kk])
            prev, cur, k = cur, step, kk
        return path, float(np.mean(ws))
    for v in list(adj):
        if len(adj[v]) != 2:
            for nxt, k in adj[v]:
                if not used[k]:
                    out.append(walk(v, nxt, k))
    for k, (a, b) in enumerate(edges):      # closed loops with no junction
        if not used[k]:
            out.append(walk(a, b, k))
    return out
