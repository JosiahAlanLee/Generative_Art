"""Tabula V · Of Visibility Read as Command — a mounted cornmeal record: a network with no centre; outsiders'
red chalk appoints one."""
import math
import random
import sys

from core import arc_pts, catmull
from marks import *
import hands as Hd
import meal

REC = (110, 300, 890, 1120)


def network(rng):
    x0, y0, x1, y1 = REC
    pts = []
    tries = 0
    while len(pts) < 17 and tries < 20000:
        tries += 1
        x, y = rng.uniform(x0 + 90, x1 - 90), rng.uniform(y0 + 90, y1 - 90)
        if all((x - px) ** 2 + (y - py) ** 2 > 150 ** 2 for px, py in pts):
            pts.append((x, y))
    edges = set()
    for i, (ax, ay) in enumerate(pts):
        near = sorted(range(len(pts)), key=lambda j: (pts[j][0] - ax) ** 2 + (pts[j][1] - ay) ** 2)[1:4]
        for j in near[:3]:
            edges.add((min(i, j), max(i, j)))
    return pts, sorted(edges)


def build_face(seed=105):
    d, h, ph, rng = meal.page(seed, REC)
    pts, edges = network(rng)
    # the most visible node: the hand paused there longest, no more
    cx0 = (REC[0] + REC[2]) / 2
    vis = min(range(len(pts)), key=lambda k: (pts[k][0] - cx0 - 60) ** 2 + (pts[k][1] - 640) ** 2)
    for i, j in edges:
        (ax, ay), (bx, by) = pts[i], pts[j]
        mx, my = (ax + bx) / 2 + rng.gauss(0, 10), (ay + by) / 2 + rng.gauss(0, 10)
        h.stroke(catmull([(ax, ay), (mx, my), (bx, by)], 10), "orn")
    for k, (x, y) in enumerate(pts):
        h.ring(x, y, 13, "hair")
        h.dot(x, y, 5.2)
        if k == vis:
            for _ in range(160):          # the thickened deposit: where the hand paused
                a, r = rng.uniform(0, 6.28), abs(rng.gauss(0, 9))
                d.grain(rng.choice(["ink_gm", "ink_gl"]), x + r * math.cos(a), y + r * math.sin(a))
            h.ring(x, y, 22, "orn")
            for _ in range(40):           # the hazard falls where the circle was drawn: grains pushed outward
                a, r = rng.uniform(0, 6.28), rng.uniform(26, 58)
                d.grain("ink_gs", x + r * math.cos(a), y + r * math.sin(a))
    vx, vy = pts[vis]
    # outsiders' labels on tapes, on the mount paper
    labels = [("the press", (150, 248)), ("funders", (40, 700)), ("investigators", (740, 1150))]
    tapes = []
    for text, (lx, ly) in labels:
        w = 30 + 10.4 * len(text)
        d.poly("tapebg_fill", [(lx, ly), (lx + w, ly), (lx + w, ly + 28), (lx, ly + 28)], closed=True)
        d.poly("tape_hair", [(lx, ly), (lx + w, ly), (lx + w, ly + 28), (lx, ly + 28)], closed=True)
        tapes.append((text, lx, ly, w))
    # red chalk: three lines converge, and a circle appoints the centre
    rc = meal.chalk(d, rng)
    for text, lx, ly, w in tapes:
        sx = lx + w / 2 if ly < REC[1] or ly > REC[3] else lx + w
        sy = ly + 28 if ly < REC[1] else ly if ly > REC[3] else ly + 14
        ang = math.atan2(vy - sy, vx - sx)
        ex, ey = vx - 40 * math.cos(ang), vy - 40 * math.sin(ang)
        rc.stroke(catmull([(sx, sy), ((sx + ex) / 2 + rng.gauss(0, 14), (sy + ey) / 2 + rng.gauss(0, 14)), (ex, ey)], 14),
                  "orn", "red")
        arrowhead(rc, (ex, ey), math.degrees(ang), 13, "red", "orn")
    circ = [(vx + (38 + rng.gauss(0, 1.2)) * math.cos(math.radians(a)), vy + (36 + rng.gauss(0, 1.2)) * math.sin(math.radians(a)))
            for a in range(-60, 330, 6)]
    rc.stroke(circ, "core", "red")
    return d.svg(), dict(tapes=tapes, vis=(vx, vy))


def face_boxes(meta):
    ENG, CUT = "IM FELL English", "Cutive Mono"
    B = meal.heads("V", "Of Visibility Read as Command")
    for k, (text, lx, ly, w) in enumerate(meta["tapes"]):
        B.append(Hd.tech(f"tape{k}", lx, ly + 4, w, text, size=15, align="center"))
    B.append(dict(id="insc", x=110, y=1222, w=780, size=24, lh=32, font=ENG, align="center", color=Hd.INK,
                  runs=[("The press, funders and investigators then appoint the centre the network refused to have.",
                         "")]))
    return B
