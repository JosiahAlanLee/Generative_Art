"""Extracted Matricis sigil and toner-paper helpers; prose page builders omitted."""
import math
import random
import sys

from core import Doc, arc_pts, bezier, catmull, resample
from marks import *

W, H = 860, 1360
STOCK = "#e9e7de"
TONER = "#151515"
GUARD = "#ddd2b6"
TYPE, BLACK = "Special Elite", "UnifrakturMaguntia"
STATEMENT = "NEITHER PARTY SHALL BE LIABLE"

# a plain stroke alphabet on a unit cell (x right, y down), enough for the statement
def _bowl(x0, y0, y1, w):
    return [(x0, y0)] + [(x0 + w + (y1 - y0) / 2 * math.cos(math.radians(a)) * 0.9,
                          (y0 + y1) / 2 + (y1 - y0) / 2 * math.sin(math.radians(a))) for a in range(-90, 91, 15)] + [(x0, y1)]


LETTERS = {
    "N": [[(0, 1), (0, 0), (0.7, 1), (0.7, 0)]],
    "E": [[(0.7, 0), (0, 0), (0, 1), (0.7, 1)], [(0, 0.5), (0.55, 0.5)]],
    "I": [[(0.35, 0), (0.35, 1)]],
    "T": [[(0, 0), (0.7, 0)], [(0.35, 0), (0.35, 1)]],
    "H": [[(0, 0), (0, 1)], [(0.7, 0), (0.7, 1)], [(0, 0.5), (0.7, 0.5)]],
    "R": [[(0, 1), (0, 0)], _bowl(0, 0, 0.5, 0.3), [(0.3, 0.5), (0.7, 1)]],
    "P": [[(0, 1), (0, 0)], _bowl(0, 0, 0.5, 0.3)],
    "A": [[(0, 1), (0.35, 0), (0.7, 1)], [(0.15, 0.6), (0.55, 0.6)]],
    "Y": [[(0, 0), (0.35, 0.5), (0.7, 0)], [(0.35, 0.5), (0.35, 1)]],
    "S": [bezier((0.66, 0.1), (0.5, -0.05), (0.02, 0.0), (0.12, 0.3), 10) +
          bezier((0.12, 0.3), (0.2, 0.5), (0.7, 0.5), (0.62, 0.78), 10)[1:] +
          bezier((0.62, 0.78), (0.55, 1.05), (0.12, 1.02), (0.04, 0.86), 10)[1:]],
    "L": [[(0, 0), (0, 1), (0.7, 1)]],
    "B": [[(0, 1), (0, 0)], _bowl(0, 0, 0.48, 0.28), _bowl(0, 0.48, 1, 0.36)],
}


def reduced(statement=STATEMENT):
    seen, out = set(), []
    for ch in statement:
        if ch.isalpha() and ch not in seen:
            seen.add(ch)
            out.append(ch)
    return out


def strike_runs(statement=STATEMENT):
    """the statement with every repeated letter struck"""
    seen, runs = set(), []
    for ch in statement:
        if ch == " ":
            runs.append((" ", ""))
        elif ch in seen:
            runs.append((ch, "x"))
        else:
            seen.add(ch)
            runs.append((ch, ""))
    merged = []
    for t, s in runs:
        if merged and merged[-1][1] == s:
            merged[-1] = (merged[-1][0] + t, s)
        else:
            merged.append((t, s))
    return merged


def monogram(h, cx, cy, s, weight="orn", color="ink"):
    """the twelve remaining letters laid over one another on a single cell"""
    for k, ch in enumerate(reduced()):
        for stroke in LETTERS[ch]:
            h.stroke([(cx + (x - 0.35) * s, cy + (y - 0.5) * s) for x, y in stroke], weight, color, amp=0.6)


def sigil(h, cx, cy, s, weight="core", color="ink", ring=True):
    """the reduced figure: shared stem, bars, the diagonal, one bowl, a leg, a fork above, a hook below"""
    P = lambda x, y: (cx + (x - 0.35) * s, cy + (y - 0.5) * s)
    h.stroke([P(0.35, -0.08), P(0.35, 1.0)], weight, color)                     # the shared stem
    h.stroke([P(0.02, 0.0), P(0.35, 0.0)], weight, color)                       # top bar, cut short
    h.stroke([P(0.05, 0.08), P(0.66, 0.94)], weight, color)                     # the diagonal
    h.stroke([P(0.35, 0.0)] + [P(0.35 + 0.3 * math.cos(math.radians(a)) + 0.0, 0.25 + 0.25 * math.sin(math.radians(a)))
                                 for a in range(-90, 91, 12)] + [P(0.35, 0.5)], weight, color)   # one bowl
    h.stroke([P(0.42, 0.5), P(0.74, 1.0)], weight, color)                       # the leg
    h.stroke([P(0.14, -0.3), P(0.35, -0.08), P(0.56, -0.3)], weight, color)     # the fork above
    h.stroke([P(0.35, 1.0), P(0.66, 1.0)], weight, color)                       # the foot
    h.stroke(bezier(P(0.35, 0.72), P(0.12, 0.66), P(0.0, 0.86), P(0.14, 0.98), 12), weight, color)  # the hook
    for p in (P(0.14, -0.3), P(0.56, -0.3), P(0.74, 1.0), P(0.02, 0.0), P(0.14, 0.98)):
        h.dot(p[0], p[1], s * 0.022, color)
    if ring:
        h.stroke(arc_pts(cx, cy + s * 0.12, s * 0.78, 0, 360, 160), "orn", color)


def styles():
    st = {}
    for c, col in (("ink", TONER), ("wh", "#efece4"), ("gd", "#8c7f62")):
        for k, wdt in (("core", 4.2), ("orn", 2.4), ("hair", 1.2), ("cip", 1.6)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    for k, op in (("s1", 0.85), ("s2", 0.5), ("s3", 0.25)):
        st[f"tn_{k}"] = {"fill": TONER, "stroke": "none", "opacity": str(op)}
    for i in range(10):
        st[f"sh{i}_fill"] = {"fill": "#2a2a26", "stroke": "none", "opacity": f"{0.11 - i * 0.011:.3f}"}
    st["guard_fill"] = {"fill": GUARD, "stroke": "none"}
    st["guardsh_fill"] = {"fill": "#6d5f4b", "stroke": "none", "opacity": "0.18"}
    st["hole_fill"] = {"fill": "#4b4335", "stroke": "none", "opacity": "0.8"}
    st["thread_orn"] = {"fill": "none", "stroke": "#cfc6ae", "stroke-width": "2", "stroke-linecap": "round"}
    return st


def sheet(seed, gutter):
    """stock, copier shadow at the outer edge, toner flecks, the guard it is hinged on"""
    rng = random.Random(seed)
    st = styles()
    order = [f"sh{i}_fill" for i in range(10)] + ["tn_s3", "tn_s2", "tn_s1"] + \
            [k for k in st if k.startswith(("ink_", "wh_", "gd_"))] + ["guardsh_fill", "guard_fill", "hole_fill", "thread_orn"]
    d = Doc(W, H, st, order=order)
    outer = W if gutter == "left" else 0
    for i in range(10):
        wdt = 6 + i * 5
        x0 = outer - wdt if gutter == "left" else 0
        d.poly(f"sh{i}_fill", [(x0, 0), (x0 + wdt, 0), (x0 + wdt, H), (x0, H)], closed=True)
    for _ in range(520):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        d.circle(rng.choice(["tn_s3", "tn_s3", "tn_s2", "tn_s1"]), x, y, rng.uniform(0.35, 1.3))
    for _ in range(9):            # a few clustered drop-outs from a dirty platen
        cx, cy = rng.uniform(30, W - 30), rng.uniform(30, H - 30)
        for _ in range(rng.randint(6, 18)):
            d.circle("tn_s2", cx + rng.gauss(0, 6), cy + rng.gauss(0, 6), rng.uniform(0.4, 1.4))
    gx = 0 if gutter == "left" else W - 24
    d.poly("guardsh_fill", [(gx + (24 if gutter == "left" else -5), 0), (gx + (29 if gutter == "left" else 0), 0),
                            (gx + (29 if gutter == "left" else 0), H), (gx + (24 if gutter == "left" else -5), H)], closed=True)
    d.poly("guard_fill", [(gx, 0), (gx + 24, 0), (gx + 24, H), (gx, H)], closed=True)
    hx = gx + 12
    holes = [140 + k * 180 for k in range(7)]
    for y in holes:
        d.circle("hole_fill", hx, y, 1.9)
    for a, b in zip(holes[:-1], holes[1:]):
        d.poly("thread_orn", [(hx, a + 3), (hx + (3 if gutter == "left" else -3), (a + b) / 2), (hx, b - 3)])
    h = Hand(d, rng, "ink", amp=0.9)
    return d, h, rng


def folio(n, gutter):
    x = W - 120 if gutter == "left" else 60
    return dict(id="folio", x=W / 2 - 60, y=H - 70, w=120, size=16, lh=20, font=TYPE, align="center", color=TONER,
                runs=[(f"— {n} —", "")])
