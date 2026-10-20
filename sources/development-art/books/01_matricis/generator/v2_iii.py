"""Second pass · Tabula III face and its facing slip.
Hatching no longer follows the values: the upper intervals have different endpoints and must not
read as comparable by density."""
import math
import random
import sys

from shapely.geometry import Polygon, Point, LineString, box as sbox
from shapely.ops import unary_union
from shapely import affinity

from core import Doc, arc_pts, offset_line, path_len, point_at, bezier, resample
from marks import *
import cipher
import hands as Hd
from page3 import CELLS, POLY, ANCHOR, figure_geom, SQ_X, SQ_Y, SQ, U

W, H = 1000, 1600
PAPER = "#f6f1e3"                     # cream technical stock
PENS = {"dk": "#33261e", "um": "#5a4331", "ol": "#5d6b2c", "sg": "#9cad7a", "mu": "#b48a3c", "yl": "#d4b45e",
        "rr": "#9e3b24"}              # rr: rust red, the one correction
UPPER = [("um", 3), ("mu", 2.6), ("yl", 1.6), ("dk", 1.2)]
LOWER = [("ol", 3), ("sg", 2.6), ("dk", 1.0), ("um", 0.8)]
UPPER_KEYS = ("TLt", "TLl", "T1", "T3", "TRt", "T2", "TRr", "T4")
ERR = (7.0, 5.0)                      # the origin error of the first diagonal pass


def styles():
    st = {}
    for k, col in PENS.items():
        for name, wdt in (("hair", 0.85), ("orn", 1.3), ("core", 2.1), ("cip", 1.15)):
            st[f"{k}_{name}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                                 "stroke-linejoin": "round", "opacity": "0.93" if name == "hair" else "1"}
        st[f"{k}_fill"] = {"fill": col, "stroke": "none"}
    for name in ("hair", "orn", "core", "cip", "fill"):
        st[f"ink_{name}"] = dict(st[f"dk_{name}"])
        st[f"red_{name}"] = dict(st[f"rr_{name}"])
    return st


def walks(h, region, n, pens, rng, vertical_bias=0.62, step=(3.0, 5.5), length=(14, 64), starts=True):
    """rectilinear walks with visible pen-down blobs and the odd repeated start"""
    if region.is_empty or n <= 0:
        return
    minx, miny, maxx, maxy = region.bounds
    names = [p for p, _ in pens]
    wts = [w for _, w in pens]
    made = tries = 0
    while made < n and tries < n * 30:
        tries += 1
        x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
        if not region.contains(Point(x, y)):
            continue
        pen = rng.choices(names, wts)[0]
        d = rng.choice([(0, 1), (0, -1)]) if rng.random() < vertical_bias else rng.choice([(1, 0), (-1, 0)])
        pts = [(x, y)]
        for _ in range(rng.randint(*length)):
            if rng.random() < 0.3:
                d = (d[1], d[0]) if rng.random() < 0.5 else (-d[1], -d[0])
                if rng.random() < vertical_bias and d[0] != 0:
                    d = (0, rng.choice([1, -1]))
            s = rng.uniform(*step)
            q = (pts[-1][0] + d[0] * s, pts[-1][1] + d[1] * s)
            if not region.contains(Point(q)):
                break
            pts.append(q)
        if len(pts) > 2:
            h.doc.poly(f"{pen}_hair", pts)
            if starts:
                h.doc.circle(f"{pen}_fill", pts[0][0], pts[0][1], rng.uniform(0.9, 1.4))
                if rng.random() < 0.12:   # a repeated start: the pen dropped twice
                    h.doc.poly(f"{pen}_hair", [(pts[0][0] + 1.2, pts[0][1] + 0.8), (pts[1][0] + 1.2, pts[1][1] + 0.8)])
            made += 1


DYP = 92   # the plotted block sits lower on the sheet now the legend has moved


def build_face(seed=3):
    rng = random.Random(seed)
    st = styles()
    doc = Doc(W, H, st)
    fur = Doc(W, H, st)
    h = Hand(doc, rng, "ink", amp=0.35)
    hf = Hand(fur, rng, "ink", amp=0.35)

    fig_u, horns_u, hole_u = figure_geom()
    sc = lambda g: affinity.affine_transform(g, [SQ, 0, 0, SQ, SQ_X, SQ_Y])
    fig, horns = sc(fig_u), sc(horns_u)
    figure_all = unary_union([fig, horns])
    keep_fig = figure_all.buffer(7)

    knock = {}
    for k, (lab, v, mx) in CELLS.items():
        ax, ay = U(ANCHOR[k])
        knock[k] = (ax, ay, 21 if len(lab) == 1 else 27)
    keep_extra = []
    # "Unknown is not absent" sits between the two question marks
    keep_extra.append(sbox(U((0.79, 0.62))[0], U((0.79, 0.62))[1], U((0.99, 0.69))[0], U((0.99, 0.69))[1]))
    knock_geom = unary_union([Point(x, y).buffer(r + 6) for (x, y, r) in knock.values()] + keep_extra)

    # cells: uniform, light, two palettes; the unknowns get hollow marks instead of hatching
    for k, (lab, v, mx) in CELLS.items():
        poly = Polygon([U(p) for p in POLY[k]]).buffer(-3.5)
        region = poly.difference(keep_fig).difference(knock_geom)
        if v is None:
            minx, miny, maxx, maxy = region.bounds
            placed = 0
            for _ in range(700):
                x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
                if region.contains(Point(x, y).buffer(4)):
                    h.ring(x, y, rng.uniform(1.6, 3.2), "hair", rng.choice(["ol", "sg", "sg"]))
                    placed += 1
                    if placed > region.area / 420:
                        break
            continue
        walks(h, region, int(region.area / 760), UPPER if k in UPPER_KEYS else LOWER, rng)

    # the figure
    spiral_c = U((0.5, 0.425))
    spiral_r = 0.072 * SQ
    body = fig.buffer(-3).difference(Point(spiral_c).buffer(spiral_r * 1.08))
    walks(h, body, int(body.area / 105), [("dk", 4), ("um", 1.6)], rng, vertical_bias=0.86, step=(2.6, 4.2),
          length=(10, 40), starts=False)
    walks(h, horns.buffer(-1.5), int(horns.area / 75), [("dk", 3), ("um", 1)], rng, vertical_bias=0.3,
          step=(2.2, 3.4), length=(6, 20), starts=False)
    for geom in (fig, horns):
        for g in ([geom] if geom.geom_type == "Polygon" else list(geom.geoms)):
            for ring in [list(g.exterior.coords)] + [list(r.coords) for r in g.interiors]:
                h.stroke(ring, "orn", "dk")
                h.stroke([(x + 0.9, y + 0.5) for (x, y) in ring], "hair", "um")
    sp = sig_mark(h, spiral_c[0], spiral_c[1], spiral_r * 0.92, "dk", "core", branch=True, turns=1.75, ang0=200)
    h.stroke(offset_line(sp, 2.0), "hair", "ol")       # the doubled trace
    h.stroke(arc_pts(spiral_c[0], spiral_c[1], spiral_r * 1.08, 0, 360, 120), "hair", "dk")

    # structure lines; the first diagonal was plotted against the wrong origin, then re-plotted in rust
    lines = [((0, 0), (1, 1)), ((1, 0), (0, 1)), ((0.5, 0), (1, 0.5)), ((1, 0.5), (0.5, 1)), ((0.5, 1), (0, 0.5)),
             ((0, 0.5), (0.5, 0)), ((0, 0.5), (1, 0.5)), ((0.5, 0), (0.5, 1))]
    cut = figure_all.buffer(3).union(knock_geom)
    for i, (a, b) in enumerate(lines):
        seg = LineString([U(a), U(b)]).difference(cut)
        segs = [seg] if seg.geom_type == "LineString" else list(getattr(seg, "geoms", []))
        for s in segs:
            if s.length < 2:
                continue
            c = list(s.coords)
            if i == 0:
                h.stroke([(x + ERR[0], y + ERR[1]) for x, y in c], "hair", "um")   # misregistered pass
                h.stroke(c, "orn", "rr")                                           # the correction
            else:
                h.stroke(c, "orn", "dk")
                h.stroke([(x + 0.9, y + 0.7) for x, y in c], "hair", "um")
    x0, y0, x1, y1 = SQ_X, SQ_Y, SQ_X + SQ, SQ_Y + SQ
    for off, wt, pen in ((0, "core", "dk"), (-9, "hair", "dk"), (-12, "hair", "mu")):
        h.stroke([(x0 + off, y0 + off), (x1 - off, y0 + off), (x1 - off, y1 - off), (x0 + off, y1 - off)], wt, pen,
                 closed=True)
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        asterisk(h, cx + (-14 if cx == x0 else 14), cy + (-14 if cy == y0 else 14), 7, 8, weight="orn", color="um")
    for k, (x, y, r) in knock.items():
        up = k in UPPER_KEYS
        h.ring(x, y, r, "orn", "dk" if up else "ol")
        h.ring(x, y, r + 3.2, "hair", "mu" if up else "sg")

    # registration witnesses: the true mark, and the one the first diagonal used
    def witness(cx, cy, pen, r=7):
        h.ring(cx, cy, r, "hair", pen)
        h.stroke([(cx - r * 1.7, cy), (cx + r * 1.7, cy)], "hair", pen, amp=0.02)
        h.stroke([(cx, cy - r * 1.7), (cx, cy + r * 1.7)], "hair", pen, amp=0.02)
    witness(x0 - 40, y0 - 40, "dk")
    witness(x0 - 40 + ERR[0], y0 - 40 + ERR[1], "um")
    witness(x1 + 40, y1 + 40, "dk")

    # inscription round the frame, in the legacy hand
    def side(text, which, start, size=11.5, color="dk"):
        if which == "top":
            tf = lambda p: (x0 + start + p[0], y0 - 9 + p[1])
        elif which == "right":
            tf = lambda p: (x1 + 9 - p[1], y0 + start + p[0])
        elif which == "bottom":
            tf = lambda p: (x1 - start - p[0], y1 + 9 - p[1])
        else:
            tf = lambda p: (x0 - 9 + p[1], y1 - start - p[0])
        return cipher.write(XHand(h, tf), text, 0, 0, size, "cip", color, rail=True, rail_color="mu")

    def fill_side(which, s0, s1):
        if s1 - s0 < 20:
            return
        pts = {"top": [(x0 + s0, y0 - 14), (x0 + s1, y0 - 14)], "right": [(x1 + 14, y0 + s0), (x1 + 14, y0 + s1)],
               "bottom": [(x1 - s0, y1 + 14), (x1 - s1, y1 + 14)], "left": [(x0 - 14, y1 - s0), (x0 - 14, y1 - s1)]}
        dotted(h, pts[which], 7, 0.9, "mu", skip_ends=True)

    for which, text in (("top", "how long does a problem take to reach someone able to act"),
                        ("right", "and how long from there to action"),
                        ("bottom", "unknown is not absent"),
                        ("left", "data usefulness is not protocol efficacy")):
        w_ = side(text, which, 34)
        fill_side(which, 34 + w_ + 12, SQ - 34)

    # a hair leader from M.'s note to the right horn
    tip = U((0.578, 0.04))
    h.stroke(bezier((706, 186), (660, 196), (612, 222), tip, 30), "hair", "rr")

    # pen-test strip: loops in each pen, interrupted by a dry section
    h = hf
    tx = 140
    for k, pen in enumerate(["dk", "um", "mu", "yl", "ol", "sg"]):
        y = 1470 + (k % 2) * 3
        pts = []
        for i in range(140):
            t = i / 139 * 6 * math.pi
            pts.append((tx + i * 0.82 + 9 * math.cos(t + math.pi), y + 7 * math.sin(t)))
        dry0, dry1 = 70, 98
        h.stroke(pts[:dry0], "hair", pen, amp=0.05)
        for j in range(dry0, dry1, 4):   # dry: the pen skips
            h.stroke(pts[j:j + 2], "hair", pen, amp=0.0)
        h.stroke(pts[dry1:], "hair", pen, amp=0.05)
        tx += 128

    sig_mark(hf, 500, 1546, 10, "dk", "orn")
    from core import merge
    return merge(W, H, [(fur, None), (doc, f"translate(0 {DYP})")]), dict(knock={k: list(v) for k, v in knock.items()})


def face_boxes(meta):
    DK, OL = PENS["dk"], PENS["ol"]
    DM, SPE, MONO = "DM Serif Display", "Spectral", "IBM Plex Mono"
    B = []

    def add(**k):
        k.setdefault("color", DK)
        k.setdefault("lh", round(k["size"] * 1.35))
        B.append(k)

    add(id="rh_l", x=56, y=30, w=440, size=11.5, font=MONO, ls=0.22, runs=[("CLAVICULA MATRICIS", "")])
    add(id="rh_r", x=504, y=30, w=440, size=11.5, font=MONO, ls=0.22, align="right", color=PENS["um"],
        runs=[("TABULA III · § 3 · § 8", "")])
    add(id="title", x=60, y=62, w=880, size=46, lh=52, font=DM, align="center", runs=[("Of the Speed of Correction", "")])
    add(id="sub", x=60, y=120, w=880, size=19, lh=26, font=SPE, align="center", color=PENS["um"],
        runs=[("the Figure in the Square of Intervals", "i")])
    B.append(Hd.mhand("m_horns", 712, 158 + DYP, 232, "These may be the jaws of an instrument.\nNo scale survives between them.",
                      size=19, color=Hd.RED))
    for k, (lab, v, mx) in CELLS.items():
        ax, ay = U(ANCHOR[k])
        add(id=f"n_{k}", x=ax - 40, y=ay - 18 + DYP, w=80, size=27, lh=34, font=DM, align="center",
            color=OL if lab == "?" else DK, runs=[(lab, "")])
    ux, uy = U((0.80, 0.625))
    B.append(Hd.mhand("m_unknown", ux, uy + DYP, 150, "Unknown is not absent.", size=19, color=Hd.RED))
    B.append(Hd.cust("s02", 120, 1086 + DYP + 8, 760, "A number may be exact and still measure the wrong interval.", size=23,
                     align="center", color=DK))
    add(id="folio", x=844, y=1560, w=100, size=11, lh=14, font=MONO, align="right", ls=0.2, runs=[("iii", "")])
    return B


# --------------------------------------------------------------- facing slip

def build_slip(seed=31):
    boxes, meta = slip_boxes()
    rng = random.Random(seed)
    st = styles()
    d = Doc(W, H, st)
    h = Hand(d, rng, "ink", amp=0.3)
    h.stroke([(56, 56), (944, 56)], "orn", "dk")
    h.stroke([(500, 222), (500, meta["y_top_end"])], "hair", "um")
    yl = meta["y_legend"]
    h.stroke([(56, yl - 26), (944, yl - 26)], "hair", "dk")
    # registration witness, as on the plotted leaf
    for (cx, cy) in ((32, 32), (968, 1568)):
        h.ring(cx, cy, 6, "hair", "dk")
        h.stroke([(cx - 10, cy), (cx + 10, cy)], "hair", "dk")
        h.stroke([(cx, cy - 10), (cx, cy + 10)], "hair", "dk")
    return d.svg(), boxes, meta


def slip_boxes():
    from layout import box_height
    DK, UM = PENS["dk"], PENS["um"]
    DM, SPE, MONO = "DM Serif Display", "Spectral", "IBM Plex Mono"
    SL = 1.12
    B, meta = [], {}

    def add(**k):
        k.setdefault("color", DK)
        k.setdefault("lh", round(k["size"] * 1.35))
        B.append(k)
        return k

    add(id="rh_l", x=56, y=24, w=440, size=11.5, font=MONO, ls=0.22, runs=[("CLAVICULA MATRICIS", "")])
    add(id="rh_r", x=504, y=24, w=440, size=11.5, font=MONO, ls=0.22, align="right", color=UM,
        runs=[("FACING SLIP · TABULA III", "")])
    add(id="head", x=56, y=96, w=888, size=34, lh=40, font=DM, runs=[("Numbers of the square", "")])
    add(id="dateline", x=56, y=148, w=888, size=12, lh=17, font=MONO, color=UM, ls=0.06,
        runs=[("EXPANDED INCIDENT PILOT, 11 OCTOBER 2026 · VALUES AS RECORDED THERE, NOT RE-AUDITED HERE", "")])
    base = add(id="rev5", x=56, y=222, w=416, size=16, lh=23.5, font=SPE, sc_font="Spectral SC", para_gap=9, runs=[
        ("Each audit is a question to put to a system. None yields a verdict by itself.", "i"), ("", "br"),
        ("Speed of correction.", "sc #5a4331"),
        (" How long does a problem take to reach someone able to act, and how long from there to action? Elections "
         "correct on a cycle of years; deployments change in weeks. Protected, non-punitive reporting adds a continuous "
         "channel between those bursts, but a channel needs a durable store or its signals fade before anyone acts.", ""),
        ("", "br"), ("Measure.", "sc #5a4331"),
        (" Split diagnosis-to-dispatch from dispatch-to-restoration. The first is organizational delay; the second is "
         "mostly physical repair. This split is the most directly testable idea in the practice, and regulator "
         "investigations of outages often carry timelines detailed enough to apply it.", "")])
    c = Hd.cust("fa_c", 528, 222, 416, "Set the numbers about the figure without making them agree. The upper chambers "
                "contain waits. The lower contain occasions on which a thing could be seen. The likeness of their vessels "
                "has deceived more readers than the cipher.\nIn two chambers leave the question standing. Do not put a "
                "zero there to make the company complete.", size=18.5, color=DK)
    B.append(c)
    yc = c["y"] + box_height(c) * SL + 22
    u = Hd.unh("fa_u", 548, yc, 396, "You have drawn the same face around every delay.", size=25)
    B.append(u)
    y_top_end = max(base["y"] + box_height(base) * SL, u["y"] + box_height(u) * SL)
    meta["y_top_end"] = y_top_end
    yl = y_top_end + 70
    meta["y_legend"] = yl
    up = [("110", "Orange 2021", "technical recognition → first supplier contact", "OR1 pp 12–14"),
          ("134", "Orange 2021", "recognition → supplier ticket", "OR1 pp 12–14"),
          ("114", "Orange 2021", "internal escalation → supplier ticket", "OR1 pp 12–14"),
          ("39", "Fastly 2021", "detection → configuration identified", "FA1"),
          ("85", "BT 2023", "decision to use disaster recovery → successful transfer", "BT1 ¶4.29–4.35"),
          ("7", "BT 2023", "the same decision → first attempt", "BT1 ¶4.29–4.35"),
          ("78", "BT 2023", "remainder, including failed execution and reversal", "BT1 ¶4.29–4.35"),
          ("17", "OVH 2021", "emergency call → responders arrive", "OV1")]
    lo = [("6", "a timed response sequence"), ("6", "a specific obstruction mechanism"),
          ("3", "external authority actually exercised"), ("3", "an implemented post-incident change, explicitly reported"),
          ("1", "a post-incident behavioural perturbation experiment"), ("0", "a usable ownership comparison"),
          ("?", "metric gaming: none documented, eight unknown"), ("?", "reporter protection: none documented, eight unknown")]
    rows = [("UPPER HALF · minutes between recorded stages. The endpoints differ and some overlap;", "#5a4331"),
            ("these are not independent summands or comparable restoration times.", "#5a4331"), ("", "")]
    for v, src, desc, loc in up:
        rows.append((v.ljust(5) + src.ljust(13) + desc.ljust(57) + loc, ""))
    rows += [("", ""), ("LOWER HALF · of the pilot's eight new units, how many sources made each observable.", "#5a4331"),
             ("Eight is the pilot's denominator, not a population. Zero counts usable comparisons,", "#5a4331"),
             ("not irrelevance.", "#5a4331"), ("", "")]
    for v, desc in lo:
        rows.append((v.ljust(5) + desc, ""))
    rows += [("", ""),
             ("OR1  Joint Orange emergency-number investigation, published 19 July 2021", "#5a4331"),
             ("BT1  Ofcom, non-confidential confirmation decision, published 24 September 2024", "#5a4331"),
             ("FA1  Fastly, Summary of June 8 outage, published 8 June 2021", "#5a4331"),
             ("OV1  BEA-RI investigation MTE-BEARI-2022-005, published 24 May 2022", "#5a4331")]
    runs = []
    for i, (t, stl) in enumerate(rows):
        if i:
            runs.append(("", "br"))
        runs.append((t if t else " ", stl))
    lg = add(id="legend", x=56, y=yl, w=888, size=12.2, lh=17.5, font=MONO, para_gap=0, pre=True, runs=runs)
    y = lg["y"] + box_height(lg) * SL + 34
    B.append(Hd.cust("s07", 56, y, 888, "The unknown is not the absent. The absent is not the disproved.", size=21,
                     color=DK))
    meta["y_end"] = y + 40
    return B, meta
