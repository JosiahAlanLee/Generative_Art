"""Open-grown bur oak (Quercus macrocarpa) for landscape plates.

`species.bur_oak` draws a young oak whole, leaf by leaf, as a specimen a few
centimetres tall on the page. A savanna oak seen across a field is drawn
another way: its foliage reads as masses, its limbs as tapered, crooked tubes,
and its bark as furrows whose number depends on how near the tree stands. This
module builds that geometry and nothing else; `crown.py` draws it for a camera.

The grammar follows the open-grown habit, illustratively rather than as a
growth model: a short, stout trunk forking low into a few heavy, wide-spreading
scaffold limbs, some nearly level and dipping before they rise, and a short
leader; branches and twigs run out to a broad, rounded crown of separate
foliage masses with sky between them. Metres, Z up, the trunk's base at the
origin. Everything is a pure function of the seed.
"""
from dataclasses import dataclass, field
from copy import deepcopy
import numpy as np

from .model import unit

STAGES = ("leafy", "bare")
# Tube sides and clump subdivision per detail level (1 far, 2 middle, 3 near).
TUBE_SIDES = {1: (10, 8, 6, 5), 2: (14, 10, 8, 6), 3: (18, 12, 8, 6)}
CLUMP_LEVEL = {1: 1, 2: 2, 3: 3}
BARK_SPACING = .045          # furrow candidates around a limb, metres apart
BARK_LIFT = .004             # furrows ride 4 mm off the bark
BARK_STEP = .04              # sample spacing along a furrow


@dataclass
class Limb:
    """One axis: a centreline (base first) and its radius at each point."""
    points: np.ndarray
    radii: np.ndarray
    order: int                # 0 trunk, 1 scaffold limb or leader, 2 branch, 3 twig
    parent: int = -1

    def length(self):
        return float(np.linalg.norm(np.diff(self.points, axis=0), axis=1).sum())


@dataclass
class Clump:
    """A foliage mass: a lumpy ellipsoid, semi-axes before its yaw."""
    centre: np.ndarray
    radii: np.ndarray
    yaw: float
    seed: int


@dataclass
class Furrow:
    """A bark furrow candidate on one limb: points just off the bark, the
    bark's outward normal at each, the distance to the neighbouring furrow at
    each (metres, around the limb), and its index k of `count` around the
    limb; a camera draws furrows by a bit-reversed rank of k, as the hatcher
    keeps hatch lines."""
    points: np.ndarray
    normals: np.ndarray
    spacing: np.ndarray
    limb: int
    k: int
    count: int


@dataclass
class Oak:
    limbs: list = field(default_factory=list)
    clumps: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def transform(self, fn, yaw=0.):
        out = deepcopy(self)
        for limb in out.limbs:
            limb.points = fn(limb.points)
        for c in out.clumps:
            c.centre = fn(c.centre[None])[0]; c.yaw = float(c.yaw + yaw)
        return out

    def placed(self, root=(0, 0, 0), yaw=0.):
        """A copy turned by `yaw` radians about its trunk and moved to `root`."""
        c, s = np.cos(yaw), np.sin(yaw)
        R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        out = self.transform(lambda p: np.asarray(p, float) @ R.T + np.asarray(root, float), yaw)
        out.metadata = dict(self.metadata, placement=dict(root=[float(v) for v in root], yaw=float(yaw)))
        return out

    def furrows(self, min_radius=.035):
        """Bark furrow candidates on every limb at least `min_radius` thick."""
        rng = np.random.default_rng([int(self.metadata.get("seed", 0)), 77])
        out = []
        for i, limb in enumerate(self.limbs):
            if limb.radii.max() >= min_radius:
                out.extend(_furrows(limb, i, rng))
        return out

    def meshes(self, detail=None):
        """Closed, outward-wound meshes: ('limbs' | 'branches' | 'crown', verts, faces).

        Trunk, scaffold limbs and leader are 'limbs'; branches and twigs are
        'branches'; each foliage mass is its own 'crown' mesh, so a renderer
        can tell the masses apart."""
        detail = int(detail or self.metadata.get("detail", 2))
        sides = TUBE_SIDES[detail]
        out = []
        for limb in self.limbs:
            v, f = tube(limb.points, limb.radii, sides[min(limb.order, 3)])
            out.append(("limbs" if limb.order <= 1 else "branches", v, f))
        for c in self.clumps:
            out.append(("crown",) + clump_mesh(c, CLUMP_LEVEL[detail]))
        return out

    def summary(self):
        return dict(limbs=len(self.limbs), clumps=len(self.clumps),
                    orders={o: sum(l.order == o for l in self.limbs) for o in range(4)},
                    trunk_radius=round(float(self.limbs[0].radii[len(self.limbs[0].radii) // 3]), 3)
                    if self.limbs else None)


# ---- geometry helpers ------------------------------------------------------------

def _perp(d):
    d = unit(d)
    u = np.cross(d, [0, 0, 1]) if abs(d[2]) < .95 else np.cross(d, [0, 1, 0])
    u = unit(u)
    return u, np.cross(d, u)


def chaikin(p, passes=1):
    """Corner cutting that keeps both end points."""
    p = np.asarray(p, float)
    for _ in range(passes):
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]):
            q += [.75 * a + .25 * b, .25 * a + .75 * b]
        q.append(p[-1])
        p = np.asarray(q)
    return p


def crooked(a, b, rng, segments=4, wiggle=.08, sag=0., smooth=2):
    """A crooked axis from a to b: a pinned random walk across the chord
    (a Brownian bridge, so it bends at elbows rather than wobbling) and an
    optional dip of `sag` x length between its ends."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a; L = float(np.linalg.norm(d))
    if L < 1e-9:
        return np.vstack([a, b])
    u, v = _perp(d)
    t = np.linspace(0, 1, segments + 1)
    walk = np.cumsum(rng.normal(0, 1, (segments + 1, 2)), axis=0); walk[0] = 0
    bridge = walk - t[:, None] * walk[-1]
    bridge *= wiggle * L / max(np.abs(bridge).max(), 1e-9)
    p = a + t[:, None] * d + bridge[:, :1] * u + bridge[:, 1:] * v
    p[:, 2] -= sag * L * np.sin(np.pi * t)
    return chaikin(p, smooth)


def frames(points):
    """Rotation-minimising frames along a polyline: tangents and (u, v), with
    v = t x u, as `geometry.beam_geometry` builds its rings (so tubes wind
    outward the same way)."""
    p = np.asarray(points, float)
    t = np.gradient(p, axis=0)
    t /= np.maximum(np.linalg.norm(t, axis=1), 1e-12)[:, None]
    u = np.empty_like(p); u[0] = _perp(t[0])[0]
    for i in range(1, len(p)):
        # Double reflection (Wang et al. 2008) carries u from point to point.
        v1 = p[i] - p[i - 1]; c1 = v1 @ v1
        if c1 < 1e-18:
            u[i] = u[i - 1]; continue
        rL = u[i - 1] - (2 / c1) * (v1 @ u[i - 1]) * v1
        tL = t[i - 1] - (2 / c1) * (v1 @ t[i - 1]) * v1
        v2 = t[i] - tL; c2 = v2 @ v2
        u[i] = rL - (2 / c2) * (v2 @ rL) * v2 if c2 > 1e-18 else rL
        u[i] = unit(u[i] - (u[i] @ t[i]) * t[i])
    v = np.cross(t, u)
    return t, u, v


def tube(points, radii, sides):
    """A closed tube along a centreline: rings, quads and two end caps."""
    p = np.asarray(points, float); r = np.asarray(radii, float)
    _, u, v = frames(p)
    a = np.arange(sides) * 2 * np.pi / sides
    rings = p[:, None] + r[:, None, None] * (np.cos(a)[None, :, None] * u[:, None] + np.sin(a)[None, :, None] * v[:, None])
    verts = rings.reshape(-1, 3)
    faces = [tuple(range(sides - 1, -1, -1)), tuple(range((len(p) - 1) * sides, len(p) * sides))]
    for i in range(len(p) - 1):
        o = i * sides
        faces += [(o + j, o + (j + 1) % sides, o + sides + (j + 1) % sides, o + sides + j) for j in range(sides)]
    return verts, faces


_ICO_V = np.array([(-1, 1.618033988749895, 0), (1, 1.618033988749895, 0), (-1, -1.618033988749895, 0),
                   (1, -1.618033988749895, 0), (0, -1, 1.618033988749895), (0, 1, 1.618033988749895),
                   (0, -1, -1.618033988749895), (0, 1, -1.618033988749895), (1.618033988749895, 0, -1),
                   (1.618033988749895, 0, 1), (-1.618033988749895, 0, -1), (-1.618033988749895, 0, 1)], float)
_ICO_F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
          (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
          (6, 2, 10), (8, 6, 7), (9, 8, 1)]


def icosphere(level):
    """Unit icosphere, faces wound outward; 20 x 4^level triangles."""
    verts = [unit(v) for v in _ICO_V]; faces = list(_ICO_F)
    for _ in range(level):
        cache = {}; nxt = []

        def mid(i, j):
            key = (min(i, j), max(i, j))
            if key not in cache:
                cache[key] = len(verts); verts.append(unit(verts[i] + verts[j]))
            return cache[key]
        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nxt += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = nxt
    return np.asarray(verts), faces


def _waves(rng, n, wavenumber):
    k = rng.normal(size=(n, 3)); k /= np.linalg.norm(k, axis=1)[:, None]
    return k * wavenumber, rng.uniform(0, 2 * np.pi, n)


def _noise(p, waves):
    k, phase = waves
    return np.sin(p @ k.T + phase).sum(1) / np.sqrt(len(phase) / 2)


def clump_mesh(clump, level=2):
    """The mass as a closed mesh: an ellipsoid lumped by three octaves of smooth
    noise (sub-masses, leaf clusters, sprays), its underside flattened as
    foliage hangs."""
    rng = np.random.default_rng(clump.seed)
    unit_v, faces = icosphere(level)
    r = np.asarray(clump.radii, float); scale = float(r.mean())
    big, mid, small = _waves(rng, 7, 2.0 / scale), _waves(rng, 7, 4.2 / scale), _waves(rng, 7, 8.5 / scale)
    local = unit_v * r
    local[:, 2] *= np.where(unit_v[:, 2] < 0, .80, 1.)
    lump = 1 + .19 * _noise(local, big) + .11 * _noise(local, mid) + .045 * _noise(local, small)
    local *= np.clip(lump, .62, 1.4)[:, None]
    c, s = np.cos(clump.yaw), np.sin(clump.yaw)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return local @ R.T + np.asarray(clump.centre, float), faces


def _resample(points, step):
    p = np.asarray(points, float)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    n = max(2, int(np.ceil(s[-1] / step)) + 1)
    q = np.linspace(0, s[-1], n)
    return np.column_stack([np.interp(q, s, p[:, i]) for i in range(3)]), q, s


def _furrows(limb, index, rng):
    """Interlaced furrows: each wanders around the limb and breaks into ridges."""
    p, q, s = _resample(limb.points, BARK_STEP)
    r = np.interp(q, s, limb.radii)
    _, u, v = frames(p)
    count = int(np.clip(round(2 * np.pi * limb.radii[0] / BARK_SPACING), 6, 48))
    out = []
    for k in range(count):
        theta = 2 * np.pi * k / count + rng.uniform(-.25, .25) * 2 * np.pi / count
        wander = .16 * np.sin(2 * np.pi * q / rng.uniform(.7, 1.6) + rng.uniform(0, 2 * np.pi))
        a = theta + wander
        n = np.cos(a)[:, None] * u + np.sin(a)[:, None] * v
        pts = p + (r + BARK_LIFT)[:, None] * n
        arc = 2 * np.pi * (r + BARK_LIFT) / count
        # Ridges of 0.25-0.9 m with short breaks: bur oak bark is blocky, not striped.
        i = int(rng.integers(0, 4))
        while i < len(q) - 2:
            run = max(3, int(rng.uniform(.25, .9) / BARK_STEP))
            j = min(len(q), i + run)
            if j - i >= 3:
                out.append(Furrow(pts[i:j], n[i:j], arc[i:j], index, k, count))
            i = j + max(1, int(rng.uniform(.04, .22) / BARK_STEP))
    return out


# ---- the grammar -------------------------------------------------------------------

def _envelope_points(rng, centre, radii, n_candidates=420):
    """Points spread over the crown envelope's surface (a jittered Fibonacci sphere)."""
    i = np.arange(n_candidates) + .5
    z = 1 - 2 * i / n_candidates; phi = np.pi * (1 + 5 ** .5) * i
    d = np.column_stack([np.sqrt(1 - z * z) * np.cos(phi), np.sqrt(1 - z * z) * np.sin(phi), z])
    d += rng.normal(0, .06, d.shape); d /= np.linalg.norm(d, axis=1)[:, None]
    return centre + d * radii, d


def _kmeans(points, k, rng, iterations=12):
    k = max(1, min(k, len(points)))
    centres = points[rng.choice(len(points), k, replace=False)].copy()
    for _ in range(iterations):
        label = np.argmin(np.linalg.norm(points[:, None] - centres[None], axis=2), axis=1)
        for j in range(k):
            if (label == j).any():
                centres[j] = points[label == j].mean(0)
    return label


def _taper(n, base, tip, flare=None):
    t = np.linspace(0, 1, n)
    r = base + (tip - base) * t ** .85
    if flare is not None:
        r *= 1 + flare * np.exp(-t / .08)
    return r


def savanna_oak(seed=1, height=7.0, *, spread=None, stage="leafy", detail=2):
    """An open-grown bur oak `height` metres tall.

    `spread` is the crown's outer horizontal radius, foliage included
    (default 0.66 of the height: open-grown bur oaks are often wider than
    they are tall). `stage` 'bare' keeps the limbs and drops the foliage.
    `detail` (1-3) sets mesh resolution only, never the tree's form, so a far
    and a near copy of one seed are the same tree.
    """
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}")
    if detail not in TUBE_SIDES:
        raise ValueError("detail must be 1, 2 or 3")
    if not isinstance(seed, (int, np.integer)):
        raise ValueError("seed must be an integer")
    H = float(height)
    if not np.isfinite(H) or H <= 1:
        raise ValueError("height must exceed 1 m")
    spread = float(spread) if spread is not None else .66 * H
    if not np.isfinite(spread) or not .25 * H <= spread <= H:
        raise ValueError("spread must be between 0.25 and 1 times the height")
    rng = np.random.default_rng(int(seed))

    # Crown envelope: an oblate ellipsoid through the masses' centres, on a low
    # crown base and leaning a little; the masses stand out of it by about
    # their own radius, so the envelope is drawn in from `spread` and `height`.
    R = spread / 1.30
    clump_r = R * .30
    base_z = H * rng.uniform(.24, .30)
    rz = (H - .62 * clump_r - base_z) / 2
    lean = rng.uniform(0, 2 * np.pi); off = R * rng.uniform(.03, .09) * np.array([np.cos(lean), np.sin(lean)])
    centre = np.array([off[0], off[1], base_z + rz])
    radii = np.array([R * rng.uniform(.93, 1.05), R * rng.uniform(.88, 1.0), rz])

    # Foliage targets: spread over the envelope, few on its underside, some recessed.
    cand, dirs = _envelope_points(rng, centre, radii)
    order = rng.permutation(len(cand)); targets = []
    for i in order:
        if dirs[i, 2] < -.42 or (dirs[i, 2] < -.1 and rng.random() < .6):
            continue
        p = cand[i]
        if all(np.linalg.norm((p - q) / [1, 1, .8]) > 1.7 * clump_r for q in targets):
            targets.append(p)
    targets = np.asarray(targets)
    pull = rng.uniform(.80, .97, len(targets))
    targets = centre + (targets - centre) * pull[:, None]

    limbs = []
    trunk_r = H * rng.uniform(.050, .058)
    fork = np.array([off[0] * .35, off[1] * .35, H * rng.uniform(.20, .25)])
    trunk_pts = crooked([0, 0, -.12], fork, rng, segments=3, wiggle=.035)
    limbs.append(Limb(trunk_pts, _taper(len(trunk_pts), trunk_r, trunk_r * .86, flare=.45), 0))

    # Scaffold limbs at spaced azimuths, leaving the trunk at staggered heights
    # (one fork for all of them reads as a knot), plus a short leader.
    n_scaffold = int(rng.integers(4, 6))
    origin_z = rng.permutation(np.linspace(.74, 1., n_scaffold)) * fork[2]
    origin_z += rng.uniform(-.03, .03, n_scaffold) * fork[2]
    origin_z = np.minimum(origin_z, fork[2])
    az0 = rng.uniform(0, 2 * np.pi)
    azimuths = az0 + np.arange(n_scaffold) * 2 * np.pi / n_scaffold + rng.uniform(-.3, .3, n_scaffold)
    rel = targets - centre
    top = rel[:, 2] / radii[2] > .62
    t_az = np.arctan2(rel[:, 1], rel[:, 0])
    owner = np.where(top, n_scaffold, np.argmin(np.abs(np.angle(np.exp(1j * (t_az[:, None] - azimuths[None])))), axis=1))
    scaffold_ids = []
    for s in range(n_scaffold + 1):
        mine = targets[owner == s]
        if s < n_scaffold:
            a = azimuths[s]; reach = rng.uniform(.60, .85)
            level = rng.uniform(0., .45)           # bur oak: some limbs nearly level
            end = np.array([centre[0] + np.cos(a) * radii[0] * reach, centre[1] + np.sin(a) * radii[1] * reach,
                            fork[2] + (centre[2] - fork[2]) * level + rng.uniform(.1, .5)])
            sag = .06 if level < .25 else .03
            start = np.array([np.interp(origin_z[s], trunk_pts[:, 2], trunk_pts[:, i]) for i in range(3)])
            pts = crooked(start, end, rng, segments=int(rng.integers(3, 6)), wiggle=.10, sag=sag)
            r0 = trunk_r * rng.uniform(.55, .68)
        else:
            if not len(mine):
                continue
            end = np.array([centre[0], centre[1], centre[2] + radii[2] * rng.uniform(.25, .45)])
            pts = crooked(fork, end, rng, segments=3, wiggle=.08)
            r0 = trunk_r * rng.uniform(.40, .50)
        limbs.append(Limb(pts, _taper(len(pts), r0, r0 * .52), 1, 0))
        scaffold_ids.append((len(limbs) - 1, mine))

    # Branches to groups of targets, twigs to each target.
    twig_ends = []
    for li, mine in scaffold_ids:
        if not len(mine):
            continue
        parent = limbs[li]
        label = _kmeans(mine, int(np.ceil(len(mine) / 2.6)), rng)
        for g in range(label.max() + 1):
            group = mine[label == g]
            if not len(group):
                continue
            gc = group.mean(0)
            # Attach on the outer two thirds of the scaffold, nearest the group.
            start = int(len(parent.points) * .35)
            j = start + int(np.argmin(np.linalg.norm(parent.points[start:] - gc, axis=1)))
            a = parent.points[j]
            hub = a + (gc - a) * rng.uniform(.62, .82)
            r2 = parent.radii[j] * rng.uniform(.50, .64)
            pts = crooked(a, hub, rng, segments=3, wiggle=.12)
            limbs.append(Limb(pts, _taper(len(pts), r2, r2 * .6), 2, li))
            bi = len(limbs) - 1
            for tgt in group:
                out = unit(tgt - centre)
                tip = tgt - out * clump_r * (.35 if stage == "leafy" else -.05)
                # Never thicker than the branch's end it leaves from.
                r3 = min(max(.016 * H / 7, r2 * .62 * rng.uniform(.8, 1.0)), r2 * .6)
                pts = crooked(hub, tip, rng, segments=3, wiggle=.13, smooth=1)
                limbs.append(Limb(pts, _taper(len(pts), r3, max(.008 * H / 7, r3 * .45)), 3, bi))
                twig_ends.append((tgt, 1.))
            # Inner foliage on about half the branches hides their wiring.
            if rng.random() < .40:
                twig_ends.append((hub + rng.normal(0, .15 * clump_r, 3), rng.uniform(.68, .88)))

    if stage == "bare":
        # Winter shows what foliage hides: short, crooked spurs off every twig
        # and along the branches. Drawn after everything else, so a bare tree's
        # other limbs are the leafy tree's, limb for limb.
        for li in range(len(limbs)):
            limb = limbs[li]
            if limb.order < 2:
                continue
            base = limb.points[-1] if limb.order == 3 else None
            spots = [len(limb.points) - 1] if limb.order == 3 else list(rng.choice(np.arange(len(limb.points) // 3,
                                                                                     len(limb.points) - 1), 2))
            for j in spots:
                at = limb.points[j]; along = unit(limb.points[j] - limb.points[max(0, j - 3)])
                for _ in range(int(rng.integers(3, 6)) if base is not None else 1):
                    d = unit(along + rng.normal(0, .6, 3) + np.array([0, 0, .3]))
                    pts = crooked(at, at + d * rng.uniform(.22, .55) * H / 7, rng, segments=3, wiggle=.2, smooth=1)
                    r = limb.radii[j] * .75
                    limbs.append(Limb(pts, _taper(len(pts), r, r * .45), 3, li))

    clumps = []
    if stage == "leafy":
        for k, (tgt, scale) in enumerate(twig_ends):
            size = clump_r * scale * rng.uniform(.72, 1.28)
            clumps.append(Clump(np.asarray(tgt, float), np.array([size, size * rng.uniform(.72, 1.0),
                                                                     size * rng.uniform(.52, .66)]),
                                float(rng.uniform(0, 2 * np.pi)), int(seed) * 1000 + k))
    meta = dict(species="bur_oak", common="Bur oak", latin="Quercus macrocarpa", habit="open-grown savanna oak",
                seed=int(seed), height=H, spread=spread, stage=stage, detail=int(detail),
                crown_base=round(base_z, 3), generator="lib/flora/oak.py", generator_version="0.1.0", units="metres")
    return Oak(limbs, clumps, meta)
