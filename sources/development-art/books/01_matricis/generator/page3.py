from portable_paths import OUTPUT
"""Tabula III — Of the Speed of Correction: the Figure in the Square of Intervals.
Multi-pen plotter hand. Cell density is driven by the numbers it carries."""
import math
import random
import sys

from shapely.geometry import Polygon, Point, LineString, box as sbox
from shapely.ops import unary_union

from core import Doc, arc_pts, catmull, offset_line, path_len, point_at, bezier, resample
from marks import *
import cipher

W, H = 1000, 1600
PAPER = "#fbf8ef"
PENS = {
    "dk": "#3a2a21",   # dark brown
    "rb": "#7f3a2b",   # red-brown
    "ol": "#566c22",   # olive
    "sg": "#a9c58d",   # sage
    "yl": "#efcd3c",   # yellow
    "mu": "#d6a12f",   # mustard
}
SQ_X, SQ_Y, SQ = 110, 236, 780
SEED = 3

# (cell, value shown, density value, max, palette)  upper: minutes; lower: units of eight
CELLS = {
    "TLt": ("110", 110, 134), "TLl": ("114", 114, 134), "T1": ("134", 134, 134), "T3": ("39", 39, 134),
    "TRt": ("85", 85, 134), "T2": ("7", 7, 134), "TRr": ("78", 78, 134), "T4": ("17", 17, 134),
    "BLl": ("6", 6, 8), "T5": ("6", 6, 8), "BLb": ("3", 3, 8), "T7": ("3", 3, 8),
    "BRb": ("1", 1, 8), "T8": ("0", 0, 8), "BRr": ("?", None, 8), "T6": ("?", None, 8),
}
POLY = {
    "TLt": [(0, 0), (0.5, 0), (0.25, 0.25)], "TLl": [(0, 0), (0.25, 0.25), (0, 0.5)],
    "TRt": [(0.5, 0), (1, 0), (0.75, 0.25)], "TRr": [(1, 0), (1, 0.5), (0.75, 0.25)],
    "BLl": [(0, 0.5), (0.25, 0.75), (0, 1)], "BLb": [(0, 1), (0.25, 0.75), (0.5, 1)],
    "BRr": [(1, 0.5), (1, 1), (0.75, 0.75)], "BRb": [(0.5, 1), (0.75, 0.75), (1, 1)],
    "T1": [(0.5, 0), (0.25, 0.25), (0.5, 0.5)], "T2": [(0.5, 0), (0.75, 0.25), (0.5, 0.5)],
    "T3": [(0.25, 0.25), (0, 0.5), (0.5, 0.5)], "T4": [(0.75, 0.25), (1, 0.5), (0.5, 0.5)],
    "T5": [(0, 0.5), (0.25, 0.75), (0.5, 0.5)], "T6": [(1, 0.5), (0.75, 0.75), (0.5, 0.5)],
    "T7": [(0.25, 0.75), (0.5, 1), (0.5, 0.5)], "T8": [(0.75, 0.75), (0.5, 1), (0.5, 0.5)],
}
# where each number sits (unit coords), kept clear of the figure
ANCHOR = {
    "TLt": (0.255, 0.075), "TLl": (0.075, 0.25), "T1": (0.33, 0.235), "T3": (0.2, 0.43),
    "TRt": (0.745, 0.075), "TRr": (0.925, 0.25), "T2": (0.67, 0.235), "T4": (0.8, 0.43),
    "BLl": (0.075, 0.75), "BLb": (0.255, 0.925), "T5": (0.2, 0.57), "T7": (0.36, 0.8),
    "BRr": (0.925, 0.75), "BRb": (0.745, 0.925), "T6": (0.8, 0.57), "T8": (0.64, 0.8),
}
UPPER_PENS = [("yl", 3), ("mu", 3), ("rb", 2), ("dk", 1.4), ("sg", 0.6)]
LOWER_PENS = [("sg", 3), ("ol", 3), ("dk", 1.5), ("mu", 0.8), ("rb", 0.4)]


def U(p):
    return (SQ_X + p[0] * SQ, SQ_Y + p[1] * SQ)


def styles():
    st = {}
    for k, col in PENS.items():
        st[f"{k}_hair"] = {"fill": "none", "stroke": col, "stroke-width": "0.85", "stroke-linecap": "round",
                           "stroke-linejoin": "round", "opacity": "0.92"}
        st[f"{k}_orn"] = {"fill": "none", "stroke": col, "stroke-width": "1.3", "stroke-linecap": "round",
                          "stroke-linejoin": "round"}
        st[f"{k}_core"] = {"fill": "none", "stroke": col, "stroke-width": "2.1", "stroke-linecap": "round",
                           "stroke-linejoin": "round"}
        st[f"{k}_cip"] = {"fill": "none", "stroke": col, "stroke-width": "1.15", "stroke-linecap": "round",
                          "stroke-linejoin": "round"}
        st[f"{k}_fill"] = {"fill": col, "stroke": "none"}
    # marks.py speaks of ink and red
    for k, wdt in (("hair", 0.85), ("orn", 1.3), ("core", 2.1), ("cip", 1.15)):
        st[f"ink_{k}"] = dict(st[f"dk_{k}"])
        st[f"red_{k}"] = dict(st[f"rb_{k}"])
    st["ink_fill"] = st["dk_fill"]
    st["red_fill"] = st["rb_fill"]
    return st


def figure_geom():
    """the horned figure, arms raised, standing in the square (unit coords)"""
    parts = []
    for sgn in (-1, 1):
        sx = 0.5 + sgn * 0.082
        hx = 0.5 + sgn * 0.158
        parts.append(Polygon([(sx - 0.02, 0.305), (sx + 0.02, 0.29), (hx + 0.016, 0.06), (hx - 0.016, 0.064)]))
        parts.append(Point(hx, 0.056).buffer(0.021))
    # head ring with the horns growing from its crown
    parts.append(Point(0.5, 0.2).buffer(0.05))
    parts.append(sbox(0.483, 0.245, 0.517, 0.295))
    parts.append(Polygon([(0.405, 0.285), (0.595, 0.285), (0.604, 0.55), (0.618, 0.585), (0.382, 0.585),
                          (0.396, 0.55)]))
    for lx in (0.428, 0.528):
        parts.append(Polygon([(lx, 0.58), (lx + 0.044, 0.58), (lx + 0.046, 0.95), (lx + 0.058, 0.985),
                              (lx - 0.012, 0.985), (lx - 0.002, 0.95)]))
    fig = unary_union(parts)
    hole = Point(0.5, 0.2).buffer(0.018)
    fig = fig.difference(hole)
    outer = Polygon(arc_pts(0.5, 0.072, 0.088, -24, 204, 70))
    inner = Polygon(arc_pts(0.5, 0.046, 0.071, -30, 210, 70))
    horns = outer.difference(inner).difference(Point(0.5, 0.2).buffer(0.05))
    if horns.geom_type != "Polygon":
        horns = max(horns.geoms, key=lambda g: g.area)
    return fig, horns, hole


def walk_fill(h, region, n_walks, pens, rng, vertical_bias=0.62, step=(3.0, 5.5), length=(14, 70)):
    """rectilinear random walks inside a region (shapely, unit-free page coords)"""
    if region.is_empty or n_walks <= 0:
        return
    minx, miny, maxx, maxy = region.bounds
    names = [p for p, _ in pens]
    wts = [w for _, w in pens]
    prepared = region
    made = 0
    tries = 0
    while made < n_walks and tries < n_walks * 30:
        tries += 1
        x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        if not prepared.contains(Point(x, y)):
            continue
        pen = rng.choices(names, wts)[0]
        vert = rng.random() < vertical_bias
        d = rng.choice([(0, 1), (0, -1)]) if vert else rng.choice([(1, 0), (-1, 0)])
        pts = [(x, y)]
        for _ in range(rng.randint(*length)):
            if rng.random() < 0.3:
                d = (d[1], d[0]) if rng.random() < 0.5 else (-d[1], -d[0])
                if rng.random() < vertical_bias and d[0] != 0:
                    d = (0, rng.choice([1, -1]))
            s = rng.uniform(*step)
            q = (pts[-1][0] + d[0] * s, pts[-1][1] + d[1] * s)
            if not prepared.contains(Point(q)):
                break
            pts.append(q)
        if len(pts) > 2:
            h.doc.poly(f"{pen}_hair", pts)
            made += 1


def build(seed=SEED):
    rng = random.Random(seed)
    st = styles()
    doc = Doc(W, H, st)
    h = Hand(doc, rng, "ink", amp=0.35)

    fig_u, horns_u, hole_u = figure_geom()
    scale = lambda g: __import__("shapely").affinity.affine_transform(g, [SQ, 0, 0, SQ, SQ_X, SQ_Y])
    fig = scale(fig_u)
    horns = scale(horns_u)
    figure_all = unary_union([fig, horns])
    keep_fig = figure_all.buffer(7)

    # number knock-outs
    knock = {}
    for k, (lab, v, mx) in CELLS.items():
        ax, ay = U(ANCHOR[k])
        rr = 21 if len(lab) == 1 else 27
        knock[k] = (ax, ay, rr)
    knock_geom = unary_union([Point(x, y).buffer(r + 6) for (x, y, r) in knock.values()])

    # -------------------------------------------------------------- cells
    for k, (lab, v, mx) in CELLS.items():
        poly = Polygon([U(p) for p in POLY[k]]).buffer(-3.5)
        region = poly.difference(keep_fig).difference(knock_geom)
        upper = k in ("TLt", "TLl", "T1", "T3", "TRt", "T2", "TRr", "T4")
        pens = UPPER_PENS if upper else LOWER_PENS
        if v is None:
            # unknown is not absent: hollow marks, no fill
            minx, miny, maxx, maxy = region.bounds
            placed = 0
            for _ in range(900):
                x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
                if region.contains(Point(x, y).buffer(4)):
                    h.ring(x, y, rng.uniform(1.6, 3.4), "hair", rng.choice(["ol", "sg", "sg"]))
                    placed += 1
                    if placed > region.area / 260:
                        break
            continue
        dens = (v / mx) if mx else 0
        n = int(region.area / 330 * (0.04 + 0.96 * dens) ** 0.9)
        if v == 0:
            n = 0
        walk_fill(h, region, n, pens, rng)

    # ------------------------------------------------------------- the figure
    # fill: dense vertical walks in dark pens
    spiral_c = U((0.5, 0.425))
    spiral_r = 0.072 * SQ
    spiral_zone = Point(spiral_c).buffer(spiral_r * 1.08)
    body = fig.buffer(-3).difference(spiral_zone)
    walk_fill(h, body, int(body.area / 86), [("dk", 4), ("rb", 1.4), ("ol", 0.5)], rng, vertical_bias=0.86,
              step=(2.6, 4.2), length=(10, 40))
    walk_fill(h, horns.buffer(-1.5), int(horns.area / 60), [("dk", 3), ("rb", 1)], rng, vertical_bias=0.3,
              step=(2.2, 3.4), length=(6, 20))
    # outline in three passes, offset like a re-inked plot
    for geom in (fig, horns):
        geoms = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
        for g in geoms:
            rings = [list(g.exterior.coords)] + [list(r.coords) for r in g.interiors]
            for ring in rings:
                for k, (pen, off) in enumerate((("dk", 0), ("rb", -1.3))):
                    pts = [(x + off * 0.6, y + off * 0.3) for (x, y) in ring]
                    h.stroke(pts, "orn" if k == 0 else "hair", pen)
    # the mark on the torso, as a pierced spiral
    sp = sig_mark(h, spiral_c[0], spiral_c[1], spiral_r * 0.92, "rb", "core", branch=True, turns=1.75, ang0=200)
    h.stroke(offset_line(sp, 1.8), "hair", "yl")
    h.stroke(arc_pts(spiral_c[0], spiral_c[1], spiral_r * 1.08, 0, 360, 120), "hair", "dk")

    # --------------------------------------------------------------- lines
    lines = [((0, 0), (1, 1)), ((1, 0), (0, 1)), ((0.5, 0), (1, 0.5)), ((1, 0.5), (0.5, 1)), ((0.5, 1), (0, 0.5)),
             ((0, 0.5), (0.5, 0)), ((0, 0.5), (1, 0.5)), ((0.5, 0), (0.5, 1))]
    for a, b in lines:
        seg = LineString([U(a), U(b)]).difference(figure_all.buffer(3)).difference(knock_geom)
        segs = [seg] if seg.geom_type == "LineString" else list(getattr(seg, "geoms", []))
        for s in segs:
            if s.length < 2:
                continue
            c = list(s.coords)
            h.stroke(c, "orn", "dk")
            h.stroke([(x + 0.9, y + 0.7) for x, y in c], "hair", "rb")
    # frame: double, with stars at the corners
    x0, y0, x1, y1 = SQ_X, SQ_Y, SQ_X + SQ, SQ_Y + SQ
    for off, wt, pen in ((0, "core", "dk"), (-9, "hair", "dk"), (-12, "hair", "mu")):
        h.stroke([(x0 + off, y0 + off), (x1 - off, y0 + off), (x1 - off, y1 - off), (x0 + off, y1 - off)], wt, pen,
                 closed=True)
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        asterisk(h, cx + (-14 if cx == x0 else 14), cy + (-14 if cy == y0 else 14), 7, 8, weight="orn",
                 color="rb")
    # badges round the numbers
    for k, (x, y, r) in knock.items():
        upper = k in ("TLt", "TLl", "T1", "T3", "TRt", "T2", "TRr", "T4")
        h.ring(x, y, r, "orn", "rb" if upper else "ol")
        h.ring(x, y, r + 3.2, "hair", "mu" if upper else "sg")

    # inscription round the frame, in the cipher hand (tops outward)
    def side(text, which, start, size=11.5, color="dk"):
        if which == "top":
            tf = lambda p: (x0 + start + p[0], y0 - 9 + p[1])
        elif which == "right":
            tf = lambda p: (x1 + 9 - p[1], y0 + start + p[0])
        elif which == "bottom":
            tf = lambda p: (x1 - start - p[0], y1 + 9 - p[1])
        else:
            tf = lambda p: (x0 - 9 + p[1], y1 - start - p[0])
        w_ = cipher.write(XHand(h, tf), text, 0, 0, size, "cip", color, rail=True, rail_color="mu")
        return w_

    def fill_side(which, s0, s1):
        if s1 - s0 < 20:
            return
        if which == "top":
            pts = [(x0 + s0, y0 - 14), (x0 + s1, y0 - 14)]
        elif which == "right":
            pts = [(x1 + 14, y0 + s0), (x1 + 14, y0 + s1)]
        elif which == "bottom":
            pts = [(x1 - s0, y1 + 14), (x1 - s1, y1 + 14)]
        else:
            pts = [(x0 - 14, y1 - s0), (x0 - 14, y1 - s1)]
        dotted(h, pts, 7, 0.9, "mu", skip_ends=True)

    for which, text in (("top", "how long does a problem take to reach someone able to act"),
                        ("right", "and how long from there to action"),
                        ("bottom", "unknown is not absent"),
                        ("left", "data usefulness is not protocol efficacy")):
        w_ = side(text, which, 34)
        fill_side(which, 34 + w_ + 12, SQ - 34)

    # tail strip: a band of walks in all six pens
    strip = sbox(56, 1492, 944, 1508)
    walk_fill(h, strip, 260, [("dk", 2), ("rb", 1.5), ("ol", 1.5), ("sg", 2), ("yl", 2), ("mu", 2)], rng,
              vertical_bias=0.25, step=(2.5, 4.5), length=(8, 30))

    # small device at the foot
    sig_mark(h, 500, 1562, 10, "rb", "orn")
    return doc, dict(knock={k: list(v) for k, v in knock.items()})


if __name__ == "__main__":
    doc, meta = build()
    open(f"{OUTPUT}/p3_plate.svg", "w").write(doc.svg())
