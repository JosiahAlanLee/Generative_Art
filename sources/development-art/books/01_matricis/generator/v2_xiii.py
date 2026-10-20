"""Second pass · Tabula XIII (a mounted record of a deposit), its verso, and the legacy-key slip."""
import math
import random
import sys

from core import Doc, arc_pts, offset_line, path_len, point_at, bezier
from marks import *
import cipher
import hands as Hd
from page2 import (MARKS, COLS, ROWS, SR, GRAIN, seal_ornament, draw_mark, EARTH, MEAL, OCHRE, ASH, styles as st2)

W, H = 1000, 1600
PAPER = "#e9dfc6"
REC = (22, 64, 978, 1578)          # the mounted record
GX, GY, GR = 292, 1296, 186
FRESH = "#f7ecc8"
THIN = {1, 6, 9}                   # medallions whose outer deposit is thin
PARTIAL = {4, 11}                  # medallions whose outer deposit survives in part
REFILL = 2                         # one border refilled (III); its sign untouched
RING_TEXT = {0: "interest-bearing being has standing"}   # the legacy hand has no digits: '(P5)' stays in the caption


def styles():
    st = st2()
    for k, wdt, op in (("gs", 1.0, 0.95), ("gm", 1.6, 0.97), ("gl", 2.3, 1.0)):
        st[f"fr_{k}"] = {"fill": "none", "stroke": FRESH, "stroke-width": str(wdt), "stroke-linecap": "round",
                         "opacity": str(op)}
    st["earth_fill"] = {"fill": EARTH, "stroke": "none"}
    st["mount_fill"] = {"fill": "#f1e8d3", "stroke": "none"}
    st["mount_orn"] = {"fill": "none", "stroke": "#b9ab8c", "stroke-width": "0.8"}
    st["pink_orn"] = {"fill": "none", "stroke": "#1c1813", "stroke-width": "1.4", "stroke-linecap": "round"}
    st["pink_hair"] = {"fill": "none", "stroke": "#1c1813", "stroke-width": "0.8", "stroke-linecap": "round"}
    return st


def ring_arcs(h, cx, cy, r, weight, color, cover, rng, segs=6):
    """an outer ring deposited in pieces: `cover` of the circumference survives"""
    a = rng.uniform(0, 360)
    per = 360 / segs
    for k in range(segs):
        span = per * cover * rng.uniform(0.75, 1.15)
        a0 = a + k * per
        h.stroke(arc_pts(cx, cy, r, a0, a0 + span, max(8, int(span / 3))), weight, color)


def build_face(seed=13):
    rng = random.Random(seed)
    st = styles()
    order = ["earth_fill", "tex_dk", "tex_lt", "ghost_orn", "ghost_fill"] + \
            [k for k in st if not k.startswith(("tex", "ghost", "earth", "mount", "pink"))] + \
            ["mount_fill", "mount_orn", "pink_orn", "pink_hair"]
    doc = Doc(W, H, st, order=order)
    h = Hand(doc, rng, "grain", amp=0.75, grain=GRAIN)
    gh = Hand(doc, rng, "ink", amp=1.2)
    x0, y0, x1, y1 = REC
    doc.poly("earth_fill", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True)
    for _ in range(2500):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        doc.grain("tex_lt" if rng.random() < 0.55 else "tex_dk", x, y)
    for _ in range(9):
        cx, cy = rng.uniform(80, 920), rng.uniform(260, 1450)
        r = rng.uniform(60, 190)
        a0 = rng.uniform(0, 360)
        gh.stroke(arc_pts(cx, cy, r, a0, a0 + rng.uniform(70, 200), 60), "orn", "ghost")
    # corner mounts and the running-head rule, on the paper
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        tri = [(cx - sx * 6, cy - sy * 6), (cx + sx * 46, cy - sy * 6), (cx - sx * 6, cy + sy * 46)]
        doc.poly("mount_fill", tri, closed=True)
        doc.poly("mount_orn", [(cx + sx * 46, cy - sy * 6), (cx - sx * 6, cy + sy * 46)])
    doc.poly("pink_orn", [(56, 52), (944, 52)])
    ring_y = 140
    for k in range(13):
        h.dot(380 + k * 20, ring_y, 1.3 if k % 2 else 2.0, "red" if k == 6 else "ink")

    for i in range(12):
        cx, cy = COLS[i % 4], ROWS[i // 4]
        if i in THIN:
            ring_arcs(h, cx, cy, SR, "hair", "ink", 0.72, rng, segs=7)
        elif i in PARTIAL:
            ring_arcs(h, cx, cy, SR, "orn", "ink", 0.55, rng, segs=4)
        else:
            h.stroke(arc_pts(cx, cy, SR, 0, 360, 200), "orn")
        if i == REFILL:
            # the old border, thin and broken, then a fresher refill laid over one stretch of it
            h.stroke(arc_pts(cx, cy, SR, 110, 330, 120), "orn")
            h.stroke(arc_pts(cx, cy, SR + 1.6, -36, 108, 90), "core", "fr")
            h.stroke(arc_pts(cx, cy, SR - 0.8, -30, 104, 90), "orn", "fr")
        h.stroke(arc_pts(cx, cy, SR - 15, 0, 360, 180), "hair")
        name, meaning = MARKS[i]
        text = RING_TEXT.get(i, f"{name} {meaning}")
        a_end = write_ring(h, text, cx, cy, SR - 12.5, -158, 9.2, "ink")
        rest = arc_pts(cx, cy, SR - 7.5, a_end + 6, -158 + 360 - 6, 60)
        if len(rest) > 3 and i not in THIN:
            dotted(h, rest, 6.0, 0.9, "ink", skip_ends=True)
        sa = math.radians(-161)
        asterisk(h, cx + (SR - 7.5) * math.cos(sa), cy + (SR - 7.5) * math.sin(sa), 3.6, 8, weight="hair",
                 color="red", centre=False)
        if i not in THIN and i not in PARTIAL:
            seal_ornament(h, cx, cy, SR - 18, rng)
        draw_mark(i, h, cx, cy, SR * 1.06)
        for a in (0, 90, 180, 270):
            if i in THIN and a in (90, 270):
                continue
            ar = math.radians(a)
            h.dot(cx + (SR + 7) * math.cos(ar), cy + (SR + 7) * math.sin(ar), 1.6)

    # the great seal, as before
    h.stroke(arc_pts(GX, GY, GR, 0, 360, 360), "core")
    h.stroke(arc_pts(GX, GY, GR - 24, 0, 360, 330), "orn")
    a = write_ring(h, "a sketch prompts a claim and never replaces one", GX, GY, GR - 19, -170, 12.5, "ink", rail=True)
    asterisk(h, GX + (GR - 12) * math.cos(math.radians(a + 4)), GY + (GR - 12) * math.sin(math.radians(a + 4)), 5, 8,
             weight="orn", color="red", centre=False)
    a2 = write_ring(h, "data usefulness is not protocol efficacy", GX, GY, GR - 19, a + 9, 12.5, "ink", rail=True)
    rest = arc_pts(GX, GY, GR - 12, a2 + 5, -170 + 360 - 5, 80)
    if len(rest) > 3:
        dotted(h, rest, 8, 1.2, "ink")
    ring_x(h, GX, GY, GR - 32, GR - 46, 36, "hair", "ink")
    for k in range(16):
        ar = math.radians(k * 22.5)
        r0, r1 = GR + 6, GR + (24 if k % 2 == 0 else 14)
        h.stroke([(GX + r0 * math.cos(ar), GY + r0 * math.sin(ar)), (GX + r1 * math.cos(ar), GY + r1 * math.sin(ar))],
                 "orn")
        if k % 2 == 0:
            asterisk(h, GX + (r1 + 8) * math.cos(ar), GY + (r1 + 8) * math.sin(ar), 5, 8, weight="hair")
    rot0 = rng.uniform(0, 360)
    pts = sig_mark(h, GX, GY, 84, "red", "core", branch=True, turns=1.75, ang0=rot0)
    dotted(h, offset_line(pts[40:], 13), 9, 1.3, "red")
    fringe(h, pts[90:], 9, 6, side=-1, weight="hair", color="red")
    for k in range(4):
        ar = rot0 + 45 + k * 90
        rr = math.radians(ar)
        curl(h, GX + 128 * math.cos(rr), GY + 128 * math.sin(rr), ar + 180, 6, 8.5, 1.3, hand=1, weight="orn")
        rs = math.radians(ar + 45)
        asterisk(h, GX + 132 * math.cos(rs), GY + 132 * math.sin(rs), 4.2, 8, weight="hair")
    return doc.svg(), {}


def face_boxes(meta):
    GAR = "EB Garamond"
    ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
    B = []

    def add(**k):
        k.setdefault("color", MEAL)
        k.setdefault("lh", round(k["size"] * 1.32))
        B.append(k)

    add(id="rh_l", x=56, y=20, w=420, size=14, font=GAR, color=Hd.INK, runs=[("Clavicula Matricis", "v")])
    add(id="rh_r", x=524, y=20, w=420, size=14, font=GAR, align="right", color=Hd.RED,
        runs=[("Tabula XIII · § 13 · a mounted record", "v")])
    add(id="title", x=60, y=78, w=880, size=44, lh=50, font=GAR, align="center",
        runs=[("Of the Twelve Marks and the Mark", "")])
    add(id="insc", x=130, y=160, w=740, size=20, lh=27, font=GAR, align="center",
        runs=[("A sketch prompts a claim and never replaces one.", "i")])
    for i, (name, meaning) in enumerate(MARKS):
        cx, cy = COLS[i % 4], ROWS[i // 4]
        add(id=f"cap{i}", x=cx - 108, y=cy + SR + 13, w=216, size=14.5, lh=19, font=GAR, align="center",
            runs=[(ROMAN[i] + " · ", "v red"), (name, "v"), ("", "br"), (meaning, "i")])
    c = Hd.cust("fc_c", 540, 1120, 404, "At the narrow turn, loosen the fingers. Too much meal will join the ends. Too "
                "little will persuade the next hand that the line was meant to break there.\nMake it again beside the "
                "first. Do not sweep the first away until the difference has been seen.", size=18.5, color=MEAL)
    B.append(c)
    B.append(Hd.unh("fc_u", 560, 1392, 380, "I swept it away because we needed the table.", size=25, color=ASH))
    add(id="folio", x=844, y=1540, w=100, size=13, lh=18, font=GAR, align="right", color=ASH, ls=0.12,
        runs=[("xiii", "v")])
    return B


# ----------------------------------------------------------------- verso

def build_verso(seed=131):
    boxes, meta = verso_boxes()
    rng = random.Random(seed)
    st = {}
    for c, col in (("ink", Hd.INK), ("red", Hd.RED), ("sep", Hd.SEPIA)):
        for k, wdt in (("core", 2.4), ("orn", 1.4), ("hair", 0.85), ("cip", 1.3)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    st["fox_fill"] = {"fill": "#b89a6a", "stroke": "none", "opacity": "0.14"}
    d = Doc(W, H, st, order=["fox_fill"] + [k for k in st if k != "fox_fill"])
    h = Hand(d, rng, "ink", amp=0.4)
    for _ in range(110):
        d.circle("fox_fill", rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 3.0) ** 1.4)
    h.stroke([(56, 56), (944, 56)], "orn")
    # the mark beside its paragraph; mark XII beside the objection
    sig_mark(h, 96, meta["y_mark"] + 30, 24, "ink", "orn", branch=True)
    sig_invariant(h, 104, meta["y_s06"] + 30, 48)
    return d.svg(), boxes, meta


def verso_boxes():
    from layout import box_height
    GAR = "EB Garamond"
    SL = 1.12
    B, meta = [], {}
    body = dict(size=19.5, lh=28, font=GAR, color=Hd.INK, para_gap=10)

    def add(**k):
        k.setdefault("color", Hd.INK)
        k.setdefault("lh", round(k["size"] * 1.32))
        B.append(k)
        return k

    add(id="rh_l", x=56, y=24, w=420, size=14, font=GAR, runs=[("Clavicula Matricis", "v")])
    add(id="rh_r", x=524, y=24, w=420, size=14, font=GAR, align="right", color=Hd.RED,
        runs=[("Verso · Tabula XIII", "v")])
    y = 120
    s1 = add(id="sketch", x=150, y=y, w=700, **body, runs=[
        ("Sketching.", "v red"), (" Any sketch made with the practice follows one rule: a sketch prompts a claim and "
                                  "never replaces one. Revision 3’s twelve sketching marks remain available, provided "
                                  "each mark’s meaning is stated every time it is used.", "")])
    y = s1["y"] + box_height(s1) * SL + 40
    meta["y_mark"] = y
    s2 = add(id="mark", x=150, y=y, w=700, **body, runs=[
        ("The mark.", "v red"), (" A loose curl with no central dot, turning outward with space between turns, its outer "
                                 "end left open, and a short branch curving away into its own open end. It suggests "
                                 "returning to a question from a changed position, with room to diverge or stop. "
                                 "Rotation and proportion carry no doctrine; Le Guin’s Kesh suggested the orientation, "
                                 "and this is not a Kesh glyph.", "")])
    y = s2["y"] + box_height(s2) * SL + 48
    items = ["Keep models contestable.", "Make purposes and exclusions visible.",
             "Protect reporting and the capacity to act on it.",
             "Know who controls what fades, and who else can read the clock.",
             "Count the costs of action and of inaction.", "Keep care independent of earned worth.",
             "Let the practice itself be revised or abandoned. No one needs permission to stop using it, and no "
             "service may depend on adherence."]
    runs = [("Orientation.", "v red")]
    for it in items:
        runs += [("", "br"), ("· ", "red"), (it, "")]
    o = add(id="orient", x=150, y=y, w=700, size=19.5, lh=28, font=GAR, para_gap=5, runs=runs)
    y = o["y"] + box_height(o) * SL + 10
    c = Hd.cust("orient_c", 170, y, 680, "This sentence was omitted from the small copies for want of room.", size=20)
    B.append(c)
    y = c["y"] + box_height(c) * SL + 96
    meta["y_s06"] = y
    add(id="xii", x=150, y=y, w=700, size=17, lh=22, font=GAR, color=Hd.SEPIA,
        runs=[("XII · ", "v red"), ("Learned invariant", "v"), (" — hard walls, one door", "i")])
    m = Hd.mhand("s06", 150, y + 32, 700, "An invariant is sometimes a discovery and sometimes a prohibition wearing "
                 "its mask.", size=26)
    B.append(m)
    y = max(m["y"] + box_height(m) * SL + 120, 1380)
    B.append(Hd.unh("s15", 190, y, 640, "There was no mark for a keeper who wished to stop.", size=30))
    meta["y_end"] = y + 40
    return B, meta


# ------------------------------------------------------------ legacy key slip

def build_keyslip(seed=7):
    W2, H2 = 1000, 440
    st = {}
    for c, col in (("ink", Hd.INK), ("red", Hd.RED), ("sep", Hd.SEPIA)):
        for k, wdt in (("core", 2.4), ("orn", 1.4), ("hair", 0.85), ("cip", 1.5)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    d = Doc(W2, H2, st)
    h = Hand(d, random.Random(seed), "ink", amp=0.2)
    h.stroke([(40, 40), (960, 40), (960, 400), (40, 400)], "hair", "sep", closed=True)
    letters = "abcdefghijklmnopqrstuvwxyz"
    cw = 880 / 13
    pos = {}
    for k, ch in enumerate(letters):
        row, col = divmod(k, 13)
        gx = 60 + cw * col
        gy = 196 + row * 120
        gw = cipher.G[ch][0] * 30
        cipher.glyph_only(h, ch, gx + (cw - gw) / 2, gy, 30, "cip", "ink")
        pos[ch] = (gx, gy)
    return d.svg(), dict(cw=cw, pos=pos, W=W2, H=H2)


def keyslip_boxes(meta):
    GAR = "EB Garamond"
    B = [dict(id="ks_h", x=60, y=60, w=880, size=15, lh=20, font=GAR, color=Hd.RED, runs=[("Proof slip · the legacy hand", "v")]),
         dict(id="ks_n", x=60, y=86, w=880, size=14.5, lh=20, font=GAR, color=Hd.SEPIA,
              runs=[("One table drew every inscription in this hand: the twelve rings and the great seal of XIII, the "
                     "margins of VIII, the frame of III. It has no digits or punctuation, so ring I carries its caption "
                     "without ‘(P5)’.", "i")])]
    for ch, (gx, gy) in meta["pos"].items():
        B.append(dict(id=f"ks_{ch}", x=gx, y=gy + 10, w=meta["cw"], size=15, lh=20, font=GAR, color=Hd.SEPIA,
                      align="center", runs=[(ch, "i")]))
    return B
