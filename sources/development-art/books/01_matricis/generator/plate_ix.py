"""Tabula IX · Of a Test That Found Nothing — plotter: two readings of six postmortems draw the same figures."""
import math
import random
import sys

from core import Doc, catmull, arc_pts, bezier, spiral_pts
from marks import *
import hands as Hd
from v2_iii import PENS, PAPER
from vi import styles as vstyles, witness, test_strip

W, H = 1000, 1600
LX0 = 64                        # row labels
GX0, CW = 300, 104              # grid: six columns
GY0 = 286
ROWS = [("competent site-reliability reading", 122, "dk"), ("reading through the practice", 122, "ol"),
        ("the review plus a generic checklist of equal length", 80, "rr"),
        (None, 48, None),
        ("retaliation against reporters", 64, "q"), ("ownership of bottlenecks", 64, "q"),
        ("incentives to game measures", 64, "q")]
NX = 1110                       # the next run, drawn as a plan
CASES = [("AWS S3", "2017"), ("GitLab", "2017"), ("GitHub", "2018"), ("Cloudflare", "2019"), ("Facebook", "2021"),
         ("Cloudflare", "2023")]


def row_y():
    ys, y = [], GY0 + 64
    for lab, hgt, kind in ROWS:
        ys.append((y, hgt))
        y += hgt
    return ys, y


def glyph(h, k, cx, cy, pen, dx=0.0, dy=0.0):
    """the figure each reading drew for case k (both readings draw the same)"""
    X = lambda x, y: (cx + x + dx, cy + y + dy)
    if k == 0:      # more servers removed than the command intended
        for i in range(7):
            x0 = -42 + i * 12
            h.stroke([X(x0, -8), X(x0 + 9, -8), X(x0 + 9, 8), X(x0, 8)], "hair", pen, closed=True, amp=0.05)
            if i >= 2:
                h.stroke([X(x0 - 1, -10), X(x0 + 10, 10)], "hair", pen, amp=0.05)
        h.stroke([X(-44, -18), X(-44, -22), X(-21, -22), X(-21, -18)], "orn", pen, amp=0.05)
    elif k == 1:    # the store emptied; none of the backups held
        h.stroke(arc_pts(cx + dx, cy - 22 + dy, 16, 0, 360, 30), "hair", pen, amp=0.05)
        h.stroke([X(-16, -22), X(-16, 2)], "orn", pen)
        h.stroke([X(16, -22), X(16, 2)], "orn", pen)
        h.stroke(arc_pts(cx + dx, cy + 2 + dy, 16, 0, 180, 20), "orn", pen)
        for i in range(5):
            x0 = -40 + i * 17
            h.stroke([X(x0, 18), X(x0 + 11, 18), X(x0 + 11, 29), X(x0, 29)], "hair", pen, closed=True, amp=0.05)
            h.stroke([X(x0 + 2, 20), X(x0 + 9, 27)], "hair", pen, amp=0.02)
    elif k == 2:    # a brief partition; both sides kept writing
        h.ring(cx - 30 + dx, cy + dy, 9, "orn", pen)
        h.ring(cx + 30 + dx, cy + dy, 9, "orn", pen)
        h.stroke([X(-21, 0), X(-5, 0)], "orn", pen)
        h.stroke([X(5, 0), X(21, 0)], "orn", pen)
        for sx in (-1, 1):
            arrowhead(h, X(sx * 30, -16), -90, 7, pen, "hair")
            h.stroke([X(sx * 30, -12), X(sx * 30, -28)], "hair", pen)
    elif k == 3:    # one expression, backtracking until the processor was full
        pts = spiral_pts(cx + dx, cy + dy, 34, 2, 0, 5.5)
        h.stroke(pts, "hair", pen, amp=0.05)
    elif k == 4:    # the routes withdrawn back to their origin
        h.dot(cx + dx, cy + dy, 4.5, pen)
        for i in range(8):
            a = math.radians(i * 45 + 10)
            p0 = X(36 * math.cos(a), 36 * math.sin(a))
            p1 = X(12 * math.cos(a), 12 * math.sin(a))
            h.stroke([p0, p1], "hair", pen)
            arrowhead(h, p1, math.degrees(a) + 180, 6, pen, "hair")
    elif k == 5:    # power gone at one site; the failover stopped short
        pts = [X(-44, -14), X(-30, -14), X(-26, -22), X(-20, -6), X(-14, -22), X(-8, -6), X(-4, -14), X(4, -14),
               X(6, 18)]
        h.stroke(pts, "hair", pen, amp=0.03)
        h.stroke([X(10, 18), X(36, 18)], "orn", pen)
        h.stroke([X(10, 4), X(30, 4)], "hair", pen)
        arrowhead(h, X(30, 4), 0, 6, pen, "hair")


def build_face(seed=109):
    rng = random.Random(seed)
    st = vstyles()
    d = Doc(W, H, st, order=["faint_hair", "ghost_orn"] + [k for k in st if k not in ("faint_hair", "ghost_orn")])
    h = Hand(d, rng, "ink", amp=0.25)
    h.stroke([(56, 58), (944, 58)], "orn", "dk")
    witness(h, 40, 40, "dk")
    witness(h, 960, 1560, "dk")
    ys, yend = row_y()
    gx1 = GX0 + 6 * CW
    # the plotted grid
    h.stroke([(LX0, GY0), (gx1, GY0)], "orn", "dk", amp=0.05)
    h.stroke([(LX0, GY0 + 64), (gx1, GY0 + 64)], "hair", "dk", amp=0.05)
    for (y, hgt), (lab, _, kind) in zip(ys, ROWS):
        if lab is None:
            continue
        h.stroke([(LX0, y + hgt), (gx1, y + hgt)], "hair", "dk" if kind != "rr" else "dk", amp=0.05)
    for c in range(7):
        x = GX0 + c * CW
        h.stroke([(x, GY0), (x, ys[2][0])], "hair", "dk", amp=0.05)
        h.stroke([(x, ys[4][0]), (x, yend)], "hair", "dk", amp=0.05)
    h.stroke([(LX0, yend), (gx1, yend)], "orn", "dk", amp=0.05)
    # the two readings: the same figure, twice, a hair apart
    for k in range(6):
        cx = GX0 + k * CW + CW / 2
        y1 = ys[0][0] + ys[0][1] / 2
        y2 = ys[1][0] + ys[1][1] / 2
        glyph(h, k, cx, y1, "dk")
        glyph(h, k, cx, y2, "ol", dx=1.6, dy=1.1)
        glyph(h, k, cx, y2, "dk", dx=-0.4, dy=-0.3) if k in (2, 4) else None
        d.circle("dk_fill", cx - 46, ys[0][0] + 12, 1.5)
        d.circle("ol_fill", cx - 46, ys[1][0] + 12, 1.5)
    # the third arm: cells outlined, nothing entered
    ph = XHand(Hand(d, rng, "ink", amp=0.1), lambda p: (p[0] + 1.2, p[1] - 0.8))
    y3, h3 = ys[2]
    for k in range(6):
        x = GX0 + k * CW
        dotted(ph, [(x + 8, y3 + 10), (x + CW - 8, y3 + 10), (x + CW - 8, y3 + h3 - 10), (x + 8, y3 + h3 - 10),
                    (x + 8, y3 + 10)], 6, 0.9, "rr", skip_ends=False)
    ph.dot(GX0 + 8, y3 + 10, 2.2, "rr")
    # the silent variables: unknown in every case
    for r in (4, 5, 6):
        y, hgt = ys[r]
        for k in range(6):
            cx = GX0 + k * CW + CW / 2
            h.ring(cx, y + hgt / 2, 9, "orn", "dk")
    # the next run, as a plan only: unseen cases, three arms, blind judges
    gy = d.poly
    src = (150, NX + 130)
    for i in range(5):
        x, y = src[0] - 26 + i * 4, src[1] - 30 + i * 12
        dotted(h, [(x, y), (x + 44, y), (x + 44, y + 30), (x, y + 30), (x, y)], 5, 0.8, "dk", skip_ends=False)
    judges = (850, NX + 130)
    for i, dy in enumerate((-34, 0, 34)):
        jx, jy = judges[0] + (i - 1) * 8, judges[1] + dy
        dotted(h, arc_pts(jx, jy, 12, 0, 360, 40), 4.5, 0.8, "dk", skip_ends=False)
        h.stroke([(jx - 13, jy - 2), (jx + 13, jy - 2)], "hair", "dk")
    for i, (pen, dy) in enumerate((("dk", -90), ("ol", 0), ("rr", 90))):
        path = catmull([(src[0] + 34, src[1]), (300, src[1] + dy * 0.8), (500, src[1] + dy), (700, src[1] + dy * 0.8),
                        (judges[0] - 30, judges[1])], 20)
        dotted(h if pen != "rr" else ph, path, 7, 1.0, pen, skip_ends=False)
        bx0 = 470
        dotted(h if pen != "rr" else ph, [(bx0, src[1] + dy - 16), (bx0 + 60, src[1] + dy - 16), (bx0 + 60, src[1] + dy + 16),
                                          (bx0, src[1] + dy + 16), (bx0, src[1] + dy - 16)], 5, 0.8, pen, skip_ends=False)
    test_strip(h, 120, 1440, rng)
    sig_mark(h, 500, 1530, 10, "dk", "orn")
    return d.svg(), dict(ys=ys, yend=yend)


def face_boxes(meta):
    MONO, DM, CUT = "IBM Plex Mono", "DM Serif Display", "Cutive Mono"
    DK, UM, OL, RR = PENS["dk"], PENS["um"], PENS["ol"], PENS["rr"]
    ys, yend = meta["ys"], meta["yend"]
    B = [dict(id="rh_l", x=56, y=30, w=440, size=11.5, lh=16, font=MONO, ls=0.22, color=DK, runs=[("CLAVICULA MATRICIS", "")]),
         dict(id="rh_r", x=504, y=30, w=440, size=11.5, lh=16, font=MONO, ls=0.22, align="right", color=UM,
              runs=[("TABULA IX · A TRIAL RECORD", "")]),
         dict(id="title", x=60, y=120, w=880, size=44, lh=50, font=DM, align="center", color=DK,
              runs=[("Of a Test That Found Nothing", "")]),
         dict(id="sub", x=60, y=GY0 - 42, w=880, size=12, lh=16, font=MONO, ls=0.12, align="center", color=UM,
              runs=[("SIX PUBLIC POSTMORTEMS", "")])]
    B[3]["y"] = GY0 - 30
    for k, (a, b) in enumerate(CASES):
        B.append(dict(id=f"c{k}", x=GX0 + k * CW + 4, y=GY0 + 12, w=CW - 8, size=12, lh=17, font=MONO, align="center",
                      color=DK, runs=[(a, ""), ("", "br"), (b, "")]))
    for r, ((y, hgt), (lab, _, kind)) in enumerate(zip(ys, ROWS)):
        if lab is None:
            continue
        col = {"dk": DK, "ol": OL, "rr": RR, "q": DK}[kind]
        B.append(dict(id=f"r{r}", x=LX0, y=y + 10, w=GX0 - LX0 - 14, size=12, lh=16, font=MONO, color=col,
                      runs=[(lab, "")]))
    B.append(dict(id="silent", x=LX0, y=ys[3][0] + 16, w=600, size=11.5, lh=15, font=MONO, ls=0.12, color=UM,
                  runs=[("ALL SIX REPORTS WERE SILENT", "")]))
    B.append(Hd.tech("s20", 120, yend + 44, 760, "I can repeat the operation. I cannot repeat the circumstances.",
                     size=19, align="center", color=DK))
    B.append(dict(id="next", x=60, y=NX - 40, w=880, size=11.5, lh=15, font=MONO, ls=0.12, align="center", color=UM,
                  runs=[("THE NEXT RUN · A PLAN, NOT YET PLOTTED", "")]))
    B.append(dict(id="nx_src", x=80, y=NX + 196, w=150, size=11.5, lh=15, font=MONO, align="center", color=DK,
                  runs=[("unseen cases", "")]))
    B.append(dict(id="nx_j", x=780, y=NX + 196, w=150, size=11.5, lh=15, font=MONO, align="center", color=DK,
                  runs=[("blind judges", "")]))
    for i, (lab, col, dy) in enumerate((("a competent review", DK, -90), ("the review plus the practice", OL, 0),
                                        ("the review plus a generic checklist of equal length", RR, 90))):
        B.append(dict(id=f"nx_a{i}", x=540, y=NX + 130 + dy + (16 if dy > 0 else -34), w=230, size=11, lh=14,
                      font=MONO, color=col, runs=[(lab, "")]))
    B.append(dict(id="folio", x=844, y=1560, w=100, size=11, lh=14, font=MONO, align="right", ls=0.2, color=DK,
                  runs=[("ix", "")]))
    return B
