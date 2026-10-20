"""Loose slips: the transcription-hand proof sheet; H, a rule for the quiet instrument; I, a receipt for the revised seal."""
import math
import random
import sys

from core import Doc, arc_pts, bezier, catmull, rot
from marks import *
import hands as Hd
import tx
import layout

GAR, PICA, ENG, MONO = "EB Garamond", "IM FELL DW Pica", "IM FELL English", "IBM Plex Mono"
SLIP_BG = "#ebe1c8"


def base_styles(extra=()):
    st = {}
    for c, col in (("ink", Hd.INK), ("red", Hd.RED), ("sep", Hd.SEPIA), ("gr", Hd.GRAPHITE)) + tuple(extra):
        for k, wdt in (("core", 2.4), ("orn", 1.4), ("hair", 0.85), ("cip", 1.5)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    return st


# ------------------------------------------------------------ key proof

KW, KH = 1000, 700
COL_X0, COL_W = 190, 62.5
ROW_Y = (226, 310, 394)
S_MARK = 27
EX = "THE CLOCK HAS AN OWNER."
EX_S, EX_Y = 28, 516


def build_keyproof(seed=9):
    st = base_styles()
    d = Doc(KW, KH, st)
    h = Hand(d, random.Random(seed), "ink", amp=0.15)
    h.stroke([(40, 40), (960, 40), (960, KH - 40), (40, KH - 40)], "hair", "sep", closed=True)
    # the table's ruling
    h.stroke([(COL_X0 - 130, 214), (COL_X0 + 12 * COL_W, 214)], "hair", "sep")
    for r in range(1, 3):
        y = ROW_Y[r] - 14
        h.stroke([(COL_X0 - 130, y), (COL_X0 + 12 * COL_W, y)], "hair", "sep", amp=0.05)
    cells = {}
    for t in (1, 2, 3):
        for b in range(1, 13):
            x = COL_X0 + (b - 1) * COL_W
            y = ROW_Y[t - 1]
            valid = (b, t) in tx.INV
            if valid:
                gx = x + (COL_W - tx.token_width(t, S_MARK)) / 2 + 0.08 * S_MARK
                tx.mark(h, b, gx, y, S_MARK, "orn", "ink")
                tx.tally(h, t, gx, y, S_MARK, "ink")
            cells[(b, t)] = (x, y, valid)
    # the example, between two thin rules, as on IV's caption strip
    wdt = tx.width(EX, EX_S)
    x0 = (KW - wdt) / 2
    h.stroke([(110, EX_Y - 14), (890, EX_Y - 14)], "hair", "ink")
    h.stroke([(110, EX_Y + EX_S + 14), (890, EX_Y + EX_S + 14)], "hair", "ink")
    tx.write(h, EX, x0, EX_Y, EX_S, color="ink")
    return d.svg(), dict(cells=cells)


def keyproof_boxes(meta):
    B = [dict(id="kp_h", x=60, y=60, w=880, size=15, lh=20, font=GAR, color=Hd.RED,
              runs=[("Proof sheet · the transcription hand", "v")]),
         dict(id="kp_n", x=60, y=86, w=880, size=14.5, lh=20, font=GAR, color=Hd.SEPIA,
              runs=[("The base signs are the twelve marks of XIII, in their order. One, two or three strokes at the lower "
                     "right choose the row. A dash marks an invalid combination, not a hidden letter. Words take a wider "
                     "interval; punctuation is not written.", "i")])]
    for b in range(1, 13):
        x = COL_X0 + (b - 1) * COL_W
        B.append(dict(id=f"kp_c{b}", x=x, y=186, w=COL_W, size=14, lh=18, font=GAR, color=Hd.SEPIA, align="center",
                      runs=[(tx.ROMAN[b - 1], "v")]))
    for t, lab in ((1, "one stroke"), (2, "two strokes"), (3, "three strokes")):
        B.append(dict(id=f"kp_r{t}", x=60, y=ROW_Y[t - 1] + 6, w=118, size=14, lh=18, font=GAR, color=Hd.SEPIA,
                      runs=[(lab, "i")]))
    for (b, t), (x, y, valid) in meta["cells"].items():
        if valid:
            B.append(dict(id=f"kp_{b}_{t}", x=x, y=y + S_MARK + 7, w=COL_W, size=16, lh=20, font=GAR, color=Hd.INK,
                          align="center", runs=[(tx.INV[(b, t)], "")]))
        else:
            B.append(dict(id=f"kp_{b}_{t}", x=x, y=y + 6, w=COL_W, size=16, lh=20, font=GAR, color=Hd.SEPIA,
                          align="center", runs=[("–", "")]))
    B.append(dict(id="kp_codes", x=60, y=EX_Y + EX_S + 30, w=880, size=12.5, lh=18, font=MONO, color=Hd.SEPIA,
                  align="center", runs=[(tx.codes(EX), "")]))
    B.append(dict(id="kp_pl", x=60, y=EX_Y + EX_S + 56, w=880, size=14.5, lh=20, font=GAR, color=Hd.SEPIA,
                  align="center", runs=[("IV, caption strip: ", "i"), ("The clock has an owner.", "")]))
    return B


# ------------------------------------------------------------ H

HW, HH = 1000, 560
H_PAPER = "#f4eedd"
H_MOUNT = "#e3d9c1"


def torn_edge(rng, x, y0, y1, amp=4.5, step=7):
    pts = []
    y = y0
    while y < y1:
        pts.append((x + rng.uniform(-amp, amp) + (rng.random() < 0.08) * rng.uniform(-6, 6), y))
        y += rng.uniform(step * 0.6, step * 1.4)
    pts.append((x, y1))
    return pts


def build_h(seed=31):
    rng = random.Random(seed)
    st = base_styles()
    st["paper_fill"] = {"fill": H_PAPER, "stroke": "none"}
    st["shadow_fill"] = {"fill": "#7a6a4e", "stroke": "none", "opacity": "0.2"}
    st["grid_hair"] = {"fill": "none", "stroke": "#b9c49e", "stroke-width": "0.6", "opacity": "0.55"}
    st["grid2_hair"] = {"fill": "none", "stroke": "#a3b083", "stroke-width": "0.8", "opacity": "0.6"}
    d = Doc(HW, HH, st, order=["shadow_fill", "paper_fill", "grid_hair", "grid2_hair"] +
            [k for k in st if k not in ("shadow_fill", "paper_fill", "grid_hair", "grid2_hair")])
    h = Hand(d, rng, "ink", amp=0.25)
    left = torn_edge(rng, 26, 18, HH - 18)
    paper = left + [(HW - 18, HH - 18), (HW - 18, 18)]
    d.poly("shadow_fill", [(x + 4, y + 5) for x, y in paper], closed=True)
    d.poly("paper_fill", paper, closed=True)
    # technical stock: a faint grid, every fifth line stronger
    for k, x in enumerate(range(40, HW - 18, 16)):
        d.poly("grid2_hair" if k % 5 == 0 else "grid_hair", [(x, 18), (x, HH - 18)])
    for k, y in enumerate(range(26, HH - 18, 16)):
        d.poly("grid2_hair" if k % 5 == 0 else "grid_hair", [(34, y), (HW - 18, y)])
    # the trial form under the rule: three headed columns, then an interval left without a head
    fx0, fx1, fy0, fy1 = 66, 934, 330, 506
    cols = [fx0, 280, 494, 708, fx1]
    h.stroke([(fx0, fy0), (fx1, fy0)], "orn", "ink", amp=0.05)
    h.stroke([(fx0, fy0 + 30), (fx1, fy0 + 30)], "hair", "ink", amp=0.05)
    h.stroke([(fx0, fy1), (fx1, fy1)], "orn", "ink", amp=0.05)
    for x in cols[1:-1]:
        h.stroke([(x, fy0), (x, fy1)], "hair", "ink", amp=0.05)
    # the interval column is closed off with a light bracket, not a head
    return d.svg(), dict(cols=cols, fy0=fy0)


def h_boxes(meta):
    B = [Hd.cust("h_rule", 66, 64, 560, "Let a known disturbance touch the instrument before you praise its quiet. Write "
                 "down what you introduced, what it registered, and what you withdrew. Then leave an interval in which "
                 "you do not touch it.\nIf it answers only when you announce the trial, enter this with the answer.",
                 size=20.5),
         Hd.cust("h_c", 666, 70, 268, "An announced trial is the only trial for which I will answer.", size=20.5),
         Hd.mhand("h_m", 676, 186, 260, "Then this record establishes the announced condition only.", size=25)]
    B[0]["font"] = PICA
    cols, fy0 = meta["cols"], meta["fy0"]
    for i, lab in enumerate(("introduced", "registered", "withdrawn")):
        B.append(dict(id=f"h_f{i}", x=cols[i] + 10, y=fy0 + 7, w=cols[i + 1] - cols[i] - 20, size=13, lh=18, font=MONO,
                      ls=0.06, color=Hd.INK, runs=[(lab, "")]))
    return B


# ------------------------------------------------------------ I

IW, IH = 1000, 500
I_PAPER = "#efe6cf"
SEAL = (232, 352, 64)
PINS = [(452, 334), (452, 382)]


def build_i(seed=41):
    rng = random.Random(seed)
    st = base_styles()
    st["paper_fill"] = {"fill": I_PAPER, "stroke": "none"}
    st["stub_fill"] = {"fill": "#e6dcc1", "stroke": "none"}
    st["shadow_fill"] = {"fill": "#7a6a4e", "stroke": "none", "opacity": "0.2"}
    st["hole_fill"] = {"fill": "#5a4c38", "stroke": "none", "opacity": "0.7"}
    st["rust_fill"] = {"fill": "#9a6a3c", "stroke": "none", "opacity": "0.16"}
    st["clean_fill"] = {"fill": "#f6efdc", "stroke": "none", "opacity": "0.65"}
    st["rule_hair"] = {"fill": "none", "stroke": "#b7a985", "stroke-width": "0.8"}
    st["stamp_core"] = {"fill": "none", "stroke": Hd.INK, "stroke-width": "2.6", "stroke-linecap": "round",
                        "opacity": "0.86"}
    st["stamp_hair"] = {"fill": "none", "stroke": Hd.INK, "stroke-width": "1.1", "stroke-linecap": "round",
                        "opacity": "0.86"}
    first = ["shadow_fill", "paper_fill", "stub_fill", "clean_fill", "rule_hair", "rust_fill", "hole_fill"]
    d = Doc(IW, IH, st, order=first + [k for k in st if k not in first])
    h = Hand(d, rng, "ink", amp=0.2)
    paper = [(18, 18), (IW - 18, 18), (IW - 18, IH - 18), (18, IH - 18)]
    d.poly("shadow_fill", [(x + 4, y + 5) for x, y in paper], closed=True)
    d.poly("paper_fill", paper, closed=True)
    # the counterfoil side: torn along the perforation, its nubs still attached
    stub = [(18, 18)] + [(78 + (3 if (k % 2) else 0), 18 + k * 9) for k in range(int((IH - 36) / 9) + 1)] + [(18, IH - 18)]
    d.poly("stub_fill", stub, closed=True)
    for k in range(int((IH - 36) / 9)):
        d.circle("hole_fill", 92, 22 + k * 9, 1.6)
    # ruled lines
    for y in range(234, IH - 30, 34):
        d.poly("rule_hair", [(118, y), (IW - 48, y)])
    # where a separate slip was pinned beside the seal: a cleaner patch, two holes, a little rust
    d.poly("clean_fill", [(362, 298), (606, 294), (608, 418), (364, 422)], closed=True)
    for (x, y) in PINS:
        d.circle("rust_fill", x + 1, y + 1, 7.5)
        d.circle("hole_fill", x, y, 1.9)
    # the stamp: open spiral with branch, no central dot, inside a ring; ink uneven
    cx, cy, r = SEAL
    sh = Hand(d, rng, "ink", amp=0.35)
    ring = arc_pts(cx, cy, r, 0, 360, 160)
    runs, cur = [], []
    for i, p in enumerate(ring):
        if rng.random() < 0.035 and cur:
            runs.append(cur)
            cur = []
        else:
            cur.append(p)
    runs.append(cur)
    for rr_ in runs:
        if len(rr_) > 1:
            d.poly("stamp_core", sh.wob(rr_, 0.3))
    d.poly("stamp_hair", sh.wob(arc_pts(cx, cy, r - 8, 0, 360, 140), 0.25))
    dotted(sh, arc_pts(cx, cy, r - 15, 0, 360, 140), 7.5, 1.1, "ink", skip_ends=False)
    sig_mark(sh, cx, cy, r * 0.36, "ink", "core")
    return d.svg(), {}


def i_boxes(meta):
    B = [Hd.cust("i_base", 128, 64, 800, "The first contradiction is entered beside the seal. The seal is not scraped "
                 "away; neither is the contradiction.\nThe next keeper receives both.", size=22),
         Hd.unh("i_u", 640, 322, 300, "I received the seal. The objection was on a separate slip.", size=28)]
    B[0]["font"] = PICA
    return B
