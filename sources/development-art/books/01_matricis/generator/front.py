"""The title leaf and the index of the tables."""
import math
import random
import sys

from core import arc_pts, bezier
from marks import *
import eng
import hands as Hd

SC, ENG, PICA = "IM FELL English SC", "IM FELL English", "IM FELL DW Pica"


def build_title(seed=99):
    d, h, rng = eng.page(seed, band=False)
    band_x(h, (380, 410), (620, 410), 9, 12, "hair", "ink")
    asterisk(h, 370, 410, 6, 8, weight="hair")
    asterisk(h, 630, 410, 6, 8, weight="hair")
    # the device: the open spiral with its branch, in a cartouche
    cx, cy = 500, 840
    h.stroke(arc_pts(cx, cy, 190, 0, 360, 240), "core")
    h.stroke(arc_pts(cx, cy, 178, 0, 360, 220), "hair")
    ring_x(h, cx, cy, 176, 152, 40, "hair", "ink")
    h.stroke(arc_pts(cx, cy, 150, 0, 360, 220), "hair")
    sig_mark(h, cx, cy + 6, 96, "ink", "core")
    for a in (0, 90, 180, 270):
        x, y = cx + 206 * math.cos(math.radians(a)), cy + 206 * math.sin(math.radians(a))
        asterisk(h, x, y, 8, 8, weight="orn")
    for sgn in (-1, 1):
        curl(h, cx + sgn * 214, cy, 0 if sgn > 0 else 180, 12, 16, 1.3, hand=-sgn, weight="hair")
    band_x(h, (330, 1236), (670, 1236), 9, 14, "hair", "ink")
    return d.svg(), {}


def title_boxes(meta):
    B = [dict(id="rh_l", x=56, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, color=eng.INK, runs=[("", "")]),
         dict(id="t1", x=60, y=236, w=880, size=78, lh=84, font=ENG, align="center", color=eng.INK,
              runs=[("Clavicula Matricis", "")]),
         dict(id="t2", x=60, y=336, w=880, size=27, lh=34, font=ENG, align="center", color=eng.RED,
              runs=[("or, the Little Key of the Matrix", "i")]),
         dict(id="t3", x=150, y=446, w=700, size=21, lh=30, font=PICA, align="center", color=eng.INK,
              runs=[("being Revisable Systems Practice, Revision 5, set out in thirteen tables by three workshops, "
                     "the retained impression, the deposited arrangement and the repeated instruction; with the leaves of "
                     "its text, its debts, and a tract of another stock bound in after the eighth table", "")]),
         dict(id="t4", x=200, y=1094, w=600, size=19, lh=26, font=PICA, align="center", color=eng.INK,
              runs=[("Revision 5, 10 October 2026", "i")]),
         dict(id="t5", x=200, y=1272, w=600, size=15, lh=20, font=SC, ls=0.2, align="center", color=eng.SEPIA,
              runs=[("No one needs permission to stop using it", "")])]
    return B[1:]


INDEX = [
    ("I", "Of the One Question", "the retained impression", "§ 1"),
    ("II", "Of the Two Clocks", "the retained impression, with a pasted drawing", "§ 2"),
    ("III", "Of the Speed of Correction", "the repeated instruction", "§ 3"),
    ("IV", "Of the Second Copy", "the deposited arrangement", "§ 4"),
    ("V", "Of Visibility Read as Command", "the deposited arrangement", "§ 5"),
    ("VI", "Of the Borrowed Face", "the repeated instruction, a foldout", "§ 6"),
    ("VII", "Of the Ten Bindings", "the retained impression", "§ 7"),
    ("VIII", "Of an Outage Delayed by Authority", "the retained impression", "§ 8"),
    ("", "Vis Maior, or the Power which Excuseth", "a tract of another stock, bound in", ""),
    ("IX", "Of a Test That Found Nothing", "the repeated instruction", "§ 9"),
    ("X", "Of an Analogy Taken to Its Limit", "the deposited arrangement", "§ 10"),
    ("XI", "Of the Closed Neck", "the retained impression, with a plotted overlay", "§ 11"),
    ("XII", "Of the Questions Left Open", "the repeated instruction", "§ 12"),
    ("XIII", "Of the Twelve Marks and the Mark", "the deposited arrangement", "§ 13"),
]
LOOSE = ["the proem, from the opening of Revision 5", "the debts and the references",
         "two proof sheets: the legacy hand and the transcription hand",
         "a border strip from the eleventh table", "slip H, a rule for the quiet instrument",
         "slip I, from a receipt for the revised seal"]


def build_index(seed=98):
    d, h, rng = eng.page(seed)
    y0 = 300
    for k in range(len(INDEX) + 1):
        y = y0 + k * 62
        dotted(h, [(380, y + 40), (760, y + 40)], 7, 0.8, "sep", skip_ends=False) if k < len(INDEX) and INDEX[k][0] else None
    h.stroke([(130, 1196), (870, 1196)], "hair")
    return d.svg(), {}


def index_boxes(meta):
    B = [dict(id="rh_l", x=56, y=28, w=420, size=13, lh=17, font=SC, ls=0.22, color=eng.INK,
              runs=[("Clavicula Matricis", "")]),
         dict(id="title", x=60, y=150, w=880, size=40, lh=46, font=ENG, align="center", color=eng.INK,
              runs=[("Index of the Tables", "")])]
    y0 = 300
    for k, (num, title, shop, sec) in enumerate(INDEX):
        y = y0 + k * 62
        if num:
            B.append(dict(id=f"n{k}", x=120, y=y, w=70, size=19, lh=24, font=SC, ls=0.1, align="right", color=eng.RED,
                          runs=[(num, "")]))
            B.append(dict(id=f"s{k}", x=800, y=y, w=80, size=16, lh=24, font=SC, ls=0.08, align="right",
                          color=eng.SEPIA, runs=[(sec, "")]))
        B.append(dict(id=f"t{k}", x=210, y=y, w=560, size=21, lh=26, font=ENG, color=eng.INK,
                      runs=[(title, "i" if not num else "")]))
        B.append(dict(id=f"w{k}", x=210, y=y + 27, w=560, size=14, lh=18, font=PICA, color=eng.SEPIA,
                      runs=[(shop, "i")]))
    B.append(dict(id="loose_h", x=130, y=1214, w=740, size=15, lh=20, font=SC, ls=0.16, align="center", color=eng.RED,
                  runs=[("Also gathered here", "")]))
    B.append(dict(id="loose", x=130, y=1244, w=740, size=16.5, lh=23, font=PICA, align="center", color=eng.INK,
                  runs=[(" · ".join(LOOSE), "i")]))
    return B
