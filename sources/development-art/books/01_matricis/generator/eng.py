"""Shared engraving-workshop furniture: styles, plate mark, frame, stars, burin rehearsals."""
import math
import random
import sys

from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from core import Doc, hatch_lines, bezier
from marks import *
import hands as Hd

W, H = 1000, 1600
PAPER, INK, RED, SEPIA = "#ebe1c8", Hd.INK, Hd.RED, Hd.SEPIA
TITLE_Y = 150


def styles():
    st = {}
    for c, col in (("ink", INK), ("red", RED), ("sep", SEPIA), ("pm", "#d6c9aa"), ("pl", "#f6efde")):
        for k, wdt in (("core", 2.9), ("orn", 1.55), ("hair", 0.9), ("cip", 1.35)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    st["fox_fill"] = {"fill": "#b89a6a", "stroke": "none", "opacity": "0.15"}
    st["tone_fill"] = {"fill": "#d9caa6", "stroke": "none", "opacity": "0.28"}
    st["wear_fill"] = {"fill": "#e6dcc0", "stroke": "none", "opacity": "0.85"}
    st["rub_hair"] = {"fill": "none", "stroke": INK, "stroke-width": "0.9", "opacity": "0.22", "stroke-linecap": "round"}
    return st


def order(st):
    first = ["tone_fill", "fox_fill"]
    late = ["wear_fill", "rub_hair"]
    return first + [k for k in st if k not in first + late] + late


def page(seed, band=True):
    rng = random.Random(seed)
    st = styles()
    d = Doc(W, H, st, order=order(st))
    h = Hand(d, rng, "ink", amp=0.4)
    for _ in range(150):
        d.circle("fox_fill", rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 3.2) ** 1.4)
    h.stroke([(56, 58), (944, 58)], "orn")
    h.stroke([(56, 62), (944, 62)], "hair")
    if band:
        band_x(h, (380, TITLE_Y + 61), (620, TITLE_Y + 61), 9, 12, "hair", "ink")
        asterisk(h, 370, TITLE_Y + 61, 6, 8, weight="hair")
        asterisk(h, 630, TITLE_Y + 61, 6, 8, weight="hair")
    sig_mark(h, 500, 1530, 11, "ink", "orn")
    return d, h, rng


def plate_frame(h, d, X0, Y0, X1, Y1):
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


def stars(h, rng, busy, xr, yr, n=16, axis=500):
    placed, tries = [], 0
    while len(placed) < n and tries < 6000:
        tries += 1
        x, y = rng.uniform(xr[0], axis - 30), rng.uniform(*yr)
        r = rng.uniform(2.6, 4.4)
        xm = 2 * axis - x
        ok = all(not busy.intersects(Point(px, y).buffer(r + 10)) for px in (x, xm))
        ok = ok and all((x - px) ** 2 + (y - py) ** 2 > (r + pr + 34) ** 2 for (px, py, pr) in placed)
        if ok:
            rd = rng.uniform(0, 45)
            for xx in (x, xm):
                placed.append((xx, y, r))
                asterisk(h, xx, y, r, 8, rot_deg=rd, weight="hair", color="sep", centre=True)


def rehearsals(h, d, rng, x, y0, n=6):
    y = y0
    for k in range(n):
        L, bend = rng.uniform(9, 24), rng.uniform(-4, 4)
        x0 = x + rng.uniform(-2, 2)
        h.stroke(bezier((x0, y), (x0 + L * 0.4, y - bend), (x0 + L * 0.7, y + bend * 0.5), (x0 + L, y + 1), 10), "hair",
                 amp=0.05)
        y += rng.uniform(12, 18)
    d.poly("rub_hair", bezier((x - 2, y + 4), (x + 6, y), (x + 14, y + 6), (x + 22, y + 3), 10))


def heads(tab, title, extra=()):
    SC, ENG = "IM FELL English SC", "IM FELL English"
    B = [dict(id="rh_l", x=56, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, color=INK, runs=[("Clavicula Matricis", "")]),
         dict(id="rh_r", x=524, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, align="right", color=RED,
              runs=[(f"Tabula {tab}", "")]),
         dict(id="title", x=60, y=TITLE_Y, w=880, size=42, lh=48, font=ENG, align="center", color=INK,
              runs=[(title, "")]),
         dict(id="folio", x=440, y=1568, w=120, size=12, lh=16, font=SC, ls=0.2, align="center", color=SEPIA,
              runs=[(tab.lower(), "")])]
    return B + list(extra)
