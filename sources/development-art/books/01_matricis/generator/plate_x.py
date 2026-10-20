"""Tabula X · Of an Analogy Taken to Its Limit — a mounted cornmeal record: a network that thins toward solitary
cells, and the preprint's two clocks."""
import math
import random
import sys

from core import arc_pts, spiral_pts, catmull, path_len, point_at
from marks import *
import hands as Hd
import meal

REC = (70, 250, 930, 1160)
BAND = (300, 760)
CA, CB = (300, 975), (700, 975)


def grow(rng):
    """a vein network: Gabriel graph over points that thin toward the right; long and late edges pruned"""
    pts = []
    tries = 0
    while tries < 20000 and len(pts) < 260:
        tries += 1
        x, y = rng.uniform(96, 650), rng.uniform(*BAND)
        keep = 1.0 - (x - 96) / 554 * 0.82
        if rng.random() > keep:
            continue
        mind = 30 + (x - 96) / 554 * 34
        if all((x - px) ** 2 + (y - py) ** 2 > mind * mind for px, py in pts):
            pts.append((x, y))
    edges = []
    n = len(pts)
    for i in range(n):
        for j in range(i + 1, n):
            (ax, ay), (bx, by) = pts[i], pts[j]
            L2 = (ax - bx) ** 2 + (ay - by) ** 2
            if L2 > 110 ** 2:
                continue
            mx, my, r2 = (ax + bx) / 2, (ay + by) / 2, L2 / 4
            if any((px - mx) ** 2 + (py - my) ** 2 < r2 for k, (px, py) in enumerate(pts) if k not in (i, j)):
                continue
            xm = (ax + bx) / 2
            if rng.random() < max(0.0, (xm - 260) / 360) * 0.9:
                continue
            edges.append((i, j))
    return pts, edges


def build_face(seed=110):
    d, h, ph, rng = meal.page(seed, REC)
    x0, y0, x1, y1 = REC
    # a dusting over the refuge, thinning to the right
    for _ in range(900):
        x = x0 + abs(rng.gauss(0, 150))
        if x < x1 - 10:
            d.grain(rng.choice(["ash_gs", "ash_gs", "ash_gm"]), x, rng.uniform(y0 + 8, BAND[1] + 30))
    pts, edges = grow(rng)
    deg = [0] * len(pts)
    for i, j in edges:
        deg[i] += 1
        deg[j] += 1
        (ax, ay), (bx, by) = pts[i], pts[j]
        mx, my = (ax + bx) / 2 + rng.gauss(0, 5), (ay + by) / 2 + rng.gauss(0, 5)
        path = catmull([(ax, ay), (mx, my), (bx, by)], 8)
        xm = (ax + bx) / 2
        h.stroke(path, "core" if xm < 270 else "orn" if xm < 430 else "hair")
    for k, (x, y) in enumerate(pts):
        if deg[k] >= 3:
            h.dot(x, y, 3.4 if x < 300 else 2.4)
        elif deg[k] == 0 and x > 420:
            h.dot(x, y, 2.0)
    # beyond the network: solitary cells only
    for _ in range(46):
        x = rng.uniform(640, x1 - 24)
        y = rng.uniform(BAND[0], BAND[1])
        h.dot(x, y, rng.uniform(1.6, 2.8))

    # the first clock: slows continuously, reaches every step
    sp = spiral_pts(CA[0], CA[1], 122, 16, -90, 3.2)
    h.stroke(sp, "orn")
    L = path_len(sp)
    for k in range(15):
        p, _ = point_at(sp, L * (k / 14) ** 0.8)
        h.dot(p[0], p[1], 4.2)
    # the second: brief bursts, frozen between, the old ones faded below detection
    for k in range(12):
        a0 = -90 + k * 30
        arc = arc_pts(CB[0], CB[1], 112, a0 - 10, a0 + 10, 16)
        age = 11 - k
        if age <= 2:
            h.stroke(arc, "core")
            h.dot(*arc[0], 3.6)
            if age == 0:
                h.dot(*arc[-1], 4.6)
        elif age <= 5:
            h.stroke(arc, "orn")
        elif age <= 9:
            gh = meal.Hand(d, rng, "grain", amp=0.75, grain={"orn": (1.3 - 0.22 * (age - 6), 0.6), "sizes": (6, 2, 0),
                                                             "stray": 0.0})
            gh.stroke(arc, "orn", "ash")
        else:
            for _ in range(4):
                p = arc[rng.randrange(len(arc))]
                d.grain("ash_gs", p[0] + rng.gauss(0, 2), p[1] + rng.gauss(0, 2))
    h.dot(CB[0], CB[1], 3.4)
    h.dot(CA[0], CA[1], 3.4)
    return d.svg(), {}


def face_boxes(meta):
    GAR, ENG = "EB Garamond", "IM FELL English"
    x0, y0, x1, y1 = REC
    lab = lambda id, x, y, w, t, al="left": dict(id=id, x=x, y=y, w=w, size=15, lh=19, font=GAR, align=al,
                                                 color=Hd.SEPIA, runs=[(t, "i")])
    B = meal.heads("X", "Of an Analogy Taken to Its Limit")
    B += [lab("l_refuge", x0, y0 - 30, 400, "steady activity in buffered refuges"),
          lab("l_harsh", x1 - 400, y0 - 30, 400, "the harshest settings hold only solitary cells", "right"),
          lab("l_ca", 100, y1 + 12, 400, "one slows continuously but still reaches every step", "center"),
          lab("l_cb", 500, y1 + 12, 400, "the other freezes between brief bursts while old signals fade below detection",
              "center")]
    B.append(dict(id="insc", x=110, y=1262, w=780, size=24, lh=32, font=ENG, align="center", color=Hd.INK,
                  runs=[("The fluid ", ""), ("exactly", "x"), (" implements the two-layer split.", "")]))
    return B
