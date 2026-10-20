"""Closed-form paper marbling applied to polylines, so a marbled sheet can be plotted.

After Lu, Jaffer, Jin, Zhao and Mao (2012), "Mathematical Marbling", IEEE
Computer Graphics and Applications 32(6), 26–35, doi:10.1109/MCG.2011.51, and
Aubrey Jaffer's notes at https://people.csail.mit.edu/jaffer/Marbling/.

Every operation is a bijection of the plane applied to every vertex of every
line, so boundaries that never crossed before an operation never cross after
it. Long segments are resampled before each operation; that is the only
approximation, and its step is a parameter.

    drop at C, radius r:      P' = C + (P - C) * sqrt(1 + r^2 / |P - C|^2)
    straight tine B, M, N:    P' = P + z * lam / (d + lam) * M,   d = |(P - B) . N|
    vortex at C:              rotate P about C through z * lam / (d + lam) / d,  d = |P - C|

The falloff ``lam / (d + lam)`` is the paper's; ``z`` is the displacement on
the tine's own line. A drop also adds its own outline as a new line.
"""
import numpy as np

__all__ = ["resample", "drop", "tine", "comb", "vortex", "stone_ground", "clip"]


def resample(lines, step):
    """Insert vertices so no segment is longer than ``step``; originals are kept."""
    out = []
    for p in lines:
        p = np.asarray(p, float)
        if len(p) < 2:
            out.append(p)
            continue
        seg = p[1:] - p[:-1]
        k = np.maximum(1, np.ceil(np.hypot(*seg.T) / step).astype(int))
        idx = np.repeat(np.arange(len(seg)), k)
        within = np.arange(k.sum()) - np.repeat(np.cumsum(k) - k, k)
        t = (within + 1) / np.repeat(k, k)
        out.append(np.vstack([p[:1], p[idx] + t[:, None] * seg[idx]]))
    return out


def _circle(c, r, step):
    n = max(24, int(np.ceil(2 * np.pi * r / step)))
    t = np.linspace(0, 2 * np.pi, n + 1)
    return np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)])


def drop(lines, c, r, step=.5):
    c = np.asarray(c, float)
    out = []
    for p in resample(lines, step):
        v = p - c
        d2 = np.maximum((v * v).sum(1, keepdims=True), 1e-12)
        out.append(c + v * np.sqrt(1 + r * r / d2))
    out.append(_circle(c, r, step))
    return out


def tine(lines, origin, direction, z, lam, step=.5):
    m = np.asarray(direction, float)
    m /= np.linalg.norm(m)
    n = np.array([-m[1], m[0]])
    b = np.asarray(origin, float)
    out = []
    for p in resample(lines, step):
        d = np.abs((p - b) @ n)[:, None]
        out.append(p + z * lam / (d + lam) * m)
    return out


def comb(lines, start, direction, across, spacing, count, z, lam, alternate=False, step=.5):
    """``count`` parallel tines drawn one after another, ``spacing`` apart along ``across``.

    Each tine moves along ``direction``; ``alternate`` reverses every other one
    (the back-and-forth gel-git stroke).
    """
    m = np.asarray(direction, float)
    m /= np.linalg.norm(m)
    a = np.asarray(across, float)
    a /= np.linalg.norm(a)
    for k in range(count):
        sign = -1 if alternate and k % 2 else 1
        lines = tine(lines, np.asarray(start, float) + k * spacing * a, sign * m, z, lam, step)
    return lines


def vortex(lines, c, z, lam, step=.5):
    c = np.asarray(c, float)
    out = []
    for p in resample(lines, step):
        v = p - c
        d = np.maximum(np.hypot(*v.T), 1e-9)
        a = z * lam / (d + lam) / d
        cos, sin = np.cos(a), np.sin(a)
        out.append(c + np.column_stack([v[:, 0] * cos - v[:, 1] * sin, v[:, 0] * sin + v[:, 1] * cos]))
    return out


def stone_ground(rng, box, count, radius, rings=2, step=.5):
    """Drops on a jittered grid; each site receives ``rings`` concentric drops.

    Returns the lines and, for each line, the index of the drop that made it
    (so a caller can alternate inks by drop or by ring).
    """
    x0, y0, x1, y1 = box
    cols = int(np.ceil(np.sqrt(count * (x1 - x0) / (y1 - y0))))
    rows = int(np.ceil(count / cols))
    sites = [(x0 + (i + .5 + rng.uniform(-.35, .35)) * (x1 - x0) / cols,
              y0 + (j + .5 + rng.uniform(-.35, .35)) * (y1 - y0) / rows)
             for j in range(rows) for i in range(cols)]
    order = rng.permutation(len(sites))
    lines, tags = [], []
    for k in order:
        r0 = radius * rng.uniform(.75, 1.25)
        for ring in range(rings):
            lines = drop(lines, sites[k], r0 * (1 - ring / (rings + .5)), step)
            tags.append(ring)
    return lines, tags


def clip(lines, box):
    """Clip lines to an axis-aligned box; returns a list of arrays."""
    from shapely.geometry import LineString, box as rect
    r = rect(*box)
    out = []
    for p in lines:
        if len(p) < 2:
            continue
        g = LineString(p).intersection(r)
        if g.is_empty:
            continue
        for part in (g.geoms if hasattr(g, "geoms") else [g]):
            if part.geom_type == "LineString" and len(part.coords) > 1:
                out.append(np.asarray(part.coords))
    return out
