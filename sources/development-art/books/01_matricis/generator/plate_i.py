"""Tabula I · Of the One Question — engraving: the scope declared before testing, and nine starting points."""
import math
import sys

from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from core import arc_pts, hatch_lines, bezier, vesica
from marks import *
import eng

X0, Y0, X1, Y1 = 56, 300, 944, 1252
C = (500, 770)
R = 290
RS = 352          # ring of the nine starting points


def P(r, a, c=C):
    return (c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))


def gear(h, cx, cy, r, teeth=12):
    pts = []
    for k in range(teeth * 4):
        a = k * 360 / (teeth * 4)
        rr = r + (6 if (k % 4) in (1, 2) else 0)
        pts.append((cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))))
    h.stroke(pts, "orn", closed=True)
    h.ring(cx, cy, r * 0.42, "orn")
    h.dot(cx, cy, 3.2)
    for k in range(6):
        a = math.radians(k * 60 + 15)
        h.stroke([(cx + r * 0.42 * math.cos(a), cy + r * 0.42 * math.sin(a)),
                  (cx + (r - 3) * math.cos(a), cy + (r - 3) * math.sin(a))], "hair")


def build_face(seed=101):
    d, h, rng = eng.page(seed)
    eng.plate_frame(h, d, X0, Y0, X1, Y1)
    cx, cy = C
    # the circle of the one question: a hatched rim
    h.stroke(arc_pts(cx, cy, R, 0, 360, 260), "core")
    h.stroke(arc_pts(cx, cy, R - 12, 0, 360, 240), "hair")
    rim = Point(C).buffer(R - 1.5, 128).difference(Point(C).buffer(R - 11, 128))
    for ln in hatch_lines(rim, 3.0, 40):
        h.stroke(ln, "hair", amp=0.04)
    # the cross: four arms from the hub to the rim
    for a in (0, 90, 180, 270):
        band_x(h, P(40, a), P(R - 14, a), 14, 9, "hair", "ink", centre_dots=True)
    h.ring(cx, cy, 40, "orn")
    h.ring(cx, cy, 31, "hair")
    hub = Point(C).buffer(39.5, 64).difference(Point(C).buffer(31.5, 64))
    for ln in hatch_lines(hub, 2.6, -40):
        h.stroke(ln, "hair", amp=0.03)

    # four emblems, one per row of the scope table
    # mature reliability reviews: a finished wheel above an empty dish
    ex, ey = P(R * 0.52, 225)
    gear(h, ex, ey - 14, 34)
    h.stroke(arc_pts(ex, ey + 44, 46, 20, 160, 40), "orn")
    h.stroke([(ex - 50, ey + 58), (ex + 50, ey + 58)], "hair")
    # agentic systems: one small root, many fast arrows
    ex, ey = P(R * 0.52, 315)
    root = (ex - 46, ey + 48)
    h.dot(*root, 5.5)
    for k in range(7):
        a = math.radians(-78 + k * 11)
        L = 70 + 14 * (k % 3)
        tip = (root[0] + L * math.cos(a) * 1.15 + 20, root[1] + L * math.sin(a))
        h.stroke(bezier(root, (root[0] + 10, root[1] - 10), (tip[0] - 20, tip[1] + 18), tip, 14), "hair")
        arrowhead(h, tip, math.degrees(math.atan2(tip[1] - root[1], tip[0] - root[0])) - 10, 7, "ink", "hair")
    # leaderless coordination: dots with trails that fade
    ex, ey = P(R * 0.52, 135)
    for k, (dx, dy) in enumerate(((-40, -30), (6, -44), (40, -8), (-30, 22), (22, 34), (-2, 2), (48, -46))):
        x, y = ex + dx, ey + dy
        h.dot(x, y, 4.2)
        a = rng.uniform(0, 6.28)
        for j in range(1, 6):
            h.dot(x - j * 7 * math.cos(a), y - j * 7 * math.sin(a), max(0.5, 2.6 - j * 0.45))
    # corrective authority implicated: an eye over a closed gate
    ex, ey = P(R * 0.52, 45)
    top, bot = vesica((ex - 40, ey - 30), (ex + 40, ey - 30), 30)
    h.stroke(top, "orn")
    h.stroke(bot, "orn")
    h.ring(ex, ey - 30, 9, "orn")
    h.dot(ex, ey - 30, 4)
    A = [(ex - 22, ey + 6), (ex + 22, ey + 6), (ex, ey + 28)]
    B = [(ex - 22, ey + 50), (ex + 22, ey + 50), (ex, ey + 28)]
    h.stroke(A, "orn", closed=True)
    h.stroke(B, "orn", closed=True)
    h.fill_poly([(ex, ey + 22), (ex + 5, ey + 28), (ex, ey + 34), (ex - 5, ey + 28)])

    # the nine starting points
    pos = {}
    for k, a in enumerate((205, 188, 172, 155)):          # descriptive claims: hollow
        x, y = P(RS, a)
        h.ring(x, y, 11, "orn")
        h.dot(x, y, 2.4)
        pos[f"P{k + 1}"] = (x, y, a)
    for k, a in enumerate((-25, -8, 8, 25)):               # adopted commitments: filled
        x, y = P(RS, a)
        h.dot(x, y, 9.5)
        h.ring(x, y, 14, "hair")
        pos[f"P{k + 5}"] = (x, y, a)
    x, y = P(RS, 90)                                       # the wager: a balance
    h.stroke([(x - 22, y - 6), (x + 22, y - 6)], "orn")
    h.stroke([(x, y - 6), (x, y + 12)], "orn")
    h.stroke([(x - 8, y + 12), (x + 8, y + 12)], "orn")
    for sx in (-22, 22):
        h.stroke([(x + sx, y - 6), (x + sx - 7, y + 6)], "hair")
        h.stroke([(x + sx, y - 6), (x + sx + 7, y + 6)], "hair")
        h.stroke(arc_pts(x + sx, y + 6, 8, 0, 180, 12), "hair")
    pos["P9"] = (x, y, 90)
    # dotted arcs gathering each group
    dotted(h, arc_pts(cx, cy, RS + 26, 150, 210, 60), 7, 1.0, "ink", skip_ends=False)
    dotted(h, arc_pts(cx, cy, RS + 26, -30, 30, 60), 7, 1.0, "ink", skip_ends=False)
    asterisk(h, *P(RS, 270), 7, 8, weight="hair")

    busy = unary_union([Point(C).buffer(RS + 70), box(X0, Y0, X0 + 250, Y0 + 190), box(X1 - 250, Y0, X1, Y0 + 190),
                        box(X0, Y1 - 190, X0 + 250, Y1), box(X1 - 250, Y1 - 190, X1, Y1), box(X1 - 80, 400, X1, 520)])
    eng.stars(h, rng, busy, (X0 + 26, 0), (Y0 + 22, Y1 - 22), n=14)
    eng.rehearsals(h, d, rng, X1 - 44, 418, 5)
    return d.svg(), dict(pos={k: (v[0], v[1], v[2]) for k, v in pos.items()})


def face_boxes(meta):
    SC, ENG, PICA = "IM FELL English SC", "IM FELL English", "IM FELL DW Pica"
    B = eng.heads("I", "Of the One Question")
    corners = [  # x, y, align, setting, contribution
        (X0 + 26, Y0 + 26, "left", "Mature network and hosting reliability reviews", "little or none beyond a competent review"),
        (X1 - 26 - 236, Y0 + 26, "right", "Agentic AI systems", "supported findings a generic checklist misses"),
        (X0 + 26, Y1 - 128, "left", "Leaderless or adversarial coordination",
         "supported findings a generic checklist misses"),
        (X1 - 26 - 236, Y1 - 128, "right", "Institutions whose corrective authority is itself implicated",
         "diagnosis only"),
    ]
    for i, (x, y, al, s, c) in enumerate(corners):
        B.append(dict(id=f"set{i}", x=x, y=y, w=236, size=14.5, lh=18, font=SC, ls=0.04, align=al, color=eng.INK,
                      runs=[(s, "")]))
        hs = 18 * (2 if len(s) > 26 else 1) + (18 if len(s) > 52 else 0)
        B.append(dict(id=f"con{i}", x=x, y=y + hs + 6, w=236, size=14.5, lh=18, font=PICA, align=al,
                      color=eng.SEPIA, runs=[(c, "i")]))
    for k, (x, y, a) in meta["pos"].items():
        lx, ly = P(RS + 52, a)
        if k == "P9":
            lx, ly = x + 34, y - 10
        B.append(dict(id=f"lab{k}", x=lx - 20, y=ly - 9, w=40, size=13, lh=17, font=SC, ls=0.06, align="center",
                      color=eng.INK, runs=[(k, "")]))
    B.append(dict(id="g1", x=X0 + 22, y=C[1] - 8 + 190, w=150, size=13, lh=16, font=PICA, align="left", color=eng.INK,
                  runs=[("four descriptive claims", "i")]))
    B.append(dict(id="g2", x=X1 - 22 - 150, y=C[1] - 8 + 190, w=150, size=13, lh=16, font=PICA, align="right",
                  color=eng.INK, runs=[("four adopted commitments", "i")]))
    B.append(dict(id="g3", x=560, y=C[1] + RS + 2, w=170, size=13, lh=16, font=PICA, color=eng.INK,
                  runs=[("one procedural wager", "i")]))
    B.append(dict(id="insc", x=110, y=1294, w=780, size=25, lh=34, font=ENG, align="center", color=eng.INK,
                  runs=[("Can it still discover that it is wrong, and act on that, as its power grows?", "i")]))
    return B
