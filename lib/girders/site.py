"""Site layout and megastructure construction: towers, bridges, gantries, detail.

Everything is seeded and deterministic.  The hierarchy is explicit:
primary framing (columns, spandrels, bracing, truss chords/webs), then
secondary members (joists, purlins, stringers, pipes, stairs), then small
instanced details (bolt plates, rivets, railings, ladders, vents, lights).
Each level has its own density in params["density"].
"""

from __future__ import annotations

import math

import numpy as np

from .scene import SceneBuilder, frame, normalize
from .trusses import TrussBridge


class Ctx:
    """Shared generation context: builder, rng, params, ruin flag, helpers."""

    RUIN_DROP = {"primary": 0.92, "secondary": 0.55, "detail": 0.5}

    def __init__(self, sb, params, rng):
        self.sb = sb
        self.p = params
        self.rng = rng
        self.ruin = params.get("ruin", 0.0) > 0.5

    def roll(self, key):
        """Probability gate for candidate members at a hierarchy level."""
        prob = self.p["density"].get(key, 1.0)
        if self.ruin:
            prob *= self.RUIN_DROP.get(key, 1.0)
        return self.rng.random() < prob

    def steel(self, rust_bias=1.0):
        """Material for a steel member (ruin scenes rust heavily)."""
        if self.ruin and self.rng.random() < 0.55 * rust_bias:
            return "rust"
        return "steel"

    def paint(self):
        if self.ruin and self.rng.random() < 0.6:
            return "rust"
        return "steel_painted"


# ------------------------------------------------------------------- towers

def floor_schedule(storeys, floor_h, rng):
    z = [floor_h * rng.uniform(0.9, 1.1)]
    for _ in range(storeys - 1):
        z.append(z[-1] + floor_h * rng.uniform(0.9, 1.1))
    return z


def build_tower(ctx, t):
    """One tower: plinth, core, slabs, perimeter frame, bracing, roof, details."""
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    x, y = t["x"], t["y"]
    sx, sy = t["sx"], t["sy"]
    g = t["group"]
    floors = t["floors"]
    n = len(floors)
    plinth_top = 1.6
    roof = floors[-1]
    cf = t["core_frac"]
    core_hx, core_hy = sx * cf / 2.0, sy * cf / 2.0

    # ---- plinth (grounded concrete base)
    sb.add_block((x, y, plinth_top / 2.0), (sx + 5.0, sy + 5.0, plinth_top),
                 "concrete", ["tower", "plinth"], g)

    # ---- core: stacked concrete segments (~5 floors each)
    for s in range(0, n, 5):
        k1 = min(n - 1, s + 4)
        z0 = plinth_top if s == 0 else floors[s - 1]
        z1 = floors[k1] + 0.3
        if z1 > z0 + 0.5:
            sb.add_block((x, y, (z0 + z1) / 2.0), (sx * cf, sy * cf, z1 - z0),
                         "concrete", ["tower", "core"], g)

    # ---- floor slabs (the top one occasionally collapses on ruins)
    top_slab_ok = True
    for k in range(n):
        if ctx.ruin and k == n - 1 and rng.random() < 0.3:
            top_slab_ok = False
            continue
        sb.add_block((x, y, floors[k] + 0.18), (sx + 0.8, sy + 0.8, 0.36),
                     "concrete", ["tower", "slab"], g)
    t["slab_ok"] = top_slab_ok

    # ---- perimeter column grid
    nbx, nby = t["bays"]
    xs = [x - sx / 2.0 + sx * i / nbx for i in range(nbx + 1)]
    ys = [y - sy / 2.0 + sy * i / nby for i in range(nby + 1)]
    col_p = "BOX500" if sx >= 15.0 else "BOX350"
    cols = {}  # (ix, iy) -> list of z anchors per storey
    for iy in (0, nby):
        for ix in range(nbx + 1):
            cols[(ix, iy)] = True
    for ix in (0, nbx):
        for iy in range(1, nby):
            cols[(ix, iy)] = True
    for (ix, iy) in cols:
        cx, cy = xs[ix], ys[iy]
        z0 = plinth_top
        for k in range(n):
            z1 = floors[k]
            if ctx.roll("primary"):
                sb.add_beam((cx, cy, z0), (cx, cy, z1), col_p, ctx.steel(),
                            ["tower", "column"], g)
            z0 = z1

    # ---- spandrels along the four faces, per storey
    for k in range(n):
        z = floors[k]
        if not ctx.roll("primary"):
            continue
        for ix in range(nbx):
            sb.add_beam((xs[ix], ys[0], z), (xs[ix + 1], ys[0], z), "I450",
                        ctx.steel(), ["tower", "spandrel"], g)
            sb.add_beam((xs[ix], ys[nby], z), (xs[ix + 1], ys[nby], z), "I450",
                        ctx.steel(), ["tower", "spandrel"], g)
        for iy in range(nby):
            sb.add_beam((xs[0], ys[iy], z), (xs[0], ys[iy + 1], z), "I450",
                        ctx.steel(), ["tower", "spandrel"], g)
            sb.add_beam((xs[nbx], ys[iy], z), (xs[nbx], ys[iy + 1], z), "I450",
                        ctx.steel(), ["tower", "spandrel"], g)

    # ---- bracing: one pattern per face, on alternate storeys
    bracing_step = 1 if ctx.p.get("bracing_all") else 2
    for face, (pxs, pys, dirx, diry) in _faces(xs, ys, nbx, nby).items():
        if face not in t["bracing"]:
            continue
        pattern = t["bracing"][face]
        for k in range(0, n - 1, bracing_step):
            if not ctx.roll("primary"):
                continue
            z0, z1 = floors[k], floors[k + 1]
            for i in range(0, len(pxs) - 1, 2):
                a = (pxs[i], pys[i], z0)
                b = (pxs[i + 1], pys[i + 1], z0)
                c = (pxs[i], pys[i], z1)
                d = (pxs[i + 1], pys[i + 1], z1)
                if pattern == "x":
                    sb.add_beam(a, d, "L120", ctx.steel(), ["tower", "brace"], g)
                    sb.add_beam(b, c, "L120", ctx.steel(), ["tower", "brace"], g)
                elif pattern == "chevron":
                    m = ((pxs[i] + pxs[i + 1]) / 2.0, (pys[i] + pys[i + 1]) / 2.0, z1)
                    sb.add_beam(a, m, "L120", ctx.steel(), ["tower", "brace"], g)
                    sb.add_beam(b, m, "L120", ctx.steel(), ["tower", "brace"], g)
                elif pattern == "k":
                    m = ((pxs[i] + pxs[i + 1]) / 2.0, (pys[i] + pys[i + 1]) / 2.0, (z0 + z1) / 2.0)
                    sb.add_beam(a, m, "L120", ctx.steel(), ["tower", "brace"], g)
                    sb.add_beam(b, m, "L120", ctx.steel(), ["tower", "brace"], g)

    # ---- joists from core to perimeter columns, per floor
    for k in range(n):
        if not ctx.roll("secondary"):
            continue
        z = floors[k] + 0.18
        for (ix, iy) in cols:
            cx, cy = xs[ix], ys[iy]
            if ix in (0, nbx) and iy in (0, nby):
                continue  # corner columns tie back diagonally via the faces
            if ix == 0:
                tx, ty = x - core_hx, min(max(cy, y - core_hy), y + core_hy)
            elif ix == nbx:
                tx, ty = x + core_hx, min(max(cy, y - core_hy), y + core_hy)
            elif iy == 0:
                tx, ty = min(max(cx, x - core_hx), x + core_hx), y - core_hy
            else:
                tx, ty = min(max(cx, x - core_hx), x + core_hx), y + core_hy
            sb.add_beam((cx, cy, z), (tx, ty, z), "I240", ctx.steel(),
                        ["tower", "joist"], g)

    # ---- full secondary joist grid spanning face to face per floor
    if ctx.p.get("joist_grid"):
        jd = ctx.p.get("joist_density", 1)
        for k in range(1, n):
            if not ctx.roll("secondary"):
                continue
            z = floors[k] + 0.15
            for ix in range(1, nbx * jd):
                xx = xs[0] + (xs[-1] - xs[0]) * ix / (nbx * jd)
                if rng.random() < 0.9:
                    sb.add_beam((xx, ys[0], z), (xx, ys[nby], z), "I240",
                                ctx.steel(), ["tower", "joist"], g)
            for iy in range(1, nby * jd):
                yy = ys[0] + (ys[-1] - ys[0]) * iy / (nby * jd)
                if rng.random() < 0.9:
                    sb.add_beam((xs[0], yy, z), (xs[nbx], yy, z), "I240",
                                ctx.steel(), ["tower", "joist"], g)

    # ---- per-floor edge railings (instanced details)
    if ctx.p.get("railings"):
        for k in range(n):
            if not ctx.roll("detail"):
                continue
            z = floors[k] + 0.5
            for i in range(nbx):
                xm = (xs[i] + xs[i + 1]) / 2.0
                w = xs[i + 1] - xs[i]
                sb.add_detail_at("railing", (xm, ys[0] + 0.15, z), (1, 0, 0), (0, 0, 1),
                                 [w - 0.4, 0.08, 1.1], ctx.steel(), g)
                sb.add_detail_at("railing", (xm, ys[nby] - 0.15, z), (1, 0, 0), (0, 0, 1),
                                 [w - 0.4, 0.08, 1.1], ctx.steel(), g)
            for i in range(nby):
                ym = (ys[i] + ys[i + 1]) / 2.0
                w = ys[i + 1] - ys[i]
                sb.add_detail_at("railing", (xs[0] + 0.15, ym, z), (0, 1, 0), (0, 0, 1),
                                 [w - 0.4, 0.08, 1.1], ctx.steel(), g)
                sb.add_detail_at("railing", (xs[nbx] - 0.15, ym, z), (0, 1, 0), (0, 0, 1),
                                 [w - 0.4, 0.08, 1.1], ctx.steel(), g)

    # ---- glass infill panels on some faces
    for k in range(0, n - 1, 2):
        if not ctx.roll("secondary") or (ctx.ruin and rng.random() < 0.6):
            continue
        z0, z1 = floors[k], floors[k + 1]
        for i in range(nbx):
            if rng.random() < 0.6:
                cx = (xs[i] + xs[i + 1]) / 2.0
                sb.add_block((cx, ys[0] - 0.1, (z0 + z1) / 2.0),
                             (sx / nbx - 0.5, 0.08, z1 - z0 - 0.5), "glass",
                             ["tower", "glass"], g)
        # facade mullions and transoms on the glazed faces
        if ctx.p.get("mullions"):
            zm = (z0 + z1) / 2.0
            for face_y in (ys[0], ys[nby]):
                for i in range(nbx):
                    x0, x1 = xs[i], xs[i + 1]
                    for q in (1, 2):
                        if rng.random() < 0.8:
                            xm = x0 + (x1 - x0) * q / 3.0
                            sb.add_beam((xm, face_y, z0), (xm, face_y, z1), "TUBE50",
                                        ctx.steel(), ["tower", "mullion"], g)
                    if rng.random() < 0.7:
                        sb.add_beam((x0, face_y, zm), (x1, face_y, zm), "TUBE50",
                                    ctx.steel(), ["tower", "mullion"], g)

    # ---- roof: parapet, purlins, tank, vents, antenna
    _roof(ctx, t, xs, ys, roof, g)

    # ---- exterior stair
    _stair(ctx, t, g)

    # ---- ladders, pipes
    _ladders(ctx, t, g)
    _pipes(ctx, t, g, core_hx, core_hy)

    return t


def _faces(xs, ys, nbx, nby):
    return {
        "south": (xs, [ys[0]] * len(xs), 1, 0),
        "north": (xs, [ys[nby]] * len(xs), 1, 0),
        "west": ([xs[0]] * len(ys), ys, 0, 1),
        "east": ([xs[nbx]] * len(ys), ys, 0, 1),
    }


def _roof(ctx, t, xs, ys, roof, g):
    sb, p, rng = ctx.sb, ctx.p, ctx.rng
    x, y, sx, sy = t["x"], t["y"], t["sx"], t["sy"]
    # parapet posts, then the top rail around the edge
    if ctx.roll("secondary"):
        for ix in range(len(xs)):
            for (px, py) in ((xs[ix], ys[0]), (xs[ix], ys[-1])):
                sb.add_beam((px, py, roof), (px, py, roof + 1.0), "TUBE50",
                            ctx.steel(), ["tower", "parapet"], g)
        for iy in range(len(ys)):
            for (px, py) in ((xs[0], ys[iy]), (xs[-1], ys[iy])):
                sb.add_beam((px, py, roof), (px, py, roof + 1.0), "TUBE50",
                            ctx.steel(), ["tower", "parapet"], g)
        for i in range(len(xs) - 1):
            sb.add_beam((xs[i], ys[0], roof + 1.0), (xs[i + 1], ys[0], roof + 1.0),
                        "TUBE50", ctx.steel(), ["tower", "parapet"], g)
            sb.add_beam((xs[i], ys[-1], roof + 1.0), (xs[i + 1], ys[-1], roof + 1.0),
                        "TUBE50", ctx.steel(), ["tower", "parapet"], g)
        for i in range(len(ys) - 1):
            sb.add_beam((xs[0], ys[i], roof + 1.0), (xs[0], ys[i + 1], roof + 1.0),
                        "TUBE50", ctx.steel(), ["tower", "parapet"], g)
            sb.add_beam((xs[-1], ys[i], roof + 1.0), (xs[-1], ys[i + 1], roof + 1.0),
                        "TUBE50", ctx.steel(), ["tower", "parapet"], g)
    # purlins both ways (a full grid at roof_grid densities)
    if ctx.roll("secondary"):
        if ctx.p.get("roof_grid"):
            nxx = max(2, t["bays"][0] * 2)
            nyy = max(2, t["bays"][1] * 2)
        else:
            nxx, nyy = t["bays"][0], t["bays"][1]
        for k in range(1, nxx):
            xx = xs[0] + (xs[-1] - xs[0]) * k / nxx
            sb.add_beam((xx, ys[0], roof + 0.05), (xx, ys[-1], roof + 0.05),
                        "I240", ctx.steel(), ["tower", "purlin"], g)
        for k in range(1, nyy):
            yy = ys[0] + (ys[-1] - ys[0]) * k / nyy
            sb.add_beam((xs[0], yy, roof + 0.05), (xs[-1], yy, roof + 0.05),
                        "I240", ctx.steel(), ["tower", "purlin"], g)
    # water tank (skip / replace on some ruins; it rests on the roof slab)
    if t.get("slab_ok") and ctx.roll("primary") and not (ctx.ruin and rng.random() < 0.4):
        tw, th = rng.uniform(3.0, 4.5), rng.uniform(2.5, 4.0)
        sb.add_block((x + rng.uniform(-sx / 4.0, sx / 4.0),
                      y + rng.uniform(-sy / 4.0, sy / 4.0), roof + th / 2.0),
                     (tw, tw, th), "steel_painted", ["tower", "tank"], g)
    # vents and lights (vent bases snap to purlin crossings so they are supported)
    for _ in range(rng.integers(2, 5)):
        if t.get("slab_ok") and ctx.roll("detail"):
            vx = xs[int(rng.integers(len(xs)))]
            vy = ys[int(rng.integers(len(ys)))]
            vh = rng.uniform(0.6, 1.4)
            sb.add_beam((vx, vy, roof + 0.05), (vx, vy, roof + vh), "TUBE140",
                        ctx.steel(), ["tower", "vent"], g)
            sb.add_detail_at("vent", (vx, vy, roof + vh), (1, 0, 0), (0, 0, 1),
                             [0.7, 0.7, 0.5], ctx.steel(), g)
    if ctx.roll("detail"):
        sb.add_detail_at("light", (x, y + sy / 2.0 - 0.5, roof + 2.0), (1, 0, 0), (0, 0, 1),
                         [0.35, 0.35, 0.35], "accent", g)
    # antenna mast with stays (cable-stayed character)
    if t.get("antenna") and t.get("slab_ok") and ctx.roll("primary"):
        ax, ay = x, y
        mh = t["antenna"]
        sb.add_beam((ax, ay, roof), (ax, ay, roof + mh), "TUBE180", ctx.steel(),
                    ["tower", "mast"], g)
        for (cx, cy) in ((xs[0], ys[0]), (xs[-1], ys[0]), (xs[0], ys[-1]), (xs[-1], ys[-1])):
            if rng.random() < 0.8:
                sb.add_beam((ax, ay, roof + mh * 0.85), (cx, cy, roof + 0.1),
                            "ROD16", ctx.steel(), ["tower", "cable"], g)


def _stair(ctx, t, g):
    sb, rng = ctx.sb, ctx.rng
    x, y, sx, sy = t["x"], t["y"], t["sx"], t["sy"]
    if not ctx.roll("secondary"):
        return
    sy0 = y - sy / 2.0 + rng.uniform(2.0, sy - 2.0)
    z0 = 1.6
    if not ctx.p.get("stairs_full"):
        # one run from the plinth to the first floor
        z1 = t["floors"][min(1, len(t["floors"]) - 1)]
        sx0 = x - sx / 2.0 - 1.2
        steps = max(4, int((z1 - z0) / 0.18))
        for yy in (sy0, sy0 + 1.1):
            sb.add_beam((sx0, yy, z0), (sx0, yy, z1), "C250", ctx.steel(),
                        ["tower", "stair"], g)
        for i in range(steps):
            zz = z0 + (z1 - z0) * (i + 0.5) / steps
            sb.add_block((sx0, sy0 + 0.55, zz), (1.2, 1.1, 0.06), "grating",
                         ["tower", "stair"], g)
        for i in range(max(1, int((z1 - z0) / 2.6))):
            zz = z0 + 2.6 * i
            sb.add_detail_at("railing", (sx0, sy0 + 1.15, zz + 1.3), (0, 0, 1), (0, 1, 0),
                             [0.08, 0.08, 2.6], ctx.steel(), g)
        sb.add_block((x - sx / 2.0 - 0.25, sy0 + 0.55, z1 + 0.3), (0.5, 1.6, 0.2),
                     "grating", ["tower", "stair"], g)
        return
    # full-height zig-zag against the west face: flights alternate between two
    # stringer lines, with a landing at every floor
    xa, xb = x - sx / 2.0 - 1.2, x - sx / 2.0 - 2.3
    zcur = z0
    for k in range(len(t["floors"]) - 1):
        znext = t["floors"][k]
        xk = xa if k % 2 == 0 else xb
        steps = max(4, int((znext - zcur) / 0.18))
        for yy in (sy0, sy0 + 1.1):
            sb.add_beam((xk, yy, zcur), (xk, yy, znext), "C250", ctx.steel(),
                        ["tower", "stair"], g)
        for i in range(steps):
            zz = zcur + (znext - zcur) * (i + 0.5) / steps
            sb.add_block((xk, sy0 + 0.55, zz), (1.2, 1.1, 0.06), "grating",
                         ["tower", "stair"], g)
        if rng.random() < 0.8:
            sb.add_detail_at("railing", (xk, sy0 + 1.15, znext - 1.3), (0, 0, 1), (0, 1, 0),
                             [0.08, 0.08, 2.6], ctx.steel(), g)
        # landing joining the two stringer lines at this floor
        sb.add_block(((xa + xb) / 2.0, sy0 + 0.55, znext + 0.15), (1.7, 1.3, 0.12),
                     "grating", ["tower", "stair"], g)
        zcur = znext


def _ladders(ctx, t, g):
    sb, rng = ctx.sb, ctx.rng
    x, y, sx, sy = t["x"], t["y"], t["sx"], t["sy"]
    for _ in range(rng.integers(1, 3)):
        if not ctx.roll("detail"):
            continue
        lx = x + rng.uniform(-sx / 3.0, sx / 3.0)
        ly = y + sy / 2.0 + 0.35
        sb.add_detail_at("ladder", (lx, ly, 2.0), (0, 0, 1), (0, 1, 0),
                         [0.6, 0.6, 5.0], ctx.steel(), g)


def _pipes(ctx, t, g, core_hx, core_hy):
    sb, rng = ctx.sb, ctx.rng
    x, y = t["x"], t["y"]
    if not ctx.roll("secondary"):
        return
    z_top = t["floors"][-1] + 0.45
    px, py = x + core_hx + 0.3, y - core_hy - 0.3
    # vertical run along the core face
    sb.add_beam((px, py, 1.6), (px, py, z_top), "TUBE90", ctx.paint(),
                ["tower", "pipe"], g)
    xs = [x - t["sx"] / 2.0 + t["sx"] * i / t["bays"][0] for i in range(t["bays"][0] + 1)]
    face_y = y - t["sy"] / 2.0
    for k in range(0, len(t["floors"]), 3):
        zz = t["floors"][k]
        if rng.random() < 0.8:
            sb.add_detail_at("pipe_run", (px, py, zz + 1.0), (1, 0, 0), (0, 0, 1),
                             [0.5, 0.5, 0.5], ctx.steel(), g)
        # horizontal branch along the ceiling to a spandrel mid-point
        if rng.random() < 0.7:
            ix = int(rng.integers(t["bays"][0]))
            xm = (xs[ix] + xs[ix + 1]) / 2.0
            sb.add_beam((px, py, zz), (xm, face_y, zz), "TUBE90",
                        ctx.paint(), ["tower", "pipe"], g)
    # pipe loop across the core top
    sb.add_beam((px, py, z_top), (x - core_hx - 0.3, py, z_top), "TUBE90",
                ctx.paint(), ["tower", "pipe"], g)


# ------------------------------------------------------- bridges & gantries

def bridge_between(ctx, ta, tb, level_frac=None):
    """Truss bridge between two towers, deck at a shared floor level."""
    p, rng = ctx.p, ctx.rng
    sb = ctx.sb
    # faces toward each other
    (ax, ay, asx, asy), (bx, by, bsx, bsy) = (
        (ta["x"], ta["y"], ta["sx"], ta["sy"]), (tb["x"], tb["y"], tb["sx"], tb["sy"]))
    if abs(ax - bx) >= abs(ay - by):  # X-aligned span
        if ax < bx:
            fa, fb = (ax + asx / 2.0, ay, 1, 0), (bx - bsx / 2.0, by, 1, 0)
        else:
            fa, fb = (ax - asx / 2.0, ay, 1, 0), (bx + bsx / 2.0, by, 1, 0)
    else:
        if ay < by:
            fa, fb = (ax, ay + asy / 2.0, 0, 1), (bx, by - bsy / 2.0, 0, 1)
        else:
            fa, fb = (ax, ay - asy / 2.0, 0, 1), (bx, by + bsy / 2.0, 0, 1)
    origin = np.array([fa[0], fa[1], 0.0])
    direction = np.array([fb[0] - fa[0], fb[1] - fa[1], 0.0])
    span = float(np.linalg.norm(direction))
    if span < 8.0:
        return None
    g = ctx.sb.group(f"bridge-{len([x for x in ctx.sb.groups if x['name'].startswith('bridge')]) + 1:02d}")

    # deck level: a floor of the lower tower, above the ground floors
    minfloors = min(len(ta["floors"]), len(tb["floors"]))
    if level_frac is None:
        k = int(rng.integers(2, max(3, minfloors - 2)))
    else:
        k = int(min(max(level_frac * minfloors, 2.0), minfloors - 2))
    deck_z = min(ta["floors"][k], tb["floors"][k])
    origin[2] = deck_z
    depth = rng.uniform(*p["bridge"]["depth"])
    width = rng.uniform(*p["bridge"]["width"])
    kind = p["bridge"]["kinds"][int(rng.integers(len(p["bridge"]["kinds"])))]
    cable = rng.random() < p["bridge"].get("cable", 0.0)
    panel = p["bridge"].get("panel", [3.2, 4.6])
    bw = TrussBridge(sb, origin, direction, deck_z, span, width, depth, kind, rng, g,
                     material=ctx.steel() if not ctx.ruin else "rust" if rng.random() < 0.5 else "steel",
                     density=p["density"]["primary"] if not ctx.ruin else 1.0,
                     density2=p["density"]["secondary"] if not ctx.ruin else 0.5,
                     panel_min=panel[0], panel_max=panel[1],
                     catwalk=rng.random() < p["bridge"].get("catwalk", 0.0),
                     cable_mast=(depth * rng.uniform(1.6, 2.4) if cable else None))
    bw.build()
    # corbel bearings at both ends (anchor the truss into the tower faces);
    # the long side runs along the span direction
    corbel_size = ((1.0, width + 0.8, 0.9) if abs(direction[0]) >= abs(direction[1])
                   else (width + 0.8, 1.0, 0.9))
    for (cx, cy, own) in ((fa[0], fa[1], ta["group"]), (fb[0], fb[1], tb["group"])):
        sb.add_block((cx, cy, deck_z + 0.45), corbel_size,
                     "concrete", ["bridge", "corbel"], own)
    # end tie rods to the towers
    if ctx.roll("secondary"):
        end_l = bw.W(0.0, -width / 2.0, 0.0)
        end_r = bw.W(span, -width / 2.0, 0.0)
        sb.add_beam((end_l[0], end_l[1], deck_z + 2.0), end_l, "ROD16",
                    ctx.steel(), ["bridge", "tie"], g)
        sb.add_beam((end_r[0], end_r[1], deck_z + 2.0), end_r, "ROD16",
                    ctx.steel(), ["bridge", "tie"], g)
    # pipe rack running alongside the deck
    if ctx.p.get("pipe_racks") and ctx.roll("secondary"):
        for (yoff, prof) in ((width / 2.0 + 0.55, "TUBE140"), (width / 2.0 + 0.85, "TUBE90")):
            sb.add_beam(bw.W(0.0, yoff, 0.9), bw.W(span, yoff, 0.9), prof,
                        ctx.paint(), ["bridge", "pipe"], g)
        for k in range(0, bw.panels + 1, 2):
            xk = k * bw.panel
            sb.add_beam(bw.W(xk, width / 2.0 + 0.7, 0.3), bw.W(xk, width / 2.0 + 0.7, 1.0),
                        "TUBE50", ctx.steel(), ["bridge", "pipe"], g)
            if rng.random() < 0.5:
                sb.add_detail_at("pipe_run", bw.W(xk, width / 2.0 + 0.7, 1.0),
                                 (1, 0, 0), (0, 0, 1), [0.4, 0.4, 0.4], ctx.steel(), g)

    # outboard catwalk under the deck on long spans (outriggers + hangers)
    if span > 20.0 and ctx.roll("secondary"):
        zc = -1.9
        for k in range(0, bw.panels + 1):
            xk = k * bw.panel
            for sgn in (-1.0, 1.0):
                y0, y1 = sgn * width / 2.0, sgn * (width / 2.0 + 0.8)
                if k < bw.panels:
                    sb.add_beam(bw.W(xk, y0, 0.0), bw.W(xk, y1, 0.0), "TUBE90",
                                ctx.steel(), ["bridge", "catwalk"], g)
                sb.add_beam(bw.W(xk, y1, 0.0), bw.W(xk, y1, zc), "TUBE50",
                            ctx.steel(), ["bridge", "catwalk"], g)
        for yoff in (-width / 2.0 - 0.8, width / 2.0 + 0.8):
            sb.add_beam(bw.W(0.0, yoff, zc), bw.W(span, yoff, zc), "C160",
                        ctx.steel(), ["bridge", "catwalk"], g)
        sb.add_block(bw.W(span / 2.0, 0.0, zc + 0.05), (span, width + 1.6, 0.08), "grating",
                     ["bridge", "catwalk"], g)
        for k in range(max(1, int(span / 2.6))):
            lx = 2.6 * k + 1.3
            for sgn in (-1.0, 1.0):
                sb.add_detail_at("railing", bw.W(lx, sgn * (width / 2.0 + 0.85), zc + 0.95),
                                 (1, 0, 0), (0, 0, 1), [0.06, 0.06, 0.9], ctx.steel(), g)
    return g


def pipe_rack_between(ctx, ta, tb):
    """Ground-level pipe rack: posts from the ground, three pipes on top."""
    sb, rng = ctx.sb, ctx.rng
    a = np.array([ta["x"], ta["y"], 0.0])
    b = np.array([tb["x"], tb["y"], 0.0])
    d = b - a
    span = float(np.linalg.norm(d))
    if span < 10.0:
        return None
    g = sb.group("pipe-rack", 0)
    nseg = max(2, int(span / 5.0))
    for q in range(nseg + 1):
        p = a + d * q / nseg
        if q == 0 or q == nseg:
            continue
        if rng.random() < 0.9:
            sb.add_beam((p[0], p[1], 0.3), (p[0], p[1], 2.7), "TUBE140",
                        ctx.steel(), ["pipe_rack", "post"], g)
    for (zoff, prof) in ((2.2, "TUBE90"), (2.55, "TUBE90"), (2.9, "TUBE50")):
        if rng.random() < 0.95:
            sb.add_beam((a[0], a[1], zoff), (b[0], b[1], zoff), prof,
                        ctx.paint(), ["pipe_rack", "pipe"], g)
    for q in range(1, nseg):
        if rng.random() < 0.4:
            p = a + d * q / nseg
            sb.add_detail_at("pipe_run", (p[0], p[1], 2.2), (1, 0, 0), (0, 0, 1),
                             [0.4, 0.4, 0.4], ctx.steel(), g)
    return g


def gantry_between(ctx, ta, tb, level_frac=1.0):
    """Gantry crane rails between two towers at a given level, with parked cranes."""
    p, rng = ctx.p, ctx.rng
    sb = ctx.sb
    (ax, ay, asx, asy), (bx, by, bsx, bsy) = (
        (ta["x"], ta["y"], ta["sx"], ta["sy"]), (tb["x"], tb["y"], tb["sx"], tb["sy"]))
    if abs(ax - bx) >= abs(ay - by):
        if ax < bx:
            fa, fb = (ax + asx / 2.0, ay, 1, 0), (bx - bsx / 2.0, by, 1, 0)
        else:
            fa, fb = (ax - asx / 2.0, ay, 1, 0), (bx + bsx / 2.0, by, 1, 0)
    else:
        if ay < by:
            fa, fb = (ax, ay + asy / 2.0, 0, 1), (bx, by - bsy / 2.0, 0, 1)
        else:
            fa, fb = (ax, ay - asy / 2.0, 0, 1), (bx, by + bsy / 2.0, 0, 1)
    origin = np.array([fa[0], fa[1], 0.0])
    direction = np.array([fb[0] - fa[0], fb[1] - fa[1], 0.0])
    span = float(np.linalg.norm(direction))
    if span < 8.0:
        return None
    g = ctx.sb.group(f"gantry-{len([x for x in ctx.sb.groups if x['name'].startswith('gantry')]) + 1:02d}")
    ang = math.atan2(direction[1], direction[0])
    ca, sa = math.cos(ang), math.sin(ang)

    def W(lx, ly, lz):
        return np.array([origin[0] + lx * ca - ly * sa,
                         origin[1] + lx * sa + ly * ca, lz])

    # rails at a floor level of the taller tower (both roofs for the top
    # level), so each end's pedestal seats on its own slab
    minfloors = min(len(ta["floors"]), len(tb["floors"]))
    if level_frac >= 0.95:
        deck_z = max(ta["floors"][-1], tb["floors"][-1]) + 1.3
        k = -1
    else:
        k = int(min(max(level_frac * minfloors, 1.0), minfloors - 2))
        deck_z = max(ta["floors"][k], tb["floors"][k]) + 0.1
    rail = 1.6  # half gauge
    for yoff in (-rail, rail):
        sb.add_beam(W(0.0, yoff, deck_z), W(span, yoff, deck_z), "I450",
                    ctx.steel(), ["gantry", "rail"], g)
        # light lattice girder under the rail on long spans
        if span > 16.0:
            nlat = max(4, int(span / 3.0))
            for q in range(nlat):
                x0, x1 = span * q / nlat, span * (q + 1) / nlat
                sb.add_beam(W(x0, yoff, deck_z - 1.2), W(x1, yoff, deck_z - 1.2),
                            "TUBE180", ctx.steel(), ["gantry", "lattice"], g)
                sb.add_beam(W(x0, yoff, deck_z - 1.2), W(x1, yoff, deck_z), "L90",
                            ctx.steel(), ["gantry", "lattice"], g)
                sb.add_beam(W(x1, yoff, deck_z - 1.2), W(x0, yoff, deck_z), "L90",
                            ctx.steel(), ["gantry", "lattice"], g)
    # bearing pedestals on both faces, rising from the slab to the rails
    ped_size = ((1.0, 3.6) if abs(direction[0]) >= abs(direction[1]) else (3.6, 1.0))
    for (cx, cy, own) in ((fa[0], fa[1], ta["group"]), (fb[0], fb[1], tb["group"])):
        own_floors = ta["floors"] if own == ta["group"] else tb["floors"]
        slab_z = own_floors[-1] if k < 0 else own_floors[k]
        z0, z1 = slab_z - 0.3, deck_z + 0.6
        sb.add_block((cx, cy, (z0 + z1) / 2.0), (ped_size[0], ped_size[1], z1 - z0),
                     "concrete", ["gantry", "bearing"], own)
    # parked cranes: cross beam + legs + hoist cable
    ncranes = p["gantry"].get("cranes", [1, 3]) if isinstance(p["gantry"], dict) else [1, 3]
    if p["scale"] == "large":
        ncranes = [ncranes[0] + 1, ncranes[1] + 1]
    for _ in range(rng.integers(ncranes[0], ncranes[1] + 1)):
        lx = rng.uniform(0.15 * span, 0.85 * span)
        if ctx.roll("primary"):
            sb.add_beam(W(lx, -rail, deck_z + 1.1), W(lx, rail, deck_z + 1.1),
                        "I600", ctx.paint(), ["gantry", "crane"], g)
            for yoff in (-rail, rail):
                sb.add_beam(W(lx, yoff, deck_z + 1.1), W(lx, yoff, deck_z + 0.1),
                            "TUBE140", ctx.steel(), ["gantry", "crane"], g)
            sb.add_beam(W(lx, 0.0, deck_z + 1.1), W(lx, 0.0, deck_z - 2.6),
                        "ROD16", ctx.steel(), ["gantry", "crane"], g)
            sb.add_block(W(lx, 0.0, deck_z - 2.9), (0.4, 0.4, 0.6), "accent",
                         ["gantry", "hook"], g)
            sb.add_detail_at("light", W(lx, rail, deck_z + 1.3), (1, 0, 0), (0, 0, 1),
                             [0.3, 0.3, 0.3], "accent", g)
    return g


def catwalk_between(ctx, ta, tb, level_frac=0.5):
    """Light industrial catwalk between two towers at a mid level."""
    p, rng = ctx.p, ctx.rng
    sb = ctx.sb
    (ax, ay, asx, asy), (bx, by, bsx, bsy) = (
        (ta["x"], ta["y"], ta["sx"], ta["sy"]), (tb["x"], tb["y"], tb["sx"], tb["sy"]))
    if abs(ax - bx) >= abs(ay - by):
        if ax < bx:
            fa, fb = (ax + asx / 2.0, ay), (bx - bsx / 2.0, by)
        else:
            fa, fb = (ax - asx / 2.0, ay), (bx + bsx / 2.0, by)
    else:
        if ay < by:
            fa, fb = (ax, ay + asy / 2.0), (bx, by - bsy / 2.0)
        else:
            fa, fb = (ax, ay - asy / 2.0), (bx, by + bsy / 2.0)
    direction = np.array([fb[0] - fa[0], fb[1] - fa[1], 0.0], dtype=float)
    span = float(np.linalg.norm(direction))
    if span < 6.0:
        return None
    g = ctx.sb.group(f"catwalk-{len([x for x in ctx.sb.groups if x['name'].startswith('catwalk')]) + 1:02d}")
    ang = math.atan2(direction[1], direction[0])
    ca, sa = math.cos(ang), math.sin(ang)
    origin = np.array([fa[0], fa[1], 0.0])

    def W(lx, ly, lz):
        return np.array([origin[0] + lx * ca - ly * sa,
                         origin[1] + lx * sa + ly * ca, lz])

    # deck at a floor level of the taller tower; brackets rise from each slab
    minfloors = min(len(ta["floors"]), len(tb["floors"]))
    klvl = int(min(max(level_frac * minfloors, 1.0), minfloors - 1))
    z = max(ta["floors"][klvl], tb["floors"][klvl]) + 0.1
    w = 1.2
    # stringers
    for yoff in (-w / 2.0, w / 2.0):
        sb.add_beam(W(0.0, yoff, z), W(span, yoff, z), "C180", ctx.steel(),
                    ["catwalk", "stringer"], g)
    # cross bars
    ncross = max(2, int(span / 1.5))
    for q in range(ncross):
        lx = span * (q + 0.5) / ncross
        sb.add_beam(W(lx, -w / 2.0, z), W(lx, w / 2.0, z), "L70", ctx.steel(),
                    ["catwalk", "cross"], g)
    # deck, railings
    sb.add_block(W(span / 2.0, 0.0, z + 0.05), (span, w, 0.08), "grating",
                 ["catwalk", "deck"], g)
    for q in range(max(1, int(span / 2.6))):
        lx = 2.6 * q + 1.3
        sb.add_detail_at("railing", W(lx, w / 2.0 + 0.05, z + 1.1), (1, 0, 0), (0, 0, 1),
                         [0.06, 0.06, 1.0], ctx.steel(), g)
        sb.add_detail_at("railing", W(lx, -w / 2.0 - 0.05, z + 1.1), (1, 0, 0), (0, 0, 1),
                         [0.06, 0.06, 1.0], ctx.steel(), g)
    # knee braces and bearing brackets at both ends (anchor into the towers)
    for (cx, cy) in (fa, fb):
        slab_z = ta["floors"][klvl] if (cx, cy) == fa else tb["floors"][klvl]
        z0, z1 = min(slab_z, z) - 0.3, z + 0.5
        sb.add_block((cx, cy, (z0 + z1) / 2.0), (0.5, w + 0.6, z1 - z0), "steel",
                     ["catwalk", "bracket"], ta["group"] if (cx, cy) == fa else tb["group"])
        sb.add_beam((cx - direction[0] / span * 0.2, cy - direction[1] / span * 0.2, z - 0.9),
                    W(0.0 if (cx, cy) == fa else span, 0.0, z - 0.15), "L90",
                    ctx.steel(), ["catwalk", "knee"], g)
    return g
