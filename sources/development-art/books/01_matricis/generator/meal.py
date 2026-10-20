"""Shared cornmeal-workshop furniture: a mounted record of a deposit on dark ground."""
import random
import sys

from core import Doc
from marks import *
import hands as Hd
from page2 import GRAIN, EARTH, MEAL, OCHRE, ASH, styles as st2

W, H = 1000, 1600
PAPER = "#ebe1c8"


def styles():
    st = st2()
    st["earth_fill"] = {"fill": EARTH, "stroke": "none"}
    st["mount_fill"] = {"fill": "#f1e8d3", "stroke": "none"}
    st["mount_orn"] = {"fill": "none", "stroke": "#b9ab8c", "stroke-width": "0.8"}
    for c, col in (("pk", Hd.INK), ("pr", Hd.RED), ("ps", Hd.SEPIA)):
        for k, wdt in (("core", 2.2), ("orn", 1.4), ("hair", 0.8), ("cip", 1.3)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    st["fox_fill"] = {"fill": "#b89a6a", "stroke": "none", "opacity": "0.14"}
    st["tapebg_fill"] = {"fill": "#f4edda", "stroke": "none"}
    st["tape_hair"] = {"fill": "none", "stroke": "#b9ab8c", "stroke-width": "0.85"}
    return st


def page(seed, rec, texture=1500):
    rng = random.Random(seed)
    st = styles()
    order = ["fox_fill", "earth_fill", "tex_dk", "tex_lt", "ghost_orn"] + \
            [k for k in st if k.startswith(("ash_", "ink_", "red_"))] + \
            ["mount_fill", "mount_orn", "tapebg_fill", "tape_hair"] + [k for k in st if k.startswith(("pk_", "pr_", "ps_"))]
    d = Doc(W, H, st, order=order)
    for _ in range(140):
        d.circle("fox_fill", rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 3.0) ** 1.4)
    x0, y0, x1, y1 = rec
    d.poly("earth_fill", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True)
    for _ in range(texture):
        d.grain("tex_lt" if rng.random() < 0.55 else "tex_dk", rng.uniform(x0, x1), rng.uniform(y0, y1))
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        tri = [(cx - sx * 6, cy - sy * 6), (cx + sx * 44, cy - sy * 6), (cx - sx * 6, cy + sy * 44)]
        d.poly("mount_fill", tri, closed=True)
        d.poly("mount_orn", [(cx + sx * 44, cy - sy * 6), (cx - sx * 6, cy + sy * 44)])
    ph = Hand(d, rng, "ink", amp=0.35)
    ph.stroke([(56, 58), (944, 58)], "orn", "pk")
    ph.stroke([(56, 62), (944, 62)], "hair", "pk")
    sig_mark(ph, 500, 1550, 11, "pk", "orn")
    h = Hand(d, rng, "grain", amp=0.75, grain=GRAIN)
    return d, h, ph, rng


def chalk(d, rng):
    return Hand(d, rng, "grain", amp=0.5, grain={"orn": (1.6, 0.5), "hair": (1.2, 0.3), "core": (2.2, 0.7),
                                                 "sizes": (4, 3, 1), "stray": 0.02})


def heads(tab, title, extra=()):
    GAR = "EB Garamond"
    B = [dict(id="rh_l", x=56, y=28, w=420, size=14, lh=18, font=GAR, color=Hd.INK, runs=[("Clavicula Matricis", "v")]),
         dict(id="rh_r", x=524, y=28, w=420, size=14, lh=18, font=GAR, align="right", color=Hd.RED,
              runs=[(f"Tabula {tab} · a mounted record", "v")]),
         dict(id="title", x=60, y=110, w=880, size=42, lh=48, font=GAR, align="center", color=Hd.INK,
              runs=[(title, "")]),
         dict(id="folio", x=844, y=1560, w=100, size=13, lh=18, font=GAR, align="right", color=Hd.SEPIA,
              runs=[(tab.lower(), "v")])]
    return B + list(extra)
