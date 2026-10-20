"""Closed-form paper marbling applied to polylines, so a marbled sheet can be plotted.

After Lu, Jaffer, Jin, Zhao and Mao (2012), "Mathematical Marbling", IEEE
Computer Graphics and Applications 32(6), 26–35, doi:10.1109/MCG.2011.51, and
Aubrey Jaffer's notes at https://people.csail.mit.edu/jaffer/Marbling/.

The continuous tine map is a shear. The drop map sends the punctured plane
outside a new disc; it is singular at the drop centre, not a bijection of the
whole plane. Finite sampling, chords, simplification and rounding can introduce
crossings even when the continuous boundaries do not cross. ``print_paths``
repairs those drawing artefacts with small gaps and checks the rounded paths.
That print repair is distinct from the continuous fluid analogy.

    drop at C, radius r:      P' = C + (P - C) * sqrt(1 + r^2 / |P - C|^2)
    straight tine B, M, N:    P' = P + z * lam / (d + lam) * M,   d = |(P - B) . N|
    vortex at C:              rotate P about C through z * lam / (d + lam) / d,  d = |P - C|

The falloff ``lam / (d + lam)`` is the paper's; ``z`` is the displacement on
the tine's own line. A drop also adds its own outline as a new line.
"""
import numpy as np

__all__ = ["resample", "drop", "tine", "comb", "vortex", "stone_ground", "clip", "print_paths"]


def resample(lines, step):
    """Insert vertices so no segment is longer than ``step``; originals are kept."""
    if not np.isfinite(step) or step <= 0:
        raise ValueError("resampling step must be finite and positive")
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
    if not isinstance(count, (int, np.integer)) or count < 1:
        raise ValueError("count must be a positive integer")
    x0, y0, x1, y1 = box
    if x1 <= x0 or y1 <= y0:
        raise ValueError("box must have positive width and height")
    cols = int(np.ceil(np.sqrt(count * (x1 - x0) / (y1 - y0))))
    rows = int(np.ceil(count / cols))
    sites = [(x0 + (i + .5 + rng.uniform(-.35, .35)) * (x1 - x0) / cols,
              y0 + (j + .5 + rng.uniform(-.35, .35)) * (y1 - y0) / rows)
             for j in range(rows) for i in range(cols)]
    order = rng.permutation(len(sites))[:count]
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


def print_paths(lines, simplify=.03, clearance=.08):
    """Return ``(paths, owners, report)`` for a marbled print, in millimetres.

    Simplify and quantise to the SVG's 0.001 mm grid *before* detecting
    intersections. Earlier paths have priority; later paths receive small
    gaps where they intersect earlier candidates. Original candidates are
    used conservatively, so a gap may remain where an earlier path was also
    trimmed. Self-intersections are noded into simple pieces first. No later
    path simplification should be applied. The result is checked after its
    final rounding; an unresolved crossing raises rather than being exported.

    This is an explicit drawing repair, not recovery of exact fluid topology.
    ``owners`` retains the input index for ink assignment after splitting.
    """
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    from shapely.strtree import STRtree

    if not np.isfinite(clearance) or clearance < .004:
        raise ValueError("clearance must be at least 0.004 mm")
    if not np.isfinite(simplify) or simplify < 0:
        raise ValueError("simplification must be finite and nonnegative")
    candidates, owners = [], []
    for owner, points in enumerate(lines):
        if len(points) < 2:
            continue
        g = LineString(points).simplify(simplify)
        g = LineString(np.round(np.asarray(g.coords), 3))
        if g.length == 0:
            continue
        parts = unary_union(g) if not g.is_simple else g
        for part in (parts.geoms if hasattr(parts, "geoms") else [parts]):
            if part.geom_type == "LineString" and part.length > .12:
                candidates.append(part)
                owners.append(owner)
    if not candidates:
        return [], [], {"crossing_pairs_before": 0, "crossing_pairs_after": 0,
                        "clearance_mm": clearance, "removed_length_mm": 0.0}
    tree = STRtree(candidates)
    before = tree.query(candidates, predicate="crosses")
    raw_crossings = int(np.count_nonzero(before[0] < before[1]))
    out, source, repaired = [], [], 0
    for k, g in enumerate(candidates):
        hits = sorted(int(j) for j in tree.query(g, predicate="intersects") if j < k)
        if hits:
            # Buffer the intersected earlier paths, rather than only their
            # crossing points. At very shallow angles a point-sized gap can
            # cross again when the new endpoints round to the SVG grid.
            mask = unary_union([candidates[j].buffer(clearance, quad_segs=4) for j in hits])
            g = g.difference(mask)
            repaired += 1
        for part in (g.geoms if hasattr(g, "geoms") else [g]):
            if part.geom_type != "LineString" or part.length <= .12:
                continue
            p = np.round(np.asarray(part.coords), 3)
            if LineString(p).length > .12:
                out.append(p)
                source.append(owners[k])
    geometries = [LineString(p) for p in out]
    if geometries:
        pairs = STRtree(geometries).query(geometries, predicate="crosses")
        crossing_count = int(np.count_nonzero(pairs[0] < pairs[1]))
        if crossing_count or any(not g.is_simple for g in geometries):
            raise ValueError("rounded marbling paths still intersect; use a finer sampling step")
    return out, source, {
        "method": "priority gaps at intersections of simplified, rounded paths",
        "crossing_pairs_before": raw_crossings, "crossing_pairs_after": 0,
        "repaired_candidates": repaired, "clearance_mm": clearance,
        "simplification_mm": simplify, "coordinate_grid_mm": .001,
        "removed_length_mm": round(sum(g.length for g in candidates)
                                   - sum(g.length for g in geometries), 3),
    }
