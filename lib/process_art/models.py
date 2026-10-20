"""Small, dimensionless process models, independently implemented from papers.

These are art studies, not calibrated geological or biological predictors.
Model state and drawing are deliberately separate. Array coordinates are y,x.
"""
from heapq import heappop, heappush

import numpy as np
from scipy.ndimage import gaussian_filter, laplace
from scipy.spatial import cKDTree


def noise(shape, rng):
    """Multiscale smooth noise, with unit standard deviation."""
    z = np.zeros(shape, dtype=float)
    for sigma, amount in [(24, 1), (12, .5), (6, .25), (3, .125)]:
        a = gaussian_filter(rng.normal(size=shape), sigma, mode="reflect")
        z += amount * a / max(a.std(), 1e-12)
    return z / max(z.std(), 1e-12)


def flood(z):
    """Priority-flood depression fill with a tiny strictly descending outlet route.

    All four edges are open outlets. The epsilon is a routing device, not sediment.
    """
    h = np.array(z, dtype=float, copy=True)
    ny, nx = h.shape
    seen = np.zeros(h.shape, bool)
    q = []
    for y, x in [(y, x) for y in range(ny) for x in (0, nx-1)] + [
            (y, x) for x in range(nx) for y in (0, ny-1)]:
        if not seen[y, x]:
            seen[y, x] = True
            heappush(q, (h[y, x], y, x))
    while q:
        level, y, x = heappop(q)
        for dy, dx in NEIGHBORS:
            yy, xx = y+dy, x+dx
            if 0 <= yy < ny and 0 <= xx < nx and not seen[yy, xx]:
                seen[yy, xx] = True
                h[yy, xx] = max(h[yy, xx], level + 1e-7)
                heappush(q, (h[yy, xx], yy, xx))
    return h


NEIGHBORS = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]


def drainage(z):
    """D8 steepest descent and exact contributing-cell accumulation.

    A receiver of -1 is an outlet or a local minimum. Every cell supplies one unit
    of runoff; accumulation is routed in descending elevation order.
    """
    h = np.asarray(z, dtype=float)
    ny, nx = h.shape
    rec = np.full(h.shape, -1, dtype=np.int64)
    slope = np.zeros(h.shape)
    for dy, dx in NEIGHBORS:
        yy, xx = np.mgrid[1:ny-1, 1:nx-1]
        s = (h[1:-1, 1:-1] - h[yy+dy, xx+dx]) / np.hypot(dy, dx)
        take = s > slope[1:-1, 1:-1]
        slope[1:-1, 1:-1][take] = s[take]
        rec[1:-1, 1:-1][take] = ((yy+dy)*nx + xx+dx)[take]
    area = np.ones(h.size, dtype=float)
    receivers = rec.ravel()
    for i in np.argsort(-h.ravel(), kind="stable"):
        if receivers[i] >= 0:
            area[receivers[i]] += area[i]
    return rec, area.reshape(h.shape), slope


def catchment(seed=11, n=176, steps=36, incision=.014):
    """Stream-power-inspired incision plus linear hillslope diffusion.

    Normalized area replaces dimensional catchment area. No sediment transport
    or deposition is modeled. Edge elevations are fixed to zero (open sea).
    """
    if n < 24 or not 0 <= steps <= 300 or not 0 <= incision <= .15:
        raise ValueError("n >= 24, steps 0..300, incision 0..0.15 required")
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[-1:1:complex(n), -1:1:complex(n)]
    envelope = np.maximum(0, (1-x*x)*(1-y*y))
    h = envelope * (1.2 + .38*noise((n, n), rng) + .22*np.sin(3*x+2*y))
    h = np.maximum(h, 0)
    initial = h.copy()
    history = []
    for _ in range(steps):
        routed = flood(h)
        rec, area, slope = drainage(routed)
        erosion = incision * np.sqrt(area) * slope
        # Limit each step to 30% of the elevation drop to its receiver.
        drop = np.zeros(h.size)
        valid = rec.ravel() >= 0
        drop[valid] = routed.ravel()[valid] - routed.ravel()[rec.ravel()[valid]]
        erosion = np.minimum(erosion, .3*drop.reshape(h.shape))
        h = np.maximum(0, h - erosion + .07*laplace(h, mode="nearest"))
        h[[0, -1], :] = 0
        h[:, [0, -1]] = 0
        history.append(float(np.sum(erosion)))
    h = flood(h)
    rec, area, slope = drainage(h)
    return {"height": h, "initial": initial, "receiver": rec, "area": area,
            "slope": slope, "incision_history": np.array(history)}


def stratigraphy(seed=11, n=320, throw=.24, fold=.24):
    """An implicit stratigraphic-age field, folded and offset across two faults.

    A kinematic deformation drawing, not a rock-mechanics solver. Blank seams
    prevent a contourer from inventing bridges across discontinuities.
    """
    if n < 24 or not np.isfinite([throw, fold]).all():
        raise ValueError("finite deformation parameters and n >= 24 required")
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[-1:1:complex(n), -1:1:complex(n)]
    phase = rng.uniform(-.4, .4)
    seam = .15 + .15*np.sin(2.4*y + phase)
    seam2 = -.53 + .10*np.sin(3.7*y)
    age = y + fold*np.sin(3.8*x + 1.4*y + phase) + .105*np.sin(8*x-2*y)
    age += .04*noise((n, n), rng)
    age += throw*(x > seam) - .48*throw*(x < seam2)
    # Weathered specimen edge and an erosional unconformity at its top.
    body = (x/.87)**2 + (y/.95)**2 < 1 + .05*np.sin(11*np.arctan2(y, x))
    roof = -.78 + .045*np.sin(5*x)
    body &= y > roof
    mask = body & (np.abs(x-seam) > .012) & (np.abs(x-seam2) > .009)
    return {"age": age, "mask": mask, "body": body, "fault1": seam,
            "fault2": seam2, "x": x, "y": y}


def gray_scott(seed=11, n=192, steps=1600, feed=.036, kill=.061):
    """Forward Euler Gray–Scott, dt=1, Du=.16, Dv=.08, reflecting edges.

    The five-point Laplacian assumes grid spacing 1. No spatial warping of the
    resulting chemistry is done here. Telemetry is actual simulated mean V.
    """
    if n < 24 or not 0 <= steps <= 10000 or not 0 < feed < .1 or not 0 < kill < .1:
        raise ValueError("n >= 24, steps 0..10000, feed/kill in (0,.1) required")
    rng = np.random.default_rng(seed)
    u = np.ones((n, n))
    v = np.zeros((n, n))
    y, x = np.mgrid[:n, :n]
    # Distributed finite-amplitude perturbations; no full-field random texture.
    for _ in range(38):
        cx, cy = rng.uniform(.14*n, .86*n, 2)
        r = rng.uniform(2.5, 5.5)
        m = (x-cx)**2 + (y-cy)**2 < r*r
        u[m] = .5 + rng.uniform(-.02, .02, m.sum())
        v[m] = .25 + rng.uniform(-.02, .02, m.sum())
    telemetry = []
    for t in range(steps):
        uvv = u*v*v
        u += .16*laplace(u, mode="reflect") - uvv + feed*(1-u)
        v += .08*laplace(v, mode="reflect") + uvv - (feed+kill)*v
        if t % 8 == 0:
            telemetry.append((t+1, float(v.mean())))
    if not np.isfinite(u).all() or not np.isfinite(v).all():
        raise FloatingPointError("unstable reaction–diffusion state")
    return {"u": u, "v": v, "telemetry": np.asarray(telemetry)}


def space_colonize(attractors, roots, step=.012, influence=.20, kill=.025, iterations=240):
    """2D nearest-node space colonization; each node has at most one parent.

    The embedding is geometric. This does not model blood flow or fungal
    resource exchange. Disconnected roots remain separate trees, never loops.
    """
    a = np.array(attractors, dtype=float, copy=True).reshape(-1, 2)
    nodes = np.asarray(roots, dtype=float).reshape(-1, 2).tolist()
    if not nodes or not np.isfinite(a).all() or not np.isfinite(nodes).all():
        raise ValueError("finite attractors and at least one finite root required")
    if not 0 < step < kill < influence or iterations < 0:
        raise ValueError("0 < step < kill < influence and iterations >= 0 required")
    parents = [-1]*len(nodes)
    for _ in range(iterations):
        if len(a) == 0:
            break
        tree = cKDTree(nodes)
        distance, nearest = tree.query(a)
        # Remove reached attractors before averaging growth directions.
        keep = distance > kill
        a, distance, nearest = a[keep], distance[keep], nearest[keep]
        active = distance < influence
        if not np.any(active):
            break
        d = a[active] - np.asarray(nodes)[nearest[active]]
        d /= np.linalg.norm(d, axis=1)[:, None]
        vectors = np.zeros((len(nodes), 2))
        np.add.at(vectors, nearest[active], d)
        ids = np.flatnonzero(np.linalg.norm(vectors, axis=1) > 1e-9)
        added = 0
        for i in ids:
            vec = vectors[i]/np.linalg.norm(vectors[i])
            p = np.asarray(nodes[i]) + step*vec
            if tree.query(p)[0] < .48*step:
                continue
            nodes.append(p.tolist())
            parents.append(int(i))
            added += 1
        if not added:
            break
    # Downstream subtree mass is used only to choose a drawing pen width.
    mass = np.ones(len(nodes))
    for i in range(len(nodes)-1, -1, -1):
        if parents[i] >= 0:
            mass[parents[i]] += mass[i]
    return {"nodes": np.asarray(nodes), "parents": np.asarray(parents), "mass": mass,
            "unreached": a}


def recurrence(values, dimension=3, delay=2, epsilon=.48, theiler=5):
    """Delay embedding, population z-score and Euclidean recurrence threshold.

    Windows containing missing values are excluded, with original row indices
    retained. Nearby times (|i-j| <= theiler) are excluded. Constant series have
    zero standardized coordinates. No claim of chaos follows from the image.
    """
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or dimension < 1 or delay < 1 or theiler < 0 or epsilon <= 0:
        raise ValueError("1D series, positive dimension/delay/epsilon, theiler >= 0 required")
    count = len(values) - (dimension-1)*delay
    if count < 2:
        raise ValueError("series too short for delay embedding")
    windows = np.column_stack([values[i*delay:i*delay+count] for i in range(dimension)])
    indices = np.flatnonzero(np.isfinite(windows).all(axis=1))
    windows = windows[indices]
    if len(windows) < 2:
        raise ValueError("not enough finite embedding windows")
    scale = windows.std(axis=0)
    scale[scale < 1e-12] = 1
    features = (windows-windows.mean(axis=0))/scale
    distances = np.linalg.norm(features[:, None] - features[None, :], axis=2)
    eligible = np.abs(indices[:, None]-indices[None, :]) > theiler
    matrix = (distances <= epsilon) & eligible
    return {"matrix": matrix, "indices": indices, "distance": distances,
            "features": features, "eligible_pairs": int(np.triu(eligible, 1).sum()),
            "pair_count": int(np.triu(matrix, 1).sum())}
