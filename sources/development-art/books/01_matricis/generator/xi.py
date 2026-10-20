"""Tabula XI · Of the Closed Neck — engraving with a plotter overlay; its verso; the transposition border strip."""
import math
import random
import sys

from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from core import Doc, catmull, path_len, point_at, offset_line, arc_pts, bezier, hatch_lines, rot
from marks import *
import hands as Hd
import layout

W, H = 1000, 1600
PAPER, INK, RED, SEPIA = "#ebe1c8", Hd.INK, Hd.RED, Hd.SEPIA
RR = "#9e3b24"                 # the plotter's rust, one family of later intervention on this leaf
AX = 500
X0, Y0, X1, Y1 = 56, 300, 944, 1420
TITLE_Y = 150

ORIG_L, ORIG_R = (262, 392), (738, 392)
J = (AX, 500)
G1 = (AX, 750, 260, 330)       # cx, cy, w, ht — the closed neck
GAP = 5.0                       # the minute gap the engraver closed
G2 = (AX, 1072, 140, 140)       # the lower gate
TERM = (AX, 1200)
LX = 793                        # x of the bypass's vertical run
FIELDS = [(100, 1252, 230, 136), (385, 1252, 230, 136), (670, 1252, 230, 136)]
INSET = (84, 684, 226, 70)


def styles():
    st = {}
    for c, col in (("ink", INK), ("red", RED), ("sep", SEPIA), ("rr", RR), ("pm", "#d6c9aa"), ("pl", "#f6efde")):
        for k, wdt in (("core", 2.9), ("orn", 1.55), ("hair", 0.9), ("cip", 1.35), ("plot", 1.7)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    st["fox_fill"] = {"fill": "#b89a6a", "stroke": "none", "opacity": "0.15"}
    st["tone_fill"] = {"fill": "#d9caa6", "stroke": "none", "opacity": "0.28"}
    st["rub_hair"] = {"fill": "none", "stroke": INK, "stroke-width": "0.9", "opacity": "0.22", "stroke-linecap": "round"}
    st["field_fill"] = {"fill": "#efe5cc", "stroke": "none", "opacity": "0.7"}
    st["paste_fill"] = {"fill": "#f3ebd7", "stroke": "none"}
    st["shadow_fill"] = {"fill": "#8a7a5c", "stroke": "none", "opacity": "0.26"}
    st["hole_fill"] = {"fill": "#5a4c38", "stroke": "none", "opacity": "0.55"}
    return st


def order(st):
    first = ["tone_fill", "fox_fill", "field_fill", "shadow_fill", "paste_fill", "hole_fill", "rub_hair"]
    late = [k for k in st if k.startswith("rr_")]
    return first + [k for k in st if k not in first and k not in late] + late


def plate_frame(h, d, rng):
    pm = (X0 - 16, Y0 - 16, X1 + 16, Y1 + 16)
    d.poly("tone_fill", [(pm[0], pm[1]), (pm[2], pm[1]), (pm[2], pm[3]), (pm[0], pm[3])], closed=True)
    h.stroke([(pm[0], pm[1]), (pm[2], pm[1]), (pm[2], pm[3]), (pm[0], pm[3])], "orn", "pm", closed=True, amp=0.15)
    h.stroke([(pm[0] + 1.6, pm[1] + 1.6), (pm[2] - 1.6, pm[1] + 1.6), (pm[2] - 1.6, pm[3] - 1.6),
              (pm[0] + 1.6, pm[3] - 1.6)], "hair", "pl", closed=True, amp=0.15)
    h.stroke([(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)], "core", closed=True)
    h.stroke([(X0 + 8, Y0 + 8), (X1 - 8, Y0 + 8), (X1 - 8, Y1 - 8), (X0 + 8, Y1 - 8)], "hair", closed=True)
    band = Polygon([(X0 + 1.5, Y0 + 1.5), (X1 - 1.5, Y0 + 1.5), (X1 - 1.5, Y1 - 1.5), (X0 + 1.5, Y1 - 1.5)]).difference(
        Polygon([(X0 + 7, Y0 + 7), (X1 - 7, Y0 + 7), (X1 - 7, Y1 - 7), (X0 + 7, Y1 - 7)]))
    for ln in hatch_lines(band, 3.2, 45):
        h.stroke(ln, "hair", amp=0.05)
    for (cx, cy) in ((X0, Y0), (X1, Y0), (X0, Y1), (X1, Y1)):
        s = 13
        h.fill_poly([(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)])
        asterisk(h, cx, cy, 8.5, 8, rot_deg=22.5, weight="orn", color="pl", centre=False)


def gate_open_form(cx, cy, w, ht, g):
    """the two triangles as first cut: apexes stop short of each other"""
    top, bot = cy - ht / 2, cy + ht / 2
    A = [(cx - w / 2, top), (cx + w / 2, top), (cx, cy - g)]
    B = [(cx - w / 2, bot), (cx + w / 2, bot), (cx, cy + g)]
    return A, B


def big_gate(h, cx, cy, w, ht, g):
    A, B = gate_open_form(cx, cy, w, ht, g)
    for T in (A, B):
        inset = Polygon(T).buffer(-w * 0.045)
        if not inset.is_empty and inset.geom_type == "Polygon":
            lattice_fill(h, list(inset.exterior.coords)[:-1], w * 0.088, marker="mixed", weight="hair", color="ink",
                         outline=False, msize=0.26)
    # the original cut: each triangle drawn as its two long sides and base; the apex tips end short of the neck
    for T in (A, B):
        h.stroke([T[2], T[0], T[1], T[2]], "core")
    # a thin echo just outside each base, as the VIII gate has none: the larger plate earns one
    for T, sgn in ((A, -1), (B, 1)):
        h.stroke([(T[0][0] - 6, T[0][1] + sgn * 7), (T[1][0] + 6, T[1][1] + sgn * 7)], "hair")
    for c in (A[0], A[1], B[0], B[1]):
        sx = -1 if c[0] < cx else 1
        sy = -1 if c[1] < cy else 1
        curl(h, c[0], c[1], 0 if sx > 0 else 180, w * 0.09, w * 0.06, 1.35, hand=sx * sy, weight="hair")
        asterisk(h, c[0] + sx * w * 0.02, c[1] + sy * w * 0.02, w * 0.045, 8, weight="hair", centre=False)
    return A, B


def closure(h, cx, cy, g):
    """the engraver's addition: joins the apexes, crisp and a hair off the original axis, with burr"""
    ox, oy = 1.7, 0.6
    k = [(cx + ox, cy - g - 5 + oy), (cx + 6.6 + ox, cy + oy), (cx + ox, cy + g + 5 + oy), (cx - 6.6 + ox, cy + oy)]
    h.fill_poly(k)
    h.stroke(k, "orn", closed=True, amp=0.02)
    # the old apex terminals still show as two small spurs left of the new knot
    h.stroke([(cx - 0.8, cy - g), (cx - 3.2, cy - g + 1.6)], "hair", amp=0.01)
    h.stroke([(cx - 0.8, cy + g), (cx - 3.2, cy + g - 1.6)], "hair", amp=0.01)
    # copper burr thrown up along the fresh cut
    for (dx, dy, r) in ((9.8, -2.4, 1.0), (11.0, 0.8, 0.8), (9.4, 3.8, 0.65), (12.8, -0.6, 0.5), (8.6, -6.2, 0.55)):
        h.dot(cx + ox + dx, cy + oy + dy, r)


def node(h, x, y):
    sig_standing(h, x, y, 11, crown=False)


def route(h, pts, end_ang):
    P = catmull(pts, 20)
    h.stroke(P, "core")
    arrowhead(h, P[-1], end_ang, 11, "ink", "core")
    return P


def mini_gates(h, fx, fy, fw, fh):
    """the engraved form of a tracing field: two small gates on a spine"""
    cx = fx + fw / 2
    g1y, g2y = fy + 56, fy + 112
    for (cy, w, ht) in ((g1y, 40, 46), (g2y, 26, 26)):
        A = [(cx - w / 2, cy - ht / 2), (cx + w / 2, cy - ht / 2), (cx, cy)]
        B = [(cx - w / 2, cy + ht / 2), (cx + w / 2, cy + ht / 2), (cx, cy)]
        h.stroke(A, "orn", closed=True, amp=0.06)
        h.stroke(B, "orn", closed=True, amp=0.06)
    h.fill_poly([(cx + 0.6, g1y - 5), (cx + 3.4, g1y), (cx + 0.6, g1y + 5), (cx - 2.2, g1y)])
    h.dot(cx, g2y, 2.2)
    h.stroke([(cx, g1y + 23), (cx, g2y - 13)], "hair")
    # two entry stubs above, meeting
    h.stroke([(cx - 34, fy + 14), (cx - 10, fy + 24), (cx, fy + 26)], "hair", amp=0.04)
    h.stroke([(cx + 34, fy + 14), (cx + 10, fy + 24), (cx, fy + 26)], "hair", amp=0.04)
    h.stroke([(cx, fy + 26), (cx, g1y - 23)], "hair")
    return cx, g1y, g2y


def stop_tick(h, x, y, w=9):
    h.stroke([(x - w, y), (x + w, y)], "orn", "rr", amp=0.02)


def build_face(seed=111):
    rng = random.Random(seed)
    st = styles()
    d = Doc(W, H, st, order=order(st))
    h = Hand(d, rng, "ink", amp=0.4)
    for _ in range(150):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        d.circle("fox_fill", x, y, rng.uniform(0.6, 3.2) ** 1.4)

    h.stroke([(56, 58), (944, 58)], "orn")
    h.stroke([(56, 62), (944, 62)], "hair")
    band_x(h, (380, TITLE_Y + 61), (620, TITLE_Y + 61), 9, 12, "hair", "ink")
    asterisk(h, 370, TITLE_Y + 61, 6, 8, weight="hair")
    asterisk(h, 630, TITLE_Y + 61, 6, 8, weight="hair")
    plate_frame(h, d, rng)
    sig_mark(h, 500, 1530, 11, "ink", "orn")

    # ------------------------------------------------ the black impression
    node(h, *ORIG_L)
    node(h, *ORIG_R)
    rl = route(h, [(ORIG_L[0], ORIG_L[1] + 28), (ORIG_L[0] + 6, J[1] - 42), (330, J[1] - 12), (420, J[1]), (J[0] - 13, J[1])], 0)
    rr_ = route(h, [(ORIG_R[0], ORIG_R[1] + 28), (ORIG_R[0] - 6, J[1] - 42), (670, J[1] - 12), (580, J[1]), (J[0] + 13, J[1])], 180)
    h.ring(J[0], J[1], 6.5, "orn")
    h.dot(J[0], J[1], 2.2)
    cx, cy, w1, ht1 = G1
    h.stroke([(AX, J[1] + 7), (AX, cy - ht1 / 2 - 14)], "core")
    arrowhead(h, (AX, cy - ht1 / 2 - 12), 90, 11, "ink", "core")
    A, B = big_gate(h, cx, cy, w1, ht1, GAP)
    closure(h, cx, cy, GAP)
    # the engraved continuation below the neck, as cut before the neck was closed
    g2x, g2y, w2, ht2 = G2
    h.stroke([(AX, cy + ht1 / 2 + 8), (AX, g2y - ht2 / 2 - 14)], "core")
    arrowhead(h, (AX, g2y - ht2 / 2 - 12), 90, 11, "ink", "core")
    sig_gate(h, g2x, g2y, w2, ht2, red="ink")
    for sgn in (-1, 1):
        leaf(h, (AX + sgn * 12, g2y), (AX + sgn * 50, g2y), 12, "orn", "ink", 5)
    h.stroke([(AX, g2y + ht2 / 2 + 6), (AX, TERM[1] - 30)], "core")
    arrowhead(h, (AX, TERM[1] - 28), 90, 11, "ink", "core")
    sig_standing(h, TERM[0], TERM[1], 10, crown=False)

    # the inset: the abbreviated copy, in a cartouche ruled for a longer line
    ix, iy, iw, ih = INSET
    h.stroke([(ix, iy), (ix + iw, iy), (ix + iw, iy + ih), (ix, iy + ih)], "orn", closed=True, amp=0.12)
    h.stroke([(ix + 5, iy + 5), (ix + iw - 5, iy + 5), (ix + iw - 5, iy + ih - 5), (ix + 5, iy + ih - 5)], "hair",
             closed=True, amp=0.1)
    for (x, y) in ((ix, iy), (ix + iw, iy), (ix, iy + ih), (ix + iw, iy + ih)):
        asterisk(h, x, y, 4.5, 8, weight="hair")
    h.stroke([(ix + 16, iy + ih - 17), (ix + iw - 16, iy + ih - 17)], "hair", "sep", amp=0.05)   # the ruled line

    # three tracing fields: the engraved forms
    for i, (fx, fy, fw, fh) in enumerate(FIELDS):
        d.poly("field_fill", [(fx, fy), (fx + fw, fy), (fx + fw, fy + fh), (fx, fy + fh)], closed=True)
        h.stroke([(fx, fy), (fx + fw, fy), (fx + fw, fy + fh), (fx, fy + fh)], "orn", closed=True, amp=0.1)
        h.stroke([(fx + 4, fy + 4), (fx + fw - 4, fy + 4), (fx + fw - 4, fy + fh - 4), (fx + 4, fy + fh - 4)], "hair",
                 closed=True, amp=0.08)
        mini_gates(h, fx, fy, fw, fh)

    # burin rehearsals at the plate's right edge; one start rubbed down
    for k, (y, L, bend) in enumerate(((1004, 18, 3), (1020, 11, -2), (1034, 24, 4), (1050, 9, 1), (1063, 16, -3),
                                      (1080, 21, 2))):
        x0 = 906 + rng.uniform(-2, 2)
        pts = bezier((x0, y), (x0 + L * 0.4, y - bend), (x0 + L * 0.7, y + bend * 0.5), (x0 + L, y + 1), 10)
        h.stroke(pts, "hair", amp=0.05)
    d.poly("rub_hair", bezier((904, 1098), (912, 1094), (920, 1100), (928, 1097), 10))

    # mirrored stars: sparse, clear of everything drawn or written
    busy = [LineString(rl).buffer(26), LineString(rr_).buffer(26), Point(J).buffer(30),
            box(cx - w1 / 2 - 60, cy - ht1 / 2 - 40, cx + w1 / 2 + 60, cy + ht1 / 2 + 40),
            box(AX - 110, g2y - ht2 / 2 - 50, AX + 110, TERM[1] + 40), box(AX - 40, J[1], AX + 40, g2y),
            box(ix - 20, iy - 20, ix + iw + 20, iy + ih + 20), box(X0, 1200, X1, Y1),
            Point(ORIG_L).buffer(70), Point(ORIG_R).buffer(70), box(LX - 150, 520, X1, 1010),
            box(880, 980, X1, 1120)]
    busy = unary_union(busy)
    placed = []
    tries = 0
    while len(placed) < 20 and tries < 6000:
        tries += 1
        x, y = rng.uniform(X0 + 26, AX - 40), rng.uniform(Y0 + 22, 1190)
        r = rng.uniform(2.6, 4.4)
        xm = 2 * AX - x
        ok = all(not busy.intersects(Point(px, y).buffer(r + 10)) for px in (x, xm))
        ok = ok and all((x - px) ** 2 + (y - py) ** 2 > (r + pr + 34) ** 2 for (px, py, pr) in placed)
        if ok:
            rd = rng.uniform(0, 45)
            for xx in (x, xm):
                placed.append((xx, y, r))
                asterisk(h, xx, y, r, 8, rot_deg=rd, weight="hair", color="sep", centre=True)

    # ------------------------------------------------ the plotter overlay, a hair off register
    ph = XHand(Hand(d, rng, "ink", amp=0.12), lambda p: (p[0] + 1.3, p[1] - 0.9))
    byp = catmull([(AX + 2, J[1] + 45), (560, J[1] + 40), (660, J[1] + 34), (744, J[1] + 50), (LX - 5, 620), (LX, 750),
                   (LX - 5, 870), (750, 940), (660, 976), (600, 972), (556, 976), (527, g2y - ht2 / 2 - 8)], 18)
    ph.stroke(byp, "plot", "rr")
    a_end = math.degrees(math.atan2(byp[-1][1] - byp[-4][1], byp[-1][0] - byp[-4][0]))
    arrowhead(ph, byp[-1], a_end, 11, "rr", "plot")
    ph.dot(byp[0][0], byp[0][1], 2.6, "rr")                                   # pen down
    ph.stroke([(byp[0][0] + 1.6, byp[0][1] + 1.2), (byp[3][0] + 1.6, byp[3][1] + 1.2)], "hair", "rr")  # second start
    # a registration witness for the overlay, outside the plate mark
    wx, wy = 968, 268
    ph.ring(wx, wy, 5.5, "hair", "rr")
    ph.stroke([(wx - 10, wy), (wx + 10, wy)], "hair", "rr")
    ph.stroke([(wx, wy - 10), (wx, wy + 10)], "hair", "rr")

    # M.'s entries in the tracing fields
    # i: both lines followed to the same closed place
    fx, fy, fw, fh = FIELDS[0]
    cxf, g1f, g2f = fx + fw / 2, fy + 56, fy + 112
    for sgn in (-1, 1):
        dotted(ph, [(cxf + sgn * 34, fy + 18), (cxf + sgn * 10, fy + 28), (cxf, fy + 30), (cxf, g1f - 9)], 4.2, 0.95,
               "rr")
    stop_tick(ph, cxf, g1f - 7)
    # ii: the passage cut beside the neck; the point reaches the lower gate
    fx, fy, fw, fh = FIELDS[1]
    cxf, g1f, g2f = fx + fw / 2, fy + 56, fy + 112
    for sgn in (-1, 1):
        dotted(ph, [(cxf + sgn * 34, fy + 18), (cxf + sgn * 10, fy + 28), (cxf, fy + 30)], 4.2, 0.95, "rr")
    dotted(ph, catmull([(cxf + 2, fy + 31), (cxf + 30, fy + 36), (cxf + 40, g1f), (cxf + 30, g1f + 26), (cxf + 4, g1f + 34),
                        (cxf, g2f - 16)], 10), 4.2, 0.95, "rr")
    stop_tick(ph, cxf, g2f - 14)
    # iii: the form only

    svg = d.svg()
    meta = dict(byp=[list(p) for p in byp[::4]], fields=FIELDS)
    return svg, meta


def text_w(s, font, size, ls=0.0, style=""):
    return layout.text_w(s, font, style, size, ls)


def face_boxes(meta):
    SC, ENG, MONO = "IM FELL English SC", "IM FELL English", "IBM Plex Mono"
    B = [dict(id="rh_l", x=56, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, color=INK, runs=[("Clavicula Matricis", "")]),
         dict(id="rh_r", x=524, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, align="right", color=RED,
              runs=[("Tabula XI", "")]),
         dict(id="title", x=60, y=TITLE_Y, w=880, size=42, lh=48, font=ENG, align="center", color=INK,
              runs=[("Of the Closed Neck", "")])]
    ix, iy, iw, ih = INSET
    B.append(dict(id="inset", x=ix + 18, y=iy + 20, w=iw - 30, size=21, lh=26, font=ENG, color=INK,
                  runs=[("Leave the neck.", "i")]))
    # the first red amendment's declaration, plotted across its own line; M.'s qualification below
    sz, ls = 14.5, 0.14
    w1 = text_w("PASSAGE", MONO, sz, ls) + 4
    w2 = text_w("RESTORED.", MONO, sz, ls) + 4
    ly = 696
    B.append(dict(id="pr1", x=LX + 1.3 - 9 - w1, y=ly, w=w1, size=sz, lh=19, font=MONO, ls=ls, align="right", color=RR,
                  runs=[("PASSAGE", "")]))
    B.append(dict(id="pr2", x=LX + 1.3 + 9, y=ly, w=w2, size=sz, lh=19, font=MONO, ls=ls, color=RR,
                  runs=[("RESTORED.", "")]))
    B.append(Hd.mhand("m_lower", LX + 12, ly + 30, 96, "Only to the lower gate.", size=23, color=RR))
    for i, (fx, fy, fw, fh) in enumerate(FIELDS):
        B.append(dict(id=f"f{i}", x=fx + 10, y=fy + 8, w=40, size=12.5, lh=15, font=SC, ls=0.1, color=SEPIA,
                      runs=[(["i", "ii", "iii"][i], "")]))
    B.append(dict(id="folio", x=440, y=1568, w=120, size=12, lh=16, font=SC, ls=0.2, align="center", color=SEPIA,
                  runs=[("xi", "")]))
    return B


# ------------------------------------------------------------------ verso

def verso_boxes():
    from layout import box_height
    SC, PICA = "IM FELL English SC", "IM FELL DW Pica"
    B, meta = [], {}
    B.append(dict(id="rh_l", x=56, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, color=INK, runs=[("Clavicula Matricis", "")]))
    B.append(dict(id="rh_r", x=524, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, align="right", color=RED,
                  runs=[("Verso · Tabula XI", "")]))
    m = Hd.mhand("g_m", 170, 0, 660, "I followed each line with the point lifted clear of the paper. Both arrived at the "
                 "same closed place. I cut a passage beside it and repeated the course. This time the point reached the "
                 "lower gate.\nI had repaired the figure exactly as intended. The intended repair was insufficient.",
                 size=29, color=RR)
    m["para_gap"] = 16
    c = Hd.cust("g_c", 170, 0, 660, "The lower gate is present in every copy. You have no warrant to remove it.", size=25)
    u = Hd.unh("g_u", 430, 0, 420, "That tells me how long it has been there.", size=31)
    hm, hc, hu = box_height(m) * 1.12, box_height(c) * 1.12, box_height(u) * 1.12
    slip_h = 96
    block = slip_h + 90 + hm + 70 + hc + 26 + hu
    top = max(150, (90 + 1460 - block) / 2)
    meta["slip_y"] = top
    y = top + slip_h + 90
    m["y"] = y
    B.append(m)
    y += hm + 70
    meta["rule_y"] = y - 36
    c["y"] = y
    B.append(c)
    y += hc + 26
    u["y"] = y
    B.append(u)
    meta["y_end"] = y + hu
    B.append(dict(id="s21", x=150, y=1430, w=700, size=15.5, lh=20, font=PICA, align="center", color=SEPIA,
                  runs=[("The new keeper read the correction as an order.", "i")]))
    B.append(dict(id="folio", x=440, y=1568, w=120, size=12, lh=16, font=SC, ls=0.2, align="center", color=SEPIA,
                  runs=[("xi v", "")]))
    return B, meta


SLIP_W = 360


def build_verso(seed=112):
    boxes, meta = verso_boxes()
    rng = random.Random(seed)
    st = styles()
    d = Doc(W, H, st, order=order(st))
    h = Hand(d, rng, "ink", amp=0.35)
    for _ in range(110):
        d.circle("fox_fill", rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 3.0) ** 1.4)
    h.stroke([(56, 58), (944, 58)], "orn")
    h.stroke([(56, 62), (944, 62)], "hair")
    # the intact witness: a strip cut from another copy and laid in, a little turned
    sy = meta["slip_y"]
    sx = (W - SLIP_W) / 2
    c = (sx + SLIP_W / 2, sy + 48)
    rect = [rot(p, math.radians(-0.9), c) for p in [(sx, sy), (sx + SLIP_W, sy), (sx + SLIP_W, sy + 96), (sx, sy + 96)]]
    d.poly("shadow_fill", [(x + 4, y + 5) for x, y in rect], closed=True)
    d.poly("paste_fill", rect, closed=True)
    sh = XHand(h, lambda p: rot(p, math.radians(-0.9), c))
    ix, iy, iw, ih = sx + 67, sy + 13, 226, 70
    sh.stroke([(ix, iy), (ix + iw, iy), (ix + iw, iy + ih), (ix, iy + ih)], "orn", closed=True)
    sh.stroke([(ix + 5, iy + 5), (ix + iw - 5, iy + 5), (ix + iw - 5, iy + ih - 5), (ix + 5, iy + ih - 5)], "hair",
              closed=True)
    for (x, y) in ((ix, iy), (ix + iw, iy), (ix, iy + ih), (ix + iw, iy + ih)):
        asterisk(sh, x, y, 4.5, 8, weight="hair")
    sh.stroke([(ix + 16, iy + ih - 17), (ix + iw - 16, iy + ih - 17)], "hair", "sep")
    meta["witness_box"] = (ix, iy, iw, ih)
    # a single rule between M.'s account and the Custodian's reply
    h.stroke([(420, meta["rule_y"]), (580, meta["rule_y"])], "hair", "sep")
    asterisk(h, 500, meta["rule_y"], 4, 8, weight="hair", color="sep")
    sig_mark(h, 500, 1530, 11, "ink", "orn")
    ENG = "IM FELL English"
    boxes.append(dict(id="witness", x=ix + 14, y=iy + 20, w=iw - 20, size=21, lh=26, font=ENG, color=INK, rot=-0.9, h=26,
                      runs=[("Leave the neck open.", "i")]))
    return d.svg(), boxes, meta


# ------------------------------------------------------- the border strip

STRIP_W, STRIP_H = 1000, 170
CIPHER = "UA NB KS NE I. N. WT ON S. N. O. T."
COLUMNS = ["I", "II", "III", "IV", "VIII", "VII", "VI", "V", "IX", "X", "XI", "XII"]
STRIP_PAPER = "#f2ead6"


def transpose(text):
    s = "".join(ch for ch in text.upper() if ch.isalpha())
    rows = [s[i:i + 12] for i in range(0, len(s), 12)]
    rows[-1] = rows[-1] + "." * (12 - len(rows[-1]))
    idx = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6, "VIII": 7, "IX": 8, "X": 9, "XI": 10, "XII": 11}
    return " ".join("".join(r[idx[c]] for r in rows) for c in COLUMNS)


def untranspose(ct):
    groups = ct.split()
    idx = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6, "VIII": 7, "IX": 8, "X": 9, "XI": 10, "XII": 11}
    cols = [None] * 12
    for c, g in zip(COLUMNS, groups):
        cols[idx[c]] = g
    rows = ["".join(cols[j][i] for j in range(12)) for i in range(len(groups[0]))]
    return "".join(rows).rstrip(".")


def strip_styles():
    st = styles()
    st["edge_fill"] = {"fill": "#e4d8bb", "stroke": "none"}
    return st


def build_strip(side, seed=113):
    rng = random.Random(seed + (side == "back"))
    st = strip_styles()
    d = Doc(STRIP_W, STRIP_H, st, order=["edge_fill", "hole_fill"] + [k for k in st if k not in ("edge_fill", "hole_fill")])
    h = Hand(d, rng, "ink", amp=0.25)
    # sewing holes along the edge that was stitched to the plate's border; mirrored on the back
    ys = 18
    for k in range(9):
        x = 70 + k * 107.5
        x = x if side == "front" else STRIP_W - x
        d.circle("hole_fill", x, ys, 1.8)
    h.stroke([(40, 34), (960, 34)], "hair", "sep", amp=0.05)
    h.stroke([(40, STRIP_H - 20), (960, STRIP_H - 20)], "hair", "sep", amp=0.05)
    meta = {}
    if side == "back":
        xs = [78 + i * (844 / 11) for i in range(12)]
        meta["xs"] = xs
        for x in xs:
            h.stroke([(x, 76), (x, 92)], "orn", "ink", amp=0.03)
    return d.svg(), meta


def strip_boxes(side, meta):
    PICA, SC = "IM FELL DW Pica", "IM FELL English SC"
    if side == "front":
        groups = CIPHER.split()
        sz, ls, gap = 31, 0.08, 30
        ws = [text_w(g, PICA, sz, ls) + 2 for g in groups]
        x = (STRIP_W - sum(ws) - gap * (len(ws) - 1)) / 2
        B = []
        for i, (g, w) in enumerate(zip(groups, ws)):
            B.append(dict(id=f"g{i}", x=round(x, 1), y=70, w=round(w + 6, 1), size=sz, lh=40, font=PICA, ls=ls,
                          color=INK, runs=[(g, "")]))
            x += w + gap
        return B
    B = []
    for i, (x, c) in enumerate(zip(meta["xs"], COLUMNS)):
        B.append(dict(id=f"c{i}", x=x - 34, y=48, w=68, size=17, lh=22, font=SC, ls=0.04, align="center", color=INK,
                      runs=[(c, "")]))
    x = meta["xs"][0]
    B.append(dict(id="crib", x=x - 30, y=98, w=60, size=19, lh=20, font=PICA, align="center", color=INK,
                  runs=[("U", ""), ("", "br"), ("A", "")]))
    return B
