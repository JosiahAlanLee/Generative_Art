"""Engraving an oak's foliage masses and limbs for one camera.

`oak.py` builds the tree; this module draws it, without knowing the camera.
The host renderer (a ray tracer, a z-buffer) supplies rasters over a screen
window: which foliage mass each pixel sees, or other geometry, or nothing; how
far away the visible point is; its world height; and its darkness. From those
`draw_masses` makes three kinds of mark:

- **rows**: cross-contours of world height over each mass, so the marks follow
  its form. Each row is one level, and a level is kept where the darkness
  exceeds its bit-reversed rank (as the crosshatch allocator keeps hatch
  lines), so a shaded mass keeps all its rows and a lit one a few. Rows are
  drawn as chains of small scallops, the engraver's sign for leaf clusters.
- **outlines**: each mass's silhouette as a scalloped line bulging outward,
  cut wherever something nearer passes in front, and opened in coherent gaps
  on the lit side, where an engraver lets the light eat the edge.
- **contact shadow**: a mass darkens where a nearer mass or limb overlaps it,
  so overlapping masses separate instead of merging.

Limbs and bark need the host's projection and ray test, so for them this
module gives world geometry: `limb_outline` (the two silhouette lines of a
tapered tube, analytically, so they are smooth whatever the mesh) and
`furrow_keep` (which points of a bark furrow to draw, from darkness and the
furrows' spacing on the page). The host projects and tests both.

Screen units are pixels; `px_per_mm` converts the pen and pitch settings,
which are in plate millimetres.
"""
from dataclasses import dataclass
import numpy as np

BITREV = np.array([int(f"{i:08b}"[::-1], 2) for i in range(256)]) / 256
SKY, OTHER = -2, -1


@dataclass
class CrownRaster:
    """Per-pixel samples of one tree's foliage masses over a screen window.

    owner: mass index >= 0, OTHER (-1) for any other geometry, SKY (-2) for none.
    depth: distance from the eye to the first hit (inf for SKY).
    height: world Z of the first hit (only read on mass pixels).
    tone: darkness 0-1 (only read on mass pixels).
    Raster pixel (row i, column j) is screen point (x0 + j * step, y0 + i * step).
    """
    owner: np.ndarray
    depth: np.ndarray
    height: np.ndarray
    tone: np.ndarray
    x0: float
    y0: float
    step: float
    px_per_mm: float

    def to_screen(self, xy):
        """Raster (column, row) coordinates to screen pixels."""
        xy = np.asarray(xy, float)
        return np.column_stack([self.x0 + xy[:, 0] * self.step, self.y0 + xy[:, 1] * self.step])


@dataclass
class Style:
    """Pen and pitch in plate millimetres; everything else is dimensionless."""
    row_pen: float = .08          # foliage weight
    outline_pen: float = .10      # branch weight
    row_pitch: float = .78        # scallop chord along rows
    row_bulge: float = .30        # scallop height, fraction of the chord
    outline_pitch: float = 1.10
    outline_bulge: float = .40
    pitch_spread: float = .50     # log-normal spread of each scallop's chord
    gamma: float = 1.25           # darkness is raised to this power for the rows: lights thin out
    floor: float = .08            # ...after this much is added, so a lit mass keeps a few rows
    coverage_cap: float = .26     # as the hatcher's c_cap: at most this much ink coverage
    min_run: float = 1.2          # shortest row piece kept, in mm
    row_open_below: float = .65   # rows break where darkness is under this...
    row_open_max: float = .55     # ...in up to this fraction of their length
    row_open_scale: float = 1.7   # mm: the length scale of those breaks
    open_below: float = .45       # outlines open where darkness is under this...
    open_max: float = .92         # ...in up to this fraction of their length
    open_scale: float = 2.6       # mm: the length scale of those openings
    contact_reach: float = 1.3    # mm: how far a contact shadow reaches
    contact_strength: float = .38
    depth_gap: float = .18        # metres: nearer by this much counts as in front
    smooth: float = 1.0           # raster px: smoothing of height before contouring
    min_pixels: int = 12          # masses smaller than this are drawn by their outline only


def _sample(arr, xy):
    """Nearest-pixel lookup at raster (column, row) coordinates, clamped."""
    j = np.clip(np.rint(xy[:, 0]).astype(int), 0, arr.shape[1] - 1)
    i = np.clip(np.rint(xy[:, 1]).astype(int), 0, arr.shape[0] - 1)
    return arr[i, j]


def _bilinear(arr, xy):
    x = np.clip(xy[:, 0], 0, arr.shape[1] - 1.001); y = np.clip(xy[:, 1], 0, arr.shape[0] - 1.001)
    j = np.floor(x).astype(int); i = np.floor(y).astype(int); fx = x - j; fy = y - i
    return (arr[i, j] * (1 - fx) * (1 - fy) + arr[i, j + 1] * fx * (1 - fy)
            + arr[i + 1, j] * (1 - fx) * fy + arr[i + 1, j + 1] * fx * fy)


def _resample(p, step):
    p = np.asarray(p, float)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    if s[-1] < 1e-9:
        return p[:1], np.zeros(1)
    q = np.linspace(0, s[-1], max(2, int(np.ceil(s[-1] / step)) + 1))
    return np.column_stack([np.interp(q, s, p[:, i]) for i in range(p.shape[1])]), q


def _runs(keep):
    ids = np.flatnonzero(keep)
    if not len(ids):
        return []
    return [g for g in np.split(ids, np.flatnonzero(np.diff(ids) != 1) + 1) if len(g) > 1]


def scallop(points, pitch, bulge, side, rng, spread=.3, samples=7):
    """A polyline redrawn as a chain of arcs about `pitch` long (log-normally
    spread), each bulging about `bulge` x its chord toward `side`.

    `side` is one 2-D direction, or one per input point (interpolated along
    the line); each arc bulges to whichever side of its chord that direction
    points. The chain starts and ends on the polyline's end points."""
    p = np.asarray(points, float)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    if s[-1] < 1e-9:
        return p[:1].copy()
    steps = [0.]
    while steps[-1] < s[-1]:
        steps.append(steps[-1] + pitch * float(np.clip(np.exp(rng.normal(0, spread)), .5, 2.2)))
    knots = np.array(steps[:-1] + [s[-1]]) if len(steps) > 2 else np.array([0., s[-1]])
    if len(knots) > 2 and knots[-1] - knots[-2] < .35 * pitch:
        knots = np.r_[knots[:-2], knots[-1]]
    K = np.column_stack([np.interp(knots, s, p[:, i]) for i in range(2)])
    side = np.asarray(side, float)
    if side.ndim == 1:
        side = np.tile(side, (len(p), 1))
    t = np.linspace(0, 1, samples)
    out = [K[:1]]
    for k, (a, b) in enumerate(zip(K[:-1], K[1:])):
        chord = b - a; L = np.linalg.norm(chord)
        if L < 1e-9:
            continue
        n = np.array([-chord[1], chord[0]]) / L
        mid = (knots[k] + knots[k + 1]) / 2
        want = np.array([np.interp(mid, s, side[:, 0]), np.interp(mid, s, side[:, 1])])
        if n @ want < 0:
            n = -n
        h = bulge * min(L, 1.3 * pitch) * rng.uniform(.55, 1.55)    # a long chord makes a flatter arc
        arc = a + t[1:, None] * chord + np.sin(np.pi * t[1:])[:, None] * h * n
        out.append(arc)
    return np.vstack(out)


def contact_tone(r, style):
    """Darkness raised where something nearer lies within reach of a mass pixel."""
    from scipy.ndimage import gaussian_filter, minimum_filter
    reach = max(1, int(round(style.contact_reach * r.px_per_mm / r.step)))
    d = np.where(np.isfinite(r.depth), r.depth, 1e9)
    near = minimum_filter(d, size=2 * reach + 1) < d - style.depth_gap
    shade = gaussian_filter(near.astype(float), reach / 2)
    return np.clip(np.nan_to_num(r.tone) + style.contact_strength * np.clip(2 * shade, 0, 1), 0, 1)


def _smooth_within(field, mask, sigma):
    from scipy.ndimage import gaussian_filter
    w = gaussian_filter(mask.astype(float), sigma)
    v = gaussian_filter(np.where(mask, field, 0.), sigma)
    out = np.full(field.shape, np.nan)
    out[mask] = v[mask] / np.maximum(w[mask], 1e-9)
    return out


def _gaps(s, tone, below, most, scale, rng):
    """Coherent openings along a line (arc length `s` in mm), more where it is lit:
    where darkness is under `below`, up to `most` of the line opens, in pieces
    on the order of `scale` mm."""
    want = np.clip((below - tone) / below, 0, 1) * most
    phase = rng.uniform(0, 2 * np.pi, 3); sc = scale * rng.uniform(.7, 1.4, 3)
    wave = sum(np.sin(2 * np.pi * s / a + ph) for a, ph in zip(sc, phase))
    # Ranked, the wave is uniform along the line, so `want` is the fraction opened.
    level = (np.argsort(np.argsort(wave)) + .5) / len(wave)
    return level >= want                   # True where the line is drawn


def _clear_of_nearer(arc, c, r, d_ref, gap):
    """Pieces of a drawn arc (raster coordinates) that do not cross anything
    nearer than its mass: a scallop's bulge may leave the mass for sky or for
    farther ground, never for a limb or a mass in front of it."""
    ok = (_sample(r.owner, arc) == c) | (_sample(r.depth, arc) >= d_ref - gap)
    return [arc[g] for g in _runs(ok)]


def draw_masses(r, rng, dz, style=None):
    """Rows and outlines for every mass in the raster.

    `dz` is the world height between neighbouring rows (the host sets it so
    that, at the tree, neighbouring rows land near the minimum gap). Returns
    dict(rows=[...], outlines=[...], stats=...), polylines in screen pixels.
    """
    import contourpy
    style = style or Style()
    mm = r.px_per_mm / r.step                 # raster pixels per plate millimetre
    tone = contact_tone(r, style)
    rows, outlines = [], []
    stats = dict(masses=0, rows=0, outlines=0, levels_kept=0, levels_seen=0)
    h, w = r.owner.shape
    for c in sorted(set(np.unique(r.owner)) - {SKY, OTHER}):
        mask = r.owner == c
        if mask.sum() < 3:
            continue
        stats["masses"] += 1
        # ---- outline: the mass's own silhouette, scalloped outward.
        from scipy.ndimage import gaussian_filter
        soft = gaussian_filter(mask.astype(float), .8)
        gy, gx = np.gradient(soft)
        for loop in contourpy.contour_generator(z=soft).lines(.5):
            if len(loop) < 4:
                continue
            pts, s = _resample(loop, .5)
            g = np.column_stack([_bilinear(gx, pts), _bilinear(gy, pts)])
            out = -g / np.maximum(np.linalg.norm(g, axis=1), 1e-9)[:, None]
            inside, outside = pts - 2 * out, pts + 2 * out
            d_in, d_out = _sample(r.depth, inside), _sample(r.depth, outside)
            o_out = _sample(r.owner, outside)
            occluded = (o_out != c) & (d_out < d_in - style.depth_gap)
            edge = (pts[:, 0] < 1.5) | (pts[:, 0] > w - 2.5) | (pts[:, 1] < 1.5) | (pts[:, 1] > h - 2.5)
            keep = ~occluded & ~edge & _gaps(s / mm, _sample(tone, inside), style.open_below, style.open_max,
                                             style.open_scale, rng)
            for run in _runs(keep):
                if s[run[-1]] - s[run[0]] < .6 * style.outline_pitch * mm:
                    continue
                arc = scallop(pts[run], style.outline_pitch * mm, style.outline_bulge, out[run], rng,
                              style.pitch_spread)
                for piece in _clear_of_nearer(arc, c, r, float(np.median(d_in[run])), style.depth_gap):
                    outlines.append(r.to_screen(piece)); stats["outlines"] += 1
        if mask.sum() < style.min_pixels:
            continue
        # ---- rows: contours of smoothed world height inside the mass.
        z = _smooth_within(r.height, mask, style.smooth)
        zy, zx = np.gradient(np.where(mask, z, np.nan))
        zx, zy = np.nan_to_num(zx), np.nan_to_num(zy)
        gen = contourpy.contour_generator(z=np.ma.masked_invalid(z))
        lo, hi = np.nanmin(z), np.nanmax(z)
        for k in range(int(np.floor(lo / dz)), int(np.ceil(hi / dz)) + 1):
            rank = BITREV[k % 256]
            for line in gen.lines(k * dz):
                if len(line) < 2:
                    continue
                stats["levels_seen"] += 1
                pts, s = _resample(line, .5)
                grad = np.column_stack([_bilinear(zx, pts), _bilinear(zy, pts)])
                gn = np.linalg.norm(grad, axis=1)
                spacing = dz / np.maximum(gn, 1e-9) / mm          # mm between neighbouring rows
                cap = np.minimum(1, style.coverage_cap * spacing / style.row_pen)
                dark = _sample(tone, pts)
                keep = rank < np.minimum(style.floor + (1 - style.floor) * dark ** style.gamma, cap)
                keep &= _sample(r.owner, pts) == c
                keep &= _gaps(s / mm, dark, style.row_open_below, style.row_open_max, style.row_open_scale, rng)
                up = grad / np.maximum(gn, 1e-9)[:, None]
                kept = False
                for run in _runs(keep):
                    if s[run[-1]] - s[run[0]] < style.min_run * mm:
                        continue
                    arc = scallop(pts[run], style.row_pitch * mm, style.row_bulge, up[run], rng,
                                  style.pitch_spread)
                    d_ref = float(np.median(_sample(r.depth, pts[run])))
                    for piece in _clear_of_nearer(arc, c, r, d_ref, style.depth_gap):
                        rows.append(r.to_screen(piece)); stats["rows"] += 1; kept = True
                stats["levels_kept"] += int(kept)
    return dict(rows=rows, outlines=outlines, stats=stats)


def limb_outline(points, radii, eye, step=.03):
    """The two silhouette lines of a tapered tube seen from `eye`.

    For a circular section of radius r centred at c with axis t, the
    silhouette points satisfy n . (c + r n - eye) = 0; with m the unit vector
    along t x (eye - c) and w the unit vector toward the eye across the axis,
    they are c + r (+-cos(a) m + sin(a) w), sin(a) = r / |eye - c across t|.
    Returns (left, right) as (N, 3) world polylines.
    """
    p = np.asarray(points, float); rad = np.asarray(radii, float)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    q = np.linspace(0, s[-1], max(2, int(np.ceil(s[-1] / step)) + 1))
    c = np.column_stack([np.interp(q, s, p[:, i]) for i in range(3)]); r = np.interp(q, s, rad)
    t = np.gradient(c, axis=0); t /= np.maximum(np.linalg.norm(t, axis=1), 1e-12)[:, None]
    v = np.asarray(eye, float) - c
    across = v - (v * t).sum(1)[:, None] * t
    dist = np.maximum(np.linalg.norm(across, axis=1), 1e-9)
    wv = across / dist[:, None]
    m = np.cross(t, wv)
    sin_a = np.clip(r / dist, 0, .999); cos_a = np.sqrt(1 - sin_a ** 2)
    left = c + r[:, None] * (cos_a[:, None] * m + sin_a[:, None] * wv)
    right = c + r[:, None] * (-cos_a[:, None] * m + sin_a[:, None] * wv)
    return left, right


def furrow_keep(k, count, tone, spacing_mm, pen_mm, coverage_cap=.32):
    """Which samples of furrow k (of `count` around its limb) to draw.

    `spacing_mm` is the page distance to the next furrow at each sample
    (arc between furrows x pixels per metre x |cos| of the view angle, in mm);
    a furrow is kept where the darkness exceeds its bit-reversed rank and the
    coverage stays under the cap, so furrows crowd on the shaded side and
    thin out toward the light and at the limb's edges."""
    rank = BITREV[int(k) % 256]           # even, odd, every fourth...: kept furrows stay evenly spaced
    cap = np.minimum(1, coverage_cap * np.asarray(spacing_mm, float) / pen_mm)
    return rank < np.minimum(np.asarray(tone, float), cap)
