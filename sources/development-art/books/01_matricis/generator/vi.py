"""Tabula VI · Of the Borrowed Face — a plotter foldout: three attempts at a supplied contour."""
import math
import random
import sys

from shapely.geometry import LineString, Point
from core import Doc, catmull, resample, bezier, arc_pts, dist
from marks import *
import hands as Hd
from v2_iii import PENS, PAPER

W2, H2 = 2000, 1250        # inside spread
WO, HO = 1000, 1250        # outside of the folded flap (same size as the half it backs)
FOLD = 1000

# the supplied contour, facing right; unit = face height
FRONT = [(0.10, 0.00), (0.20, 0.07), (0.26, 0.19), (0.285, 0.31), (0.262, 0.375), (0.31, 0.47), (0.385, 0.56),
         (0.33, 0.60), (0.305, 0.615), (0.325, 0.665), (0.292, 0.70), (0.315, 0.745), (0.262, 0.79), (0.29, 0.88),
         (0.25, 0.95), (0.15, 0.99)]
JAW = [(0.15, 0.99), (0.05, 0.955), (-0.06, 0.88), (-0.12, 0.78)]
CHEEK = [(0.225, 0.55), (0.17, 0.62), (0.10, 0.69), (0.04, 0.73)]
NECK = [(0.13, 1.0), (0.11, 1.12), (0.10, 1.26)]
EYE = [(0.16, 0.37), (0.215, 0.365)]


def perturb(pts, amp, rng, freq=2.0):
    ph = rng.uniform(0, 6.28)
    out = []
    for i, (x, y) in enumerate(pts):
        t = i / max(1, len(pts) - 1)
        out.append((x + amp * math.sin(t * freq * math.pi + ph), y + amp * 0.5 * math.cos(t * freq * 1.3 * math.pi + ph)))
    return out


def attempts(rng):
    """three successive attempts: closer each time; the third meets the cheek, overshoots the jaw"""
    out = []
    for k, amp in enumerate((0.05, 0.022, 0.006)):
        f = perturb(FRONT, amp, rng, 2.2)
        if k == 0:
            f = [(x + (0.035 if 0.45 < y < 0.62 else 0), y) for x, y in f]      # a longer nose
        cheek = perturb(CHEEK, amp * 1.2, rng, 1.5) if k < 2 else list(CHEEK)
        jaw = perturb(JAW, amp, rng, 1.2)
        if k == 2:
            jaw = JAW[:-1] + [(-0.155, 0.75), (-0.19, 0.70)]                      # past the target's angle
        out.append(dict(front=f, cheek=cheek, jaw=jaw, neck=perturb(NECK, amp, rng), eye=perturb(EYE, amp * 0.5, rng)))
    return out


def residual(att, s):
    """mean distance (px at scale s) from the attempt's lines to the target's"""
    tot, n = 0.0, 0
    for key, tgt in (("front", FRONT), ("cheek", CHEEK), ("jaw", JAW)):
        T = LineString([(x * s, y * s) for x, y in tgt])
        for p in resample([(x * s, y * s) for x, y in att[key]], 3.0):
            tot += T.distance(Point(p))
            n += 1
    return tot / n


def styles():
    st = {}
    for k, col in PENS.items():
        for name, wdt in (("hair", 0.85), ("orn", 1.35), ("core", 2.1), ("cip", 1.15)):
            st[f"{k}_{name}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                                 "stroke-linejoin": "round"}
        st[f"{k}_fill"] = {"fill": col, "stroke": "none"}
    st["ghost_orn"] = {"fill": "none", "stroke": PENS["ol"], "stroke-width": "1.2", "stroke-dasharray": "2 4",
                       "stroke-linecap": "round"}
    st["faint_hair"] = {"fill": "none", "stroke": PENS["sg"], "stroke-width": "0.9", "opacity": "0.75"}
    st["thread_orn"] = {"fill": "none", "stroke": "#b8a57e", "stroke-width": "1.6", "stroke-linecap": "round"}
    st["scrap_fill"] = {"fill": "#efe7d2", "stroke": "none"}
    st["shadow_fill"] = {"fill": "#7a6a4e", "stroke": "none", "opacity": "0.22"}
    st["crease_fill"] = {"fill": "#6d5f4b", "stroke": "none", "opacity": "0.05"}
    st["crease2_fill"] = {"fill": "#6d5f4b", "stroke": "none", "opacity": "0.05"}
    st["notch_hair"] = {"fill": "none", "stroke": "#b9ab88", "stroke-width": "1.1"}
    st["show_hair"] = {"fill": "none", "stroke": PENS["dk"], "stroke-width": "1.3", "opacity": "0.085",
                       "stroke-linecap": "round", "stroke-linejoin": "round"}
    for name in ("hair", "orn", "core", "cip", "fill"):
        st[f"ink_{name}"] = dict(st[f"dk_{name}"])
        st[f"red_{name}"] = dict(st[f"rr_{name}"])
    return st


def plot(h, pts, pen, rng, x0, y0, s, weight="orn"):
    P = [(x0 + x * s, y0 + y * s) for x, y in catmull(pts, 8)]
    h.stroke(P, weight, pen, amp=0.35)
    h.doc.circle(f"{pen}_fill", P[0][0], P[0][1], 1.5)
    if rng.random() < 0.6:   # a repeated start where the pen came down twice
        h.stroke([(P[0][0] + 1.4, P[0][1] + 1.0), (P[2][0] + 1.4, P[2][1] + 1.0)], "hair", pen, amp=0.1)
    return P


def ghost(d, pts, x0, y0, s):
    P = [(x0 + x * s, y0 + y * s) for x, y in catmull(pts, 8)]
    d.poly("ghost_orn", P)


def witness(h, cx, cy, pen, r=6):
    h.ring(cx, cy, r, "hair", pen)
    h.stroke([(cx - r * 1.8, cy), (cx + r * 1.8, cy)], "hair", pen, amp=0.02)
    h.stroke([(cx, cy - r * 1.8), (cx, cy + r * 1.8)], "hair", pen, amp=0.02)


def crease(d, x, H):
    """a soft fold: a faint band and two edge notches, nothing drawn across the sheet"""
    d.poly("crease_fill", [(x - 9, 0), (x, 0), (x, H), (x - 9, H)], closed=True)
    d.poly("crease2_fill", [(x, 0), (x + 4, 0), (x + 4, H), (x, H)], closed=True)
    d.poly("notch_hair", [(x, 0), (x, 14)])
    d.poly("notch_hair", [(x, H - 14), (x, H)])


def test_strip(h, x, y, rng, pen="um"):
    """pen-wetting loops, a dry section, then pressure returning; no plaintext"""
    cx = x
    for k in range(17):
        if 8 <= k <= 10:          # the dry section: the pen moves, little ink arrives
            pts = [(cx + 7 * math.cos(math.radians(a)) + a * 0.03, y + 7 * math.sin(math.radians(a))) for a in range(0, 360, 20)]
            for i in range(0, len(pts) - 1, 3):
                h.stroke(pts[i:i + 2], "hair", pen, amp=0.05)
        else:
            r = 7 + rng.uniform(-0.6, 0.6)
            pts = [(cx + r * math.cos(math.radians(a)) + a * 0.03, y + r * math.sin(math.radians(a))) for a in range(0, 380, 15)]
            h.stroke(pts, "hair" if k < 3 or k > 12 else "orn", pen, amp=0.08)
        cx += 15


PANELS = [(150, 250), (560, 250), (970, 250)]     # face origins (forehead top), scale S
S = 470
TAB = (1490, 236, 300, 340)                       # x, y, w, h of the registration tab
TAB_S = 230
EYELET = (TAB[0] + TAB[2] - 22, TAB[1] + TAB[3] - 20)
SLIP = (1430, 700, 500, 200, -0.6)                # the unsigned instruction
SCRAP = (1440, 940, 470, 220, 1.4)                # the procedural scrap, folded inside
LAB_Y, Q_Y, RES_Y = 890, 905, 950


def build_inside(seed=6):
    rng = random.Random(seed)
    st = styles()
    order = ["crease_fill", "crease2_fill", "notch_hair", "faint_hair", "shadow_fill", "scrap_fill", "thread_orn",
             "ghost_orn"] + [k for k in st if k.startswith(tuple(f"{p}_" for p in PENS))] + \
            [k for k in st if k.startswith(("ink_", "red_"))]
    d = Doc(W2, H2, st, order=order)
    h = Hand(d, rng, "ink", amp=0.3)
    crease(d, FOLD, H2)
    witness(h, 40, 40, "dk")
    witness(h, 1960, 1210, "dk")

    atts = attempts(rng)
    res = []
    for k, ((x0, y0), att) in enumerate(zip(PANELS, atts)):
        # the target, registered over each attempt as a dotted ghost
        for part in (FRONT, JAW, CHEEK):
            ghost(d, part, x0, y0, S)
        for key in ("front", "jaw", "cheek", "neck", "eye"):
            plot(h, att[key], "dk", rng, x0, y0, S, "orn" if key in ("front", "jaw") else "hair")
        witness(h, x0 - 60, y0 - 20, "um")
        res.append(residual(att, S))
    # the one rust-red correction: M.'s endpoint ticks on the third attempt's jaw overshoot
    x0, y0 = PANELS[2]
    tj = (x0 + JAW[-1][0] * S, y0 + JAW[-1][1] * S)
    aj = (x0 + atts[2]["jaw"][-1][0] * S, y0 + atts[2]["jaw"][-1][1] * S)
    h.stroke([tj, aj], "orn", "rr")
    for p in (tj, aj):
        h.stroke([(p[0] - 5, p[1] - 5), (p[0] + 5, p[1] + 5)], "hair", "rr")

    # under the tab: a different profile, too slight to say which came first
    tx0, ty0, tw, th = TAB
    hid = perturb(FRONT, 0.03, random.Random(99), 3.1)
    d.poly("faint_hair", [(tx0 + 70 + x * TAB_S, ty0 + 50 + y * TAB_S) for x, y in catmull(hid, 6)])
    d.poly("faint_hair", [(tx0 + 70 + x * TAB_S, ty0 + 50 + y * TAB_S)
                          for x, y in catmull(perturb(JAW, 0.03, random.Random(98)), 6)])

    # the pasted instruction slip and the folded procedural scrap
    for (x, y, w, hh, ang) in (SLIP, SCRAP):
        c = (x + w / 2, y + hh / 2)
        rect = [rot(p, math.radians(ang), c) for p in [(x, y), (x + w, y), (x + w, y + hh), (x, y + hh)]]
        d.poly("shadow_fill", [(px + 4, py + 5) for px, py in rect], closed=True)
        d.poly("scrap_fill", rect, closed=True)
    # the instruction's empty signature rule
    x, y, w, hh, ang = SLIP
    c = (x + w / 2, y + hh / 2)
    h.stroke([rot((x + 300, y + hh - 26), math.radians(ang), c), rot((x + w - 36, y + hh - 26), math.radians(ang), c)],
             "hair", "um")
    # the scrap's crease, below its writing: the lower half was folded under
    x, y, w, hh, ang = SCRAP
    c = (x + w / 2, y + hh / 2)
    h.stroke([rot((x + 6, y + 124), math.radians(ang), c), rot((x + w - 6, y + 124), math.radians(ang), c)], "hair", "sg")

    # the removable thread: from the tab's eyelet to the unsigned instruction
    ex, ey = EYELET
    thread = catmull([(ex, ey), (ex + 46, ey + 44), (ex + 10, ey + 96), (1700, SLIP[1] + 6)], 16)
    d.poly("thread_orn", thread)
    d.circle("um_fill", 1700, SLIP[1] + 6, 2.4)

    # a pen-wetting strip at the lower margin of the right half
    test_strip(h, 1060, 1206, rng)
    return d.svg(), dict(res=res, atts=atts)


def tab_svg():
    """the tab's own drawing, as an inline svg inside its button"""
    tx0, ty0, tw, th = TAB
    pts = lambda part: " ".join(f"{70 + x * TAB_S:.1f},{50 + y * TAB_S:.1f}" for x, y in catmull(part, 6))
    ol, um, dk = PENS["ol"], PENS["um"], PENS["dk"]
    parts = "".join(f'<polyline points="{pts(p)}" fill="none" stroke="{ol}" stroke-width="1.6" stroke-linecap="round"/>'
                    for p in (FRONT, JAW, CHEEK))
    # two registration witnesses: the tab was re-registered at least once
    reg = (f'<circle cx="24" cy="24" r="6" fill="none" stroke="{dk}" stroke-width="0.9"/>'
           f'<line x1="13" y1="24" x2="35" y2="24" stroke="{dk}" stroke-width="0.9"/>'
           f'<line x1="24" y1="13" x2="24" y2="35" stroke="{dk}" stroke-width="0.9"/>'
           f'<circle cx="28" cy="27" r="6" fill="none" stroke="{um}" stroke-width="0.9"/>'
           f'<line x1="17" y1="27" x2="39" y2="27" stroke="{um}" stroke-width="0.9"/>'
           f'<line x1="28" y1="16" x2="28" y2="38" stroke="{um}" stroke-width="0.9"/>'
           f'<circle cx="{tw - 22}" cy="{th - 20}" r="6" fill="#f6f1e3" stroke="{dk}" stroke-width="1"/>')
    return (f'<svg width="{tw}" height="{th}" viewBox="0 0 {tw} {th}" aria-hidden="true" '
            f'style="position: absolute; left: 0px; top: 0px">{parts}{reg}</svg>')


def tab_html():
    tx0, ty0, tw, th = TAB
    base = (f"position: absolute; width: {tw}px; height: {th}px; padding: 0; margin: 0; border: 0; "
            f"background: #fbf7ec; box-shadow: 2px 4px 6px rgba(60,40,20,0.30); cursor: pointer")
    closed = (f'<sc-if value="{{{{ closed }}}}" hint-placeholder-val="{{{{ true }}}}">'
              f'<button aria-label="Lift the registration tab" onClick="{{{{ toggle }}}}" style="{base}; left: {tx0}px; '
              f'top: {ty0}px">{tab_svg()}</button></sc-if>')
    lifted = (f'<sc-if value="{{{{ lifted }}}}" hint-placeholder-val="{{{{ false }}}}">'
              f'<button aria-label="Put the registration tab back" onClick="{{{{ toggle }}}}" style="{base}; '
              f'left: {tx0 + 150}px; top: {ty0 - 120}px; transform: rotate(9deg)">{tab_svg()}</button></sc-if>')
    return closed + "\n" + lifted


SCRIPT = """class Component extends DCLogic {
renderVals() {
const lifted = !!(this.state && this.state.lifted);
return { lifted: lifted, closed: !lifted, toggle: () => this.setState({ lifted: !lifted }) };
}
}"""


def inside_boxes(meta):
    MONO = "IBM Plex Mono"
    DK, UM = PENS["dk"], PENS["um"]
    B = [dict(id="rh_l", x=56, y=30, w=600, size=11.5, lh=16, font=MONO, ls=0.22, color=DK,
              runs=[("CLAVICULA MATRICIS · TABULA VI · INSIDE THE FOLD", "")])]
    for k, ((x0, y0), r) in enumerate(zip(PANELS, meta["res"])):
        B.append(dict(id=f"att{k}", x=x0 - 70, y=LAB_Y, w=300, size=12.5, lh=17, font=MONO, color=UM,
                      runs=[(["attempt i", "attempt ii", "attempt iii"][k], "")]))
        B.append(dict(id=f"res{k}", x=x0 - 70, y=RES_Y, w=300, size=11, lh=15, font=MONO, color=DK,
                      runs=[(f"mean residual {r:.1f} px", "")]))
    x0, y0 = PANELS[2]
    q = Hd.unh("whose", x0 - 74, Q_Y, 330, "Smaller by whose measure?", size=30)
    q.update(rot=-2.5, h=36)
    B.append(q)
    B.append(Hd.mhand("f_m", x0 - 70, 1004, 400, "The final error was small. The face was the one supplied with the "
                      "instrument.", size=24, color=PENS["rr"]))
    B.append(Hd.unh("f_u", 90, 1004, 740, "I learned the expression before I learned whose expression it was. It served "
                    "me well in the room where it was taught.", size=28))
    sx, sy = SLIP[0], SLIP[1]
    B.append(Hd.cust("f_c", sx + 26, sy + 20, 450, "Draw the face you are to become upon the movable strip. Place it where "
                     "the instrument can return to it. Each departure shall summon a correction, and each correction "
                     "shall diminish the departure.\nWhen the two lines coincide, the work is accomplished.", size=17.5))
    cx, cy = SCRAP[0], SCRAP[1]
    B.append(Hd.tech("f_scrap", cx + 22, cy + 20, 430, "Before the next sitting, draw once with the strip removed. Keep "
                     "this drawing outside the sequence. Do not call its difference an error until you have chosen what "
                     "the sitting is for.", size=13.5, color=DK))
    B.append(dict(id="tabnote", x=1490, y=592, w=300, size=11.5, lh=16, font=MONO, color=UM,
                  runs=[("registration tab · movable", "")]))
    return B


def build_outside(meta, seed=61):
    """the back of the folded flap: the attempts show through, mirrored, at the weight of the paper"""
    rng = random.Random(seed)
    st = styles()
    d = Doc(WO, HO, st, order=["show_hair", "crease_fill", "crease2_fill", "notch_hair", "shadow_fill"] +
            [k for k in st if k.startswith(("dk_", "um_", "rr_", "ink_"))])
    h = Hand(d, rng, "ink", amp=0.3)
    for (x0, y0), att in zip(PANELS, meta["atts"]):
        for key in ("front", "jaw", "cheek", "neck"):
            P = [(FOLD - (x0 + x * S), y0 + y * S) for x, y in catmull(att[key], 8)]
            P = [(x, y) for x, y in P if 0 <= x <= WO]
            if len(P) > 1:
                d.poly("show_hair", P)
    # the fold is this leaf's left edge
    d.poly("shadow_fill", [(0, 0), (16, 0), (16, HO), (0, HO)], closed=True)
    d.poly("notch_hair", [(16, 0), (16, 14)])
    d.poly("notch_hair", [(16, HO - 14), (16, HO)])
    h.stroke([(56, 56), (944, 56)], "orn", "dk")
    witness(h, 960, HO - 40, "dk")
    sig_mark(h, 500, HO - 64, 10, "dk", "orn")
    return d.svg(), {}


def outside_boxes():
    MONO, DM = "IBM Plex Mono", "DM Serif Display"
    DK, UM = PENS["dk"], PENS["um"]
    return [dict(id="rh_l", x=56, y=24, w=440, size=11.5, lh=16, font=MONO, ls=0.22, color=DK, runs=[("CLAVICULA MATRICIS", "")]),
            dict(id="rh_r", x=504, y=24, w=440, size=11.5, lh=16, font=MONO, ls=0.22, align="right", color=UM,
                 runs=[("TABULA VI · A FOLDOUT", "")]),
            dict(id="title", x=60, y=930, w=880, size=46, lh=52, font=DM, align="center", color=DK,
                 runs=[("Of the Borrowed Face", "")]),
            Hd.cust("s10", 160, 1010, 680, "The likeness improved. The instruction remained unsigned.", size=24,
                    align="center", color=DK),
            dict(id="folio", x=56, y=HO - 46, w=100, size=11, lh=14, font=MONO, ls=0.2, color=DK, runs=[("vi", "")])]
