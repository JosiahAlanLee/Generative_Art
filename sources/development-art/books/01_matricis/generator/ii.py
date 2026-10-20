"""Tabula II · Of the Two Clocks — engraving, with one clock on a pasted drawing."""
import math
import random
import sys

from shapely.geometry import Polygon, Point
from core import Doc, arc_pts, hatch_lines, bezier, rot, catmull
from marks import *
import hands as Hd

W, H = 1000, 1600
PAPER, INK, RED, SEPIA = "#ebe1c8", Hd.INK, Hd.RED, Hd.SEPIA
PEN = "#3d2f22"                       # brown-black pen on the pasted drawing
C1, R1 = (330, 700), 250              # cut into the plate
C2, R2 = (745, 700), 165              # drawn on the paste
TANGENT = (580, 700)
PASTE = [(566, 512), (928, 516), (925, 890), (569, 886)]
PASTE_ROT = 1.2
PM = (40, 420, 960, 990)              # plate mark
A_REC, A_DIS1 = 150, 360              # recognition -> dispatch on the first face (deg, clockwise)
A_DIS2, A_RES = 180, 420              # dispatch -> restoration on the second face (420 = 60)


def styles():
    st = {}
    for c, col in (("ink", INK), ("red", RED), ("sep", SEPIA), ("pen", PEN), ("pm", "#d6c9aa"), ("pl", "#f6efde")):
        for k, wdt in (("core", 2.8), ("orn", 1.5), ("hair", 0.85), ("cip", 1.3)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    st["fox_fill"] = {"fill": "#b89a6a", "stroke": "none", "opacity": "0.15"}
    st["tone_fill"] = {"fill": "#d9caa6", "stroke": "none", "opacity": "0.28"}
    st["shadow_fill"] = {"fill": "#8a7a5c", "stroke": "none", "opacity": "0.28"}
    st["paste_fill"] = {"fill": "#f3ebd7", "stroke": "none"}
    st["glue_orn"] = {"fill": "none", "stroke": "#cdbb93", "stroke-width": "3", "opacity": "0.55",
                      "stroke-linejoin": "round"}
    st["tapebg_fill"] = {"fill": "#f4edda", "stroke": "none"}
    st["tape_hair"] = {"fill": "none", "stroke": "#b9ab8c", "stroke-width": "0.85"}
    return st


def order(st):
    first = ["tone_fill", "fox_fill"]
    plate = [k for k in st if k.startswith(("ink_", "sep_", "pm_", "pl_"))]
    paste = ["shadow_fill", "paste_fill", "glue_orn", "pen_core", "pen_orn", "pen_hair", "pen_cip", "pen_fill"]
    late = ["tapebg_fill", "tape_hair", "red_core", "red_orn", "red_hair", "red_cip", "red_fill"]
    return first + plate + paste + late


def P(c, r, a):
    return (c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))


def build_face(seed=21):
    rng = random.Random(seed)
    st = styles()
    d = Doc(W, H, st, order=order(st))
    h = Hand(d, rng, "ink", amp=0.35)
    for _ in range(150):
        d.circle("fox_fill", rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 3.2) ** 1.4)
    h.stroke([(56, 58), (944, 58)], "orn")
    h.stroke([(56, 62), (944, 62)], "hair")
    band_x(h, (380, 211), (620, 211), 9, 12, "hair", "ink")
    x0, y0, x1, y1 = PM
    d.poly("tone_fill", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True)
    h.stroke([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "orn", "pm", closed=True, amp=0.15)
    h.stroke([(x0 + 1.6, y0 + 1.6), (x1 - 1.6, y0 + 1.6), (x1 - 1.6, y1 - 1.6), (x0 + 1.6, y1 - 1.6)], "hair", "pl",
             closed=True, amp=0.15)

    # three witness lines, engraved, running under the paste
    wy = [C2[1] - R2, C2[1], C2[1] + R2]
    for y in wy:
        h.stroke([(70, y), (930, y)], "hair", amp=0.1)
        asterisk(h, 64, y, 4, 8, weight="hair")

    # ---- the first clock: cut into the plate
    cx, cy = C1
    h.stroke(arc_pts(cx, cy, R1, 0, 360, 240), "core")
    h.stroke(arc_pts(cx, cy, R1 - 9, 0, 360, 240), "hair")
    h.stroke(arc_pts(cx, cy, R1 - 44, 0, 360, 220), "orn")
    # rim shading: close radial hatching on the lower right of the rim
    for k in range(150):
        a = 0 + k * 1.2
        p0, p1 = P(C1, R1 - 8, a), P(C1, R1 - 1, a + 2.5)
        h.stroke([p0, p1], "hair", amp=0.02)
    for k in range(60):
        a = k * 6
        r0 = R1 - 44
        h.stroke([P(C1, r0 + 2, a), P(C1, r0 + (16 if k % 5 == 0 else 9), a)], "hair" if k % 5 else "orn", amp=0.02)
    # the interval as a parallel-hatched sector
    sector = Polygon([C1] + arc_pts(cx, cy, R1 - 52, A_REC, A_DIS1, 120))
    sector = sector.difference(Point(C1).buffer(34))
    for ln in hatch_lines(sector, 4.2, 38):
        h.stroke(ln, "hair", amp=0.05)
    for a in (A_REC, A_DIS1):
        h.stroke([P(C1, 34, a), P(C1, R1 - 44, a)], "orn")
    # boss and a single hand at the dispatch end
    h.ring(cx, cy, 14, "orn")
    h.dot(cx, cy, 6)
    hand = [P(C1, -26, A_DIS1), P(C1, 30, A_DIS1 - 4), P(C1, R1 - 62, A_DIS1), P(C1, 30, A_DIS1 + 4)]
    h.fill_poly(hand)
    # the shared tick: engraved half
    h.stroke([(TANGENT[0] - 26, TANGENT[1]), (566, TANGENT[1])], "core")

    # ---- the paste: a separate sheet laid over the plate, slightly turned
    pc = (746, 701)
    paste = [rot(p, math.radians(PASTE_ROT), pc) for p in PASTE]
    d.poly("shadow_fill", [(x + 4, y + 5) for x, y in paste], closed=True)
    d.poly("paste_fill", paste, closed=True)
    d.poly("glue_orn", paste, closed=True)
    # a lifted corner, top right
    tr = paste[1]
    fold = [(tr[0] - 34, tr[1]), (tr[0], tr[1] + 34), (tr[0] - 26, tr[1] + 26)]
    d.poly("shadow_fill", [(tr[0] - 34, tr[1]), (tr[0], tr[1] + 34), (tr[0] + 3, tr[1] + 3)], closed=True)
    d.poly("paste_fill", fold, closed=True)
    pen = XHand(Hand(d, rng, "ink", amp=0.7), lambda p: rot(p, math.radians(PASTE_ROT), pc))
    # the pasted drawing's own witness lines, a hair off the plate's
    for y in wy:
        pen.stroke([(580, y + 2.2), (912, y + 2.2)], "hair", "pen")
    cx2, cy2 = C2
    pen.stroke(arc_pts(cx2, cy2, R2, 0, 360, 200), "orn", "pen")
    pen.stroke(arc_pts(cx2, cy2, R2 - 30, 0, 360, 180), "hair", "pen")
    for k in range(60):
        a = k * 6
        pen.stroke([P(C2, R2 - 30, a), P(C2, R2 - 30 + (12 if k % 5 == 0 else 6), a)], "hair", "pen")
    sector2 = Polygon([C2] + arc_pts(cx2, cy2, R2 - 36, A_DIS2, A_RES, 120)).difference(Point(C2).buffer(22))
    for ln in hatch_lines(sector2, 6.5, -50):
        pen.stroke(ln, "hair", "pen")
    for a in (A_DIS2, A_RES):
        pen.stroke([P(C2, 22, a), P(C2, R2 - 30, a)], "orn", "pen")
    pen.ring(cx2, cy2, 9, "orn", "pen")
    pen.stroke([P(C2, -14, A_RES), P(C2, R2 - 44, A_RES)], "orn", "pen")
    # the shared tick: drawn half
    pen.stroke([(568, TANGENT[1] + 1), (TANGENT[0] + 26, TANGENT[1] + 1)], "core", "pen")

    # an access request, a fine line from the second face back across the boundary into the first
    req = catmull([(706, 812), (640, 792), (592, 760), (548, 760), (500, 776)], 14)
    h.stroke(req, "hair", "ink", amp=0.25)
    arrowhead(h, req[-1], 160, 8, "ink", "hair")

    # typed labels on tapes (the later technical hand)
    for (lx0, ly0, lx1, ly1) in ((62, 846, 186, 870), (550, 545, 646, 569), (776, 870, 914, 894)):
        d.poly("tapebg_fill", [(lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1)], closed=True)
        d.poly("tape_hair", [(lx0, ly0), (lx1, ly0), (lx1, ly1), (lx0, ly1)], closed=True)
    h.stroke([(598, 570), (586, 690)], "hair", "sep", amp=0.1)
    h.stroke([P(C1, R1 + 4, A_REC), (150, 846)], "hair", "sep", amp=0.1)
    pen.stroke([P(C2, R2 + 4, A_RES), (842, 872)], "hair", "sep")

    # red strikes are text; a small red caret where M. writes
    band_x(h, (420, 1216), (580, 1216), 7, 8, "hair", "sep", centre_dots=True)
    sig_mark(h, 500, 1550, 11, "ink", "orn")
    return d.svg(), {}


def face_boxes(meta):
    SC, ENG = "IM FELL English SC", "IM FELL English"
    B = [dict(id="rh_l", x=56, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, color=INK, runs=[("Clavicula Matricis", "")]),
         dict(id="rh_r", x=524, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, align="right", color=RED,
              runs=[("Tabula II", "")]),
         dict(id="title", x=60, y=150, w=880, size=42, lh=48, font=ENG, align="center", color=INK,
              runs=[("Of the Two Clocks", "")])]
    B.append(Hd.tech("t_rec", 62, 849, 124, "recognition", size=14, align="center"))
    B.append(Hd.tech("t_dis", 550, 548, 96, "dispatch", size=14, align="center"))
    B.append(Hd.tech("t_res", 776, 873, 138, "restoration", size=14, align="center"))
    B.append(Hd.cust("insc", 110, 1050, 780, [("The ", ""), ("first", "x"), (" clock measures the wound. The ", ""),
                                               ("second", "x"), (" measures permission to touch it.", "")],
                     size=23, align="center"))
    B.append(Hd.mhand("m_names", 560, 1124, 340, "The names have changed places twice.", size=23))
    B.append(dict(id="folio", x=440, y=1568, w=120, size=12, lh=16, font=SC, ls=0.2, align="center", color=SEPIA,
                  runs=[("ii", "")]))
    return B


def build_verso(seed=22):
    boxes, meta = verso_boxes()
    rng = random.Random(seed)
    st = styles()
    d = Doc(W, H, st, order=order(st))
    h = Hand(d, rng, "ink", amp=0.35)
    for _ in range(110):
        d.circle("fox_fill", rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 3.0) ** 1.4)
    h.stroke([(56, 58), (944, 58)], "orn")
    h.stroke([(56, 62), (944, 62)], "hair")
    # M.'s entry: one interval ruler with the dispatch entered twice
    y = meta["y_m"] + 92
    h.stroke([(200, y), (800, y)], "orn")
    for k in range(31):
        x = 200 + k * 20
        h.stroke([(x, y), (x, y - (9 if k % 5 == 0 else 5))], "hair", amp=0.02)
    for x, lab in ((200, 0), (800, 1)):
        h.stroke([(x, y - 14), (x, y + 6)], "orn")
    rh = XHand(h, lambda p: (p[0] + 1.1, p[1] - 0.7))
    for x in (452, 528):
        rh.stroke([(x, y - 22), (x, y + 10)], "core", "red")
    rh.stroke(bezier((452, y + 14), (470, y + 26), (510, y + 26), (528, y + 14), 20), "hair", "red")
    return d.svg(), boxes, meta


def verso_boxes():
    from layout import box_height
    SC = "IM FELL English SC"
    B, meta = [], {}
    B.append(dict(id="rh_l", x=56, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, color=INK, runs=[("Clavicula Matricis", "")]))
    B.append(dict(id="rh_r", x=524, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, align="right", color=RED,
                  runs=[("Verso · Tabula II", "")]))
    c = Hd.cust("d_main", 150, 0, 700, "Start the first when the break is recognized. Stop it when the work is sent. "
                "Let the second continue until the work is done. Enter the names of these moments before entering their "
                "distance.\nDo not weigh the stone by the time spent asking to lift it. Do not suppose that every hand "
                "beyond the gate has permission to proceed.\nIf the account provides only one hour, preserve one hour. "
                "A second dial drawn upon the leaf will not recover the missing witness.", size=24)
    hc = box_height(c) * 1.12
    block = hc + 80 + 220 + 40
    top = max(150, (100 + 1540 - block) / 2)
    c["y"] = top
    B.append(c)
    y = c["y"] + hc + 80
    meta["y_m"] = y
    B.append(Hd.mhand("d_m", 150, y, 700, "The dispatch was repeated. I have entered both times.", size=28))
    B.append(Hd.tech("d_tick", 400, y + 112, 200, "dispatch · dispatch", size=13, align="center", color=RED))
    y2 = y + 220
    B.append(Hd.cust("d_c", 150, y2, 700, "Then the old partition no longer fits the account.", size=24))
    meta["y_end"] = y2 + 40
    return B, meta
