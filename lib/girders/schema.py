"""Validator for girders-scene-1 files.

``validate(scene)`` returns a list of error strings (empty means valid).  It
checks the format, materials/profiles references, finite geometry, bounds,
zero lengths, stats, and a rough structural check: every block rests on a
chain of supports down to the ground, and every beam is anchored (endpoints
meet blocks, ground or other members at nodes).  Beams tagged ``free`` or
``stub`` may cantilever (one end in the air) but must still be anchored at
one end.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

GROUND_TOL = 0.4          # how far above the site ground an end may sit
BLOCK_TOL = 0.4           # beam end -> block surface allowance
NODE_TOL = 0.06           # two beam ends meeting at a node
SEG_TOL = 0.25            # beam end lying on another member's length
BOUNDS_TOL = 0.05
FREE_TAGS = ("free", "stub")

KINDS = ("I", "C", "L", "box", "tube", "rod")


def _finite(*arrs):
    for a in arrs:
        if not np.all(np.isfinite(a)):
            return False
    return True


def validate(scene):
    """Return a list of problems; an empty list means the scene is valid."""
    errs = []
    if not isinstance(scene, dict):
        return ["scene is not a dict"]
    if scene.get("format") != "girders-scene-1":
        errs.append(f"format must be 'girders-scene-1', got {scene.get('format')!r}")
    if not isinstance(scene.get("seed"), int):
        errs.append("seed must be an int")
    gen = scene.get("generator", {})
    if gen.get("name") != "girders":
        errs.append(f"generator.name must be 'girders', got {gen.get('name')!r}")

    # ---- top-level containers
    for key in ("blocks", "beams", "details", "groups"):
        if not isinstance(scene.get(key), list):
            errs.append(f"{key} must be a list")
            return errs
    if not isinstance(scene.get("profiles"), dict) or not scene["profiles"]:
        errs.append("profiles must be a non-empty dict")
    mats = scene.get("materials")
    if not isinstance(mats, list) or not mats:
        errs.append("materials must be a non-empty list")
        mats = []

    # ---- bounds
    bnd = scene.get("bounds")
    if not isinstance(bnd, dict) or "min" not in bnd or "max" not in bnd:
        errs.append("bounds missing min/max")
        lo = np.array([-1e9, -1e9, -1e9])
        hi = np.array([1e9, 1e9, 1e9])
    else:
        lo, hi = np.asarray(bnd["min"], dtype=float), np.asarray(bnd["max"], dtype=float)
        if lo.shape != (3,) or hi.shape != (3,) or not _finite(lo, hi):
            errs.append("bounds must be finite 3-vectors")
        elif np.any(hi <= lo):
            errs.append("bounds.max must exceed bounds.min per axis")
    ground = float(lo[2])

    profiles = scene["profiles"]
    for name, pr in profiles.items():
        if not isinstance(pr, dict) or pr.get("kind") not in KINDS:
            errs.append(f"profile {name!r}: kind must be one of {KINDS}")
            continue
        for dim, v in pr.items():
            if dim == "kind":
                continue
            if not isinstance(v, (int, float)) or not np.isfinite(v) or v <= 0:
                errs.append(f"profile {name!r}: dimension {dim!r} must be a positive number")
    for m in mats:
        if not isinstance(m, str) or not m:
            errs.append(f"material entry {m!r} must be a non-empty string")

    # ---- numeric arrays
    blocks = scene["blocks"]
    beams = scene["beams"]
    details = scene["details"]
    groups = scene["groups"]
    gids = set()
    for g in groups:
        if not isinstance(g, dict) or not isinstance(g.get("id"), int):
            errs.append(f"bad group entry {g!r}")
            continue
        if g["id"] in gids:
            errs.append(f"duplicate group id {g['id']}")
        gids.add(g["id"])
    for g in groups:
        if g.get("parent") is not None and g["parent"] not in gids:
            errs.append(f"group {g.get('id')}: parent {g.get('parent')} does not exist")

    # ----- blocks
    bcenter = np.zeros((len(blocks), 3))
    bsize = np.zeros((len(blocks), 3))
    for i, b in enumerate(blocks):
        if b.get("group") not in gids:
            errs.append(f"block {i}: unknown group {b.get('group')}")
        if b.get("material") not in mats:
            errs.append(f"block {i}: unknown material {b.get('material')!r}")
        c = np.asarray(b.get("center", [np.nan] * 3), dtype=float)
        s = np.asarray(b.get("size", [np.nan] * 3), dtype=float)
        bcenter[i], bsize[i] = c, s
        if c.shape != (3,) or s.shape != (3,) or not _finite(c, s):
            errs.append(f"block {i}: center/size must be finite 3-vectors")
            continue
        if np.any(s <= 0):
            errs.append(f"block {i}: size must be strictly positive")
        if np.any(c - s / 2.0 < lo - BOUNDS_TOL) or np.any(c + s / 2.0 > hi + BOUNDS_TOL):
            errs.append(f"block {i}: outside bounds")
        yaw = b.get("yaw", 0.0)
        if not isinstance(yaw, (int, float)) or not np.isfinite(yaw):
            errs.append(f"block {i}: yaw must be finite")

    # ----- beams
    ba = np.zeros((len(beams), 3))
    bb = np.zeros((len(beams), 3))
    blen = np.zeros(len(beams))
    for i, b in enumerate(beams):
        if b.get("group") not in gids:
            errs.append(f"beam {i}: unknown group {b.get('group')}")
        if b.get("profile") not in profiles:
            errs.append(f"beam {i}: unknown profile {b.get('profile')!r}")
        if b.get("material") not in mats:
            errs.append(f"beam {i}: unknown material {b.get('material')!r}")
        a = np.asarray(b.get("a", [np.nan] * 3), dtype=float)
        c = np.asarray(b.get("b", [np.nan] * 3), dtype=float)
        ba[i], bb[i] = a, c
        if a.shape != (3,) or c.shape != (3,) or not _finite(a, c):
            errs.append(f"beam {i}: endpoints must be finite 3-vectors")
            continue
        ln = float(np.linalg.norm(c - a))
        blen[i] = ln
        if ln < 1e-6:
            errs.append(f"beam {i}: zero length")
        if np.any(a < lo - BOUNDS_TOL) or np.any(a > hi + BOUNDS_TOL) or \
           np.any(c < lo - BOUNDS_TOL) or np.any(c > hi + BOUNDS_TOL):
            errs.append(f"beam {i}: endpoint outside bounds")
        roll = b.get("roll", 0.0)
        if not isinstance(roll, (int, float)) or not np.isfinite(roll):
            errs.append(f"beam {i}: roll must be finite")

    # ----- details
    for i, d in enumerate(details):
        if d.get("group") not in gids:
            errs.append(f"detail {i}: unknown group {d.get('group')}")
        if d.get("material") not in mats:
            errs.append(f"detail {i}: unknown material {d.get('material')!r}")
        tr = np.asarray(d.get("transform", [np.nan] * 16), dtype=float)
        sz = np.asarray(d.get("size", [np.nan] * 3), dtype=float)
        if tr.shape != (16,) or sz.shape != (3,) or not _finite(tr, sz):
            errs.append(f"detail {i}: transform/size must be finite")
            continue
        if np.any(sz <= 0):
            errs.append(f"detail {i}: size must be strictly positive")
        if not isinstance(d.get("kind"), str) or not d["kind"]:
            errs.append(f"detail {i}: kind must be a non-empty string")
        if not (tr[3] == 0.0 and tr[7] == 0.0 and tr[11] == 0.0 and tr[15] == 1.0):
            errs.append(f"detail {i}: transform last row should be [0,0,0,1]")
        if np.linalg.norm(tr[:3]) < 1e-12:
            errs.append(f"detail {i}: transform x axis is zero")

    # ----- stats
    st = scene.get("stats")
    if isinstance(st, dict):
        for key, n in (("blocks", len(blocks)), ("beams", len(beams)), ("details", len(details))):
            if st.get(key) != n:
                errs.append(f"stats.{key} says {st.get(key)} but there are {n}")
    else:
        errs.append("stats missing")

    if errs:
        return errs
    if len(bcenter):
        ground = float(np.min(bcenter[:, 2] - bsize[:, 2] / 2.0))
    errs.extend(_support_check(scene, lo, ground, bcenter, bsize, ba, bb, blen))
    return errs


# ------------------------------------------------------------- support check

def _union(parent, a, b):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    while parent[b] != b:
        parent[b] = parent[parent[b]]
        b = parent[b]
    if a != b:
        parent[max(a, b)] = min(a, b)


def _find(parent, a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a


def _support_check(scene, lo, ground, bcenter, bsize, ba, bb, blen):
    """Union-find over blocks+beams+ground; report members that float.

    Order matters for speed: cheap checks (ground, shared nodes, member
    contact) run first and mark endpoints anchored; block-distance checks
    then only run for endpoints nothing else anchored, and the beam-through-
    slab test only runs for blocks that are still floating.
    """
    errs = []
    nK = len(bcenter)
    nB = len(ba)
    if nB == 0:
        return errs
    parent = np.arange(nK + nB + 1)
    GROUND = nK + nB

    blk_min = bcenter - bsize / 2.0
    blk_max = bcenter + bsize / 2.0
    ends = np.concatenate([ba, bb])                       # (2 nB, 3)
    end_beam = np.concatenate([np.arange(nB), np.arange(nB)])

    # 1. grounded blocks and beam ends
    gnd_block = blk_min[:, 2] <= ground + GROUND_TOL
    for i in np.nonzero(gnd_block)[0]:
        _union(parent, i, GROUND)
    gnd_end = ends[:, 2] <= ground + GROUND_TOL
    anchored = np.zeros(len(ends), dtype=bool)
    anchored[gnd_end] = True
    for e in np.nonzero(gnd_end)[0]:
        _union(parent, nK + end_beam[e], GROUND)

    # 2. beams meeting at nodes
    tree = cKDTree(ends)
    for e, neigh in enumerate(tree.query_ball_point(ends, NODE_TOL)):
        for m in neigh:
            if end_beam[m] != end_beam[e]:
                _union(parent, nK + end_beam[e], nK + end_beam[m])

    # 3. beam end lying on another member's length (directed per beam)
    etree = cKDTree(ends)
    r = blen / 2.0 + SEG_TOL
    seg_tol2 = SEG_TOL * SEG_TOL
    for bi in range(nB):
        mid = (ba[bi] + bb[bi]) / 2.0
        ax, ay, az = ba[bi]
        vx, vy, vz = bb[bi, 0] - ax, bb[bi, 1] - ay, bb[bi, 2] - az
        vv = vx * vx + vy * vy + vz * vz
        for e in etree.query_ball_point(mid, r[bi]):
            if end_beam[e] == bi:
                continue
            px, py, pz = ends[e]
            t = ((px - ax) * vx + (py - ay) * vy + (pz - az) * vz) / vv
            if t < 0.0:
                t = 0.0
            elif t > 1.0:
                t = 1.0
            dx = ax + t * vx - px
            dy = ay + t * vy - py
            dz = az + t * vz - pz
            if dx * dx + dy * dy + dz * dz <= seg_tol2:
                anchored[e] = True
                _union(parent, nK + bi, nK + end_beam[e])

    # 4. beam end near a block surface: only ends nothing else anchored
    # (floating members get a second chance in the repair pass below)
    btree = cKDTree(bcenter)
    radii = np.sqrt(np.sum(bsize * bsize, axis=1)) / 2.0 + BLOCK_TOL
    rmax = float(radii.max())
    for e in np.nonzero(~anchored)[0]:
        p = ends[e]
        for j in btree.query_ball_point(p, rmax):
            d = np.maximum(blk_min[j] - p, 0.0) + np.maximum(p - blk_max[j], 0.0)
            if np.dot(d, d) <= BLOCK_TOL * BLOCK_TOL:
                anchored[e] = True
                _union(parent, nK + end_beam[e], j)

    # 5. blocks resting on blocks (chunked O(n^2) with numpy)
    tol = 0.75
    for ci in range(0, nK, 1024):
        i = np.arange(ci, min(ci + 1024, nK))
        bottoms = blk_min[:, 2][None, :]
        z_ok = (bottoms >= blk_min[i, 2][:, None] - tol) & \
               (bottoms <= blk_max[i, 2][:, None] + tol)
        ox = np.minimum(blk_max[i, 0][:, None], blk_max[:, 0][None, :]) - \
            np.maximum(blk_min[i, 0][:, None], blk_min[:, 0][None, :])
        oy = np.minimum(blk_max[i, 1][:, None], blk_max[:, 1][None, :]) - \
            np.maximum(blk_min[i, 1][:, None], blk_min[:, 1][None, :])
        ok = z_ok & (ox > 0.2) & (oy > 0.2)
        for a, b in zip(*np.nonzero(ok)):
            j = ci + a
            if j == b:
                continue
            _union(parent, j, b)

    # 6. blocks supported by beams passing through their slab box: only
    # blocks that are still floating need it
    ground_root = _find(parent, GROUND)
    need = [i for i in range(nK) if _find(parent, i) != ground_root]
    if need:
        slab_lo = np.column_stack([blk_min[:, 0] - 0.35, blk_min[:, 1] - 0.35,
                                   blk_min[:, 2] - 0.8]) - 1e-4
        slab_hi = np.column_stack([blk_max[:, 0] + 0.35, blk_max[:, 1] + 0.35,
                                   blk_min[:, 2] + 0.6]) + 1e-4
        ntree = cKDTree(bcenter[need])
        rmax2 = float(radii[need].max()) if len(need) else 0.0
        for bi in range(nB):
            mid = (ba[bi] + bb[bi]) / 2.0
            for j in ntree.query_ball_point(mid, blen[bi] / 2.0 + rmax2):
                k = need[j]
                if _segment_box(a=ba[bi], c=bb[bi], l=slab_lo[k], h=slab_hi[k]):
                    _union(parent, nK + bi, k)

    # 7. repair pass: members of floating components get one more chance to
    # reach blocks or be reached by beams (their ends may have been anchored
    # by other members without ever touching the support chain)
    for _ in range(2):
        ground_root = _find(parent, GROUND)
        float_beams = [i for i in range(nB) if _find(parent, nK + i) != ground_root]
        float_blocks = [i for i in range(nK) if _find(parent, i) != ground_root]
        if not float_beams and not float_blocks:
            break
        for bi in float_beams:
            for e in (bi, bi + nB):
                p = ends[e]
                for j in btree.query_ball_point(p, rmax):
                    d = np.maximum(blk_min[j] - p, 0.0) + np.maximum(p - blk_max[j], 0.0)
                    if np.dot(d, d) <= BLOCK_TOL * BLOCK_TOL:
                        anchored[e] = True
                        _union(parent, nK + bi, j)
        for bi in float_blocks:
            for j in btree.query_ball_point(bcenter[bi], radii[bi] + rmax):
                if j == bi:
                    continue
                u0 = blk_min[bi, 2]
                z0, z1 = blk_min[j, 2], blk_max[j, 2]
                if not (z0 - 0.75 <= u0 <= z1 + 0.75):
                    continue
                ox = min(blk_max[bi, 0], blk_max[j, 0]) - max(blk_min[bi, 0], blk_min[j, 0])
                oy = min(blk_max[bi, 1], blk_max[j, 1]) - max(blk_min[bi, 1], blk_min[j, 1])
                if ox > 0.2 and oy > 0.2:
                    _union(parent, bi, j)
        if float_blocks:
            mtree = cKDTree((ba + bb) / 2.0)
            lmax = float(blen.max())
            for bi in float_blocks:
                l = slab_lo[bi]
                h = slab_hi[bi]
                for m in mtree.query_ball_point(bcenter[bi], radii[bi] + 0.6 + lmax / 2.0):
                    if _segment_box(ba[m], bb[m], l, h):
                        _union(parent, nK + m, bi)

    # 8. every block reaches ground
    ground_root = _find(parent, GROUND)
    for i in range(nK):
        if _find(parent, i) != ground_root:
            errs.append(f"block {i}: no support path to the ground")

    # 9. every beam: anchored at >= 1 end; connected to ground unless free
    for i in range(nB):
        if not (anchored[i] or anchored[i + nB]):
            errs.append(f"beam {i}: neither end meets a block, ground or member")
            continue
        tags = scene["beams"][i].get("tags") or []
        if not any(t in FREE_TAGS for t in tags) and _find(parent, nK + i) != ground_root:
            errs.append(f"beam {i}: member chain does not reach the ground")
    return errs


def _segment_box(a, c, l, h):
    """Does segment a->c intersect AABB [l, h]? (slab method, one box.)"""
    ax, ay, az = a
    cx, cy, cz = c
    if (l[0] <= ax <= h[0] and l[1] <= ay <= h[1] and l[2] <= az <= h[2]) or \
       (l[0] <= cx <= h[0] and l[1] <= cy <= h[1] and l[2] <= cz <= h[2]):
        return True
    t0, t1 = 0.0, 1.0
    for (a0, c0, l0, h0) in ((ax, cx, l[0], h[0]), (ay, cy, l[1], h[1]), (az, cz, l[2], h[2])):
        da = c0 - a0
        if -1e-12 < da < 1e-12:
            if a0 < l0 or a0 > h0:
                return False
            continue
        t0c = (l0 - a0) / da
        t1c = (h0 - a0) / da
        if t0c > t1c:
            t0c, t1c = t1c, t0c
        if t0c > t0:
            t0 = t0c
        if t1c < t1:
            t1 = t1c
    return t0 <= t1




def _segment_box_hits(a, c, lo, hi):
    """Segment vs AABB test: which segments intersect which boxes (slab method)."""
    d = c - a
    out = np.zeros((len(a), len(lo)), dtype=bool)
    for bi in range(len(lo)):
        l = lo[bi]
        h = hi[bi]
        t0 = np.zeros(len(a))
        t1 = np.ones(len(a))
        ok = np.ones(len(a), dtype=bool)
        for ax in range(3):
            da = d[:, ax]
            na = np.abs(da) < 1e-12
            with np.errstate(divide="ignore", invalid="ignore"):
                t0c = np.where(na, 0.0, (l[ax] - a[:, ax]) / da)
                t1c = np.where(na, 0.0, (h[ax] - a[:, ax]) / da)
            t0 = np.maximum(t0, np.minimum(t0c, t1c))
            t1 = np.minimum(t1, np.maximum(t0c, t1c))
            ok &= (~na) | ((a[:, ax] >= l[ax]) & (a[:, ax] <= h[ax]))
        pin = ((a[:, 0] >= l[0]) & (a[:, 0] <= h[0]) & (a[:, 1] >= l[1]) &
               (a[:, 1] <= h[1]) & (a[:, 2] >= l[2]) & (a[:, 2] <= h[2]))
        cin = ((c[:, 0] >= l[0]) & (c[:, 0] <= h[0]) & (c[:, 1] >= l[1]) &
               (c[:, 1] <= h[1]) & (c[:, 2] >= l[2]) & (c[:, 2] <= h[2]))
        out[:, bi] = (ok & (t0 <= t1)) | pin | cin
    return out
