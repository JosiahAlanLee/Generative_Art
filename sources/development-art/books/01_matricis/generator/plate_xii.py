"""Tabula XII · Of the Questions Left Open — plotter: seven figures the pen left unfinished, and an eighth cell."""
import math
import random
import sys

from core import Doc, catmull, arc_pts, bezier
from marks import *
import hands as Hd
from v2_iii import PENS, PAPER
from vi import styles as vstyles, witness, test_strip

W, H = 1000, 1600
CW, CH, GX, GY = 420, 262, 20, 18
X0, Y0 = 70, 300
LABELS = ["No accountable recipient", "Representatives in networks built without them", "The refuge dependency",
          "Records versus fading", "Single-owner infrastructure", "Who judges preservation",
          "Enforcement, allocation and cross-scale coordination", None]


def cell(k):
    c, r = k % 2, k // 2
    return X0 + c * (CW + GX), Y0 + r * (CH + GY)


def start(h, d, p, pen, rng):
    d.circle(f"{pen}_fill", p[0], p[1], 1.6)
    if rng.random() < 0.5:
        h.stroke([(p[0] + 1.4, p[1] + 1.0), (p[0] + 9, p[1] + 2)], "hair", pen, amp=0.1)


def build_face(seed=112):
    rng = random.Random(seed)
    st = vstyles()
    d = Doc(W, H, st, order=["faint_hair", "ghost_orn"] + [k for k in st if k not in ("faint_hair", "ghost_orn")])
    h = Hand(d, rng, "ink", amp=0.25)
    h.stroke([(56, 58), (944, 58)], "orn", "dk")
    witness(h, 40, 40, "dk")
    witness(h, 960, 1560, "dk")
    for k in range(8):
        x, y = cell(k)
        for (cx, cy, sx, sy) in ((x, y, 1, 1), (x + CW, y, -1, 1), (x, y + CH, 1, -1), (x + CW, y + CH, -1, -1)):
            h.stroke([(cx, cy + sy * 14), (cx, cy), (cx + sx * 14, cy)], "hair", "dk", amp=0.02)
    meta = {}
    # 1 no accountable recipient: a route toward an address with no one at it
    x, y = cell(0)
    m = (x + CW - 90, y + 150)
    dotted(h, arc_pts(m[0], m[1], 30, 0, 360, 60), 6, 0.9, "dk", skip_ends=False)
    path = catmull([(x + 40, y + 190), (x + 110, y + 120), (x + 200, y + 175), (m[0] - 70, m[1] - 4)], 18)
    start(h, d, path[0], "dk", rng)
    h.stroke(path, "orn", "dk")
    # 2 representatives in networks built without them: a place for a trustee, outlined, unfilled
    x, y = cell(1)
    nodes = [(x + 70, y + 90), (x + 150, y + 70), (x + 250, y + 95), (x + 340, y + 80), (x + 90, y + 190),
             (x + 190, y + 215), (x + 300, y + 200), (x + 360, y + 170)]
    for i, j in ((0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6), (6, 7), (3, 7), (1, 5), (2, 6)):
        h.stroke([nodes[i], nodes[j]], "hair", "dk")
    for p in nodes:
        h.dot(p[0], p[1], 4.2, "dk")
    trustee = (x + 215, y + 148)
    dotted(h, arc_pts(trustee[0], trustee[1], 15, 0, 360, 40), 5, 0.9, "ol", skip_ends=False)
    p2 = catmull([(x + 30, y + 240), (x + 120, y + 245), (trustee[0] - 40, trustee[1] + 34)], 12)
    start(h, d, p2[0], "ol", rng)
    h.stroke(p2, "hair", "ol")
    # 3 the refuge dependency: walls left with a gap; an inner figure that keeps moving
    x, y = cell(2)
    wall = [(x + 60, y + 70), (x + CW - 60, y + 70), (x + CW - 60, y + CH - 40), (x + 60, y + CH - 40), (x + 60, y + 118)]
    start(h, d, wall[0], "dk", rng)
    h.stroke(wall, "orn", "dk")
    blob = catmull([(x + 150, y + 120), (x + 230, y + 105), (x + 290, y + 150), (x + 250, y + 195), (x + 170, y + 190),
                    (x + 140, y + 150), (x + 175, y + 128)], 14)
    start(h, d, blob[0], "ol", rng)
    h.stroke(blob, "hair", "ol")
    # 4 records versus fading
    x, y = cell(3)
    rec = [(x + 40, y + 110), (x + CW - 40, y + 110)]
    start(h, d, rec[0], "dk", rng)
    h.stroke(rec, "orn", "dk")
    for k in range(13):
        tx = x + 40 + k * 26
        h.stroke([(tx, y + 104), (tx, y + 116)], "hair", "dk")
    cx_, k = x + 40, 0
    start(h, d, (cx_, y + 180), "ol", rng)
    while cx_ < x + CW - 60:
        L = max(2.0, 26 - k * 2.4)
        gap = 8 + k * 3.2
        if rng.random() < 1.0 - k * 0.07:
            h.stroke([(cx_, y + 180), (cx_ + L, y + 180)], "orn", "ol", amp=0.05)
        cx_ += L + gap
        k += 1
    # 5 single-owner infrastructure: one owner; three branches, none chosen
    x, y = cell(4)
    own = (x + 70, y + 140)
    h.dot(own[0], own[1], 9, "dk")
    h.ring(own[0], own[1], 15, "hair", "dk")
    ends = [(x + 300, y + 76), (x + 300, y + 146), (x + 300, y + 216)]
    for i, e in enumerate(ends):
        dotted(h, catmull([(own[0] + 18, own[1]), ((own[0] + e[0]) / 2, (own[1] + e[1]) / 2 + (i - 1) * 6),
                           (e[0] - 34, e[1])], 12), 7, 1.0, "dk", skip_ends=False)
    h.ring(ends[0][0] + 6, ends[0][1], 10, "hair", "dk")
    h.ring(ends[1][0] - 2, ends[1][1], 9, "hair", "dk")
    h.ring(ends[1][0] + 20, ends[1][1], 9, "hair", "ol")
    for (dx, dy) in ((0, -8), (16, 4), (2, 12), (26, -10), (30, 10)):
        h.ring(ends[2][0] + dx, ends[2][1] + dy, 5, "hair", "ol")
    meta["ends"] = ends
    # 6 who judges preservation: a regress, exposed and not ended
    x, y = cell(5)
    c6 = (x + 160, y + 148)
    for i, r in enumerate((92, 72, 54, 38, 24, 12)):
        ox = i * 7
        a1 = 330 if i < 5 else 200
        arc = arc_pts(c6[0] + ox, c6[1], r, -90, a1 - 90, max(16, int(r * 1.6)))
        start(h, d, arc[0], "dk", rng)
        h.stroke(arc, "hair" if i else "orn", "dk")
    ph = XHand(Hand(d, rng, "ink", amp=0.1), lambda p: (p[0] + 1.2, p[1] - 0.8))
    ph.stroke(arc_pts(c6[0], c6[1], 92, 240, 262, 12), "plot" if "rr_plot" in st else "orn", "rr")
    ph.dot(*arc_pts(c6[0], c6[1], 92, 240, 240, 2)[0], 2.0, "rr")
    # 7 enforcement, allocation, cross-scale: two grids at two scales; the binding line stops between them
    x, y = cell(6)
    for i in range(4):
        h.stroke([(x + 40 + i * 50, y + 70), (x + 40 + i * 50, y + 220)], "hair", "dk")
        h.stroke([(x + 40, y + 70 + i * 50), (x + 190, y + 70 + i * 50)], "hair", "dk")
    for i in range(7):
        h.stroke([(x + 270 + i * 16, y + 120), (x + 270 + i * 16, y + 216)], "hair", "ol")
        h.stroke([(x + 270, y + 120 + i * 16), (x + 366, y + 120 + i * 16)], "hair", "ol")
    lk = [(x + 190, y + 145), (x + 226, y + 150)]
    start(h, d, lk[0], "dk", rng)
    h.stroke(lk, "orn", "dk")
    # 8: nothing
    test_strip(h, 120, 1470, rng)
    sig_mark(h, 500, 1532, 10, "dk", "orn")
    return d.svg(), meta


def face_boxes(meta):
    MONO, DM, CUT = "IBM Plex Mono", "DM Serif Display", "Cutive Mono"
    DK, UM = PENS["dk"], PENS["um"]
    B = [dict(id="rh_l", x=56, y=30, w=440, size=11.5, lh=16, font=MONO, ls=0.22, color=DK, runs=[("CLAVICULA MATRICIS", "")]),
         dict(id="rh_r", x=504, y=30, w=440, size=11.5, lh=16, font=MONO, ls=0.22, align="right", color=UM,
              runs=[("TABULA XII", "")]),
         dict(id="title", x=60, y=112, w=880, size=44, lh=50, font=DM, align="center", color=DK,
              runs=[("Of the Questions Left Open", "")])]
    B.append(Hd.tech("insc", 120, 196, 760, "None of these is resolved here, and nothing in the practice requires "
                     "them to be.", size=17, align="center", color=DK))
    for k, lab in enumerate(LABELS):
        if not lab:
            continue
        x, y = cell(k)
        B.append(dict(id=f"lab{k}", x=x + 22, y=y + 16, w=CW - 44, size=12, lh=16, font=MONO, color=UM,
                      runs=[(lab, "")]))
    for i, (t, e) in enumerate(zip(("public ownership", "a public option alongside private ones",
                                    "polycentric replacement"), meta["ends"])):
        B.append(dict(id=f"own{i}", x=e[0] + 40, y=e[1] - 8, w=110, size=10.5, lh=13, font=MONO, color=DK,
                      runs=[(t, "")]))
    B.append(dict(id="folio", x=844, y=1560, w=100, size=11, lh=14, font=MONO, align="right", ls=0.2, color=DK,
                  runs=[("xii", "")]))
    return B
