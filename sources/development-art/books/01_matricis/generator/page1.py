from portable_paths import OUTPUT
"""Tabula VIII — Of an Outage Delayed by Authority (Rev 5 §8). Ink and rubric."""
import json
import math
import random
import sys

from core import Doc, catmull, path_len, point_at, offset_line, arc_pts, bezier
from marks import *
import cipher
from layout import box_height

W, H = 1000, 1600
PAPER, INK, RED = "#ebe1c8", "#1c1813", "#a3271b"
SEPIA = "#6d5f4b"
AX = 470  # the escalation axis
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 8


def styles():
    st = {}
    for c, col in (("ink", INK), ("red", RED), ("sep", SEPIA)):
        for k, wdt in (("core", 2.9), ("orn", 1.55), ("hair", 0.9), ("cip", 1.35)):
            st[f"{c}_{k}"] = {"fill": "none", "stroke": col, "stroke-width": str(wdt), "stroke-linecap": "round",
                              "stroke-linejoin": "round"}
        st[f"{c}_fill"] = {"fill": col, "stroke": "none"}
    st["fox_fill"] = {"fill": "#b89a6a", "stroke": "none", "opacity": "0.16"}
    return st


class XHand:
    """forwards to a Hand after transforming points (for rotated inscriptions)"""

    def __init__(self, h, tf):
        self.h, self.tf, self.rng = h, tf, h.rng

    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None):
        self.h.stroke([self.tf(p) for p in pts], weight, color, closed, amp)

    def dot(self, x, y, r, color="ink"):
        p = self.tf((x, y))
        self.h.dot(p[0], p[1], r, color)

    def ring(self, x, y, r, weight="orn", color="ink"):
        p = self.tf((x, y))
        self.h.ring(p[0], p[1], r, weight, color)

    def fill_poly(self, pts, color="ink"):
        self.h.fill_poly([self.tf(p) for p in pts], color)


def build(seed=SEED, keep=None, glosses=None):
    rng = random.Random(seed)
    doc = Doc(W, H, styles(), order=["fox_fill"] + [k for k in styles() if k != "fox_fill"])
    h = Hand(doc, rng, "ink", amp=0.42)

    # foxing
    for _ in range(140):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        doc.circle("fox_fill", x, y, rng.uniform(0.6, 3.2) ** 1.4)

    # ---------------------------------------------------------- page furniture
    h.stroke([(56, 58), (944, 58)], "orn", "ink")
    h.stroke([(56, 62), (944, 62)], "hair", "ink")
    band_x(h, (380, 131), (620, 131), 9, 12, "hair", "ink")
    asterisk(h, 370, 131, 6, 8, weight="hair", color="red")
    asterisk(h, 630, 131, 6, 8, weight="hair", color="red")

    # plate frame
    X0, Y0, X1, Y1 = 56, 222, 944, 1146
    h.stroke([(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)], "core", "ink", closed=True)
    h.stroke([(X0 + 7, Y0 + 7), (X1 - 7, Y0 + 7), (X1 - 7, Y1 - 7), (X0 + 7, Y1 - 7)], "hair", "ink", closed=True)
    for (cx, cy) in ((X0, Y0), (X1, Y0), (X0, Y1), (X1, Y1)):
        s = 13
        h.fill_poly([(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)], "ink")
        asterisk(h, cx, cy, 8.5, 8, rot_deg=22.5, weight="orn", color="red", centre=False)

    # marginal wards in the cipher hand, written up the left margin and down the right
    def vert(text, x, y_mid, size, up=True):
        wd = cipher.measure(text, size)
        if up:
            tf = lambda p: (x + (p[1] - 0), y_mid + wd / 2 - p[0])  # rotate -90
        else:
            tf = lambda p: (x - (p[1] - 0), y_mid - wd / 2 + p[0])  # rotate +90
        xh = XHand(h, lambda p: tf((p[0], p[1])))
        cipher.write(xh, text, 0, 0, size, rail=True)

    vert("a sketch prompts a claim and never replaces one", 40, (Y0 + Y1) / 2, 13, up=True)
    vert("data usefulness is not protocol efficacy", 960, (Y0 + Y1) / 2, 13, up=False)

    # ------------------------------------------------------------- the seal
    yN, yB, yG, yApex, yD, yF, yGr = 292, 340, 428, 574, 884, 980, 1036
    exec_h, exec_w = 150, 172

    # spine: NOC -> gate -> executive -> handoff -> dispatch -> crew -> break
    def spine(y0, y1, arrow=True):
        h.stroke([(AX, y0), (AX, y1)], "core", "ink")
        if arrow:
            arrowhead(h, (AX, y1), 90, 11, "ink", "core")

    # NOC: a cross-arm in the vèvè manner
    band_x(h, (AX - 92, yN), (AX - 30, yN), 10, 4, "hair", "ink", centre_dots=True)
    band_x(h, (AX + 30, yN), (AX + 92, yN), 10, 4, "hair", "ink", centre_dots=True)
    curl(h, AX - 92, yN, 180, 4, 9, 1.35, hand=1, weight="hair", color="ink")
    curl(h, AX + 92, yN, 0, 4, 9, 1.35, hand=-1, weight="hair", color="ink")
    sig_standing(h, AX, yN, 11, crown=True)
    spine(yN + 26, yG - 62)
    sig_gate(h, AX, yG, 122, 122)
    for sgn in (-1, 1):
        leaf(h, (AX + sgn * 15, yG), (AX + sgn * 62, yG), 15, "orn", "ink", 6)
        asterisk(h, AX + sgn * 70, yG, 4.5, 8, weight="hair", color="red", centre=False)
    spine(yG + 62, yApex - 54)
    sig_authority(h, AX, yApex + exec_h / 2, exec_w, exec_h)
    # handoff: the spine leaves the base of the triangle and waits on a ladder
    hy0, hy1 = yApex + exec_h + 30, yD - 34
    h.stroke([(AX, yApex + exec_h), (AX, hy0)], "core", "ink")
    band_x(h, (AX, hy0), (AX, hy1), 17, 6, "orn", "ink", centre_dots=False)
    for k in range(6):
        yy = hy0 + (k + 0.5) * (hy1 - hy0) / 6
        h.dot(AX, yy, 1.4, "red")
    h.stroke([(AX, hy1), (AX, yD - 25)], "core", "ink")
    arrowhead(h, (AX, yD - 25), 90, 11, "ink", "core")
    sig_standing(h, AX, yD, 11, crown=False)
    for sgn in (-1, 1):
        asterisk(h, AX + sgn * 64, yD - 2, 5, 8, weight="hair", color="ink")
    spine(yD + 25, yF - 26)
    sig_standing(h, AX, yF, 11, crown=False)
    spine(yF + 25, yGr - 6)

    # ground and the break
    sig_ground(h, 120, 880, yGr, 22)
    # the fibre itself, inside the ground, broken at the axis
    for (a, b) in ((120, AX - 16), (AX + 16, 880)):
        h.stroke([(a, yGr + 13), (b, yGr + 13)], "orn", "sep")
    sig_break(h, AX, yGr + 13, 15, "red")

    # the added route (rubric): leaves below NOC, sweeps around, arrives at dispatch
    route = catmull([(AX, yB), (AX + 70, yB + 6), (AX + 245, yB + 62), (AX + 352, yB + 182), (AX + 362, yB + 312),
                     (AX + 302, yB + 440), (AX + 168, yD - 12), (AX + 28, yD)], 22)
    h.stroke(route, "core", "red")
    arrowhead(h, route[-1], 180, 12, "red", "core")
    dotted(h, offset_line(route, -9), 9, 1.0, "red")
    fringe(h, route[6:-14], 11, 5.5, side=1, weight="hair", color="red")
    h.dot(AX, yB, 4.2, "red")
    h.ring(AX, yB, 7.5, "hair", "red")
    L = path_len(route)
    marks = []
    for frac in (0.40, 0.535, 0.67):
        p, t = point_at(route, L * frac)
        asterisk(h, p[0], p[1], 7.5, 8, weight="orn", color="red", centre=False)
        h.dot(p[0], p[1], 2.6, "red")
        marks.append(p)
    # leaves at the route's far side
    xs = [p[0] for p in route]
    i_far = xs.index(max(xs))
    pf = route[i_far]
    leaf(h, (pf[0] + 6, pf[1] - 4), (pf[0] + 52, pf[1] - 34), 14, "orn", "red", 6)
    leaf(h, (pf[0] + 6, pf[1] + 4), (pf[0] + 52, pf[1] + 34), 14, "orn", "red", 6)
    asterisk(h, pf[0] + 60, pf[1], 6, 8, weight="hair", color="red", centre=True)

    # unverified attribution: dashed pointer into the waiting handoff
    sig_pointer(h, (AX - 150, 838), (AX - 16, 808), "red")

    # rulers: diagnosis->dispatch (left), dispatch->restoration (right)
    def ruler(x, y0, y1, side):
        h.stroke([(x, y0), (x, y1)], "orn", "ink")
        n = int((y1 - y0) / 10)
        for i in range(n + 1):
            y = y0 + i * (y1 - y0) / n
            ln = 9 if i % 5 == 0 else 4.5
            h.stroke([(x, y), (x + side * ln, y)], "hair", "ink", amp=0.02)
        for y in (y0, y1):
            h.stroke([(x - 7, y), (x + 7, y)], "orn", "ink")
            asterisk(h, x, y - 9 if y == y0 else y + 9, 5.5, 8, weight="hair", color="ink")
            dotted(h, [(x + side * 14, y), (x + side * 40, y)], 6, 0.9, "ink", skip_ends=False)

    ruler(98, yN, yD, 1)
    ruler(904, yD, yGr, -1)

    # key band
    ky = 1100
    h.stroke([(X0 + 7, ky - 32), (X1 - 7, ky - 32)], "hair", "ink")
    key_x = [92, 300, 512, 722, 92, 300, 512, 722]
    key_y = [ky - 8, ky - 8, ky - 8, ky - 8, ky + 22, ky + 22, ky + 22, ky + 22]
    kx = iter(zip(key_x, key_y))
    x, y = next(kx); sig_standing(h, x, y, 6.5, orn=0)
    x, y = next(kx); sig_gate(h, x, y, 22, 22, orn=0)
    x, y = next(kx); sig_authority(h, x, y + 1, 22, 20, orn=0)
    x, y = next(kx); h.stroke(bezier((x - 12, y + 6), (x - 2, y + 6), (x + 2, y - 7), (x + 13, y - 7), 20), "core", "red")
    x, y = next(kx); sig_pointer(h, (x - 12, y + 5), (x + 13, y - 5), "red", 4, 3)
    x, y = next(kx); sig_substrate_small(h, x, y - 2, 13)
    x, y = next(kx); sig_break(h, x, y, 7, "red")
    x, y = next(kx); band_x(h, (x, y - 11), (x, y + 11), 9, 3, "hair", "ink", centre_dots=False)

    # glosses in the cipher hand, under the plate labels
    for (text, x, y, size, align) in (glosses or []):
        wdt = cipher.measure(text, size)
        x0 = x - wdt if align == "right" else x
        cipher.write(h, text, x0, y, size, weight="cip", color="sep", rail=False)

    # stars in mirrored pairs across the axis, vèvè-wise (seeded; clear of text and sigils)
    if keep is not None:
        def free(x, y, r, placed):
            if not (X0 + 24 < x < X1 - 24 and Y0 + 20 < y < 1010):
                return False
            if any(a - 8 < x < c + 8 and b - 8 < y < d + 8 for (a, b, c, d) in keep):
                return False
            return all((x - px) ** 2 + (y - py) ** 2 > (r + pr + 22) ** 2 for (px, py, pr) in placed)
        placed = []
        tries = 0
        while len(placed) < 44 and tries < 8000:
            tries += 1
            x, y = rng.uniform(X0 + 24, AX - 120), rng.uniform(Y0 + 20, 1010)
            r = rng.uniform(2.6, 5.0)
            xm = 2 * AX - x
            if free(x, y, r, placed) and free(xm, y, r, placed + [(x, y, r)]):
                n = rng.choice([6, 8, 8])
                rd = rng.uniform(0, 45)
                for xx in (x, xm):
                    placed.append((xx, y, r))
                    asterisk(h, xx, y, r, n, rot_deg=rd, weight="hair", color="sep", centre=True)

    # tail-pieces under the columns
    for cx in (268, 732):
        band_x(h, (cx - 46, 1522), (cx + 46, 1522), 7, 6, "hair", "sep", centre_dots=True)
        curl(h, cx - 46, 1522, 180, 3, 6, 1.3, hand=1, weight="hair", color="sep")
        curl(h, cx + 46, 1522, 0, 3, 6, 1.3, hand=-1, weight="hair", color="sep")

    # folio device: the mark
    sig_mark(h, 500, 1560, 11, "red", "orn")

    return doc, dict(route=[list(p) for p in route[::6]], marks=marks, ky=ky, key_x=key_x, key_y=key_y, yN=yN, yG=yG, yApex=yApex, yD=yD, yF=yF,
                     yGr=yGr, exec_h=exec_h)


if __name__ == "__main__":
    doc, meta = build()
    open(f"{OUTPUT}/p1_plate.svg", "w").write(doc.svg())
    json.dump(meta, open(f"{OUTPUT}/p1_meta.json", "w"))
    print("ok")
