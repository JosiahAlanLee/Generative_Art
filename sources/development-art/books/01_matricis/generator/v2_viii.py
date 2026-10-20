"""Second pass · Tabula VIII face and its facing record."""
import math
import random
import sys

from core import Doc, merge, catmull, path_len, point_at, offset_line, arc_pts, bezier
from marks import *
import cipher
import hands as Hd

W, H = 1000, 1600
PAPER, INK, RED, SEPIA = "#ebe1c8", Hd.INK, Hd.RED, Hd.SEPIA
AX = 470
DY = 110          # the plate block sits lower now the lede has moved to the facing record
TITLE_Y = 150


def styles():
    st = {}
    for c, col in (("ink", INK), ("red", RED), ("sep", SEPIA), ("pm", "#d6c9aa"), ("pl", "#f6efde"),
                   ("tape", "#b9ab8c")):
        for k, wdt in (("core", 2.9), ("orn", 1.55), ("hair", 0.9), ("cip", 1.35)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    st["fox_fill"] = {"fill": "#b89a6a", "stroke": "none", "opacity": "0.15"}
    st["tone_fill"] = {"fill": "#d9caa6", "stroke": "none", "opacity": "0.28"}
    st["tapebg_fill"] = {"fill": "#f4edda", "stroke": "none"}
    return st


def ORDER(st):
    first = ["tone_fill", "fox_fill", "tapebg_fill"]
    return first + [k for k in st if k not in first]


ROUTE_PTS = [(AX, 340), (AX + 70, 346), (AX + 245, 402), (AX + 352, 522), (AX + 362, 652), (AX + 302, 780),
             (AX + 168, 872), (AX + 28, 884)]


def route_geom():
    route = catmull(ROUTE_PTS, 22)
    L = path_len(route)
    marks = [point_at(route, L * f)[0] for f in (0.40, 0.535, 0.67)]
    return route, marks


def build_face(seed=8, keep=None):
    rng = random.Random(seed)
    st = styles()
    fur = Doc(W, H, st, order=ORDER(st))     # page furniture, page coordinates
    pl = Doc(W, H, st, order=ORDER(st))      # the plate, drawn in plate coordinates then shifted by DY
    hf = Hand(fur, rng, "ink", amp=0.42)
    h = Hand(pl, rng, "ink", amp=0.42)

    for _ in range(150):
        fur.circle("fox_fill", rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 3.2) ** 1.4)

    # running head rules and title ornament
    hf.stroke([(56, 58), (944, 58)], "orn")
    hf.stroke([(56, 62), (944, 62)], "hair")
    band_x(hf, (380, TITLE_Y + 61), (620, TITLE_Y + 61), 9, 12, "hair", "ink")
    asterisk(hf, 370, TITLE_Y + 61, 6, 8, weight="hair")
    asterisk(hf, 630, TITLE_Y + 61, 6, 8, weight="hair")

    # plate mark: the shallow edge a plate leaves in the paper, with a little plate tone
    X0, Y0, X1, Y1 = 56, 222, 944, 1080
    pm = (X0 - 16, Y0 + DY - 16, X1 + 16, Y1 + DY + 16)
    fur.poly("tone_fill", [(pm[0], pm[1]), (pm[2], pm[1]), (pm[2], pm[3]), (pm[0], pm[3])], closed=True)
    hf.stroke([(pm[0], pm[1]), (pm[2], pm[1]), (pm[2], pm[3]), (pm[0], pm[3])], "orn", "pm", closed=True, amp=0.15)
    hf.stroke([(pm[0] + 1.6, pm[1] + 1.6), (pm[2] - 1.6, pm[1] + 1.6), (pm[2] - 1.6, pm[3] - 1.6),
               (pm[0] + 1.6, pm[3] - 1.6)], "hair", "pl", closed=True, amp=0.15)

    # caption ornament and folio device
    band_x(hf, (420, 1312), (580, 1312), 7, 8, "hair", "sep", centre_dots=True)
    sig_mark(hf, 500, 1550, 11, "ink", "orn")

    # -------------------------------------------------------------- plate
    h.stroke([(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)], "core", closed=True)
    h.stroke([(X0 + 8, Y0 + 8), (X1 - 8, Y0 + 8), (X1 - 8, Y1 - 8), (X0 + 8, Y1 - 8)], "hair", closed=True)
    # close hatching in the border band
    from shapely.geometry import Polygon
    band = Polygon([(X0 + 1.5, Y0 + 1.5), (X1 - 1.5, Y0 + 1.5), (X1 - 1.5, Y1 - 1.5), (X0 + 1.5, Y1 - 1.5)]).difference(
        Polygon([(X0 + 7, Y0 + 7), (X1 - 7, Y0 + 7), (X1 - 7, Y1 - 7), (X0 + 7, Y1 - 7)]))
    from core import hatch_lines
    for ln in hatch_lines(band, 3.2, 45):
        h.stroke(ln, "hair", amp=0.05)
    for (cx, cy) in ((X0, Y0), (X1, Y0), (X0, Y1), (X1, Y1)):
        s = 13
        h.fill_poly([(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)])
        asterisk(h, cx, cy, 8.5, 8, rot_deg=22.5, weight="orn", color="pl", centre=False)

    def vert(text, x, y_mid, size, up=True):
        wd = cipher.measure(text, size)
        if up:
            tf = lambda p: (x + p[1], y_mid + wd / 2 - p[0])
        else:
            tf = lambda p: (x - p[1], y_mid - wd / 2 + p[0])
        cipher.write(XHand(h, tf), text, 0, 0, size, rail=True)

    vert("a sketch prompts a claim and never replaces one", 53, (Y0 + Y1) / 2, 12, up=True)
    vert("data usefulness is not protocol efficacy", 947, (Y0 + Y1) / 2, 12, up=False)

    yN, yB, yG, yApex, yD, yF, yGr = 292, 340, 428, 574, 884, 980, 1036
    exec_h, exec_w = 150, 172

    def spine(y0, y1, arrow=True):
        h.stroke([(AX, y0), (AX, y1)], "core")
        if arrow:
            arrowhead(h, (AX, y1), 90, 11, "ink", "core")

    band_x(h, (AX - 92, yN), (AX - 30, yN), 10, 4, "hair", "ink", centre_dots=True)
    band_x(h, (AX + 30, yN), (AX + 92, yN), 10, 4, "hair", "ink", centre_dots=True)
    curl(h, AX - 92, yN, 180, 4, 9, 1.35, hand=1, weight="hair")
    curl(h, AX + 92, yN, 0, 4, 9, 1.35, hand=-1, weight="hair")
    sig_standing(h, AX, yN, 11, crown=True)
    spine(yN + 26, yG - 62)
    sig_gate(h, AX, yG, 122, 122)
    for sgn in (-1, 1):
        leaf(h, (AX + sgn * 15, yG), (AX + sgn * 62, yG), 15, "orn", "ink", 6)
    spine(yG + 62, yApex - 54)
    sig_authority(h, AX, yApex + exec_h / 2, exec_w, exec_h)
    hy0, hy1 = yApex + exec_h + 30, yD - 34
    h.stroke([(AX, yApex + exec_h), (AX, hy0)], "core")
    band_x(h, (AX, hy0), (AX, hy1), 17, 6, "orn", "ink", centre_dots=True)
    h.stroke([(AX, hy1), (AX, yD - 25)], "core")
    arrowhead(h, (AX, yD - 25), 90, 11, "ink", "core")
    sig_standing(h, AX, yD, 11, crown=False)
    for sgn in (-1, 1):
        asterisk(h, AX + sgn * 64, yD - 2, 5, 8, weight="hair")
    spine(yD + 25, yF - 26)
    sig_standing(h, AX, yF, 11, crown=False)
    spine(yF + 25, yGr - 6)
    sig_ground(h, 120, 880, yGr, 22)
    for (a, b) in ((120, AX - 16), (AX + 16, 880)):
        h.stroke([(a, yGr + 13), (b, yGr + 13)], "orn", "sep")
    sig_break(h, AX, yGr + 13, 15, "ink")

    # the added route: vermilion laid on after printing, a hair off register
    rh = XHand(h, lambda p: (p[0] + 1.3, p[1] - 0.9))
    route, marks = route_geom()
    rh.stroke(route, "core", "red")
    arrowhead(rh, route[-1], 180, 12, "red", "core")
    dotted(rh, offset_line(route, -9), 9, 1.0, "red")
    fringe(rh, route[6:-14], 11, 5.5, side=1, weight="hair", color="red")
    rh.dot(AX, yB, 4.2, "red")
    rh.ring(AX, yB, 7.5, "hair", "red")
    for p in marks:
        asterisk(rh, p[0], p[1], 7.5, 8, weight="orn", color="red", centre=False)
        rh.dot(p[0], p[1], 2.6, "red")
    xs = [p[0] for p in route]
    pf = route[xs.index(max(xs))]
    leaf(rh, (pf[0] + 6, pf[1] - 4), (pf[0] + 52, pf[1] - 34), 14, "orn", "red", 6)
    leaf(rh, (pf[0] + 6, pf[1] + 4), (pf[0] + 52, pf[1] + 34), 14, "orn", "red", 6)
    sig_pointer(rh, (AX - 150, 838), (AX - 16, 808), "red")

    # rulers: timestamp boundaries only
    def ruler(x, y0, y1, side):
        h.stroke([(x, y0), (x, y1)], "orn")
        n = int((y1 - y0) / 10)
        for i in range(n + 1):
            y = y0 + i * (y1 - y0) / n
            h.stroke([(x, y), (x + side * (9 if i % 5 == 0 else 4.5), y)], "hair", amp=0.02)
        for y in (y0, y1):
            h.stroke([(x - 7, y), (x + 7, y)], "orn")
            asterisk(h, x, y - 9 if y == y0 else y + 9, 5.5, 8, weight="hair")
            dotted(h, [(x + side * 14, y), (x + side * 40, y)], 6, 0.9, "ink", skip_ends=False)

    ruler(98, yN, yD, 1)
    ruler(904, yD, yGr, -1)
    # the dividing tick, marked again in red by M.
    rh.stroke([(884, yD - 9), (924, yD - 9)], "orn", "red")
    rh.stroke([(884, yD - 13), (884, yD - 5)], "orn", "red")
    rh.stroke([(924, yD - 13), (924, yD - 5)], "orn", "red")

    # tapes behind the later typed labels
    for (x0, y0, x1, y1) in ((300, yN - 14, 356, yN + 14), (178, yD - 14, 404, yD + 14)):
        pl.poly("tapebg_fill", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True)
        h.stroke([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "hair", "tape", closed=True, amp=0.1)

    # cipher glosses under the engraved labels only
    for (text, x, y, size) in (("mandatory escalation", 352, yG + 36, 9.5), ("executive", 395, yApex + 75 + 30, 10),
                               ("field crew", 408, yF + 26, 9.5), ("added route", 618, 333, 9.5)):
        wdt = cipher.measure(text, size)
        x0 = x - wdt if x != 618 else x
        cipher.write(h, text, x0, y, size, weight="cip", color="sep", rail=False)

    # mirrored stars, fewer than before, clear of labels and sigils
    if keep is not None:
        def free(x, y, r, placed):
            if not (X0 + 24 < x < X1 - 24 and Y0 + 20 < y < 1010):
                return False
            if any(a - 8 < x < c + 8 and b - 8 < y < d + 8 for (a, b, c, d) in keep):
                return False
            return all((x - px) ** 2 + (y - py) ** 2 > (r + pr + 30) ** 2 for (px, py, pr) in placed)
        placed = []
        tries = 0
        while len(placed) < 26 and tries < 8000:
            tries += 1
            x, y = rng.uniform(X0 + 24, AX - 120), rng.uniform(Y0 + 20, 1010)
            r = rng.uniform(2.6, 4.6)
            xm = 2 * AX - x
            if free(x, y, r, placed) and free(xm, y, r, placed + [(x, y, r)]):
                rd = rng.uniform(0, 45)
                for xx in (x, xm):
                    placed.append((xx, y, r))
                    asterisk(h, xx, y, r, 8, rot_deg=rd, weight="hair", color="sep", centre=True)

    svg = merge(W, H, [(fur, None), (pl, f"translate(0 {DY})")])
    meta = dict(yN=yN, yG=yG, yApex=yApex, yD=yD, yF=yF, yGr=yGr, exec_h=exec_h, marks=[list(m) for m in marks],
                route=[list(p) for p in route[::6]])
    return svg, meta


def face_boxes(meta):
    D = DY
    yN, yG, yApex, yD, yF, yGr, eh = (meta[k] for k in ("yN", "yG", "yApex", "yD", "yF", "yGr", "exec_h"))
    SC, PICA, ENG = "IM FELL English SC", "IM FELL DW Pica", "IM FELL English"
    B = []

    def add(**k):
        k.setdefault("color", INK)
        k.setdefault("lh", round(k["size"] * 1.3))
        B.append(k)

    add(id="rh_l", x=56, y=28, w=420, size=13, font=SC, ls=0.22, runs=[("Clavicula Matricis", "")])
    add(id="rh_r", x=524, y=28, w=420, size=13, font=SC, ls=0.22, align="right", color=RED,
        runs=[("Tabula VIII · § 8", "")])
    add(id="title", x=60, y=TITLE_Y, w=880, size=42, lh=48, font=ENG, align="center",
        runs=[("Of an Outage Delayed by Authority", "")])
    B.append(Hd.tech("l_noc", 300, yN - 10 + D, 56, "NOC", size=16, align="center"))
    add(id="l_gate", x=120, y=yG - 23 + D, w=232, size=15.5, lh=20, font=SC, align="right", ls=0.04,
        runs=[("Mandatory escalation", "")])
    add(id="l_gate2", x=120, y=yG + D, w=232, size=14, lh=18, font=PICA, align="right", runs=[("a required gate", "i")])
    ym = yApex + eh / 2
    add(id="l_exec", x=140, y=ym - 30 + D, w=255, size=18, lh=22, font=SC, align="right", ls=0.04,
        runs=[("Executive", "")])
    add(id="l_exec2", x=140, y=ym - 6 + D, w=255, size=14, lh=18, font=PICA, align="right",
        runs=[("authority; no direct repair capacity", "i")])
    add(id="l_wait", x=AX + 24, y=788 + D, w=200, size=13.5, lh=18, font=SC, ls=0.06, runs=[("Handoff waits", "")])
    add(id="l_ptr", x=118, y=784 + D, w=190, size=14.5, lh=17, font=PICA, align="right", color=RED,
        runs=[("Reported refusal / disputed ownership", "i")])
    add(id="l_ptr2", x=118, y=820 + D, w=190, size=12.5, lh=15, font=PICA, align="right",
        runs=[("unverified: a hypothesis about this handoff; check the records", "i")])
    B.append(Hd.tech("l_disp", 178, yD - 10 + D, 226, "technical dispatch", size=16, align="center"))
    add(id="l_crew", x=196, y=yF - 12 + D, w=212, size=16.5, lh=22, font=SC, align="right", ls=0.04,
        runs=[("Field crew", "")])
    add(id="l_break", x=AX + 38, y=yGr - 30 + D, w=340, size=14.5, lh=18, font=PICA, sc_font=SC,
        runs=[("Fiber break", "sc"), (" · the physical cause of the outage", "i")])
    add(id="l_r1", x=76 - 230, y=(yN + yD) / 2 - 9 + D, w=460, h=18, size=12.5, lh=18, font=SC, ls=0.14,
        align="center", rot=-90, runs=[("recognition-to-dispatch", "")])
    add(id="l_r2", x=640, y=(yD + yGr) / 2 + 4 + D, w=246, size=13.5, lh=18, font=SC, align="right", ls=0.04,
        runs=[("Dispatch-to-restoration", "")])
    B.append(Hd.mhand("m_tick", 642, yD + 2 + D, 244, "The stone was broken here.\nPermission was still required below.",
                      size=20, align="right"))
    add(id="l_route", x=618, y=256 + D, w=300, size=15, lh=19, font=SC, ls=0.04, color=RED,
        runs=[("Added, pre-authorized technical route", "")])
    add(id="l_route2", x=618, y=296 + D, w=300, size=13.5, lh=17, font=PICA,
        runs=[("add before you remove: the old route is kept", "i")])
    for i, (p, txt) in enumerate(zip(meta["marks"], ("named owner", "alternate on-call", "timed fallback"))):
        add(id=f"l_m{i}", x=p[0] - 214, y=p[1] - 10 + D, w=196, size=14.5, lh=19, font=PICA, align="right",
            color=RED, runs=[(txt, "i")])
    B.append(Hd.cust("s03", 130, 1236, 740, "Do not confuse the shortest path with a path anyone is allowed to take.",
                     size=23, align="center"))
    add(id="folio", x=440, y=1568, w=120, size=12, lh=16, font=SC, ls=0.2, align="center", color=SEPIA,
        runs=[("viii", "")])
    return B


# ------------------------------------------------------------ facing record

def build_verso(seed=81):
    meta = dict(kx=[92, 300, 512, 722, 92, 300, 512, 722])
    boxes = verso_boxes(meta)
    rng = random.Random(seed)
    st = styles()
    d = Doc(W, H, st, order=ORDER(st))
    h = Hand(d, rng, "ink", amp=0.4)
    for _ in range(120):
        d.circle("fox_fill", rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 3.0) ** 1.4)
    h.stroke([(56, 58), (944, 58)], "orn")
    h.stroke([(56, 62), (944, 62)], "hair")
    h.stroke([(56, 196), (944, 196)], "hair")
    h.stroke([(500, 236), (500, meta["y_cols"])], "hair", "sep")
    yd = meta["y_dep"]
    band_x(h, (380, yd - 34), (620, yd - 34), 7, 12, "hair", "sep", centre_dots=True)
    rh = XHand(h, lambda p: (p[0] + 1.2, p[1] - 0.8))
    rt = bezier((78, yd + 44), (104, yd + 44), (110, yd + 8), (134, yd + 4), 30)
    rh.stroke(rt, "core", "red")
    arrowhead(rh, rt[-1], -10, 9, "red", "core")
    ky = meta["y_key"]
    h.stroke([(56, ky - 34), (944, ky - 34)], "hair")
    kyy = [ky, ky, ky, ky, ky + 32, ky + 32, ky + 32, ky + 32]
    kx = meta["kx"]
    it = iter(zip(kx, kyy))
    x, y = next(it); sig_standing(h, x, y, 6.5, orn=0)
    x, y = next(it); sig_gate(h, x, y, 22, 22, orn=0)
    x, y = next(it); sig_authority(h, x, y + 1, 22, 20, orn=0)
    x, y = next(it); h.stroke(bezier((x - 12, y + 6), (x - 2, y + 6), (x + 2, y - 7), (x + 13, y - 7), 20), "core", "red")
    x, y = next(it); sig_pointer(h, (x - 12, y + 5), (x + 13, y - 5), "red", 4, 3)
    x, y = next(it); sig_substrate_small(h, x, y - 2, 13)
    x, y = next(it); sig_break(h, x, y, 7, "ink")
    x, y = next(it); band_x(h, (x, y - 11), (x, y + 11), 9, 3, "hair", "ink", centre_dots=True)
    return d.svg(), boxes, meta


def verso_boxes(meta):
    SC, PICA, ENG = "IM FELL English SC", "IM FELL DW Pica", "IM FELL English"
    body = dict(size=17.5, lh=24.5, font=PICA, sc_font="IM FELL DW Pica SC", para_gap=9, color=INK)
    B = []

    def add(**k):
        k.setdefault("color", INK)
        k.setdefault("lh", round(k["size"] * 1.3))
        B.append(k)

    add(id="rh_l", x=56, y=28, w=420, size=13, font=SC, ls=0.22, runs=[("Clavicula Matricis", "")])
    add(id="rh_r", x=524, y=28, w=420, size=13, font=SC, ls=0.22, align="right", color=RED,
        runs=[("Facing record · Tabula VIII", "")])
    add(id="head", x=56, y=88, w=600, size=30, lh=36, font=ENG, runs=[("Record of a hypothetical incident", "")])
    B.append(Hd.tech("stamp", 56, 140, 888, "CONTEMPORARY · HYPOTHETICAL · NOT AN ACCOUNT OF ANY EMPLOYER", size=13.5,
                     ls=0.08))
    from layout import box_height
    SL = 1.12  # slack against renderer differences

    colA = dict(id="colA", x=56, y=236, w=420, **body, runs=[
        ("A hypothetical network operations incident, not an account of any employer. A fiber cut causes an outage. "
         "Repair waits because the escalation matrix routes approval through non-technical executives, two of whom "
         "are in conflict.", "i"), ("", "br"),
        ("Inference:", "sc red"), (" locate the break, verify alarms, arrange access, estimate repair time.", ""),
        ("", "br"),
        ("Criticism:", "sc red"), (" rebuild the timeline. When was the diagnosis available, which authorization "
                                    "was missing, and what evidence supports the claim of obstruction?", ""),
        ("", "br"),
        ("Constitution:", "sc red"), (" why does rank rather than technical competence control dispatch, and who "
                                       "can change that rule?", ""), ("", "br"),
        ("Audits.", "sc red"), (" Map customers, field crews, carrier partners, technicians and executives, keeping "
                                 "responsibility, expertise and control separate. A technician who cannot safely "
                                 "challenge a manager is part of the model, not a personality defect. “Fast escalation” "
                                 "as a measure can reward notifying executives while repairs wait.", "")])
    B.append(colA)
    yA = colA["y"] + box_height(colA) * SL
    colB = dict(id="colB", x=524, y=236, w=420, **body, runs=[
        ("Measure.", "sc red"), (" Split diagnosis-to-dispatch from dispatch-to-restoration. The first is "
                                  "organizational delay; the second is mostly physical repair. This split is the most "
                                  "directly testable idea in the practice, and regulator investigations of outages "
                                  "often carry timelines detailed enough to apply it.", "")])
    B.append(colB)
    y = colB["y"] + box_height(colB) * SL + 6
    mm = Hd.mhand("m_measure", 534, y, 400,
                  "Timestamp boundaries, not causal partitions. Technical work can sit above the tick; "
                  "access, authorization, supply or coordination can wait below it.", size=21)
    B.append(mm)
    y = mm["y"] + box_height(mm) * SL + 14
    colB2 = dict(id="colB2", x=524, y=y, w=420, **body, runs=[
        ("Proposal.", "sc red"), (" Trial standing technical dispatch authority under specified conditions, keeping "
                                   "executive notification, a shared record and independent review. Compare "
                                   "restoration delays and mistaken dispatches by severity. Name who must act on a "
                                   "substantiated obstruction, and with what appeal; popularity, shame and bonuses do "
                                   "not substitute for authority over people and resources.", "")])
    B.append(colB2)
    yB = colB2["y"] + box_height(colB2) * SL
    meta["y_cols"] = max(yA, yB)
    y0 = max(yA, yB) + 96
    meta["y_dep"] = y0
    add(id="dep_h", x=150, y=y0, w=700, size=15, lh=20, font=SC, ls=0.12, color=RED,
        runs=[("Deposition of the alternate route", "")])
    dep = dict(id="dep", x=150, y=y0 + 32, w=700, size=18.5, lh=26, font=PICA, color=RED,
               runs=[("I was drawn in red after the outage, though the master said I had always been there. They named "
                      "me bypass. I was not a bypass until someone granted me a key, and I was not a correction until a "
                      "worker could use me without asking the gate I avoided. The old road remained, as the diagram "
                      "commanded. Its keeper was still paid.", "i")])
    B.append(dep)
    y = dep["y"] + box_height(dep) * SL + 18
    dc = Hd.cust("dep_c", 150, y, 700, "The old road also carried warnings. These were omitted from the red drawing.",
                 size=19)
    B.append(dc)
    y = dc["y"] + box_height(dc) * SL + 12
    B.append(Hd.mhand("dep_m", 150, y, 700, "No trial of the red route is entered on this leaf.", size=22))
    meta["y_end"] = y + 40
    meta["y_key"] = max(y + 150, 1380)
    add(id="s22", x=150, y=y + 76, w=700, size=14, lh=19, font=PICA, color=SEPIA,
        runs=[("This space was left for a reply.", "i")])
    keys = ["standing: an actor with interests", "a required gate", "a centre of decision, contestable",
            "an added route; the old one kept", "unverified attribution", "conditions beneath", "the break",
            "a handoff, waiting"]
    ky = meta["y_key"]
    for i, t in enumerate(keys):
        add(id=f"k{i}", x=meta["kx"][i] + 22, y=ky + (0 if i < 4 else 32) - 10, w=190, size=13.5, lh=18, font=PICA,
            runs=[(t, "i")])
    add(id="wards", x=56, y=ky + 80, w=888, size=13, lh=18, font=PICA, color=SEPIA,
        runs=[("Margins of the plate, in the legacy hand: left, “A sketch prompts a claim and never replaces one”; "
               "right, “Data usefulness is not protocol efficacy.”", "i")])
    return B
