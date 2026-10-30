"""Girders v2 megastructures: ``fault-spine`` and ``suspended-delta``.

Two original inhabited megastructure generators built on the same primitives
as the v1 site (SceneBuilder, TrussBridge, profiles, detail kinds) and emitting
the same ``girders-scene-1`` format, so the Blender builder in studies/girders
consumes them unchanged.  Both avoid the v1 tower-grid / curtain-wall look:

- ``fault-spine`` — an asymmetric industrial canyon: two irregular rows of
  tall inhabited blocks facing each other across a narrow gap.  Blocks step
  and offset (terraced setbacks), huge trussed cantilevers jut out from the
  canyon rims, and deep connecting truss ribs (8-18 m) leap across the
  canyon at several levels.  More than half the floor plates are omitted so
  the secondary steel lattice reads through the open structure.
- ``suspended-delta`` — a horizontal, layered inhabited bridge megastructure:
  a squat central hub with 3-6 deck tiers radiating like a river delta,
  each tier a deep-trussed inhabited bridge ending at a sparse, irregular
  buttress tower.  Large voids open between the branches; cable stays and
  nets (ROD30) lace the buttress tops to the decks.

Membership hierarchy is explicit in tags: every beam carries ``primary`` or
``secondary``; the fine lattice (0.6-1.2 m pitch, L70/L90/TUBE90 sections) is
``secondary``.  Long members are split into ~2-3 m segments with splice
details, which both reads as fabricated steel and keeps the scene validator
fast on multi-hundred-thousand-beam scenes.

Deterministic: identical (seed, preset, scale) inputs give identical scenes.
"""

from __future__ import annotations

import math

import numpy as np

from .scene import SceneBuilder, frame, normalize
from .site import Ctx, floor_schedule
from .trusses import TrussBridge

V2_VERSION = "0.2.0"


class V2Stats:
    """Bookkeeping for the numeric guarantees the v2 presets make."""

    def __init__(self):
        self.floor_slots = 0
        self.floor_kept = 0
        self.glass_blocks = 0
        self.cantilever_groups = 0
        self.setback_groups = 0
        self.deep_trusses = 0
        self.truss_depths = []

    def floors(self, kept):
        self.floor_slots += 1
        self.floor_kept += int(kept)


# ----------------------------------------------------------------- helpers

def _beam_split(sb, a, b, split, profile, material, tags, group, roll=0.0):
    """One member as segments of at most ``split`` metres, sharing endpoints.

    Splitting keeps the validator's member-proximity queries local (the
    radius grows with member length) and gives every segment a splice
    joint where detail can be instanced.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    v = b - a
    length = float(np.linalg.norm(v))
    if length < 1e-9:
        return []
    nseg = max(1, int(math.ceil(length / max(split, 0.5))))
    v = v / length
    out = []
    for s in range(nseg):
        a0 = a + v * (length * s / nseg)
        b0 = a + v * (length * (s + 1) / nseg)
        out.append(sb.add_beam(a0, b0, profile, material, list(tags), group, roll))
    return out


def _lattice_face_mapped(sb, ctx, group, P, z0, width, height, pitch, split,
                         tags, profile="L70", diag_rate=0.0, splice_rate=0.0):
    """A vertical lattice rectangle mapped by P(s) -> (x, y), s in [0, width].

    The rectangle rises ``height`` metres from ``z0``.  Verticals +
    horizontals at ``pitch``, split into <= ``split``-metre segments; sparse
    zig-zag diagonals land on vertical/horizontal members.  Returns the
    number of beams added.
    """
    rng = ctx.rng
    nv = max(2, int(round(width / pitch)))
    nh = max(2, int(round(height / pitch)))
    added = 0
    mat = ctx.steel()
    for i in range(nv + 1):
        s = width * i / nv
        px, py = P(s)
        added += len(_beam_split(sb, (px, py, z0), (px, py, z0 + height), split,
                                 profile, mat, tags, group, 0))
    for j in range(nh + 1):
        z = z0 + height * j / nh
        p0, p1 = P(0.0), P(width)
        added += len(_beam_split(sb, (p0[0], p0[1], z), (p1[0], p1[1], z), split,
                                 profile, mat, tags, group, 0))
    if diag_rate > 0.0:
        for j in range(nh - 1):
            if rng.random() >= diag_rate:
                continue
            i = int(rng.integers(nv))
            s0, s1 = width * i / nv, width * (i + 1) / nv
            z0j, z1j = z0 + height * j / nh, z0 + height * (j + 1) / nh
            p0, p1 = P(s0), P(s1)
            added += len(_beam_split(sb, (p0[0], p0[1], z0j), (p1[0], p1[1], z1j),
                                     split, profile, mat, tags, group, 0))
    if splice_rate > 0.0:
        for i in range(nv + 1):
            for j in range(nh + 1):
                if rng.random() < splice_rate:
                    px, py = P(width * i / nv)
                    z = z0 + height * j / nh
                    sb.add_detail_at("bolt_plate", (px, py, z), (1.0, 0.0, 0.0),
                                     (0.0, 0.0, 1.0), [0.55, 0.40, 0.02],
                                     mat, group)
    return added


def _lattice_floor_mapped(sb, ctx, group, P, w_len, d_len, z, pitch, split,
                          tags, profile="L70", skip_rate=0.0):
    """A horizontal lattice floor mapped by P(s, t) -> (x, y).

    Joists run in both directions at ``pitch``; their ends lie on the
    perimeter members at the same level, so every joist anchors.  Returns
    the number of beams added.
    """
    rng = ctx.rng
    mat = ctx.steel()
    added = 0
    nw = max(1, int(round(w_len / pitch)))
    nd = max(1, int(round(d_len / pitch)))
    for i in range(1, nw):
        if skip_rate > 0.0 and rng.random() < skip_rate:
            continue
        s = w_len * i / nw
        p0, p1 = P(s, 0.0), P(s, d_len)
        added += len(_beam_split(sb, (p0[0], p0[1], z), (p1[0], p1[1], z), split,
                                 profile, mat, tags, group, 0))
    for j in range(1, nd):
        if skip_rate > 0.0 and rng.random() < skip_rate:
            continue
        t = d_len * j / nd
        p0, p1 = P(0.0, t), P(w_len, t)
        added += len(_beam_split(sb, (p0[0], p0[1], z), (p1[0], p1[1], z), split,
                                 profile, mat, tags, group, 0))
    return added


def lattice_face(sb, ctx, group, x0, y0, z0, ux, uy, width, height, pitch, split,
                 tags, profile="L70", diag_rate=0.0, splice_rate=0.0):
    """Axis-aligned facade lattice: rectangle from (x0, y0, z0) along (ux, uy)."""
    return _lattice_face_mapped(
        sb, ctx, group, lambda s: (x0 + ux * s, y0 + uy * s), z0, width, height,
        pitch, split, tags, profile, diag_rate, splice_rate)


def lattice_floor(sb, ctx, group, x0, y0, x1, y1, z, pitch, split, tags,
                  profile="L70", skip_rate=0.0):
    """Axis-aligned floor lattice between (x0, y0) and (x1, y1) at height z."""
    return _lattice_floor_mapped(
        sb, ctx, group,
        lambda s, t: (x0 + (x1 - x0) * s / max(abs(x1 - x0), 1e-9),
                      y0 + (y1 - y0) * t / max(abs(y1 - y0), 1e-9)),
        abs(x1 - x0), abs(y1 - y0), z, pitch, split, tags, profile, skip_rate)


# ---------------------------------------------------------- inhabited blocks

def _stack_footprint(bx, by, w, d, k, canyon_side, shrink_w, shrink_d):
    """Footprint of stack ``k``: each upper stack steps back from the canyon."""
    wk = max(9.0, w - k * shrink_w)
    dk = max(9.0, d - k * shrink_d)
    yk = by + (d - dk) / 2.0 if canyon_side < 0 else by - (d - dk) / 2.0
    return bx, yk, wk, dk


def build_block(ctx, bx, by, w, d, storeys, floor_h, idx, stats, canyon_side=-1,
                setback_stacks=1, glass_rate=0.1, end_faces=True):
    """One inhabited block: plinth, stepped stacks, frames, lattice, details.

    Each stack is its own group (``block-NN`` for the base, ``setback-NN-k``
    for the stepped upper stacks).  Returns the base group id.
    """
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    pitch = p["pitch"]
    split = p["split"]
    slab_keep = p.get("slab_keep", 0.45)
    plinth_top = 1.6
    floors = floor_schedule(storeys, floor_h, rng)
    n = len(floors)
    gid = sb.group(f"block-{idx:02d}")
    sb.add_block((bx, by, plinth_top / 2.0), (w + 3.0, d + 3.0, plinth_top),
                 "concrete", ["block", "plinth"], gid)

    # ---- stack boundaries (terraced setbacks)
    cuts = [0]
    if setback_stacks >= 1:
        cuts.append(max(cuts[-1] + 3, int(math.ceil(n * 0.55))))
    if setback_stacks >= 2:
        cuts.append(max(cuts[-1] + 3, int(math.ceil(n * 0.8))))
    cuts.append(n)
    cuts = sorted(set(cuts))
    bay = p.get("bay", 4.4)

    lower_top = plinth_top
    for k in range(len(cuts) - 1):
        k0, k1 = cuts[k], cuts[k + 1]
        if k1 <= k0:
            continue
        bxk, byk, wk, dk = _stack_footprint(bx, by, w, d, k, canyon_side,
                                            p.get("shrink_w", 4.0), p.get("shrink_d", 4.0))
        if k == 0:
            stk_gid = gid
        else:
            stk_gid = sb.group(f"setback-{idx:02d}-{k}")
            stats.setback_groups += 1
        xs = np.linspace(bxk - wk / 2.0, bxk + wk / 2.0, max(3, int(wk / bay) + 1))
        ys = np.linspace(byk - dk / 2.0, byk + dk / 2.0, max(3, int(dk / bay) + 1))
        stack_top = floors[k1 - 1]
        z_base = lower_top

        # ---- columns (perimeter grid, one member per storey)
        lines = []
        for (xx, yy) in [(xs, [ys[0]] * len(xs)), (xs, [ys[-1]] * len(xs))]:
            lines.extend(zip(xx, yy))
        for (xx, yy) in [([xs[0]] * len(ys), ys), ([xs[-1]] * len(ys), ys)]:
            lines.extend(zip(xx, yy))
        for (cx, cy) in lines:
            z0 = z_base
            for s in range(k0, k1):
                z1 = floors[s]
                sb.add_beam((cx, cy, z0), (cx, cy, z1), "BOX500" if wk >= 24.0 else "BOX350",
                            ctx.steel(), ["primary", "block", "column"], stk_gid)
                z0 = z1
            if k > 0:
                # tie the stack base into the lower roof with short stubs
                sb.add_beam((cx, cy, z_base), (cx, cy, z_base - 0.55), "I300",
                            ctx.steel(), ["primary", "block", "column"], stk_gid)

        # ---- spandrels and floor plates per floor
        for s in range(k0, k1):
            z = floors[s]
            keep = rng.random() < slab_keep
            if s == k1 - 1 and k < len(cuts) - 2:
                keep = True  # every non-top stack keeps its roof for the stack above
            else:
                stats.floors(keep)  # omission is measured on optional plates
            for i in range(len(xs) - 1):
                sb.add_beam((xs[i], ys[0], z), (xs[i + 1], ys[0], z), "I450",
                            ctx.steel(), ["primary", "block", "spandrel"], stk_gid)
                sb.add_beam((xs[i], ys[-1], z), (xs[i + 1], ys[-1], z), "I450",
                            ctx.steel(), ["primary", "block", "spandrel"], stk_gid)
            for j in range(len(ys) - 1):
                sb.add_beam((xs[0], ys[j], z), (xs[0], ys[j + 1], z), "I450",
                            ctx.steel(), ["primary", "block", "spandrel"], stk_gid)
                sb.add_beam((xs[-1], ys[j], z), (xs[-1], ys[j + 1], z), "I450",
                            ctx.steel(), ["primary", "block", "spandrel"], stk_gid)
            if keep:
                sb.add_block((bxk, byk, z + 0.18), (wk + 0.8, dk + 0.8, 0.36),
                             "concrete", ["block", "slab"], stk_gid)
                if ctx.roll("detail"):
                    # fall protection just inside the open lattice faces
                    face_y0 = byk - dk / 2.0
                    face_y1 = byk + dk / 2.0
                    for lx in np.arange(xs[0] + 1.3, xs[-1] - 0.5, 2.6):
                        if rng.random() < 0.8:
                            sb.add_detail_at("railing", (lx, face_y0 + 0.45, z + 0.5),
                                             (1, 0, 0), (0, 0, 1), [2.6, 0.08, 1.1],
                                             ctx.steel(), stk_gid)
                        if rng.random() < 0.8:
                            sb.add_detail_at("railing", (lx, face_y1 - 0.45, z + 0.5),
                                             (1, 0, 0), (0, 0, 1), [2.6, 0.08, 1.1],
                                             ctx.steel(), stk_gid)
            # secondary floor lattice, kept or not (omitted plates expose it)
            if ctx.roll("secondary"):
                lattice_floor(sb, ctx, stk_gid, xs[0], ys[0], xs[-1], ys[-1], z + 0.15,
                              pitch, split, ["secondary", "block", "joist"])

        # ---- lattice faces on all four sides of the stack (the structural
        # envelope: always present, so gated floor lattices stay supported).
        # The top stack rises to the roof lattice so that it is supported too.
        face_h = stack_top - z_base + (0.42 if k == len(cuts) - 2 else 0.0)
        for (x0, y0, ux, uy, wf) in [
                (xs[0], ys[0], 1.0, 0.0, wk), (xs[0], ys[-1], 1.0, 0.0, wk)]:
            lattice_face(sb, ctx, stk_gid, x0, y0, z_base, ux, uy, wf,
                         face_h, pitch, split,
                         ["secondary", "block", "lattice"], "L70",
                         diag_rate=p.get("diag_rate", 0.06),
                         splice_rate=p.get("splice_rate", 0.05))
        for (x0, y0, ux, uy, wf) in [
                (xs[0], ys[0], 0.0, 1.0, dk), (xs[-1], ys[0], 0.0, 1.0, dk)]:
            if not end_faces:
                continue
            lattice_face(sb, ctx, stk_gid, x0, y0, z_base, ux, uy, wf,
                         face_h, pitch, split,
                         ["secondary", "block", "lattice"], "L90",
                         diag_rate=p.get("diag_rate", 0.06) * 0.5,
                         splice_rate=p.get("splice_rate", 0.05) * 0.5)

        # ---- glass strip windows on the canyon face of the base stack only
        if k == 0 and glass_rate > 0.0:
            face_y = byk - dk / 2.0 if canyon_side < 0 else byk + dk / 2.0
            for s in range(k0, k1 - 1):
                if rng.random() >= glass_rate:
                    continue
                z0, z1 = floors[s], floors[s + 1]
                i = int(rng.integers(max(1, len(xs) - 1)))
                cx = (xs[i] + xs[i + 1]) / 2.0
                gb = sb.add_block((cx, face_y + 0.05, (z0 + z1) / 2.0),
                                  (xs[i + 1] - xs[i] - 0.6, 0.08, z1 - z0 - 0.5),
                                  "glass", ["block", "glass"], stk_gid)
                stats.glass_blocks += 1
                for q in (0.0, 1.0):
                    mx = xs[i] + (xs[i + 1] - xs[i]) * q
                    sb.add_beam((mx, face_y, z0), (mx, face_y, z1), "TUBE50",
                                ctx.steel(), ["secondary", "block", "mullion"], stk_gid)

        lower_top = stack_top + 0.36

    # ---- roof furniture
    bxr, byr, wr, dr = _stack_footprint(bx, by, w, d, len(cuts) - 2, canyon_side,
                                        p.get("shrink_w", 4.0), p.get("shrink_d", 4.0))
    roof = floors[-1] + 0.36
    rw = max(2, int(round(wr / pitch)))
    rd = max(2, int(round(dr / pitch)))
    lattice_floor(sb, ctx, gid, bxr - wr / 2.0, byr - dr / 2.0, bxr + wr / 2.0,
                  byr + dr / 2.0, roof + 0.06, pitch, split,
                  ["secondary", "block", "joist"])
    if ctx.roll("secondary"):
        for (px, py) in [(bxr - wr / 2.0, byr - dr / 2.0), (bxr + wr / 2.0, byr - dr / 2.0),
                         (bxr + wr / 2.0, byr + dr / 2.0), (bxr - wr / 2.0, byr + dr / 2.0)]:
            sb.add_beam((px, py, roof), (px, py, roof + 1.0), "TUBE50",
                        ctx.steel(), ["secondary", "block", "parapet"], gid)
        for (a, b) in [((bxr - wr / 2.0, byr - dr / 2.0), (bxr + wr / 2.0, byr - dr / 2.0)),
                       ((bxr + wr / 2.0, byr - dr / 2.0), (bxr + wr / 2.0, byr + dr / 2.0)),
                       ((bxr + wr / 2.0, byr + dr / 2.0), (bxr - wr / 2.0, byr + dr / 2.0)),
                       ((bxr - wr / 2.0, byr + dr / 2.0), (bxr - wr / 2.0, byr - dr / 2.0))]:
            sb.add_beam((a[0], a[1], roof + 1.0), (b[0], b[1], roof + 1.0), "TUBE50",
                        ctx.steel(), ["secondary", "block", "parapet"], gid)
    for _ in range(rng.integers(2, 5)):
        if ctx.roll("detail"):
            # vents snap to roof-lattice crossings so they are supported
            vx = bxr - wr / 2.0 + wr * int(rng.integers(rw + 1)) / rw
            vy = byr - dr / 2.0 + dr * int(rng.integers(rd + 1)) / rd
            vh = rng.uniform(0.6, 1.4)
            sb.add_beam((vx, vy, roof + 0.06), (vx, vy, roof + vh), "TUBE140",
                        ctx.steel(), ["secondary", "block", "vent"], gid)
            sb.add_detail_at("vent", (vx, vy, roof + vh), (1, 0, 0), (0, 0, 1),
                             [0.7, 0.7, 0.5], ctx.steel(), gid)
    # occasional orange light cluster on the roof
    if ctx.roll("detail") and rng.random() < 0.7:
        for _ in range(rng.integers(2, 4)):
            lx = bxr - wr / 2.0 + wr * int(rng.integers(rw + 1)) / rw
            ly = byr - dr / 2.0 + dr * int(rng.integers(rd + 1)) / rd
            sb.add_detail_at("light", (lx, ly, roof + 0.9), (1, 0, 0), (0, 0, 1),
                             [0.35, 0.35, 0.35], "accent", gid)

    # ---- exterior stair on the outer face, pipes, ladders
    _block_stair(ctx, bx, by, w, d, floors, gid, canyon_side)
    _block_pipes(ctx, bx, by, w, d, floors, gid, canyon_side)
    _block_ladders(ctx, bx, by, w, d, gid, canyon_side)
    return gid, {"bx": bx, "by": by, "w": w, "d": d, "floors": floors,
                 "tx": bxr, "ty": byr, "tw": wr, "td": dr, "roof": roof,
                 "canyon_side": canyon_side}


def _block_stair(ctx, bx, by, w, d, floors, gid, canyon_side):
    """Exterior zig-zag stair up one end face (in the gap between blocks)."""
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    if not ctx.roll("secondary") or len(floors) < 3:
        return
    if rng.random() < 0.45:
        return  # not every block carries a full stair
    sx0 = bx - w / 2.0 - 1.6
    sy0 = (by + d / 2.0) - rng.uniform(2.0, d - 2.0) if canyon_side < 0 \
        else (by - d / 2.0) + rng.uniform(2.0, d - 2.0)
    zcur = 1.6
    for k in range(len(floors) - 1):
        znext = floors[k]
        xk = sx0 if k % 2 == 0 else sx0 - 1.0
        steps = max(4, int((znext - zcur) / 0.18))
        for yy in (sy0, sy0 + 1.1):
            sb.add_beam((xk, yy, zcur), (xk, yy, znext), "C250", ctx.steel(),
                        ["secondary", "block", "stair"], gid)
        for i in range(steps):
            zz = zcur + (znext - zcur) * (i + 0.5) / steps
            sb.add_block((xk, sy0 + 0.55, zz), (1.2, 1.1, 0.06), "grating",
                         ["block", "stair"], gid)
        if rng.random() < 0.8:
            sb.add_detail_at("railing", (xk, sy0 + 1.15, znext - 1.3), (0, 0, 1),
                             (0, 1, 0), [0.08, 0.08, 2.6], ctx.steel(), gid)
        sb.add_block(((sx0 + sx0 - 1.0) / 2.0, sy0 + 0.55, znext + 0.15),
                     (1.6, 1.3, 0.12), "grating", ["block", "stair"], gid)
        zcur = znext


def _block_pipes(ctx, bx, by, w, d, floors, gid, canyon_side):
    """Vertical pipe run with horizontal branches on the outer face."""
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    if not ctx.roll("secondary"):
        return
    px = bx + rng.uniform(-w / 3.0, w / 3.0)
    py = by + d / 2.0 + 0.45 if canyon_side < 0 else by - d / 2.0 - 0.45
    z_top = floors[-1] + 0.45
    sb.add_beam((px, py, 1.6), (px, py, z_top), "TUBE90", ctx.paint(),
                ["secondary", "block", "pipe"], gid)
    for k in range(0, len(floors), 3):
        zz = floors[k]
        if rng.random() < 0.8:
            sb.add_detail_at("pipe_run", (px, py, zz + 1.0), (1, 0, 0), (0, 0, 1),
                             [0.5, 0.5, 0.5], ctx.steel(), gid)
        if rng.random() < 0.6:
            qx = bx + rng.uniform(-w / 2.0, w / 2.0)
            sb.add_beam((px, py, zz), (qx, py - canyon_side * 0.1, zz), "TUBE90",
                        ctx.paint(), ["secondary", "block", "pipe"], gid)


def _block_ladders(ctx, bx, by, w, d, gid, canyon_side):
    sb, rng = ctx.sb, ctx.rng
    for _ in range(rng.integers(1, 3)):
        if not ctx.roll("detail"):
            continue
        lx = bx + rng.uniform(-w / 3.0, w / 3.0)
        ly = by - d / 2.0 - 0.35 if canyon_side < 0 else by + d / 2.0 + 0.35
        # local Z up (the builder convention: ladders stand on world Z)
        sb.add_detail_at("ladder", (lx, ly, 2.0), (1, 0, 0), (0, 0, 1),
                         [0.6, 0.6, 5.0], ctx.steel(), gid)


def build_cantilever(ctx, stats, anchor, idx):
    """A huge trussed cantilever deck jutting out from a block face.

    ``anchor``: dict(bx, by, face_xy, outward (unit vector), z, w, L, depth,
    back, group).  Side trusses run from a backspan inside the block out to
    the free tip; anchor columns tie the backspan ends down to the plinth so
    the whole frame reaches ground.  Returns the group id.
    """
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    g = sb.group(f"cantilever-{idx:02d}")
    stats.cantilever_groups += 1
    ox, oy = anchor["face_xy"]
    ux, uy = anchor["outward"]
    z = anchor["z"]
    w = anchor["w"]
    L = anchor["L"]
    depth = anchor["depth"]
    back = anchor["back"]
    split = p["split"]
    ang = math.atan2(uy, ux)
    ca, sa = math.cos(ang), math.sin(ang)

    def W(lx, ly, lz):
        return np.array([ox + lx * ca - ly * sa,
                         oy + lx * sa + ly * ca, lz], dtype=float)

    panels = max(6, int(round(L / max(split, 1.0))))
    panel = L / panels
    back_panels = max(2, int(math.ceil(back / panel)))
    xs = [-back_panels * panel] + [i * panel for i in range(panels + 1)]
    for side in (-w / 2.0, w / 2.0):
        # top and bottom chords, split per panel (backspan + cantilever)
        for k in range(len(xs) - 1):
            a0, a1 = xs[k], xs[k + 1]
            sb.add_beam(W(a0, side, z), W(a1, side, z), "I600",
                        ctx.steel(), ["primary", "cantilever", "chord"], g)
            sb.add_beam(W(a0, side, z + depth), W(a1, side, z + depth), "I600",
                        ctx.steel(), ["primary", "cantilever", "chord"], g)
        # warren webs between the chords, per panel
        for k in range(len(xs) - 1):
            a0, a1 = xs[k], xs[k + 1]
            if k % 2 == 0:
                sb.add_beam(W(a0, side, z), W(a1, side, z + depth), "C250",
                            ctx.steel(), ["secondary", "cantilever", "web"], g,
                            roll=math.radians(90.0))
            else:
                sb.add_beam(W(a0, side, z + depth), W(a1, side, z), "C250",
                            ctx.steel(), ["secondary", "cantilever", "web"], g,
                            roll=math.radians(90.0))
        # end posts at the face and the tip
        for xk in (xs[0], xs[-1]):
            sb.add_beam(W(xk, side, z), W(xk, side, z + depth), "I300",
                        ctx.steel(), ["secondary", "cantilever", "vertical"], g)
        # anchor columns: backspan ends down to the plinth (grounded)
        sb.add_beam(W(xs[0], side, z + depth), W(xs[0], side, 1.6), "BOX350",
                    ctx.steel(), ["primary", "cantilever", "anchor"], g)
        sb.add_beam(W(xs[0], side, z), W(xs[0], side, 1.6), "BOX350",
                    ctx.steel(), ["primary", "cantilever", "anchor"], g)
    # cross beams at every panel node (deck support + top ties)
    for k in range(len(xs)):
        xk = xs[k]
        sb.add_beam(W(xk, -w / 2.0, z), W(xk, w / 2.0, z), "I240",
                    ctx.steel(), ["secondary", "cantilever", "cross"], g)
        if k % 2 == 0:
            sb.add_beam(W(xk, -w / 2.0, z + depth), W(xk, w / 2.0, z + depth),
                        "C180", ctx.steel(), ["secondary", "cantilever", "cross"], g)
    # deck segments (grating over the bottom cross beams)
    nseg = max(2, int(round(L / 8.0)))
    for s in range(nseg):
        cx = panel * 0.5 + L * (s + 0.5) / nseg
        sb.add_block(W(cx, 0.0, z + 0.08), (L / nseg, w + 0.4, 0.14), "grating",
                     ["cantilever", "deck"], g, yaw=ang)
    # railings along both edges and the tip
    for s in range(0, max(1, int(L / 2.6))):
        lx = 2.6 * s + 1.3
        for side in (-w / 2.0, w / 2.0):
            if rng.random() < 0.85:
                sb.add_detail_at("railing", W(lx, side + 0.05, z + 1.0), (1, 0, 0),
                                 (0, 0, 1), [2.6, 0.08, 1.1], ctx.steel(), g)
    if rng.random() < 0.8:
        sb.add_detail_at("railing", W(L + 0.05, 0.0, z + 1.0),
                         (uy, -ux, 0.0), (0, 0, 1), [w - 0.3, 0.08, 1.1],
                         ctx.steel(), g)
    if rng.random() < 0.6:
        sb.add_detail_at("light", W(L - 0.6, 0.0, z + 1.6), (1, 0, 0), (0, 0, 1),
                         [0.35, 0.35, 0.35], "accent", g)
    for k in range(0, len(xs), 2):
        if rng.random() < 0.6:
            sb.add_detail_at("bolt_plate", W(xs[k], w / 2.0, z), (1, 0, 0),
                             (0, 0, 1), [0.9, 0.5, 0.02], ctx.steel(), g)
    return g


def deep_rib(ctx, stats, fa, fb, deck_z, depth, width, own_a, own_b):
    """A deep truss rib (8-18 m) spanning between two block faces."""
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    a = np.array([fa[0], fa[1], deck_z], dtype=float)
    b = np.array([fb[0], fb[1], deck_z], dtype=float)
    direction = b - a
    span = float(np.linalg.norm(direction))
    if span < 8.0:
        return None
    g = sb.group(f"rib-{stats.deep_trusses + 1:02d}")
    kind = p["rib_kinds"][int(rng.integers(len(p["rib_kinds"])))]
    bw = TrussBridge(sb, a, direction, deck_z, span, width, depth, kind, rng, g,
                     material=ctx.steel(), density=1.0, density2=1.0,
                     panel_min=p.get("rib_panel", [2.8, 3.4])[0],
                     panel_max=p.get("rib_panel", [2.8, 3.4])[1])
    bw.build()
    stats.deep_trusses += 1
    stats.truss_depths.append(round(depth, 3))
    _split_group_beams(sb, g, p["split"])
    # corbel bearings at both ends (anchor the truss into the block faces)
    corbel_size = ((1.0, width + 0.8, 0.9) if abs(direction[0]) >= abs(direction[1])
                   else (width + 0.8, 1.0, 0.9))
    sb.add_block((fa[0], fa[1], deck_z + 0.45), corbel_size, "concrete",
                 ["rib", "corbel"], own_a)
    sb.add_block((fb[0], fb[1], deck_z + 0.45), corbel_size, "concrete",
                 ["rib", "corbel"], own_b)
    # end tie rods back to the blocks above the deck
    if ctx.roll("secondary"):
        end_l = bw.W(0.0, -width / 2.0, 0.0)
        end_r = bw.W(span, -width / 2.0, 0.0)
        sb.add_beam((end_l[0], end_l[1], deck_z + 2.0), end_l, "ROD30",
                    ctx.steel(), ["secondary", "rib", "tie"], g)
        sb.add_beam((end_r[0], end_r[1], deck_z + 2.0), end_r, "ROD30",
                    ctx.steel(), ["secondary", "rib", "tie"], g)
    return g


# ------------------------------------------------------------ fault-spine

def build_fault_spine(ctx):
    """Two asymmetric rows of stepped inhabited blocks across a canyon."""
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    stats = V2Stats()
    gap = rng.uniform(*p["gap"])
    canyon = []  # south row (tall), north row (lower), facing each other
    for row in (0, 1):
        lo, hi = p["blocks_per_row"]
        nb = int(rng.integers(lo, hi + 1))
        storeys_lo, storeys_hi = p["storeys_south"] if row == 0 else p["storeys_north"]
        canyon_side = -1 if row == 0 else 1
        row_gap = rng.uniform(*p["row_gap"])
        ws = [rng.uniform(*p["block_w"]) for _ in range(nb)]
        total = sum(ws) + (nb - 1) * row_gap + 2.0 * p["jitter"]
        x = -total / 2.0
        blks = []
        for i in range(nb):
            w = ws[i]
            d = rng.uniform(*p["block_d"])
            x += w / 2.0 + rng.uniform(-p["jitter"], p["jitter"])
            y = (d / 2.0 + gap / 2.0) * (1 if row == 0 else -1)
            storeys = int(rng.integers(storeys_lo, storeys_hi + 1))
            gid, info = build_block(ctx, x, y, w, d, storeys,
                                    rng.uniform(*p["floor_h"]), 10 * row + i,
                                    stats, canyon_side=canyon_side,
                                    setback_stacks=int(rng.integers(1, p["setback_stacks"] + 1)),
                                    glass_rate=p.get("glass_rate", 0.1))
            info.update({"group": gid, "canyon_side": canyon_side,
                         "i": i, "row": row})
            blks.append(info)
            x += w / 2.0 + row_gap
        canyon.append(blks)

    south, north = canyon

    # ---- deep truss ribs across the canyon, at several levels
    rib_levels = p["rib_levels"]
    for i in range(min(len(south), len(north))):
        j = min(max(i + int(rng.integers(-1, 2)), 0), len(north) - 1)
        ta, tb = south[i], north[j]
        for level in range(rib_levels):
            if rng.random() < 0.22:
                continue
            ns, nn = len(ta["floors"]), len(tb["floors"])
            k = int((0.42 + 0.2 * level) * (min(ns, nn) - 2))
            deck_z = min(ta["floors"][k], tb["floors"][k])
            fa = (ta["bx"], ta["by"] - ta["d"] / 2.0)
            fb = (tb["bx"], tb["by"] + tb["d"] / 2.0)
            deep_rib(ctx, stats, fa, fb, deck_z, rng.uniform(*p["rib_depth"]),
                     rng.uniform(*p["rib_width"]), ta["group"], tb["group"])

    # ---- huge cantilevers from the canyon rims
    def _cant(blk, into_canyon):
        n = len(blk["floors"])
        z = blk["floors"][int(0.55 * n)]
        w = rng.uniform(*p["cant_w"])
        if into_canyon:
            avail = gap - 2.0
            L = min(rng.uniform(*p["cant_len"]), avail * 0.8)
            face_xy = (blk["bx"], blk["by"] - blk["d"] / 2.0)
            outward = (0.0, -1.0)
        else:
            L = rng.uniform(10.0, 22.0)
            face_xy = (blk["bx"], blk["by"] + blk["d"] / 2.0)
            outward = (0.0, 1.0)
        back = min(6.0, blk["d"] / 2.0 - 2.0)
        build_cantilever(ctx, stats,
                         {"bx": blk["bx"], "by": blk["by"], "face_xy": face_xy,
                          "outward": outward, "z": z, "w": w, "L": max(L, 6.0),
                          "depth": rng.uniform(*p["cant_depth"]), "back": back},
                         stats.cantilever_groups + 1)
    for q, blk in enumerate(south):
        if q % max(1, len(south) // p["cantilevers"]) == 0 and q < p["cantilevers"]:
            _cant(blk, True)
    for q, blk in enumerate(north):
        if q % max(1, len(north) // max(1, p["cantilevers"] // 2)) == 0 \
                and q < max(1, p["cantilevers"] // 2):
            _cant(blk, False)

    # ---- draped cable nets across the canyon between facing roofs
    gnet = sb.group("canyon-nets")
    for i in range(min(len(south), len(north))):
        ta, tb = south[i], north[i]
        a_y = ta["ty"] - ta["td"] / 2.0
        b_y = tb["ty"] + tb["td"] / 2.0
        for xoff in (-3.0, 3.0):
            a = (ta["tx"] + xoff, a_y, ta["roof"] + 0.06)
            b = (tb["tx"] + xoff, b_y, tb["roof"] + 0.06)
            mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0,
                   min(a[2], b[2]) * 0.55)
            _beam_split(sb, a, mid, p["split"], "ROD30", ctx.steel(),
                        ["secondary", "net", "cable"], gnet)
            _beam_split(sb, mid, b, p["split"], "ROD30", ctx.steel(),
                        ["secondary", "net", "cable"], gnet)

    # ---- ground-level pipe rack along the canyon floor
    xmin = min(b["bx"] - b["w"] / 2.0 for b in south + north)
    xmax = max(b["bx"] + b["w"] / 2.0 for b in south + north)
    gpr = sb.group("canyon-pipe")
    for xx in np.arange(xmin, xmax, 6.0):
        if rng.random() < 0.9:
            sb.add_beam((xx, 0.0, 0.3), (xx, 0.0, 2.7), "TUBE140",
                        ctx.steel(), ["secondary", "canyon", "post"], gpr)
    for (zoff, prof) in ((2.2, "TUBE90"), (2.55, "TUBE90"), (2.9, "TUBE50")):
        if rng.random() < 0.95:
            _beam_split(sb, (xmin, 0.0, zoff), (xmax, 0.0, zoff), p["split"],
                        prof, ctx.paint(), ["secondary", "canyon", "pipe"], gpr)
    _ground_apron(ctx)
    return _finalize(ctx, stats)


# ------------------------------------------------------- suspended-delta

def _build_buttress(ctx, bx, by, wb, h_b, idx, ux=1.0, uy=0.0, tier_ends=None):
    """A sparse irregular buttress: corner columns, lattice faces, mast.

    ``tier_ends`` lists (end_offset, half_width, deck_z) for every deck tier
    that lands at this buttress; a pair of transfer columns rises for each,
    standing just outside the face the decks meet, so the deck ends can tie
    into the frame instead of hanging from stays alone.  Returns the group
    id, the mast top and the inboard face origin.
    """
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    g = sb.group(f"buttress-{idx:02d}")
    sb.add_block((bx, by, 0.8), (wb + 2.5, wb + 2.5, 1.6), "concrete",
                 ["buttress", "plinth"], g)
    hw = wb / 2.0
    corners = [(bx - hw, by - hw), (bx + hw, by - hw), (bx + hw, by + hw), (bx - hw, by + hw)]
    for (cx, cy) in corners:
        _beam_split(sb, (cx, cy, 1.6), (cx, cy, h_b), p["split"], "BOX350",
                    ctx.steel(), ["primary", "buttress", "column"], g)
    for (x0, y0, ux2, uy2) in [(bx - hw, by - hw, 1.0, 0.0), (bx + hw, by + hw, -1.0, 0.0),
                               (bx - hw, by + hw, 0.0, -1.0), (bx + hw, by - hw, 0.0, 1.0)]:
        lattice_face(sb, ctx, g, x0, y0, 1.6, ux2, uy2, wb, h_b - 1.6,
                     p["pitch"], p["split"], ["secondary", "buttress", "lattice"],
                     "L70", diag_rate=p.get("diag_rate", 0.06),
                     splice_rate=p.get("splice_rate", 0.05))
    for (a, b) in [(corners[0], corners[2]), (corners[1], corners[3])]:
        sb.add_beam((a[0], a[1], h_b), (b[0], b[1], h_b), "I450",
                    ctx.steel(), ["primary", "buttress", "cap"], g)
    # purlins along the cap edges, seated on the corner-column tops
    if ctx.roll("secondary"):
        for yedge in (by - hw, by + hw):
            sb.add_beam((bx - hw, yedge, h_b + 0.25), (bx + hw, yedge, h_b + 0.25),
                        "I240", ctx.steel(), ["secondary", "buttress", "purlin"], g)
            if rng.random() < 0.7:
                sb.add_detail_at("rivet_row", (bx, yedge, h_b + 0.25), (1, 0, 0),
                                 (0, 0, 1), [0.8, 0.12, 0.12], ctx.steel(), g)
    # transfer columns for the deck tier ends
    fx, fy = bx - ux * hw, by - uy * hw   # inboard face center
    px, py = -uy, ux                       # perpendicular (along the face)
    if tier_ends:
        for (off, half_w, z) in tier_ends:
            for sgn in (-1.0, 1.0):
                cx = fx + px * sgn * half_w - ux * off
                cy = fy + py * sgn * half_w - uy * off
                _beam_split(sb, (cx, cy, 1.6), (cx, cy, z), p["split"], "BOX350",
                            ctx.steel(), ["primary", "buttress", "transfer"], g)
                # raker back to the plinth face: the ground path for columns
                # standing out in the void
                _beam_split(sb, (cx, cy, z), (fx, fy, 1.6), p["split"], "C250",
                            ctx.steel(), ["primary", "buttress", "raker"], g)
    mast_h = rng.uniform(*p.get("mast_h", [10.0, 16.0]))
    _beam_split(sb, (bx, by, h_b), (bx, by, h_b + mast_h), p["split"], "TUBE300",
                ctx.steel(), ["primary", "buttress", "mast"], g)
    # orange light cluster on the cap
    if ctx.roll("detail"):
        for _ in range(rng.integers(2, 4)):
            lx = bx + rng.uniform(-hw + 0.5, hw - 0.5)
            ly = by + rng.uniform(-hw + 0.5, hw - 0.5)
            sb.add_detail_at("light", (lx, ly, h_b + 0.9), (1, 0, 0), (0, 0, 1),
                             [0.35, 0.35, 0.35], "accent", g)
    return g, (bx, by, h_b + mast_h)


def _build_tier(ctx, stats, origin, direction, deck_z, span, deck_w, depth,
                idx, kind, glass=True):
    """One inhabited layered deck: deep side trusses + open floors inside."""
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    g = sb.group(f"deck-{idx:02d}")
    bw = TrussBridge(sb, origin, direction, deck_z, span, deck_w, depth, kind,
                     rng, g, material=ctx.steel(), density=1.0, density2=1.0,
                     panel_min=p["deck_panel"][0], panel_max=p["deck_panel"][1],
                     catwalk=True)
    bw.build()
    stats.deep_trusses += 1
    stats.truss_depths.append(round(depth, 3))
    pitch, split = p["pitch"], p["split"]
    hw = deck_w / 2.0

    def P(s, t):
        w = bw.W(s, -hw + t, 0.0)
        return (w[0], w[1])

    for fz in p["floors_in"]:
        keep = rng.random() < p.get("slab_keep", 0.42)
        stats.floors(keep)
        zf = deck_z + fz
        # edge stringers, split at the truss panel joints so the inhabited
        # floor system hangs from the truss verticals
        for side in (-hw, hw):
            for k in range(bw.panels):
                sb.add_beam(bw.W(k * bw.panel, side, fz),
                            bw.W((k + 1) * bw.panel, side, fz), "C160",
                            ctx.steel(), ["secondary", "deck", "stringer"], g)
                if rng.random() < 0.5:
                    sb.add_detail_at("rivet_row", bw.W(k * bw.panel, side, fz),
                                     (1, 0, 0), (0, 0, 1), [0.8, 0.12, 0.12],
                                     ctx.steel(), g)
        for xk in (0.0, span):
            sb.add_beam(bw.W(xk, -hw, fz), bw.W(xk, hw, fz), "I240",
                        ctx.steel(), ["secondary", "deck", "beam"], g)
        _lattice_floor_mapped(sb, ctx, g, P, span, deck_w, zf, pitch, split,
                              ["secondary", "deck", "joist"])
        if keep:
            for s in range(2):
                bw.block((span * (2 * s + 1) / 4.0, 0.0, fz + 0.15),
                         (span / 2.0 - 0.4, deck_w - 0.6, 0.28), "concrete",
                         ["deck", "slab"])
        # railing along both deck edges at this inhabited level
        if ctx.roll("detail"):
            for lx in np.arange(1.2, span - 0.5, 1.7):
                for side in (-hw, hw):
                    if rng.random() < 0.85:
                        sb.add_detail("railing",
                                      frame(bw.W(lx, side, fz + 1.0),
                                            bw._dir((1.0, 0.0, 0.0)),
                                            bw._dir((0.0, 0.0, 1.0))),
                                      [1.7, 0.08, 1.1], ctx.steel(), g)
    # TrussBridge emits span-length handrails and width-length crosses;
    # split them so member-proximity queries stay local on large scenes
    _split_group_beams(sb, g, split)

    # one narrow glazed bay at the outer end (well under the glass cap)
    if glass and rng.random() < p.get("glass_rate", 0.22):
        fz0 = p["floors_in"][0]
        xk = span - 1.0
        side = hw - 1.6
        sb.add_block(bw.W(xk, side, fz0 + 1.5), (2.2, 1.8, 2.8), "glass",
                     ["deck", "glass"], g,
                     yaw=math.atan2(direction[1], direction[0]))
        stats.glass_blocks += 1
        for ty in (side - 0.9, side + 0.9):
            sb.add_beam(bw.W(xk, ty, fz0), bw.W(xk, ty, fz0 + 3.0), "TUBE50",
                        ctx.steel(), ["secondary", "deck", "mullion"], g)
    if rng.random() < 0.3:
        sb.add_detail_at("light", bw.W(span - 1.5, hw - 1.2, depth - 0.4),
                         (1, 0, 0), (0, 0, 1), [0.35, 0.35, 0.35], "accent", g)
    return bw


def _hub_tower(ctx, tw, z0, z1):
    """A lattice tower rising from the hub to above the top deck tier."""
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    g = sb.group("hub-tower")
    hw = tw / 2.0
    corners = [(-hw, -hw), (hw, -hw), (hw, hw), (-hw, hw)]
    for (cx, cy) in corners:
        _beam_split(sb, (cx, cy, z0), (cx, cy, z1), p["split"], "BOX500",
                    ctx.steel(), ["primary", "hub", "column"], g)
    for (x0, y0, ux, uy) in [(-hw, -hw, 1.0, 0.0), (hw, hw, -1.0, 0.0),
                             (-hw, hw, 0.0, -1.0), (hw, -hw, 0.0, 1.0)]:
        lattice_face(sb, ctx, g, x0, y0, z0, ux, uy, tw, z1 - z0,
                     p["pitch"], p["split"], ["secondary", "hub", "lattice"], "L70",
                     diag_rate=p.get("diag_rate", 0.06) * 0.5,
                     splice_rate=p.get("splice_rate", 0.05))
    for (a, b) in [(corners[0], corners[2]), (corners[1], corners[3])]:
        sb.add_beam((a[0], a[1], z1), (b[0], b[1], z1), "I450",
                    ctx.steel(), ["primary", "hub", "cap"], g)
    if ctx.roll("detail"):
        for _ in range(rng.integers(3, 5)):
            lx, ly = rng.uniform(-hw + 0.4, hw - 0.4), rng.uniform(-hw + 0.4, hw - 0.4)
            sb.add_detail_at("light", (lx, ly, z1 + 0.7), (1, 0, 0), (0, 0, 1),
                             [0.35, 0.35, 0.35], "accent", g)
    return g, (0.0, 0.0, z1)


def build_suspended_delta(ctx):
    """A layered inhabited bridge megastructure radiating from a hub."""
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    stats = V2Stats()
    nb = p["branches"]
    nt = p["tiers"]
    skip_tiers = p.get("skip_tiers", 0)
    hub_w = rng.uniform(*p["hub_w"])
    pitch, split = p["pitch"], p["split"]
    deck_z0 = p["deck_z0"]
    tier_h = p["tier_h"]
    depth_max = p["truss_depth"][1]

    # ---- hub: stacked irregular blocks with lattice faces
    hw2 = hub_w / 2.0
    sb.add_block((0.0, 0.0, 0.8), (hub_w + 5.0, hub_w + 5.0, 1.6), "concrete",
                 ["hub", "plinth"], sb.group("hub-01"))
    hub_blocks = []
    for k, (sw, sd, sh) in enumerate(p["hub_blocks"]):
        g = sb.group(f"hub-{k + 2:02d}")
        jx, jy = rng.uniform(-1.5, 1.5), rng.uniform(-1.5, 1.5)
        zbase = 1.6 + sum(prev[2] for prev in p["hub_blocks"][:k])
        sb.add_block((jx, jy, zbase + sh / 2.0), (sw * hub_w, sd * hub_w, sh),
                     "concrete", ["hub", "core"], g)
        for (cx, cy) in [(jx - sw * hub_w / 2.0, jy - sd * hub_w / 2.0),
                         (jx + sw * hub_w / 2.0, jy - sd * hub_w / 2.0),
                         (jx + sw * hub_w / 2.0, jy + sd * hub_w / 2.0),
                         (jx - sw * hub_w / 2.0, jy + sd * hub_w / 2.0)]:
            _beam_split(sb, (cx, cy, zbase), (cx, cy, zbase + sh), split,
                        "BOX500", ctx.steel(), ["primary", "hub", "column"], g)
        for (x0, y0, ux2, uy2, wf) in [
                (jx - sw * hub_w / 2.0, jy - sd * hub_w / 2.0, 1.0, 0.0, sw * hub_w),
                (jx + sw * hub_w / 2.0, jy + sd * hub_w / 2.0, -1.0, 0.0, sw * hub_w),
                (jx - sw * hub_w / 2.0, jy + sd * hub_w / 2.0, 0.0, -1.0, sd * hub_w),
                (jx + sw * hub_w / 2.0, jy - sd * hub_w / 2.0, 0.0, 1.0, sd * hub_w)]:
            lattice_face(sb, ctx, g, x0, y0, zbase, ux2, uy2, wf, sh,
                         pitch, split, ["secondary", "hub", "lattice"], "L70",
                         diag_rate=p.get("diag_rate", 0.06),
                         splice_rate=p.get("splice_rate", 0.05))
        hub_blocks.append({"g": g, "x": jx, "y": jy,
                           "w": sw * hub_w, "d": sd * hub_w,
                           "z0": zbase, "z1": zbase + sh})
    hub_top = hub_blocks[-1]["z1"]

    # ---- hub tower rising above the top deck tier, then a short mast
    top_deck = deck_z0 + (nt - 1) * tier_h
    tower_top_z = top_deck + depth_max + 8.0
    tw = p.get("tower_w", 0.32) * hub_w
    gt, tower_top = _hub_tower(ctx, tw, hub_top, tower_top_z)
    gm = sb.group("hub-mast")
    _beam_split(sb, (0.0, 0.0, tower_top_z), (0.0, 0.0, tower_top_z + 14.0),
                split, "TUBE300", ctx.steel(), ["primary", "hub", "mast"], gm)
    mast_top = (0.0, 0.0, tower_top_z + 14.0)
    g_stays = sb.group("stays")
    g_hubstays = sb.group("hub-stays")
    g_nets = sb.group("cable-nets")

    # ---- branches: radiating tiers of inhabited deck, buttress at each end
    mast_tops = []
    for i in range(nb):
        ang = i * 2.0 * math.pi / nb + rng.uniform(-0.14, 0.14)
        ux, uy = math.cos(ang), math.sin(ang)
        L = rng.uniform(*p["branch_len"])
        bx, by = ux * L, uy * L
        wb = rng.uniform(*p["buttress_w"])
        j_skip = int(rng.integers(nt)) if skip_tiers > 0 else nt

        # 1. decide the tier geometry up front.  Starts, ends and widths come
        # from permuted offset sets, so per-branch variety is guaranteed
        # (>= 8 m of start/end spread, >= 20% of width spread) instead of
        # just likely.  The sets are scaled per branch so the shortest tier
        # keeps at least 30 m of span at every scale.
        max_avail = max(0.0, (L - wb / 2.0 - 1.0) - (hw2 + 9.0) - 30.0)
        off_scale = min(1.0, max_avail / 48.0)
        r0_offs = rng.permutation(np.arange(5) * 4.0) * off_scale   # 0..16 m
        end_offs = rng.permutation(np.arange(5) * 8.0) * off_scale  # 0..32 m
        w_facts = rng.permutation(np.array([0.80, 0.90, 1.00, 1.10, 1.20]))
        w_base = rng.uniform(*p["deck_w"])
        tier_geos = []
        k_built = 0
        for j in range(nt):
            if j == j_skip:
                tier_geos.append(None)
                continue
            deck_z = deck_z0 + j * tier_h
            r0 = hw2 + 9.0 + float(r0_offs[k_built])
            end_off = float(end_offs[k_built])
            deck_w = w_base * float(w_facts[k_built])
            k_built += 1
            depth = min(rng.uniform(*p["truss_depth"]), tier_h - 2.0)
            kind = p["deck_kinds"][int(rng.integers(len(p["deck_kinds"])))]
            tier_geos.append({"deck_z": deck_z, "r0": r0, "end_off": end_off,
                              "deck_w": deck_w, "hw": deck_w / 2.0, "depth": depth,
                              "kind": kind})
        built = [g2 for g2 in tier_geos if g2 is not None]
        span_base = L - wb / 2.0 - 1.0

        # 2. buttress tall enough to carry the top tier, with transfer columns
        h_b = top_deck + max(g2["depth"] for g2 in built) + rng.uniform(*p["buttress_over"])
        bg, mtop = _build_buttress(ctx, bx, by, wb, h_b, i + 1, ux, uy,
                                   tier_ends=[(g2["end_off"], g2["hw"], g2["deck_z"])
                                              for g2 in built])
        mast_tops.append(mtop)
        fx, fy = bx - ux * wb / 2.0, by - uy * wb / 2.0   # inboard face center
        px, py = -uy, ux

        # 3. build the tiers, tie each end into the frames
        for j, geo in enumerate(tier_geos):
            if geo is None:
                continue
            span = span_base - geo["r0"] - geo["end_off"]
            bw = _build_tier(ctx, stats, (ux * geo["r0"], uy * geo["r0"], geo["deck_z"]),
                             (ux, uy), geo["deck_z"], span, geo["deck_w"],
                             geo["depth"], i * 10 + j, geo["kind"])
            # ---- outer end: struts and knees into the buttress transfer columns
            for sgn in (-1.0, 1.0):
                end = bw.W(span, sgn * geo["hw"], 0.0)
                top = bw.W(span, sgn * geo["hw"], geo["depth"])
                col = (fx + px * sgn * geo["hw"] - ux * geo["end_off"],
                       fy + py * sgn * geo["hw"] - uy * geo["end_off"])
                _beam_split(sb, (end[0], end[1], end[2]), (col[0], col[1], geo["deck_z"]),
                            split, "I240", ctx.steel(),
                            ["secondary", "deck", "strut"], bg)
                _beam_split(sb, (top[0], top[1], top[2]), (col[0], col[1], geo["deck_z"]),
                            split, "C180", ctx.steel(),
                            ["secondary", "deck", "knee"], bg)
            # ---- inner end: struts into the hub tower / hub block columns
            hk = next((hb for hb in hub_blocks
                       if hb["z0"] - 0.2 <= geo["deck_z"] <= hb["z1"] + 0.2), None)
            for sgn in (-1.0, 1.0):
                end = bw.W(0.0, sgn * geo["hw"], 0.0)
                if hk is not None:
                    tx = hk["x"] + (hk["w"] / 2.0) * (1.0 if ux > 0 else -1.0)
                    ty = hk["y"] + (hk["d"] / 2.0) * (1.0 if uy > 0 else -1.0)
                    tgt_g = hk["g"]
                else:
                    tx = (tw / 2.0) * (1.0 if ux > 0 else -1.0)
                    ty = (tw / 2.0) * (1.0 if uy > 0 else -1.0)
                    tgt_g = gt
                _beam_split(sb, (end[0], end[1], end[2]), (tx, ty, geo["deck_z"]),
                            split, "I240", ctx.steel(),
                            ["secondary", "deck", "strut"], tgt_g)
            # stays from the buttress mast to the outer deck top chord
            if j % 2 == 0:
                for k in range(0, bw.panels - 1, 4):
                    node = bw.W(k * bw.panel, -geo["hw"], geo["depth"])
                    _beam_split(sb, mtop, (node[0], node[1], node[2]),
                                split, "ROD30", ctx.steel(),
                                ["secondary", "deck", "cable"], g_stays)
                    node = bw.W(k * bw.panel, geo["hw"], geo["depth"])
                    _beam_split(sb, mtop, (node[0], node[1], node[2]),
                                split, "ROD30", ctx.steel(),
                                ["secondary", "deck", "cable"], g_stays)
            # hub stays from the tower top to the inner top chords
            for sgn in (-1.0, 1.0):
                node = bw.W(0.0, sgn * geo["hw"], geo["depth"])
                _beam_split(sb, tower_top, (node[0], node[1], node[2]),
                            split, "ROD30", ctx.steel(),
                            ["secondary", "deck", "cable"], g_hubstays)

        # lateral mid-span buttress beside the longest branches
        if L > 0.9 * p["branch_len"][1] and p.get("buttress_extra", 0) > 0 \
                and i < p["buttress_extra"]:
            mx = ux * L * 0.55 - uy * (p["deck_w"][1] + 4.0)
            my = uy * L * 0.55 + ux * (p["deck_w"][1] + 4.0)
            _build_buttress(ctx, mx, my, rng.uniform(*p["buttress_w"]),
                            deck_z0 + rng.uniform(6.0, 14.0), 90 + i + 1, ux, uy)

    # ---- cable nets between adjacent buttress masts (draped in the middle)
    for i in range(nb):
        a = mast_tops[i]
        b = mast_tops[(i + 1) % nb]
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0,
               (a[2] + b[2]) / 2.0 - rng.uniform(6.0, 10.0))
        _beam_split(sb, a, mid, split, "ROD30", ctx.steel(),
                    ["secondary", "net", "cable"], g_nets)
        _beam_split(sb, mid, b, split, "ROD30", ctx.steel(),
                    ["secondary", "net", "cable"], g_nets)

    # ---- huge cantilevers jutting from the hub blocks between branches
    hb = hub_blocks[1] if len(hub_blocks) > 1 else hub_blocks[0]
    for c in range(p["cantilevers"]):
        ang = (c + 0.5) * 2.0 * math.pi / nb + rng.uniform(-0.12, 0.12)
        ux, uy = math.cos(ang), math.sin(ang)
        if abs(ux) >= abs(uy):
            px = hb["x"] + (hb["w"] / 2.0) * (1.0 if ux > 0 else -1.0)
            off = max(-hb["d"] / 2.0 + 1.5, min(hb["d"] / 2.0 - 1.5,
                                                (uy / abs(ux)) * hb["w"] / 2.0))
            py = hb["y"] + off
            back = min(5.0, hb["w"] / 2.0 - 1.5)
        else:
            py = hb["y"] + (hb["d"] / 2.0) * (1.0 if uy > 0 else -1.0)
            off = max(-hb["w"] / 2.0 + 1.5, min(hb["w"] / 2.0 - 1.5,
                                                (ux / abs(uy)) * hb["d"] / 2.0))
            px = hb["x"] + off
            back = min(5.0, hb["d"] / 2.0 - 1.5)
        build_cantilever(ctx, stats,
                         {"bx": hb["x"], "by": hb["y"], "face_xy": (px, py),
                          "outward": (ux, uy), "z": rng.uniform(hb["z0"] + 3.0, hb["z1"] - 2.0),
                          "w": rng.uniform(5.0, 8.0), "L": rng.uniform(12.0, 20.0),
                          "depth": rng.uniform(*p["cant_depth"]), "back": back},
                         stats.cantilever_groups + 1)
    _ground_apron(ctx)
    return _finalize(ctx, stats)


def _split_group_beams(sb, gid, maxlen):
    """Split every beam of ``gid`` longer than ``maxlen`` into segments.

    Geometry is unchanged (segments share endpoints and keep profile,
    material, tags, roll); only the instance count grows, and the scene
    validator stays fast on dense scenes.  Beam ids are renumbered later
    in _finalize.
    """
    idxs = [i for i, b in enumerate(sb.beams)
            if b["group"] == gid and np.linalg.norm(np.subtract(b["b"], b["a"])) > maxlen]
    for i in reversed(idxs):
        b = sb.beams[i]
        _beam_split(sb, b["a"], b["b"], maxlen, b["profile"], b["material"],
                    b["tags"], b["group"], b["roll"])
        del sb.beams[i]


def _ground_apron(ctx, margin=18.0, tile=24.0):
    """A site apron of concrete tiles: ground contact, cast shadows, a site
    edge.  The tile under the site centre carries ``["site", "ground"]``
    (exactly one such block, top at z = 0, as the render-ready tests
    require); the rest are ``["site", "apron"]``.  Tiling keeps every
    block small, which keeps the scene validator's block-proximity queries
    local on megastructure-size scenes.
    """
    sb = ctx.sb
    mn, mx = sb.bounds(pad=0.0)
    min_x, min_y = float(mn[0]) - margin, float(mn[1]) - margin
    max_x, max_y = float(mx[0]) + margin, float(mx[1]) + margin
    nx = max(1, int(math.ceil((max_x - min_x) / tile)))
    ny = max(1, int(math.ceil((max_y - min_y) / tile)))
    cx, cy = (min_x + max_x) / 2.0, (min_y + max_y) / 2.0
    i0 = min(nx - 1, int((cx - min_x) * nx / (max_x - min_x)))
    j0 = min(ny - 1, int((cy - min_y) * ny / (max_y - min_y)))
    for i in range(nx):
        for j in range(ny):
            x0 = min_x + (max_x - min_x) * i / nx
            x1 = min_x + (max_x - min_x) * (i + 1) / nx
            y0 = min_y + (max_y - min_y) * j / ny
            y1 = min_y + (max_y - min_y) * (j + 1) / ny
            tags = ["site", "ground"] if (i == i0 and j == j0) \
                else ["site", "apron"]
            sb.add_block(((x0 + x1) / 2.0, (y0 + y1) / 2.0, -0.8),
                         (x1 - x0, y1 - y0, 1.6), "concrete", tags, 0)


def _finalize(ctx, stats):
    """Attach the v2 numeric guarantees to the scene stats."""
    sb = ctx.sb
    scene = sb.scene(V2_VERSION)
    beams = scene["beams"]
    blocks = scene["blocks"]
    n = len(beams)
    nsec = sum(1 for b in beams if "secondary" in (b.get("tags") or ()))
    for i, b in enumerate(scene["beams"]):
        b["id"] = i
    scene["stats"].update({
        "secondary_beams": nsec,
        "secondary_frac": round(nsec / n, 4) if n else 0.0,
        "glass_blocks": stats.glass_blocks,
        "glass_frac": round(stats.glass_blocks / len(blocks), 4) if blocks else 0.0,
        "floor_slots": stats.floor_slots,
        "floor_kept": stats.floor_kept,
        "floor_omission": round(1.0 - stats.floor_kept / stats.floor_slots, 4)
        if stats.floor_slots else 0.0,
        "cantilever_groups": stats.cantilever_groups,
        "setback_groups": stats.setback_groups,
        "deep_trusses": stats.deep_trusses,
        "truss_depth_min": min(stats.truss_depths) if stats.truss_depths else 0.0,
        "truss_depth_max": max(stats.truss_depths) if stats.truss_depths else 0.0,
        "lattice_pitch": ctx.p.get("pitch", 0.0),
    })
    return scene


def build(ctx):
    """Dispatch to the v2 structure builders by preset."""
    kind = ctx.p.get("v2")
    if kind == "fault-spine":
        return build_fault_spine(ctx)
    if kind == "suspended-delta":
        return build_suspended_delta(ctx)
    raise ValueError(f"unknown v2 structure {kind!r}")
