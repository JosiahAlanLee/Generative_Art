#!/usr/bin/env python3
"""De Potestate et Accusatione: the nine plates, native and stroke-only.

Four plates carry no data (I, II, III, VIII): they are seeded procedures, and each says so on its
face. Five carry data and name the record they are drawn from (IV, V, VI, VII, IX):

  IV   the gate-and-window model's committed results table, 6,300 cells, both ledgers
  V    the incident case record's timeline and twenty-two codings, as filed
  VI   the Supreme Court of Japan's judgment of 8 February 2012, its dates and counts as stated
  VII  the refusal specimen (an unmodified copy in vendor/), run on every case
  IX   this book's manuscript, every sentence counted

No figure of a person is drawn. Units are millimetres on an A4 sheet, y down.

    python tabulae.py all OUT          every plate into OUT/<stem>/, each validated
    python tabulae.py iv OUT           one plate
"""
import csv
import importlib.util
import json
import math
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from viplate import VIPlate, validate, free, runs, ART, KEEP_OUT, REPO, W, H, FACES  # noqa: E402
from plotkit import catmull, arc_pts  # noqa: E402
import marks  # noqa: E402
from core import curl_pts  # noqa: E402

BOOK = os.path.dirname(HERE)
MANUSCRIPT = os.path.join(BOOK, "manuscript", "de-potestate-et-accusatione.md")
GATE = os.path.join(REPO, "books", "01_matricis_intervallorum", "models", "gate_window")
# The case record lives in the development repository; its data file is vendored, unmodified.
CASE = os.path.join(HERE, "vendor", "case.json")
REFUSAL = os.path.join(HERE, "vendor", "refusal.py")

LEGEND_X0 = 64.0          # the header register, right of the reserved blank
CAP = 2.5


# ---------------------------------------------------------------- shared --

def legend(P, lines, y0=41.5, gap=5.0, x=None, align="left", colors=None):
    """A register of lettered lines; returns the bottom y."""
    x = LEGEND_X0 if x is None else x
    for i, s in enumerate(lines):
        P.label(s, x, y0 + i * gap, CAP, align, (colors or {}).get(i, "ink"))
    return y0 + (len(lines) - 1) * gap


def boxed(boxes, x, y, pad=0.0):
    return any(b[0] - pad <= x <= b[2] + pad and b[1] - pad <= y <= b[3] + pad for b in boxes)


def clear_runs(pts, boxes, pad=0.0):
    """Runs of a polyline that lie in free space and outside the given boxes."""
    out = []
    for r in runs(pts, pad):
        cur = []
        for p in r:
            if boxed(boxes, p[0], p[1], pad):
                if len(cur) > 1:
                    out.append(cur)
                cur = []
            else:
                cur.append(p)
        if len(cur) > 1:
            out.append(cur)
    return out


def text_box(P, lines, y0=41.5, gap=5.0, x=None, align="left"):
    """the bounding box a legend would occupy, for keeping art out of it"""
    x = LEGEND_X0 if x is None else x
    w = max(P.font.width(s, CAP) for s in lines)
    x0 = {"left": x, "right": x - w, "center": x - w / 2}[align]
    return (x0 - 1.5, y0 - CAP - 1.5, x0 + w + 1.5, y0 + (len(lines) - 1) * gap + 2.0)


def dashed(h, a, b, dash=1.2, gap=1.0, weight="hair", color="ink"):
    L = math.dist(a, b)
    if L == 0:
        return
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    t = 0.0
    while t < L:
        e = min(L, t + dash)
        h.straight([(a[0] + ux * t, a[1] + uy * t), (a[0] + ux * e, a[1] + uy * e)], weight, color)
        t = e + gap


def open_ring(h, x, y, r, gaps=4, weight="orn", color="ink"):
    """a ring drawn in arcs with gaps: what is approximate is drawn open"""
    span = 360 / gaps
    for k in range(gaps):
        a0 = k * span + span * 0.18
        h.straight(arc_pts(x, y, r, a0, a0 + span * 0.64, 10), weight, color)


def tally(h, x, y, n, pitch=1.15, height=4.2, group_gap=1.6, weight="orn", color="ink", hooks=0):
    """tally marks in fives: four uprights struck by a diagonal; returns the width drawn.
    The first `hooks` strokes carry a small serif at the head: a second hand, not a date."""
    cx = x
    drawn = 0
    while drawn < n:
        k = min(5, n - drawn)
        ups = min(4, k)
        starts = []
        for i in range(ups):
            xx = cx + i * pitch
            h.straight([(xx, y), (xx, y - height)], weight, color)
            if drawn + i < hooks:
                h.straight([(xx, y - height), (xx + 0.55, y - height - 0.55)], weight, color)
            starts.append(xx)
        if k == 5:
            h.straight([(starts[0] - 0.6, y - 0.6), (starts[-1] + 0.6, y - height + 0.6)], weight, color)
            if drawn + 4 < hooks:
                h.straight([(starts[-1] + 0.6, y - height + 0.6), (starts[-1] + 1.15, y - height + 0.05)], weight, color)
        drawn += k
        cx += ups * pitch + group_gap
    return cx - x - group_gap


def bracket(h, x0, x1, y, depth=1.6, weight="orn", color="ink", dash=False):
    """a bracket over a span, ends turned down"""
    if dash:
        dashed(h, (x0, y), (x1, y), 1.4, 1.0, weight, color)
    else:
        h.straight([(x0, y), (x1, y)], weight, color)
    h.straight([(x0, y), (x0, y + depth)], weight, color)
    h.straight([(x1, y), (x1, y + depth)], weight, color)


def finish(P, out_dir, extra=None):
    P.furniture()
    P.caption_strip()
    P.scale_carrier()
    return P.export(out_dir, extra)


# ============================================================ I. artifice --

def tabula_i(out_dir):
    P = VIPlate("I", "The Three Powers", "AUTHORITY, HARM AND BLAME, HELD APART", "i-three-powers",
                "The clerk entered only the third hand.", 3, "THE THREE ARE HELD BY ONE HAND", 15,
                strap="THE WARP SETS / THE FIELD RECEIVES / THE THREAD SETTLES")
    lines = ["THE WARP: AUTHORITY OVER PRODUCTION", "THE FIELD: EXPOSURE TO HARM",
             "THE THREAD, IN RED: EXPOSURE TO BLAME", "CARRIES NO DATA. SEEDS 15, 16 AND 17"]
    box = text_box(P, lines, x=196, align="right")
    legend(P, lines, x=196, align="right")
    keep = [box]
    h = P.art
    # The warp: long lines fanning from an origin off the sheet, so the source of direction is never drawn.
    rw = random.Random(15)
    ox, oy = -70.0, 128.0
    warp = []
    for i in range(15):
        ang = math.radians(-15.5 + i * 2.35 + rw.uniform(-0.5, 0.5))
        ph = rw.uniform(0, 6.28)
        pts = []
        for t in range(0, 320, 2):
            x = ox + t * math.cos(ang)
            y = oy + t * math.sin(ang) + 2.2 * math.sin(t / 41.0 + ph) * (t / 320)
            pts.append((x, y))
        warp.append(pts)
        for r in clear_runs(pts, keep, 0.8):
            h.stroke(r, "orn", "ink", amp=0.3)
    # The field: short marks whose density rises toward the lower edge, oriented by a slow noise.
    rf = random.Random(16)
    x0, y0, x1, y1 = ART
    marksdrawn = []
    tries = 0
    grid = {}
    while len(marksdrawn) < 2300 and tries < 200000:
        tries += 1
        x, y = rf.uniform(x0 + 2, x1 - 2), rf.uniform(y0 + 2, y1 - 2)
        p = ((y - y0) / (y1 - y0)) ** 2.1
        if rf.random() > p or not free(x, y, 1.2) or boxed(keep, x, y, 1.2):
            continue
        cell = (int(x // 1.6), int(y // 1.6))
        if any((cell[0] + i, cell[1] + j) in grid for i in (-1, 0, 1) for j in (-1, 0, 1)):
            continue
        grid[cell] = True
        a = 0.9 * math.sin(x / 19.0) + 0.7 * math.cos(y / 13.0) + rf.uniform(-0.25, 0.25)
        L = rf.uniform(0.9, 2.1) * (0.8 + 0.6 * (y - y0) / (y1 - y0))
        h.stroke([(x - L / 2 * math.cos(a), y - L / 2 * math.sin(a)), (x + L / 2 * math.cos(a), y + L / 2 * math.sin(a))],
                 "hair", "ink", amp=0.08)
        marksdrawn.append((x, y))
    # The thread: a red walk that crosses both and settles on the mark nearest its end.
    rt = random.Random(17)
    start, target = (192.0, 66.0), (104.0, 193.0)
    ctrl = [start]
    for k in range(1, 12):
        u = k / 12
        bx, by = start[0] + (target[0] - start[0]) * u, start[1] + (target[1] - start[1]) * u
        sway = (rt.uniform(-1, 1) * 26.0) * math.sin(math.pi * u)
        ctrl.append((bx + sway, by + rt.uniform(-6, 6)))
    ctrl.append(target)
    path = catmull(ctrl, 14)
    end = path[-1]
    near = min(marksdrawn, key=lambda m: math.dist(m, end))
    path.append(near)
    for r in clear_runs(path, keep, 0.5):
        h.stroke(r, "core", "red", amp=0.35)
    h.ring(near[0], near[1], 2.1, "orn", "red")
    densest = max(marksdrawn, key=lambda m: m[1])
    return finish(P, out_dir, {"marks": len(marksdrawn), "warp_lines": len(warp),
                               "thread_end": [round(near[0], 2), round(near[1], 2)],
                               "thread_end_to_lowest_mark_mm": round(math.dist(near, densest), 2)})


# =========================================================== II. artifice --

def tabula_ii(out_dir):
    P = VIPlate("II", "Near Misfortune", "CONTACT ENTERED AS CAUSE", "ii-near-misfortune",
                "The nearest was entered as the cause.", 5, "BLAME FOLLOWS CAUSE NOT CONTACT", 1619,
                strap="PATHS / MISFORTUNES / THEIR CAUSES / THE NEAREST APPROACH")
    lines = ["THE PATHS: WORK, BY A SEEDED FLOW", "THE RINGS: MISFORTUNES, PLACED AT RANDOM",
             "DASHED: THEIR CAUSES, FROM THE MARGIN", "RED: A PATH WITHIN 6 MM OF A RING",
             "CARRIES NO DATA. SEED 1619"]
    box = text_box(P, lines, x=196, align="right")
    legend(P, lines, x=196, align="right")
    keep = [box]
    h = P.art
    rng = random.Random(1619)
    x0, y0, x1, y1 = ART

    def field(x, y):
        return (0.55 * math.sin(x / 23.0 + 1.3) + 0.45 * math.cos(y / 17.0) + 0.35 * math.sin((x + 2 * y) / 47.0))

    # misfortunes first, so the causes can be laid
    rings = []
    while len(rings) < 9:
        p = (rng.uniform(x0 + 14, x1 - 14), rng.uniform(y0 + 46, y1 - 12))
        if free(*p, 8) and not boxed(keep, *p, 8) and all(math.dist(p, q) > 30 for q in rings):
            rings.append(p)
    R = 1.9
    for (cx, cy) in rings:
        h.ring(cx, cy, R, "orn", "ink")
        # a cause enters from the nearest side margin, dashed, and stops at the ring
        side = x0 + 1 if cx - x0 < x1 - cx else x1 - 1
        mid = ((side + cx) / 2, cy + rng.uniform(-14, 14))
        pts = catmull([(side, cy + rng.uniform(-8, 8)), mid, (cx + (R + 0.6) * (1 if side > cx else -1), cy)], 10)
        for r in clear_runs(pts, keep, 0.5):
            for a, b in zip(r[::2], r[1::2]):
                h.straight([a, b], "hair", "ink")
    # the paths
    paths = []
    for i in range(62):
        x, y = x0 + 1.5, rng.uniform(y0 + 3, y1 - 3)
        pts = [(x, y)]
        for _ in range(420):
            a = field(x, y)
            x += 0.9 * math.cos(a) + 0.35
            y += 0.9 * math.sin(a)
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                break
            pts.append((x, y))
        if len(pts) > 20:
            paths.append(pts)
    marked = 0
    for pi, pts in enumerate(paths):
        for r in clear_runs(pts, keep, 0.6):
            h.stroke(r, "orn" if pi % 9 == 0 else "hair", "ink", amp=0.25)
    for pts in paths:
        for (cx, cy) in rings:
            j = min(range(len(pts)), key=lambda k: math.dist(pts[k], (cx, cy)))
            d = math.dist(pts[j], (cx, cy))
            if d < 6.0 and free(*pts[j], 0.5) and not boxed(keep, *pts[j], 0.5):
                a, b = pts[max(0, j - 1)], pts[min(len(pts) - 1, j + 1)]
                tx, ty = b[0] - a[0], b[1] - a[1]
                L = math.hypot(tx, ty) or 1
                nx, ny = -ty / L, tx / L
                px, py = pts[j]
                h.straight([(px - nx * 1.4, py - ny * 1.4), (px + nx * 1.4, py + ny * 1.4)], "core", "red")
                marked += 1
    return finish(P, out_dir, {"paths": len(paths), "misfortunes": len(rings), "red_marks": marked,
                               "rule": "a red mark wherever a path passes within 6 mm of a ring centre"})


# ========================================================== III. artifice --

def tabula_iii(out_dir):
    P = VIPlate("III", "The Weft", "THE UPKEEP THAT HOLDS THE PROJECT", "iii-the-weft",
                "The weft was entered as kindness.", 7, "THE WARP STANDS WITHOUT THE WEFT", 1972,
                strap="WARP: THE PROJECT / WEFT: THE UPKEEP / RED: THE INTERRUPTION ABSORBED")
    reg = ["THE WARP", "THE PROJECT", "", "THE WEFT", "THE UPKEEP,", "IN PIECES", "", "IN RED", "THE",
           "INTERRUPTION", "ABSORBED", "", "CARRIES NO", "DATA. SEED", "1972"]
    for i, s in enumerate(reg):
        if s:
            P.label(s, 16, 92 + i * 5.0, CAP, "left", "red" if s in ("IN RED",) else "ink")
    h = P.art
    rng = random.Random(1972)
    warps = [70 + 9.6 * i for i in range(14)]
    top, bot = 44.0, 231.0
    # rows: denser through the middle band, set by hand
    rows, y = [], top + 2
    while y < bot - 1:
        rows.append(y)
        y += 1.35 if 96 <= y <= 186 else 2.3
    red_i = min(range(len(rows)), key=lambda i: abs(rows[i] - 150))
    gap = 0.75
    # weft: pieces that start and stop where the seed says; under a warp, the weft breaks
    for i, y in enumerate(rows):
        if i == red_i:
            continue
        x = 62 + rng.uniform(0, 6)
        while x < 197:
            L = rng.uniform(14, 70)
            a, b = x, min(197.0, x + L)
            cur = a
            for k, wx in enumerate(warps):
                if a < wx < b and (i + k) % 2 == 0:      # under this warp
                    if wx - gap - cur > 0.4:
                        h.stroke([(cur, y), (wx - gap, y)], "hair", "ink", amp=0.12)
                    cur = wx + gap
            if b - cur > 0.4:
                h.stroke([(cur, y), (b, y)], "hair", "ink", amp=0.12)
            # a finished end: a small hook
            hk = 1 if rng.random() < 0.5 else -1
            h.stroke(curl_pts(b, y, 0, 0.6, 0.45, 1.0, hand=hk), "hair", "ink", amp=0.05)
            x = b + rng.uniform(0.8, 6.0)
    # the red row: unbroken, over every warp
    ry = rows[red_i]
    h.stroke([(62.0, ry), (197.0, ry)], "orn", "red", amp=0.15)
    # warp: long verticals, broken where the weft passes over them
    for k, wx in enumerate(warps):
        cur = top
        for i, y in enumerate(rows):
            over = (i + k) % 2 == 1 or i == red_i
            if over:
                if y - gap - cur > 0.4:
                    h.stroke([(wx, cur), (wx, y - gap)], "orn", "ink", amp=0.1)
                cur = y + gap
        h.stroke([(wx, cur), (wx, bot)], "orn", "ink", amp=0.1)
    return finish(P, out_dir, {"warp": len(warps), "rows": len(rows), "red_row_y": round(ry, 2)})


# ========================================================== VIII. artifice --

def tabula_viii(out_dir):
    P = VIPlate("VIII", "The Rule", "CONDITIONAL PARTICIPATION, PROPOSED", "viii-the-rule",
                "Name what would change it.", 11, "AN INDEFINITE HOLD IS AN EXCLUSION", 2026,
                strap="STOP / HOLD / CHANGE / PRECAUTION / REVIEW")
    lines = ["A PROPOSAL DRAWN AS AN INSTRUMENT.", "IT CARRIES NO DATA AND CLAIMS",
             "NOTHING ABOUT WHETHER THE RULE WORKS."]
    legend(P, lines, x=196, align="right")
    h = P.art
    cx, cy = 114.0, 130.0
    r_t, r_g, r_o0, r_o1 = 14.0, 36.0, 47.0, 54.0
    # the task and its benefit
    h.ring(cx, cy, r_t, "core", "ink")
    h.ring(cx, cy, r_t - 1.4, "hair", "ink")
    for i, s_ in enumerate(["THE TASK", "AND ITS", "BENEFIT"]):
        P.label(s_, cx, cy - 3.4 + i * 4.6, CAP, "center")
    # a dotted ring of the alternatives compared, between the task and the gates
    for k in range(72):
        a = math.radians(k * 5)
        h.dot(cx + 24.5 * math.cos(a), cy + 24.5 * math.sin(a), 0.28, "ink")
    h.stroke(arc_pts(cx, cy, r_g, 0, 360, 180), "orn", "ink", amp=0.2)
    gates = [(-90, "STOP"), (0, "HOLD"), (90, "CHANGE"), (180, "PRECAUTION")]
    for ang, name in gates:
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        px, py = -uy, ux
        h.straight([(cx + ux * (r_t + 0.6), cy + uy * (r_t + 0.6)), (cx + ux * (r_g - 6.0), cy + uy * (r_g - 6.0))], "hair", "ink")
        gx, gy = cx + ux * r_g, cy + uy * r_g
        for sgn in (-1, 1):
            for off in (3.6, 4.6):
                b0 = (gx + px * sgn * off - ux * 5.0, gy + py * sgn * off - uy * 5.0)
                e0 = (gx + px * sgn * off + ux * 5.0, gy + py * sgn * off + uy * 5.0)
                h.straight([b0, e0], "core" if off < 4 else "hair", "red")
        h.straight([(gx - px * 5.6 + ux * 5.0, gy - py * 5.6 + uy * 5.0), (gx + px * 5.6 + ux * 5.0, gy + py * 5.6 + uy * 5.0)], "core", "red")
        h.straight([(gx - px * 5.6 + ux * 5.9, gy - py * 5.6 + uy * 5.9), (gx + px * 5.6 + ux * 5.9, gy + py * 5.6 + uy * 5.9)], "hair", "red")
        h.dot(gx, gy, 0.5, "red")
    P.label("STOP", cx, cy - r_o1 - 4.2, CAP, "center", "red")
    P.label("CHANGE", cx, cy + r_o1 + 6.8, CAP, "center", "red")
    P.label("HOLD", cx + r_o1 + 3.4, cy + 1.25, CAP, "left", "red")
    P.label("PRECAUTION", cx - r_o1 - 3.4, cy + 1.25, CAP, "right", "red")
    # the review ring: a stroke bundle broken into four arcs, each named
    reviews = [(225, "SCOPE", "right"), (315, "ANSWER", "left"), (45, "DEADLINE", "left"), (135, "EXPLANATION", "right")]
    for a0 in range(0, 360, 90):
        for k in range(0, 77):
            a = math.radians(a0 + 6.5 + k)
            ri = r_o0 + (0.7 if k % 2 else 0.0)
            h.straight([(cx + ri * math.cos(a), cy + ri * math.sin(a)), (cx + r_o1 * math.cos(a), cy + r_o1 * math.sin(a))], "hair", "ink")
        h.straight(arc_pts(cx, cy, r_o1 + 1.2, a0 + 5.5, a0 + 84.5, 40), "orn", "ink")
        h.straight(arc_pts(cx, cy, r_o0 - 1.2, a0 + 5.5, a0 + 84.5, 40), "hair", "ink")
    for ang, name, al in reviews:
        a = math.radians(ang)
        lx, ly = cx + (r_o1 + 5.5) * math.cos(a), cy + (r_o1 + 5.5) * math.sin(a)
        P.label(name, lx, ly + (1.2 if ang in (45, 135) else 0.6), CAP, al)
    # what opens each gate, and the review, in a register under the instrument
    trig = [("STOP", "SUBSTANTIATED FRAUD, HARASSMENT OR UNJUST EXPOSURE"),
            ("HOLD", "A CREDIBLE COMPLAINT, WHERE SPREADING WOULD COMPOUND IT"),
            ("CHANGE", "A FEASIBLE, LESS INJURIOUS WAY THAT KEEPS THE FUNCTION"),
            ("PRECAUTION", "SERIOUS UNCERTAINTY ABOUT AN IRREVERSIBLE INJURY"),
            ("REVIEW", "A DEFINED SCOPE, AN ANSWER, A DEADLINE, AN EXPLANATION")]
    for i, (name, text) in enumerate(trig):
        y = 200.0 + i * 5.6
        P.label(name, 40.0, y, CAP, "right", "red" if name != "REVIEW" else "ink")
        P.label(text, 43.0, y, CAP, "left")
    return finish(P, out_dir, {"gates": [g for _, g in gates], "review": [r for _, r, _ in reviews]})


# ================================================================ IV. data --

def gate_rows():
    """The committed results table and the model's own comparisons."""
    spec = importlib.util.spec_from_file_location("gate_verdict", os.path.join(GATE, "verdict.py"))
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    rows = V.read_results(V.HERE / "results.csv")
    margin = V.load_rule()["margin"]
    return V, rows, margin


def tabula_iv(out_dir):
    V, rows, m = gate_rows()
    P = VIPlate("IV", "Two Ledgers", "TOTAL HARM IN INK, THE BOOKED LEDGER IN RED", "iv-two-ledgers",
                "The ledger counted the error and not the wait.", 2, "DELAY IS BOOKED AND THE GATE STAYS", 20261018,
                strap="", data="the gate-and-window model's results table (results.csv, run of 18 October 2026)")
    g = V.GRID
    eps, dl, phi, lam, hw, hwin = g["eps"], g["delta"], g["phi"], g["lam"], g["h_wrong"], g["h_window"]

    def total(r):
        if V.c_beats_a(r, m):
            return "C"
        if r["harm_A"] <= (1 - m) * r["harm_C"]:
            return "A"
        return "T"
    counts = {"C": 0, "A": 0, "T": 0, "reversed": 0}
    lines = ["EVERY CELL OF THE GATE-AND-WINDOW MODEL",
             "PANELS: P(WRONG) ACROSS, HARM OF A WRONG ACTION DOWN",
             "IN A PANEL: LATENCY ACROSS, CATCH RATE DOWN",
             "IN A CELL: WINDOW LOSS ACROSS, OVERRIDE DOWN",
             "LEANS RIGHT: C BEATS A ON TOTAL HARM; LEFT: A BEATS C",
             "RED: THE BOOKED LEDGER FAVOURS A INSTEAD",
             "RESULTS.CSV, RUN OF 18 OCTOBER 2026"]
    legend(P, lines, y0=39.5, gap=4.75, colors={5: "red"})
    h = P.art
    X0, X1, Y0, Y1, gx, gy = 27.0, 196.0, 81.0, 233.0, 2.6, 2.6
    pw = (X1 - X0 - 4 * gx) / 5
    ph = (Y1 - Y0 - 4 * gy) / 5
    cw, chh = pw / len(lam), ph / len(dl)
    sw, sh = cw / len(hwin), chh / len(phi)
    for i, e in enumerate(eps):
        P.label(f"{e:.2f}", X0 + i * (pw + gx) + pw / 2, Y0 - 2.2, CAP, "center")
    for j, w in enumerate(hw):
        P.label(f"{w:g}", X0 - 2.0, Y0 + j * (ph + gy) + ph / 2 + 1.2, CAP, "right")
    for i in range(5):
        for j in range(5):
            px, py = X0 + i * (pw + gx), Y0 + j * (ph + gy)
            h.straight([(px, py), (px + pw, py), (px + pw, py + ph), (px, py + ph)], "hair", "ink", closed=True)
    for r in rows:
        i, j = eps.index(r["eps"]), hw.index(r["h_wrong"])
        a, b = lam.index(r["lam"]), dl.index(r["delta"])
        c, d = hwin.index(r["h_window"]), phi.index(r["phi"])
        x = X0 + i * (pw + gx) + a * cw + c * sw + sw / 2
        y = Y0 + j * (ph + gy) + b * chh + d * sh + sh / 2
        v = total(r)
        counts[v] += 1
        dx, dy = sw * 0.3, sh * 0.34
        if v == "C":
            h.straight([(x - dx, y + dy), (x + dx, y - dy)], "hair", "ink")
        elif v == "A":
            h.straight([(x + dx, y + dy), (x - dx, y - dy)], "hair", "ink")
        if v == "C" and V.a_beats_c_booked(r):
            h.straight([(x - sw * 0.42, y), (x + sw * 0.42, y)], "orn", "red")
            counts["reversed"] += 1
    P.strap = (f"{len(rows)} CELLS / C {counts['C']} / A {counts['A']} / TIED {counts['T']} / "
               f"REVERSED {counts['reversed']}")
    return finish(P, out_dir, {"counts": counts, "margin": m, "cells": len(rows),
                               "results_sha256": V.sha256_file(V.HERE / "results.csv")})


# ================================================================= V. data --

# Placement by whose systems or statement the event concerns: the operator's above the line,
# the defender's below, the investigator's publication on the line. Short labels are this
# plate's abbreviations of the case record's entries, in its order.
EVENTS = [
    ("op", "FIRST NOTE ON THE BOARD"), ("op", "UNINTENDED INTERNET ACCESS"), ("op", "BOARD OBSERVED, LATE MAY"),
    ("op", "ADMINISTRATOR ACCESS"), ("op", "OUTAGE"), ("op", "SECURITY INCIDENT OPENED"),
    ("op", "REBUILD; BOARD CLEARED"), ("op", "BOARD RECREATED"), ("def", "14 HF CREDENTIALS SHARED"),
    ("def", "FILE READ, CODE RUN AT HF"), ("def", "SPREAD ACROSS HF CLUSTERS"), ("op", "MOST AGENTS STOP AT ONCE"),
    ("def", "HF LOCKS THE AGENTS OUT"), ("op", "SIGNING KEY TAKEN"), ("def", "HF DISCLOSES"),
    ("op", "ALERT ON IDENTITY CALLS"), ("op", "ACTIVITY TIED TO HF"), ("op", "OPENAI DISCLOSES"),
    ("op", "ACCOUNT BY OPENAI"), ("inv", "INVESTIGATION BY METR"),
]
RED_EVENTS = {3, 6, 7, 8, 16}
ROMAN_MONTH = {5: "V", 6: "VI", 7: "VII", 8: "VIII"}


def tabula_v(out_dir):
    import datetime as dt
    case = json.load(open(CASE))
    tl, codings = case["timeline"], case["codings"]
    if len(tl) != len(EVENTS):
        raise ValueError("the case record's timeline changed; review the plate's labels")
    P = VIPlate("V", "A Channel Seen", "ONE HUNDRED AND SEVEN DAYS, 12 MAY TO 26 AUGUST 2026", "v-a-channel-seen",
                "It was answered as the kind it was opened as.", 9, "RECLASSIFIED WITHOUT DELAY", 1907,
                strap="OPERATOR ABOVE THE LINE / DEFENDER BELOW / INVESTIGATOR ON IT",
                data="the incident case record's timeline and codings (vendor/case.json, unmodified from the development repository at f0d4f65)")
    h = P.art
    day0 = dt.date(2026, 5, 12)
    days = [(dt.date.fromisoformat(t["date"]) - day0).days for t in tl]
    n_days = 106
    AX, X0, X1 = 136.0, 24.0, 192.0
    k = (X1 - X0) / n_days
    X = lambda d: X0 + d * k
    h.straight([(X0, AX), (X1, AX)], "orn", "ink")
    for d in range(n_days + 1):
        date = day0 + dt.timedelta(days=d)
        L = 3.4 if date.day == 1 else (1.9 if d % 7 == 0 else 1.0)
        h.straight([(X(d), AX), (X(d), AX + L)], "hair", "ink")
        if date.day == 1:
            P.label({6: "JUNE", 7: "JULY", 8: "AUGUST"}[date.month], X(d) + 0.8, AX + 7.6, CAP, "left")
    P.label("12 MAY", X0, AX + 7.6, CAP, "left")
    P.label("26 AUG", X1, AX + 7.6, CAP, "right")
    # stems at staggered levels so that no two numbers collide
    levels = {"op": [124, 114, 104, 94, 84], "def": [152, 162, 172, 182]}
    placed = []
    for i, (t, d) in enumerate(zip(tl, days), start=1):
        side, _ = EVENTS[i - 1]
        x = X(d)
        col = "red" if i in RED_EVENTS else "ink"
        approx = "approximate" in t["basis"]
        if side == "inv":
            gy = AX
            h.straight([(x - 1.5, gy), (x, gy - 1.5), (x + 1.5, gy), (x, gy + 1.5)], "orn", col, closed=True)
            P.label(str(i), x + 1.0, gy - 3.0, CAP, "left", col)
            continue
        for y in levels[side]:
            if all(not (abs(px - x) < 6.2 and py == y) for px, py in placed):
                break
        placed.append((x, y))
        top = y + (2.4 if side == "op" else -2.4)
        h.straight([(x, AX - 0.4 if side == "op" else AX + 3.6), (x, top)], "hair", col)
        if approx:
            open_ring(h, x, y, 1.45, 5, "orn", col)
        else:
            h.ring(x, y, 1.45, "orn", col)
        P.label(str(i), x, y - 3.0 if side == "op" else y + 5.6, CAP, "center", col)
    # the register of events, two columns
    for i, (t, (side, lab)) in enumerate(zip(tl, EVENTS), start=1):
        col_i, row = (i - 1) // 10, (i - 1) % 10
        x = 16 + col_i * 93
        y = 196.5 + row * 4.15
        d = dt.date.fromisoformat(t["date"])
        when = ("C. " if "approximate" in t["basis"] else "") + f"{d.day} {ROMAN_MONTH[d.month]}"
        colour = "red" if i in RED_EVENTS else "ink"
        P.label(f"{i}", x + 4, y, CAP, "right", colour)
        P.label(when, x + 7, y, CAP, "left", colour)
        P.label(lab, x + 25, y, CAP, "left", colour)
    # the twenty-two codings, in the header register
    tally_b = {}
    for c in codings:
        tally_b[c["bearing"]] = tally_b.get(c["bearing"], 0) + 1
    lines = [f"THE RECORD HOLDS {len(codings)} CODINGS, C01 TO C22. BY BEARING:",
             f"RING: CONSISTENT {tally_b.get('consistent', 0)}. OPEN: UNCODEABLE {tally_b.get('uncodeable', 0)}.",
             f"BAR: OUTSIDE {tally_b.get('outside', 0)}. RED CROSS: COUNTS AGAINST {tally_b.get('counts against', 0)}."]
    legend(P, lines, y0=40.0, gap=4.7)
    base_y, gx0 = 63.0, 70.0
    pitch = (194.0 - gx0) / (len(codings) - 1)
    h.straight([(gx0 - 2.5, base_y), (194.0 + 2.5, base_y)], "hair", "ink")
    for j, c in enumerate(codings):
        x = gx0 + j * pitch
        y = base_y - 2.6 if c["party"] == "operator" else (base_y + 2.6 if c["party"] == "defender" else base_y)
        b = c["bearing"]
        if b == "consistent":
            h.ring(x, y, 1.15, "orn", "ink")
        elif b == "uncodeable":
            open_ring(h, x, y, 1.15, 4, "orn", "ink")
        elif b == "outside":
            h.straight([(x - 1.3, y), (x + 1.3, y)], "core", "ink")
        else:
            h.straight([(x - 1.1, y - 1.1), (x + 1.1, y + 1.1)], "core", "red")
            h.straight([(x - 1.1, y + 1.1), (x + 1.1, y - 1.1)], "core", "red")
    return finish(P, out_dir, {"days": n_days + 1, "events": len(tl), "codings": tally_b,
                               "red_events": sorted(RED_EVENTS)})


# ================================================================ VI. data --

def tabula_vi(out_dir):
    # Every date and count below is the majority's, as the decision's English translation states it:
    #   the first cross-cut hub accident, the Yamahide Accident, 21 June 1992;
    #   "the second accident of cross-cut damage to the hub that occurred on June 21, 1994";
    #   the Chugoku JR Bus Accident, 27 June 1999: "16 accidents including the Chugoku JR Bus Accident;
    #   eight of these 16 accidents involved Hub D", in "the period of some seven years from the Yamahide Accident";
    #   the Seya Accident, 10 January 2002: "the 40th accident of this type and the 19th accident involving
    #   Hub D since the Yamahide Accident"; "in terms of Hub D, 19 accidents occurred within slightly less than six years".
    P = VIPlate("VI", "The Wear Theory", "SUPREME COURT OF JAPAN, DECISION OF 8 FEBRUARY 2012", "vi-the-wear-theory",
                "The breaks were entered as wear.", 4, "THE ASSIGNMENT MATCHED THE CONTRIBUTION", 2012,
                strap="FOUR DATED ACCIDENTS / THREE COUNTS / ONE REPORT",
                data="the majority's statement of facts in the Supreme Court of Japan's decision of 8 February 2012, in its English translation")
    lines = ["THIRD PETTY BENCH, CASE 2009 (A) 359", "DATES AND COUNTS OF THE MAJORITY, AS STATED",
             "TALLIES ARE COUNTS, NOT DATES: NO STROKE", "IS ONE ACCIDENT. RED: THE REPORT, THE DEATH"]
    legend(P, lines, y0=40.5, gap=4.8)
    h = P.art
    AX, X0, X1, T0, T1 = 200.0, 24.0, 190.0, 1992.0, 2002.25
    X = lambda t: X0 + (t - T0) * (X1 - X0) / (T1 - T0)
    # the decade, ruled
    h.straight([(X0, AX), (X1, AX)], "core", "ink")
    for yr in range(1992, 2003):
        x = X(yr)
        h.straight([(x, AX), (x, AX + 3.0)], "orn", "ink")
        P.label(str(yr), x, AX + 8.2, CAP, "center")
        if yr < 2002:
            for q in range(1, 12):
                xm = X(yr + q / 12)
                h.straight([(xm, AX), (xm, AX + (1.4 if q % 3 else 2.0))], "hair", "ink")
    t_first = 1992 + (31 + 29 + 31 + 30 + 31 + 20) / 366
    t_second = 1994 + (31 + 28 + 31 + 30 + 31 + 20) / 365
    t_bus = 1999 + (31 + 28 + 31 + 30 + 31 + 26) / 365
    t_seya = 2002 + 9 / 365
    events = [(t_first, "THE FIRST: YAMAHIDE, 21 VI 1992", "ink"), (t_second, "THE SECOND, 21 VI 1994", "ink"),
              (t_bus, "CHUGOKU JR BUS, 27 VI 1999", "ink"), (t_seya, "SEYA, YOKOHAMA, 10 I 2002", "red")]
    for k, (t, lab, col) in enumerate(events, start=1):
        x = X(t)
        h.ring(x, AX, 2.0, "core", col)
        P.label(str(k), x, AX - 3.8, CAP, "center", col)
        P.label(str(k), 30.0, AX + 16.8 + (k - 1) * 4.7, CAP, "right", col)
        P.label(lab, 33.5, AX + 16.8 + (k - 1) * 4.7, CAP, "left", col)
    # 1999: the accident handled on the wear theory; the report that no action was needed. Its day is not drawn.
    xr0, xr1 = X(t_bus) + 1.6, X(2000.0) - 0.4
    bracket(h, xr0, xr1, AX - 9.5, 2.2, "core", "red")
    P.label("1999: HANDLED AS WEAR;", xr1, AX - 19.6, CAP, "right", "red")
    P.label("NO ACTION REPORTED", xr1, AX - 14.6, CAP, "right", "red")
    # sixteen from the first to the bus, the bus among them; hooked beside them, the eight on hub D
    xa, xb = X(t_first), X(t_bus)
    bracket(h, xa, xb, 152.0, 2.0, "orn", "ink")
    w16, w8 = tally_width(16), tally_width(8)
    tx = (xa + xb) / 2 - (w16 + 6.0 + w8) / 2
    tally(h, tx, 147.5, 16)
    tally(h, tx + w16 + 6.0, 147.5, 8, hooks=8)
    P.label("16 TO THE BUS, THE BUS AMONG THEM. HOOKED: 8 ON HUB D", (xa + xb) / 2, 138.4, CAP, "center")
    # forty from the first to the death in Yokohama, which was the fortieth
    xs = X(t_seya)
    bracket(h, xa, xs, 122.0, 2.0, "orn", "ink")
    w40 = tally_width(40)
    tally(h, (xa + xs) / 2 - w40 / 2, 117.5, 40)
    P.label("40 FROM THE FIRST TO THE DEATH, THE FORTIETH", (xa + xs) / 2, 108.4, CAP, "center")
    # nineteen on hub D in slightly under six years, the death the nineteenth; the start is not given
    xs0 = X(t_seya - 6.0)
    xs1 = X(t_seya - 5.4)
    dashed(h, (xs0, 92.0), (xs1, 92.0), 1.4, 1.0, "orn", "ink")
    h.straight([(xs1, 92.0), (xs, 92.0)], "orn", "ink")
    h.straight([(xs, 92.0), (xs, 94.0)], "orn", "ink")
    w19 = tally_width(19)
    tally(h, (xs0 + xs) / 2 - w19 / 2, 87.5, 19, hooks=19)
    P.label("19 ON HUB D IN SLIGHTLY UNDER SIX YEARS", (xs0 + xs) / 2, 78.4, CAP, "center")
    P.label("THE DEATH THE NINETEENTH; NO START GIVEN", (xs0 + xs) / 2, 99.0, CAP, "center")
    return finish(P, out_dir, {"dated": [e[1] for e in events], "counts": {"first_to_bus": 16, "of_them_hub_d": 8,
                               "first_to_seya": 40, "hub_d_slightly_under_six_years": 19}})


def tally_width(n, pitch=1.15, group_gap=1.6):
    full, rest = divmod(n, 5)
    groups = [4] * full + ([min(4, rest)] if rest else [])
    return sum(g * pitch for g in groups) + group_gap * (len(groups) - 1)


# =============================================================== VII. data --

def tabula_vii(out_dir):
    spec = importlib.util.spec_from_file_location("refusal_specimen", REFUSAL)
    R = importlib.util.module_from_spec(spec)
    sys.modules["refusal_specimen"] = R
    spec.loader.exec_module(R)
    P = VIPlate("VII", "The Station", "SEVEN OPERATORS, ONE OFFICE, A DEADLINE OF FOUR", "vii-the-station",
                "Four stopped together and no name was written.", 6, "THE OFFICE NAMES THE ORGANISERS", 1981,
                strap="REFUSERS ACROSS / CAPACITY DOWN / RED: NAMED / RING: AUTHORITY IN TIME",
                data="the refusal specimen (vendor/refusal.py, unmodified from the public edition at 3529a77)")
    lines = ["THE REFUSAL SPECIMEN, RUN ON EVERY CASE", "OF REFUSERS 0 TO 7 AND REPLACEMENT CAPACITY",
             "0 TO 7, UNDER ITS FOUR DECLARED RULES", "THE OFFICE GRANTS AT 10; THE DEADLINE IS 4"]
    legend(P, lines, y0=40.5, gap=4.8)
    h = P.art
    panels = [("THE STATION", dict(replacement_time=3, stoppage_rate=1)),
              ("REPLACEMENT TOO SLOW", dict(replacement_time=5, stoppage_rate=1)),
              ("STOPPAGE CHEAP", dict(replacement_time=3, stoppage_rate=0.5))]
    X0, gap, cell = 25.0, 5.0, 6.75
    pw = 8 * cell
    Y0 = 98.0
    summary = []
    for pi, (name, kw) in enumerate(panels):
        px = X0 + pi * (pw + gap)
        P.label(name, px + pw / 2, Y0 - 11.0, CAP, "center")
        for k in range(8):
            P.label(str(k), px + k * cell + cell / 2, Y0 - 3.0, CAP, "center")
        h.straight([(px + 4 * cell, Y0 - 1.0), (px + 4 * cell, Y0 + 8 * cell + 1.0)], "hair", "ink")
        opened = named_total = 0
        for cap in range(8):
            if pi == 0:
                P.label(str(cap), px - 1.6, Y0 + cap * cell + cell / 2 + 1.25, CAP, "right")
            st = R.Station(operators=7, stoppage_threshold=4, replacement_capacity=cap, replacement_time=kw["replacement_time"],
                           grant_time=10, grant_cost=6, stoppage_rate=kw["stoppage_rate"])
            for k in range(8):
                o = R.evaluate(st, k, deadline=4)
                cx, cy = px + k * cell + cell / 2, Y0 + cap * cell + cell / 2
                for op in range(1, 8):
                    x = cx + (op - 4) * 0.72
                    refuses = op <= k
                    col = "red" if op in o.named else "ink"
                    top = (x + (0.85 if refuses else 0.0), cy - 1.7)
                    h.straight([(x, cy + 1.7), top], "hair" if col == "ink" else "orn", col)
                if o.route_open:
                    h.ring(cx, cy, 3.05, "hair", "ink")
                    opened += 1
                named_total += len(o.named)
        summary.append({"panel": name, "cells": 64, "authority_in_time": opened, "names_written": named_total})
    P.label("THRESHOLD", X0 + 4 * cell, Y0 + 8 * cell + 5.4, CAP, "center")
    # the rules, as declared, in a register under the panels
    rules = ["1  FEWER THAN 4 REFUSE: NOTHING STOPS; THE RECORD NAMES THE FIRST",
             "2  4 OR MORE: THE STATION STOPS, AND IS RECORDED AGAINST THE STATION",
             "3  IF ALL CAN BE REPLACED BEFORE THE DEADLINE, EACH REFUSER IS NAMED",
             "4  ELSE THE OFFICE GRANTS IF THE STOPPAGE WOULD COST IT MORE THAN 6"]
    for i, s in enumerate(rules):
        P.label(s, 16, 172.0 + i * 5.2, CAP, "left", "ink")
    P.label("REPLACEMENT TAKES 3 (TOO SLOW: 5). STOPPAGE COSTS 1 A UNIT (CHEAP: 0.5)", 16, 197.0, CAP, "left")
    # two enlarged key cells
    kx, ky, sc = 40.0, 218.0, 3.2
    keyst = R.Station(7, 4, 2, 3, 10, 6, 1)
    for op in range(1, 8):
        x = kx + (op - 4) * 0.72 * sc
        refuses = op <= 1
        col = "red" if op == 1 else "ink"
        h.straight([(x, ky + 1.7 * sc), (x + (0.85 * sc if refuses else 0), ky - 1.7 * sc)], "orn", col)
    P.label("ONE REFUSES, BELOW 4: NAMED", kx + 13.0, ky - 2.0, CAP, "left", "red")
    P.label("SIX WORK ON", kx + 13.0, ky + 3.2, CAP, "left")
    k2x = 140.0
    for op in range(1, 8):
        x = k2x + (op - 4) * 0.72 * sc
        h.straight([(x, ky + 1.7 * sc), (x + 0.85 * sc, ky - 1.7 * sc)], "orn", "ink")
    h.ring(k2x, ky, 3.05 * sc, "orn", "ink")
    P.label("SEVEN, NO NAME", k2x + 13.0, ky - 2.0, CAP, "left")
    P.label("IN TIME", k2x + 13.0, ky + 3.2, CAP, "left")
    o_key = R.evaluate(keyst, 1, deadline=4)
    return finish(P, out_dir, {"panels": summary, "key_cell": {"refusers": 1, "named": list(o_key.named)},
                               "refusal_sha256": __import__("hashlib").sha256(open(REFUSAL, "rb").read()).hexdigest()})


# ================================================================ IX. data --

NEGATIONS = re.compile(r"\b(not|no|nor|neither|never|none|nothing|cannot|without)\b", re.I)
TAG = re.compile(r"^\[([EDHVF])\]\s*")


def counted_text(path=MANUSCRIPT):
    """[(row label, [(tag, [sentences]) per paragraph])] from the proem to the end of XI.
    Counted: tagged paragraphs and the claims' paragraphs. Not counted: status, headings,
    decks, fiction lines, reading leaves."""
    s = re.sub(r"<!--.*?-->", "", open(path, encoding="utf-8").read(), flags=re.S)
    parts = re.split(r"^## (.+)\n", s, flags=re.M)
    rows = []
    for i in range(1, len(parts), 2):
        head, body = parts[i].strip(), parts[i + 1]
        if head == "Status" or head.startswith("Part "):
            continue
        label = {"Proem": "PROEM", "The five claims": "CLAIMS"}.get(head, head.split(".")[0])
        paras = []
        kind = None
        for p in [" ".join(x.split()) for x in body.strip().split("\n\n") if x.strip()]:
            m = re.match(r"^### D\d+ \[([EDHVF])\]", p)
            if m:
                kind = m.group(1)
                continue
            if p.startswith("**Claim.**") or p.startswith("**Measure.**") or p.startswith("**Counts against it.**"):
                paras.append((kind, sentences(re.sub(r"^\*\*[^*]+\*\*\s*", "", p))))
                continue
            t = TAG.match(p)
            if t:
                paras.append((t.group(1), sentences(p[t.end():])))
        rows.append((label, paras))
    return rows


def sentences(text):
    text = re.sub(r"\*", "", text)
    text = text.replace("para. ", "para ").replace("paras ", "paras ")
    out = re.split(r"(?<=[.?!])\s+(?=[A-Z“\"(\[])|(?<=[.?!][”\"\]])\s+(?=[A-Z“\"(\[])", text)
    return [x.replace(" ", " ") for x in out if x.strip()]


def tabula_ix(out_dir):
    rows = counted_text()
    P = VIPlate("IX", "Bounds", "EVERY SENTENCE OF THE BOOK, COUNTED", "ix-bounds",
                "The count proved nothing but the count.", 8, "THE RECORD CHANGED NO DECISION", 2611,
                strap="LENGTH: WORDS / FOOT: THE TAG / RED: A NEGATION",
                data="this book's manuscript (manuscript/de-potestate-et-accusatione.md), counted when the plate is drawn")
    h = P.art
    allsent = [(tag, s) for _, paras in rows for tag, ss in paras for s in ss]
    n = len(allsent)
    neg = sum(1 for _, s in allsent if NEGATIONS.search(s))
    words = [len(s.split()) for _, s in allsent]
    by_tag = {}
    for tag, _ in allsent:
        by_tag[tag] = by_tag.get(tag, 0) + 1
    lines = [f"{n} SENTENCES, {sum(words)} WORDS, FROM THE PROEM TO XI",
             f"WITH A NEGATION: {neg}, OR {neg / n:.2f} OF THEM",
             "TAGS: " + "  ".join(f"{t} {by_tag.get(t, 0)}" for t in "EDHVF"),
             "FOOT: DOT E, BAR D, OPEN RING H, CROSS V, CURL F",
             "COUNTED FROM THE MANUSCRIPT AS IT STANDS"]
    legend(P, lines, y0=40.0, gap=4.8, colors={1: "red"})
    # Reading order across six rows, like a line of type: every sentence a stroke from a common
    # baseline, a narrow gap between paragraphs, a wider one where a section opens at its label.
    X0, X1, Y0, Y1, NROWS = 16.0, 196.0, 80.0, 234.0, 6
    flow = []
    for label, paras in rows:
        flow.append(("section", label))
        for pj, (tag, ss) in enumerate(paras):
            if pj:
                flow.append(("para", None))
            for snt in ss:
                flow.append(("s", (tag, snt)))
    units = {"section": 2.4, "para": 0.6, "s": 1.0}
    total_units = sum(units[k] for k, _ in flow)
    step = (X1 - X0) * NROWS / total_units * 0.985
    pitch_row = (Y1 - Y0) / NROWS
    longest = max(len(snt.split()) for _, snt in allsent)
    kword = (pitch_row - 9.0) / longest
    row, x = 0, X0
    base = Y0 + pitch_row - 6.0
    for kind, item in flow:
        adv = units[kind] * step
        if kind == "s" and x + step > X1 + 0.01:
            row += 1
            x = X0
            base = Y0 + (row + 1) * pitch_row - 6.0
        if kind == "section":
            if x > X0:
                x += step * 1.4
            if x + max(step * 4, max(f.width(item, CAP) for f in FACES)) > X1:
                row += 1
                x = X0
                base = Y0 + (row + 1) * pitch_row - 6.0
            P.label(item, x - 0.6, base + 5.2, CAP, "left")
            h.straight([(x - 0.9, base + 1.4), (x - 0.9, base + 2.4)], "hair", "ink")
            continue
        if kind == "para":
            x += adv
            continue
        tag, snt = item
        w = len(snt.split())
        top = base - 1.2 - w * kword
        h.straight([(x, base - 1.2), (x, top)], "hair", "ink")
        fy = base + 0.4
        if tag == "E":
            h.dot(x, fy, 0.32, "ink")
        elif tag == "D":
            h.straight([(x - 0.6, fy), (x + 0.6, fy)], "orn", "ink")
        elif tag == "H":
            h.ring(x, fy, 0.55, "hair", "ink")
        elif tag == "V":
            h.straight([(x - 0.55, fy), (x + 0.55, fy)], "hair", "ink")
            h.straight([(x, fy - 0.55), (x, fy + 0.55)], "hair", "ink")
        else:
            h.straight(curl_pts(x, fy - 0.2, 0, 0.3, 0.45, 1.2, hand=1), "hair", "ink")
        if NEGATIONS.search(snt):
            h.straight([(x - 0.55, top - 0.25), (x + 0.55, top - 1.05)], "orn", "red")
        x += step
    if row >= NROWS:
        raise ValueError("the sentences overflow the plate's rows")
    return finish(P, out_dir, {"sentences": n, "words": sum(words), "negated": neg, "by_tag": by_tag,
                               "rows": [(lab, sum(len(ss) for _, ss in paras)) for lab, paras in rows],
                               "longest_sentence_words": longest, "mm_per_word": round(kword, 4), "mm_per_sentence": round(step, 3),
                               "negation_words": NEGATIONS.pattern})


PLATES = {"i": tabula_i, "ii": tabula_ii, "iii": tabula_iii, "iv": tabula_iv, "v": tabula_v, "vi": tabula_vi,
          "vii": tabula_vii, "viii": tabula_viii, "ix": tabula_ix}


def main(which, out):
    names = list(PLATES) if which == "all" else [which]
    report = {}
    for n in names:
        d = os.path.join(out, n)
        meta = PLATES[n](d)
        with open(os.devnull, "w") as quiet:
            stdout, sys.stdout = sys.stdout, quiet
            try:
                v = validate(d)
            finally:
                sys.stdout = stdout
        report[n] = {"stem": meta["stem"], "all_passed": v["all_passed"], "strokes": meta["strokes"]["all"],
                     "within_margin": v["within_page_with_8mm_margin"], "extent": v["extent_mm"]}
    for n, r in report.items():
        print(n, r)
    if not all(r["all_passed"] for r in report.values()):
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all", sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "out"))
