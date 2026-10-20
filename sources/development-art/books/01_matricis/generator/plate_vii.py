"""Tabula VII · Of the Ten Bindings — engraving: ten constraints bound to an empty seat, and to the plate itself."""
import math
import sys

from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from core import arc_pts, hatch_lines, bezier, catmull, resample
from marks import *
import eng
import hands as Hd

X0, Y0, X1, Y1 = 56, 300, 944, 1252
C = (500, 776)
R0, RI = 80, 58          # the binding ring around the empty seat
R1 = 330                 # ring of seals
WEAR_A = 36              # where the ring's finest hatching wore through


def P(r, a, c=C):
    return (c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))


def cord(h, pts, amp=3.4, lam=15, weight="hair", ticks=True):
    """a two-strand twisted cord along a polyline"""
    P_ = resample(pts, 1.5)
    A, B = [], []
    L = 0.0
    for i, p in enumerate(P_):
        if i:
            L += math.hypot(p[0] - P_[i - 1][0], p[1] - P_[i - 1][1])
        j0, j1 = max(0, i - 1), min(len(P_) - 1, i + 1)
        tx, ty = P_[j1][0] - P_[j0][0], P_[j1][1] - P_[j0][1]
        n = math.hypot(tx, ty) or 1
        nx, ny = -ty / n, tx / n
        s = math.sin(2 * math.pi * L / lam)
        A.append((p[0] + nx * amp * s, p[1] + ny * amp * s))
        B.append((p[0] - nx * amp * s, p[1] - ny * amp * s))
    h.stroke(A, weight, amp=0.05)
    h.stroke(B, weight, amp=0.05)
    if ticks:
        k = int(lam / 1.5 / 2)
        for i in range(k // 2, len(P_), k * 2):
            h.stroke([A[i], B[min(len(B) - 1, i + k)]], "hair", amp=0.02)


def build_face(seed=107):
    d, h, rng = eng.page(seed)
    eng.plate_frame(h, d, X0, Y0, X1, Y1)
    cx, cy = C
    # the empty seat and its binding ring
    h.stroke(arc_pts(cx, cy, R0, 0, 360, 200), "core")
    h.stroke(arc_pts(cx, cy, RI, 0, 360, 180), "orn")
    ring = Point(C).buffer(R0 - 2, 128).difference(Point(C).buffer(RI + 2, 128))
    for ln in hatch_lines(ring, 2.2, 35):
        h.stroke(ln, "hair", amp=0.02)
    for ln in hatch_lines(ring, 3.4, -55):
        h.stroke(ln, "hair", amp=0.02)
    # wear: the finest work went first
    wx, wy = P((R0 + RI) / 2, WEAR_A)
    patch = [rotp for rotp in (P(RI - 1, WEAR_A - 9), P((R0 + RI) / 2, WEAR_A - 13), P(R0 + 1, WEAR_A - 7),
                               P(R0 + 2, WEAR_A + 6), P((R0 + RI) / 2, WEAR_A + 12), P(RI - 2, WEAR_A + 8))]
    d.poly("wear_fill", catmull(patch + patch[:1], 6), closed=True)
    for k in range(3):
        a = WEAR_A - 6 + k * 5
        p0, p1 = P(RI + 4, a), P(RI + 10 + k * 3, a + 2)
        d.poly("rub_hair", [p0, p1])

    seals = []
    for k in range(10):
        a = -90 + k * 36
        sx, sy = P(R1, a)
        seals.append((sx, sy, a))
        h.ring(sx, sy, 26, "core")
        h.ring(sx, sy, 20, "hair")
        for j in range(8):
            aa = math.radians(j * 45 + 22.5)
            h.stroke([(sx + 26 * math.cos(aa), sy + 26 * math.sin(aa)), (sx + 32 * math.cos(aa), sy + 32 * math.sin(aa))],
                     "hair", amp=0.02)
        p0, p1 = P(R1 - 30, a), P(R0 + 3, a)
        if k == 9:
            # the tenth passes a gatekeeper; a second strand goes round it
            gm = P((R1 + R0) / 2, a)
            g0, g1 = P((R1 + R0) / 2 + 26, a), P((R1 + R0) / 2 - 26, a)
            cord(h, [p0, g0], weight="orn")
            cord(h, [g1, p1], weight="orn")
            # the gate, set across the cord
            ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a))
            vx, vy = -uy, ux
            T1 = [(gm[0] + 26 * ux + 24 * vx, gm[1] + 26 * uy + 24 * vy), (gm[0] + 26 * ux - 24 * vx, gm[1] + 26 * uy - 24 * vy), gm]
            T2 = [(gm[0] - 26 * ux + 24 * vx, gm[1] - 26 * uy + 24 * vy), (gm[0] - 26 * ux - 24 * vx, gm[1] - 26 * uy - 24 * vy), gm]
            for T in (T1, T2):
                inset = Polygon(T).buffer(-3.5)
                if not inset.is_empty:
                    for ln in hatch_lines(inset, 3.0, a + 45):
                        h.stroke(ln, "hair", amp=0.02)
            h.stroke(T1, "orn", closed=True)
            h.stroke(T2, "orn", closed=True)
            h.dot(*gm, 4.2)
            by = [g0, (gm[0] + 30 * ux + 52 * vx, gm[1] + 30 * uy + 52 * vy), (gm[0] + 64 * vx, gm[1] + 64 * vy),
                  (gm[0] - 30 * ux + 52 * vx, gm[1] - 30 * uy + 52 * vy), g1]
            cord(h, catmull(by, 10), amp=2.2, lam=11, weight="hair", ticks=False)
            meta_gate = gm
        else:
            cord(h, [p0, p1], weight="orn")
    # the bindings also hold the plate: a stitch over the frame above seal 1 and below seal 6
    for (a, yb, sgn) in ((-90, Y0, -1), (90, Y1, 1)):
        sx, sy = P(R1 + 30, a)
        path = [(sx, sy), (sx, yb - sgn * 40), (sx + 4, yb + sgn * 12), (sx + 26, yb + sgn * 18), (sx + 30, yb - sgn * 10),
                (sx + 22, yb - sgn * 44)]
        cord(h, catmull(path, 12), weight="orn")
    busy = unary_union([Point(C).buffer(R1 + 50), box(X1 - 330, Y1 - 150, X1, Y1), box(470, Y0, 560, Y0 + 120),
                        box(470, Y1 - 120, 560, Y1)])
    eng.stars(h, rng, busy, (X0 + 26, 0), (Y0 + 22, Y1 - 22), n=12)
    eng.rehearsals(h, d, rng, X0 + 18, Y1 - 140, 5)
    return d.svg(), dict(seals=[(x, y, a) for x, y, a in seals], gate=meta_gate)


def face_boxes(meta):
    ENG = "IM FELL English"
    B = eng.heads("VII", "Of the Ten Bindings")
    for k, (x, y, a) in enumerate(meta["seals"]):
        B.append(dict(id=f"n{k + 1}", x=x - 20, y=y - 12, w=40, size=19, lh=24, font=ENG, align="center",
                      color=eng.INK, runs=[(str(k + 1), "")]))
    B.append(Hd.cust("s12", X1 - 318, Y1 - 118, 290, "The plate wore through where the prohibition had been finest.",
                     size=17.5, align="right"))
    B.append(dict(id="insc", x=110, y=1294, w=780, size=25, lh=34, font=ENG, align="center", color=eng.INK,
                  runs=[("These bound every application of the practice, including applications to itself.", "i")]))
    return B
