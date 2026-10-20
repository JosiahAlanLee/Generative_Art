from portable_paths import OUTPUT
"""Tabula XIII — Of the Twelve Marks and the Mark (Rev 5 §13). Cornmeal on dark earth."""
import math
import random
import sys

from core import Doc, arc_pts, offset_line, path_len, point_at, catmull, bezier
from marks import *
import cipher

W, H = 1000, 1600
EARTH, MEAL, OCHRE, ASH = "#17120d", "#e8d5a3", "#c9532f", "#9d927c"
SEED = 13

COLS = [162.5, 387.5, 612.5, 837.5]
ROWS = [345, 615, 885]
SR = 98                         # seal radius
GX, GY, GR = 292, 1292, 186     # the great seal

MARKS = [
    ("Interest-bearing being", "has standing (P5)"),
    ("Sentience candidate", "standing uncertain"),
    ("Boundary", "commons or institution"),
    ("Centre of decision", "authority, contestable"),
    ("Bottleneck", "fails the bypass test"),
    ("Regulation", "returns to set point"),
    ("Revision", "returns displaced"),
    ("Additive change", "new branch, old kept"),
    ("Substitutive change", "old route struck out"),
    ("Generative substrate", "conditions beneath"),
    ("Reflexive loop", "the map moves it"),
    ("Learned invariant", "hard walls, one door"),
]


def styles():
    st = {}
    for c, col in (("ink", MEAL), ("red", OCHRE), ("ash", ASH)):
        for k, wdt, op in (("gs", 1.0, 0.9), ("gm", 1.55, 0.92), ("gl", 2.2, 0.95)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "opacity": str(op)}
    st["tex_lt"] = {"fill": "none", "stroke": "#2a2219", "stroke-width": "1.4", "stroke-linecap": "round"}
    st["tex_dk"] = {"fill": "none", "stroke": "#0d0a07", "stroke-width": "1.8", "stroke-linecap": "round"}
    st["ghost_orn"] = {"fill": "none", "stroke": MEAL, "stroke-width": "1.2", "stroke-linecap": "round",
                       "opacity": "0.075"}
    st["ghost_hair"] = st["ghost_orn"]
    st["ghost_core"] = st["ghost_orn"]
    st["ghost_fill"] = {"fill": MEAL, "opacity": "0.06"}
    return st


GRAIN = {"core": (2.9, 1.0), "orn": (1.95, 0.6), "hair": (1.3, 0.33), "cip": (2.05, 0.35),
         "sizes": (5, 3, 1), "stray": 0.035}


def seal_ornament(h, cx, cy, r, rng):
    """the variable ornament every seal carries; the mark inside is the stable core"""
    band = rng.choice(["x", "dots", "ticks", "x"])
    if band == "x":
        ring_x(h, cx, cy, r - 1, r - 9, rng.choice([24, 28, 32]), "hair", "ink")
    elif band == "dots":
        h.stroke(arc_pts(cx, cy, r - 1, 0, 360, 160), "hair")
        dotted(h, arc_pts(cx, cy, r - 6, 0, 360, 160), 5.2, 0.9, "ink", skip_ends=False)
    else:
        h.stroke(arc_pts(cx, cy, r - 1, 0, 360, 160), "hair")
        for k in range(48):
            a = math.radians(k * 7.5)
            h.stroke([(cx + (r - 1) * math.cos(a), cy + (r - 1) * math.sin(a)),
                      (cx + (r - (8 if k % 4 == 0 else 5)) * math.cos(a), cy + (r - (8 if k % 4 == 0 else 5)) * math.sin(a))], "hair")
    r = r - 12
    kind = rng.choice(["stars", "crooks", "dots", "rays"])
    if kind == "stars":
        for i in range(8):
            a = math.radians(22.5 + i * 45)
            asterisk(h, cx + r * 0.82 * math.cos(a), cy + r * 0.82 * math.sin(a), 3.2, 8, weight="hair")
    elif kind == "crooks":
        for i in range(4):
            a = 45 + i * 90
            ar = math.radians(a)
            x0, y0 = cx + r * 0.9 * math.cos(ar), cy + r * 0.9 * math.sin(ar)
            curl(h, x0, y0, a + 180, 3, 5.5, 1.3, hand=1, weight="hair")
    elif kind == "dots":
        for i in range(16):
            a = math.radians(i * 22.5 + 11.25)
            h.dot(cx + r * 0.84 * math.cos(a), cy + r * 0.84 * math.sin(a), 1.1)
    else:
        for i in range(12):
            a = math.radians(i * 30 + 15)
            h.stroke([(cx + r * 0.78 * math.cos(a), cy + r * 0.78 * math.sin(a)),
                      (cx + r * 0.88 * math.cos(a), cy + r * 0.88 * math.sin(a))], "hair")


def draw_mark(i, h, cx, cy, s):
    if i == 0:
        sig_standing(h, cx, cy + 4, s * 0.15, crown=True)
    elif i == 1:
        sig_candidate(h, cx, cy, s * 0.15)
    elif i == 2:
        sig_boundary(h, cx, cy, s * 0.42)
    elif i == 3:
        sig_authority(h, cx, cy + s * 0.14, s * 0.68, s * 0.55)
    elif i == 4:
        sig_bottleneck(h, cx, cy, s * 0.48)
    elif i == 5:
        sig_regulation(h, cx, cy, s * 0.36)
    elif i == 6:
        pts = sig_mark(h, cx, cy, s * 0.44, "red", "core", branch=False, turns=1.75, ang0=90)
        dotted(h, offset_line(pts[60:], s * 0.07), s * 0.075, 0.9, "red")
        asterisk(h, pts[-1][0], pts[-1][1] - 7, 4, 8, weight="hair", color="red")
    elif i == 7:
        sig_branch(h, cx - s * 0.52, cx + s * 0.46, cy + s * 0.14)
    elif i == 8:
        sig_branch(h, cx - s * 0.52, cx + s * 0.46, cy + s * 0.14, struck=True)
    elif i == 9:
        sig_ground(h, cx - s * 0.55, cx + s * 0.55, cy + s * 0.04, s * 0.26, step=5.5)
        h.dot(cx, cy - s * 0.2, s * 0.08)
        asterisk(h, cx - s * 0.3, cy - s * 0.24, 3.4, 8, weight="hair")
        asterisk(h, cx + s * 0.3, cy - s * 0.24, 3.4, 8, weight="hair")
    elif i == 10:
        sig_reflexive(h, cx, cy + s * 0.12, s * 0.52)
    elif i == 11:
        sig_invariant(h, cx + s * 0.04, cy, s * 0.6)


def build(seed=SEED):
    rng = random.Random(seed)
    st = styles()
    doc = Doc(W, H, st, order=["tex_dk", "tex_lt", "ghost_orn", "ghost_fill"] +
              [k for k in st if not k.startswith(("tex", "ghost"))])
    h = Hand(doc, rng, "grain", amp=0.75, grain=GRAIN)
    gh = Hand(doc, rng, "ink", amp=1.2)  # ghosts: earlier drawings, scuffed away

    # ground texture
    for _ in range(2600):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        doc.grain("tex_lt" if rng.random() < 0.55 else "tex_dk", x, y)
    # ghosts of earlier drawings
    for _ in range(9):
        cx, cy = rng.uniform(80, 920), rng.uniform(260, 1450)
        r = rng.uniform(60, 190)
        a0 = rng.uniform(0, 360)
        pts = arc_pts(cx, cy, r, a0, a0 + rng.uniform(70, 200), 60)
        gh.stroke(pts, "orn", "ghost")
        if rng.random() < 0.5:
            gh.stroke([(cx - r * 0.6, cy), (cx + r * 0.6, cy + rng.uniform(-40, 40))], "orn", "ghost")

    # running head rules
    h.stroke([(56, 60), (944, 60)], "orn")
    h.stroke([(56, 64), (944, 64)], "hair", "ash")
    ring_y = 136
    for k in range(13):
        x = 380 + k * 20
        h.dot(x, ring_y, 1.3 if k % 2 else 2.0, "red" if k == 6 else "ink")

    # ---------------------------------------------------------- the twelve
    for i in range(12):
        cx, cy = COLS[i % 4], ROWS[i // 4]
        h.stroke(arc_pts(cx, cy, SR, 0, 360, 200), "orn")
        h.stroke(arc_pts(cx, cy, SR - 15, 0, 360, 180), "hair")
        name, meaning = MARKS[i]
        a_end = write_ring(h, f"{name} {meaning}", cx, cy, SR - 12.5, -158, 9.2, "ink")
        # close the ring with a dotted arc and a star
        gap = 6
        rest = arc_pts(cx, cy, SR - 7.5, a_end + gap, -158 + 360 - gap, 60)
        if len(rest) > 3:
            dotted(h, rest, 6.0, 0.9, "ink", skip_ends=True)
        sa = math.radians(-158 - 3)
        asterisk(h, cx + (SR - 7.5) * math.cos(sa), cy + (SR - 7.5) * math.sin(sa), 3.6, 8, weight="hair",
                 color="red", centre=False)
        seal_ornament(h, cx, cy, SR - 18, rng)
        draw_mark(i, h, cx, cy, SR * 1.06)
        # cardinal studs outside the ring
        for a in (0, 90, 180, 270):
            ar = math.radians(a)
            px, py = cx + (SR + 7) * math.cos(ar), cy + (SR + 7) * math.sin(ar)
            h.dot(px, py, 1.6)

    # --------------------------------------------------------- the great seal
    h.stroke(arc_pts(GX, GY, GR, 0, 360, 360), "core")
    h.stroke(arc_pts(GX, GY, GR - 24, 0, 360, 330), "orn")
    a = write_ring(h, "a sketch prompts a claim and never replaces one", GX, GY, GR - 19, -170, 12.5, "ink",
                   rail=True)
    asterisk(h, GX + (GR - 12) * math.cos(math.radians(a + 4)), GY + (GR - 12) * math.sin(math.radians(a + 4)),
             5, 8, weight="orn", color="red", centre=False)
    a2 = write_ring(h, "data usefulness is not protocol efficacy", GX, GY, GR - 19, a + 9, 12.5, "ink", rail=True)
    rest = arc_pts(GX, GY, GR - 12, a2 + 5, -170 + 360 - 5, 80)
    if len(rest) > 3:
        dotted(h, rest, 8, 1.2, "ink")
    asterisk(h, GX + (GR - 12) * math.cos(math.radians(-174)), GY + (GR - 12) * math.sin(math.radians(-174)), 5, 8,
             weight="orn", color="red", centre=False)
    ring_x(h, GX, GY, GR - 32, GR - 46, 36, "hair", "ink")
    # outer rays
    for k in range(16):
        ar = math.radians(k * 22.5)
        r0, r1 = GR + 6, GR + (24 if k % 2 == 0 else 14)
        h.stroke([(GX + r0 * math.cos(ar), GY + r0 * math.sin(ar)), (GX + r1 * math.cos(ar), GY + r1 * math.sin(ar))],
                 "orn")
        if k % 2 == 0:
            asterisk(h, GX + (r1 + 8) * math.cos(ar), GY + (r1 + 8) * math.sin(ar), 5, 8, weight="hair")
    # the mark, rotation left to the seed (rotation and proportion carry no doctrine)
    rot0 = rng.uniform(0, 360)
    pts = sig_mark(h, GX, GY, 84, "red", "core", branch=True, turns=1.75, ang0=rot0)
    dotted(h, offset_line(pts[40:], 13), 9, 1.3, "red")
    fringe(h, pts[90:], 9, 6, side=-1, weight="hair", color="red")
    end = pts[-1]
    asterisk(h, end[0], end[1], 7, 8, weight="orn", color="red", centre=False)
    # four crooks and four stars in the field, kept off the centre (no central dot)
    for k in range(4):
        ar = rot0 + 45 + k * 90
        rr = math.radians(ar)
        x0, y0 = GX + 128 * math.cos(rr), GY + 128 * math.sin(rr)
        curl(h, x0, y0, ar + 180, 6, 8.5, 1.3, hand=1, weight="orn")
        rs = math.radians(ar + 45)
        asterisk(h, GX + 132 * math.cos(rs), GY + 132 * math.sin(rs), 4.2, 8, weight="hair")

    # ------------------------------------------------------ key to the cipher
    h.stroke([(56, 1500), (944, 1500)], "hair", "ash")
    letters = "abcdefghijklmnopqrstuvwxyz"
    cw = 888 / 26
    for k, ch in enumerate(letters):
        gw = cipher.G[ch][0] * 15
        cipher.glyph_only(h, ch, 56 + cw * k + (cw - gw) / 2, 1532, 15, "cip", "ink")
    return doc, dict(cw=cw)


if __name__ == "__main__":
    doc, meta = build()
    open(f"{OUTPUT}/p2_plate.svg", "w").write(doc.svg())
