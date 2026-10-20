"""Tabula IV · Of the Second Copy — a mounted record of two deposits; the second copies the first's omission."""
import math
import random
import sys

from shapely.geometry import Polygon
from core import Doc, arc_pts, bezier, catmull, offset_line, path_len, point_at, lattice
from marks import *
import hands as Hd
import tx
from page2 import GRAIN, EARTH, MEAL, OCHRE, ASH, styles as st2

W, H = 1000, 1600
PAPER = "#ebe1c8"
REC = (90, 300, 910, 1100)
FRESH = "#f7ecc8"
UNIT, GAPW = 70, 6
X0U = 182                      # first unit's left edge
Y1, Y2 = 540, 840              # the two deposits' centre lines
MISSING = 5                    # the unit both copies lack


def ux(i):
    return X0U + i * (UNIT + GAPW)


def styles():
    st = st2()
    for k, wdt, op in (("gs", 1.0, 0.95), ("gm", 1.6, 0.97), ("gl", 2.3, 1.0)):
        st[f"fr_{k}"] = {"fill": "none", "stroke": FRESH, "stroke-width": str(wdt), "stroke-linecap": "round",
                         "opacity": str(op)}
    st["earth_fill"] = {"fill": EARTH, "stroke": "none"}
    st["mount_fill"] = {"fill": "#f1e8d3", "stroke": "none"}
    st["mount_orn"] = {"fill": "none", "stroke": "#b9ab8c", "stroke-width": "0.8"}
    for c, col in (("pk", Hd.INK), ("pr", Hd.RED)):
        for k, wdt in (("core", 2.2), ("orn", 1.4), ("hair", 0.8), ("cip", 1.3)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    st["fox_fill"] = {"fill": "#b89a6a", "stroke": "none", "opacity": "0.14"}
    return st


def unit(h, i, cx, cy, rng, jit=1.0):
    """one element of the deposit's sequence"""
    j = lambda: rng.uniform(-2, 2) * jit
    if i == 0:
        sig_gate(h, cx + j(), cy + j(), 42, 48, red="ink", orn=0)
    elif i == 1:
        h.dot(cx + j(), cy - 14 + j(), 5.2)
        h.dot(cx + j(), cy + 14 + j(), 5.2)
    elif i == 2:
        sig_mark(h, cx + j(), cy + j(), 22, "ink", "orn", branch=True, ang0=rng.uniform(60, 120))
    elif i == 3:
        box = [(cx - 28, cy - 22), (cx + 28, cy - 22), (cx + 28, cy + 22), (cx - 28, cy + 22)]
        lattice_fill(h, box, 11, marker="dot", weight="hair", outline=True)
    elif i == 4:
        h.stroke(tri_pts(cx + j(), cy + j(), 44, 40), "orn", closed=True)
        h.dot(cx, cy + 6, 3.6)
    elif i == 6:
        asterisk(h, cx + j(), cy + j(), 18, 8, weight="orn")
    elif i == 7:
        curl(h, cx - 4, cy + 10, 200, 4, 11, 1.3, hand=1, weight="orn")
        curl(h, cx + 4, cy + 10, -20, 4, 11, 1.3, hand=-1, weight="orn")
    elif i == 8:
        for off in (-6, 6):
            pts = [(cx - 28 + k * 4, cy + off + 5 * math.sin(k * 0.6 + rng.uniform(-0.2, 0.2))) for k in range(15)]
            h.stroke(pts, "orn")


def deposit(h, cy, rng, scuff, jit=1.0):
    for i in range(9):
        cx = ux(i) + UNIT / 2
        if i == MISSING:
            if scuff:   # the edges of the lost segment, grains dragged out by a thumb
                for _ in range(40):
                    x = rng.uniform(ux(i) - 4, ux(i) + 10) if rng.random() < 0.5 else rng.uniform(ux(i) + UNIT - 10, ux(i) + UNIT + 4)
                    h.doc.grain("ink_gs", x, cy + rng.gauss(0, 18))
            continue
        # the hand pauses at the start of each element: a thickened deposit
        for _ in range(26):
            h.doc.grain(rng.choice(["ink_gm", "ink_gl"]), ux(i) + 6 + rng.gauss(0, 2.5), cy - 28 + rng.gauss(0, 3))
        unit(h, i, cx, cy, rng, jit)
    # rules above and below the run, broken where the element is missing
    for yy in (cy - 40, cy + 40):
        h.stroke([(ux(0) - 6, yy), (ux(MISSING) - 4, yy)], "hair")
        h.stroke([(ux(MISSING) + UNIT + 4, yy), (ux(8) + UNIT + 6, yy)], "hair")


def spills(h, cy, rng, n):
    for _ in range(n):
        x = rng.uniform(ux(0), ux(8) + UNIT)
        if ux(MISSING) - 8 < x < ux(MISSING) + UNIT + 8:
            continue
        y = cy + rng.choice([-1, 1]) * rng.uniform(44, 70)
        for _ in range(rng.randint(8, 22)):
            h.doc.grain(rng.choice(["ink_gs", "ink_gm"]), x + rng.gauss(0, 4), y + rng.gauss(0, 3))


def build_face(seed=44):
    rng = random.Random(seed)
    st = styles()
    order = ["fox_fill", "earth_fill", "tex_dk", "tex_lt", "ghost_orn"] + \
            [k for k in st if k.startswith(("ink_", "red_", "ash_", "fr_"))] + \
            ["mount_fill", "mount_orn"] + [k for k in st if k.startswith(("pk_", "pr_"))]
    d = Doc(W, H, st, order=order)
    h = Hand(d, rng, "grain", amp=0.75, grain=GRAIN)
    for _ in range(140):
        d.circle("fox_fill", rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 3.0) ** 1.4)
    x0, y0, x1, y1 = REC
    d.poly("earth_fill", [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True)
    for _ in range(1500):
        d.grain("tex_lt" if rng.random() < 0.55 else "tex_dk", rng.uniform(x0, x1), rng.uniform(y0, y1))
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        tri = [(cx - sx * 6, cy - sy * 6), (cx + sx * 44, cy - sy * 6), (cx - sx * 6, cy + sy * 44)]
        d.poly("mount_fill", tri, closed=True)
        d.poly("mount_orn", [(cx + sx * 44, cy - sy * 6), (cx - sx * 6, cy + sy * 44)])
    ph = Hand(d, rng, "ink", amp=0.35)
    ph.stroke([(56, 58), (944, 58)], "orn", "pk")
    ph.stroke([(56, 62), (944, 62)], "hair", "pk")

    deposit(h, Y1, rng, scuff=True)
    deposit(h, Y2, rng, scuff=False, jit=1.6)
    spills(h, Y1, rng, 9)
    spills(h, Y2, rng, 9)

    # the copying path: one unmistakable trail from the first run to the second
    path = catmull([(ux(0) - 14, Y1), (ux(0) - 48, Y1 + 60), (ux(0) - 60, (Y1 + Y2) / 2), (ux(0) - 48, Y2 - 60),
                    (ux(0) - 14, Y2)], 18)
    dotted(h, path, 7, 2.0, "ink", skip_ends=False)
    arrowhead(h, path[-1], 20, 12, "ink", "orn")

    # a test stroke at the edge: unhandled, its grain still sharp
    th = Hand(d, rng, "grain", amp=0.4, grain={"core": (4.0, 0.45), "orn": (3.0, 0.3), "hair": (2, 0.2),
                                               "sizes": (3, 3, 2), "stray": 0.0})
    th.stroke(bezier((812, 1046), (836, 1030), (858, 1052), (876, 1040), 20), "orn", "fr")

    # later red chalk: M. measures both blanks with endpoint ticks
    rc = Hand(d, rng, "grain", amp=0.5, grain={"orn": (1.6, 0.5), "hair": (1.2, 0.3), "core": (2.2, 0.7),
                                               "sizes": (4, 3, 1), "stray": 0.02})
    for cy in (Y1, Y2):
        yy = cy - 62
        a, b = ux(MISSING) - 2, ux(MISSING) + UNIT + 2
        rc.stroke([(a, yy), (b, yy)], "orn", "red")
        rc.stroke([(a, yy - 8), (a, yy + 8)], "orn", "red")
        rc.stroke([(b, yy - 8), (b, yy + 8)], "orn", "red")

    # caption strip on the mount paper: two thin rules and the transcription hand
    ph.stroke([(64, 1196), (936, 1196)], "hair", "pk")
    ph.stroke([(64, 1258), (936, 1258)], "hair", "pk")
    s = 29
    wdt = tx.width("THE CLOCK HAS AN OWNER.", s)
    tx.write(ph, "THE CLOCK HAS AN OWNER.", (W - wdt) / 2, 1211, s, color="pk")
    sig_mark(ph, 500, 1550, 11, "pk", "orn")
    meta = dict(patch=(ux(MISSING) - 20, Y1 - 52, UNIT + 40, 104))
    return d.svg(), meta


def face_boxes(meta):
    GAR = "EB Garamond"
    B = [dict(id="rh_l", x=56, y=28, w=420, size=14, lh=18, font=GAR, color=Hd.INK, runs=[("Clavicula Matricis", "v")]),
         dict(id="rh_r", x=524, y=28, w=420, size=14, lh=18, font=GAR, align="right", color=Hd.RED,
              runs=[("Tabula IV · a mounted record", "v")]),
         dict(id="title", x=60, y=110, w=880, size=42, lh=48, font=GAR, align="center", color=Hd.INK,
              runs=[("Of the Second Copy", "")])]
    B.append(Hd.cust("s09", 200, 196, 600, "Two copies. One omission.", size=24, align="center"))
    B.append(dict(id="folio", x=844, y=1560, w=100, size=13, lh=18, font=GAR, align="right", color=Hd.SEPIA,
                  runs=[("iv", "v")]))
    return B


def patch_html(meta):
    x, y, w, hgt = meta["patch"]
    clip = "polygon(3% 6%, 22% 1%, 47% 4%, 71% 0%, 97% 5%, 100% 31%, 96% 58%, 99% 86%, 92% 100%, 63% 96%, 38% 100%, 9% 97%, 0% 71%, 4% 42%)"
    closed = (f'<sc-if value="{{{{ closed }}}}" hint-placeholder-val="{{{{ true }}}}">'
              f'<button aria-label="Lift the paper patch" onClick="{{{{ toggle }}}}" style="position: absolute; left: {x}px; '
              f'top: {y}px; width: {w}px; height: {hgt}px; padding: 0; border: 0; margin: 0; background: #e7dec8; '
              f'opacity: 0.96; clip-path: {clip}; cursor: pointer"></button></sc-if>')
    lifted = (f'<sc-if value="{{{{ lifted }}}}" hint-placeholder-val="{{{{ false }}}}">'
              f'<button aria-label="Lay the patch back" onClick="{{{{ toggle }}}}" style="position: absolute; left: {x - 26}px; '
              f'top: {y - 112}px; width: {w + 30}px; height: {hgt}px; padding: 10px 10px; box-sizing: border-box; border: 0; '
              f'margin: 0; background: #efe7d2; clip-path: {clip}; transform: rotate(-7deg); cursor: pointer; '
              f"font-family: 'Zeyada', cursive; font-size: 17px; line-height: 18px; color: #4a463f; text-align: left\">"
              f'I copied the place where the word had been.</button></sc-if>')
    return closed + "\n" + lifted


SCRIPT = """class Component extends DCLogic {
renderVals() {
const lifted = !!(this.state && this.state.lifted);
return { lifted: lifted, closed: !lifted, toggle: () => this.setState({ lifted: !lifted }) };
}
}"""


def build_verso(seed=45):
    boxes, meta = verso_boxes()
    rng = random.Random(seed)
    st = styles()
    d = Doc(W, H, st, order=["fox_fill"] + [k for k in st if k.startswith(("pk_", "pr_"))])
    ph = Hand(d, rng, "ink", amp=0.35)
    for _ in range(110):
        d.circle("fox_fill", rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.6, 3.0) ** 1.4)
    ph.stroke([(56, 58), (944, 58)], "orn", "pk")
    ph.stroke([(56, 62), (944, 62)], "hair", "pk")
    return d.svg(), boxes, meta


def verso_boxes():
    from layout import box_height
    GAR = "EB Garamond"
    B, meta = [], {}
    B.append(dict(id="rh_l", x=56, y=28, w=420, size=14, lh=18, font=GAR, color=Hd.INK, runs=[("Clavicula Matricis", "v")]))
    B.append(dict(id="rh_r", x=524, y=28, w=420, size=14, lh=18, font=GAR, align="right", color=Hd.RED,
                  runs=[("Verso · Tabula IV", "v")]))
    main = dict(id="e_main", x=150, y=0, w=700, size=23, lh=33, font=GAR, color=Hd.INK, para_gap=14,
                runs=[("The first copy had a pale place beneath the seal. I left a pale place beneath mine. When the third "
                       "keeper asked why, I told her that the master had reserved it.", ""), ("", "br"),
                      ("Thereafter no one wrote there. The reserved place passed intact through six hands. Everything "
                       "around it was amended.", "")])
    hm = box_height(main) * 1.12
    m = Hd.mhand("e_m", 150, 0, 700, "The copies agree on the size of the blank. That is the extent of their agreement.",
                 size=28)
    u = Hd.unh("e_u", 190, 0, 660, "The first sheet had been patched. I cannot tell you what the patch covered.", size=30)
    block = hm + 70 + box_height(m) * 1.12 + 90 + box_height(u) * 1.12
    top = (100 + 1540 - block) / 2
    main["y"] = top
    m["y"] = top + hm + 70
    u["y"] = m["y"] + box_height(m) * 1.12 + 90
    B += [main, m, u]
    return B, meta
