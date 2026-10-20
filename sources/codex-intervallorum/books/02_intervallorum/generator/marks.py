"""Hands (ink / cornmeal grain / plotter pen), vèvè-grammar ornament, and the
sigils: each Revision 3 sketching mark as a stable core with seeded ornament."""
import math
import random

from shapely.geometry import Polygon, Point

from core import (Wobble, arc_pts, spiral_pts, curl_pts, resample, lattice, hatch_lines, tri_pts,
                  vesica, dist, lerp, rot, offset_line, point_at, path_len, bezier, catmull)


# ------------------------------------------------------------------ hands --

class Hand:
    """Routes strokes to style buckets. weight in {'core','orn','hair'}, color in {'ink','red',...}"""

    def __init__(self, doc, rng, mode="ink", amp=0.5, grain=None):
        self.doc, self.rng, self.mode = doc, rng, mode
        self.wob = Wobble(rng, amp)
        self.grain_cfg = grain or {}

    def key(self, weight, color):
        return f"{color}_{weight}"

    # ---- strokes
    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None):
        if len(pts) < 2:
            return
        if closed:
            pts = list(pts) + [pts[0]]
        if self.mode == "grain":
            self._grain_stroke(self.wob(pts, amp), weight, color)
        else:
            self.doc.poly(self.key(weight, color), self.wob(pts, amp))

    def _grain_stroke(self, pts, weight, color):
        cfg = self.grain_cfg
        dens, spread = cfg.get(weight, (1.6, 1.0))
        rs = resample(pts, 1.0 / dens)
        for i, p in enumerate(rs):
            j0, j1 = max(0, i - 1), min(len(rs) - 1, i + 1)
            tx, ty = rs[j1][0] - rs[j0][0], rs[j1][1] - rs[j0][1]
            L = math.hypot(tx, ty) or 1
            o = self.rng.gauss(0, spread)
            x, y = p[0] - ty / L * o + self.rng.gauss(0, 0.25), p[1] + tx / L * o + self.rng.gauss(0, 0.25)
            size = self.rng.choices(("s", "m", "l"), weights=cfg.get("sizes", (5, 3, 1)))[0]
            self.doc.grain(f"{color}_g{size}", x, y)
        # a few strays
        for _ in range(int(len(rs) * cfg.get("stray", 0.04))):
            p = self.rng.choice(rs)
            self.doc.grain(f"{color}_gs", p[0] + self.rng.gauss(0, spread * 4), p[1] + self.rng.gauss(0, spread * 4))

    def dot(self, x, y, r, color="ink"):
        if self.mode == "grain":
            n = int(r * r * 3.2) + 4
            for _ in range(n):
                a = self.rng.uniform(0, 6.283)
                rr = r * math.sqrt(self.rng.random())
                size = self.rng.choices(("s", "m", "l"), weights=(2, 3, 2))[0]
                self.doc.grain(f"{color}_g{size}", x + rr * math.cos(a), y + rr * math.sin(a))
            self.stroke(arc_pts(x, y, r, 0, 360, 36), "hair", color)
        else:
            self.doc.circle(f"{color}_fill", x, y, r)

    def fill_poly(self, pts, color="ink"):
        if self.mode == "grain":
            poly = Polygon(pts)
            minx, miny, maxx, maxy = poly.bounds
            n = int(poly.area * 0.9)
            k = 0
            while k < n:
                x, y = self.rng.uniform(minx, maxx), self.rng.uniform(miny, maxy)
                if poly.contains(Point(x, y)):
                    self.doc.grain(f"{color}_g{self.rng.choice('sml')}", x, y)
                    k += 1
            self.stroke(pts, "hair", color, closed=True)
        else:
            self.doc.poly(f"{color}_fill", pts, closed=True)

    def ring(self, x, y, r, weight="orn", color="ink"):
        self.stroke(arc_pts(x, y, r, 0, 360, max(16, int(r * 2.2))), weight, color, amp=min(0.4, r * 0.05))


# --------------------------------------------------------------- ornament --

def asterisk(h, cx, cy, r, n=8, rot_deg=None, weight="orn", color="ink", tipdots=False, centre=True):
    rot_deg = h.rng.uniform(0, 45) if rot_deg is None else rot_deg
    for i in range(n // 2):
        a = math.radians(rot_deg + i * 360 / n)
        h.stroke([(cx - r * math.cos(a), cy - r * math.sin(a)), (cx + r * math.cos(a), cy + r * math.sin(a))],
                 weight, color, amp=0.15)
    if centre:
        h.dot(cx, cy, max(0.9, r * 0.16), color)
    if tipdots:
        for i in range(n):
            a = math.radians(rot_deg + i * 360 / n)
            h.dot(cx + r * 1.18 * math.cos(a), cy + r * 1.18 * math.sin(a), max(0.7, r * 0.09), color)


def curl(h, x0, y0, ang, stem, r, turns=1.25, hand=1, weight="orn", color="ink", end_dot=True):
    pts = curl_pts(x0, y0, ang, stem, r, turns, hand)
    h.stroke(pts, weight, color)
    if end_dot:
        h.dot(pts[-1][0], pts[-1][1], max(0.9, r * 0.13), color)
    return pts


def dotted(h, pts, spacing, r, color="ink", skip_ends=True):
    L = path_len(pts)
    n = int(L / spacing)
    for i in range(1 if skip_ends else 0, n + (0 if skip_ends else 1)):
        p, _ = point_at(pts, i * L / max(1, n))
        h.dot(p[0], p[1], r, color)


def fringe(h, pts, spacing, length, side=1, weight="hair", color="ink", lean=0.0):
    L = path_len(pts)
    n = int(L / spacing)
    for i in range(1, n):
        p, t = point_at(pts, i * L / n)
        nx, ny = -t[1] * side, t[0] * side
        h.stroke([p, (p[0] + nx * length + t[0] * lean, p[1] + ny * length + t[1] * lean)], weight, color, amp=0.1)


def arrowhead(h, tip, ang_deg, size, color="ink", weight="core", filled=False):
    a = math.radians(ang_deg)
    l = (tip[0] - size * math.cos(a - 0.42), tip[1] - size * math.sin(a - 0.42))
    r_ = (tip[0] - size * math.cos(a + 0.42), tip[1] - size * math.sin(a + 0.42))
    if filled:
        h.fill_poly([l, tip, r_, lerp(tip, lerp(l, r_, 0.5), 0.72)], color)
    else:
        h.stroke([l, tip, r_], weight, color, amp=0.1)


def lattice_fill(h, pts, step, marker="x", weight="hair", color="ink", ang=45, marker_color=None, msize=0.3,
                 outline=True):
    poly = Polygon(pts)
    lines, cents = lattice(poly, step, ang)
    for ln in lines:
        h.stroke(ln, weight, color, amp=0.15)
    mc = marker_color or color
    for (x, y) in cents:
        m = marker if marker != "mixed" else h.rng.choice(["x", "x", "dot", "star", "none"])
        s = step * msize
        if m == "x":
            h.stroke([(x - s, y - s), (x + s, y + s)], "hair", mc, amp=0.05)
            h.stroke([(x + s, y - s), (x - s, y + s)], "hair", mc, amp=0.05)
        elif m == "dot":
            h.dot(x, y, max(0.8, step * 0.07), mc)
        elif m == "star":
            asterisk(h, x, y, s * 1.1, 8, weight="hair", color=mc, centre=False)
    if outline:
        h.stroke(pts, weight if weight != "hair" else "orn", color, closed=True)
    return cents


def leaf(h, p0, p1, w, weight="orn", color="ink", veins=7):
    top, bot = vesica(p0, p1, w)
    h.stroke(top, weight, color)
    h.stroke(bot, weight, color)
    h.stroke([p0, p1], "hair", color, amp=0.2)
    for i in range(1, veins):
        t = i / veins
        a = lerp(p0, p1, t)
        b = top[int(t * (len(top) - 1))]
        c = bot[int(t * (len(bot) - 1))]
        h.stroke([a, lerp(a, b, 0.8)], "hair", color, amp=0.05)
        h.stroke([a, lerp(a, c, 0.8)], "hair", color, amp=0.05)


def band_x(h, p0, p1, width, cells, weight="orn", color="ink", centre_dots=True):
    """a double-ruled band with an X in each cell (vèvè cross-arm grammar)"""
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    nx, ny = -math.sin(ang) * width / 2, math.cos(ang) * width / 2
    a0, a1 = (p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny)
    b0, b1 = (p0[0] - nx, p0[1] - ny), (p1[0] - nx, p1[1] - ny)
    h.stroke([a0, a1, b1, b0], weight, color, closed=True)
    for i in range(cells + 1):
        t = i / cells
        if 0 < i < cells:
            h.stroke([lerp(a0, a1, t), lerp(b0, b1, t)], "hair", color, amp=0.1)
    for i in range(cells):
        t0, t1 = i / cells, (i + 1) / cells
        h.stroke([lerp(a0, a1, t0), lerp(b0, b1, t1)], "hair", color, amp=0.1)
        h.stroke([lerp(b0, b1, t0), lerp(a0, a1, t1)], "hair", color, amp=0.1)
        if centre_dots:
            c = lerp(lerp(a0, a1, (t0 + t1) / 2), lerp(b0, b1, (t0 + t1) / 2), 0.5)
            h.dot(c[0], c[1], max(0.8, width * 0.07), color)


# ----------------------------------------------------------------- sigils --
# Each takes (h, centre, size, ...) and returns ports for connections.

def sig_standing(h, cx, cy, r, orn=1.0, crown=True, color="ink"):
    """filled dot: an interest-bearing being with standing"""
    rng = h.rng
    h.dot(cx, cy, r, color)
    if orn <= 0:
        return {"top": (cx, cy - r), "bot": (cx, cy + r), "l": (cx - r, cy), "r": (cx + r, cy)}
    R = r * 2.05
    h.ring(cx, cy, R, "hair", color)
    dotted(h, arc_pts(cx, cy, R * 1.32, 0, 360, 90), R * 0.36, max(0.9, r * 0.09), color, skip_ends=False)
    if crown:
        k = rng.choice([3, 5])
        for i in range(k):
            a = -90 + (i - (k - 1) / 2) * (100 / max(1, k - 1))
            ar = math.radians(a)
            p0 = (cx + R * math.cos(ar), cy + R * math.sin(ar))
            p1 = (cx + R * 1.95 * math.cos(ar), cy + R * 1.95 * math.sin(ar))
            h.stroke([p0, p1], "hair", color)
            asterisk(h, p1[0], p1[1], r * 0.55, 8, weight="hair", color=color)
    # side scrolls
    hand = 1
    for sgn in (-1, 1):
        x0 = cx + sgn * R
        curl(h, x0, cy, 0 if sgn > 0 else 180, R * 0.55, R * 0.42, 1.3, hand=-sgn, weight="hair", color=color)
    return {"top": (cx, cy - R), "bot": (cx, cy + R), "l": (cx - R, cy), "r": (cx + R, cy)}


def sig_candidate(h, cx, cy, r, color="ink", orn=1.0):
    """hollow dot: standing uncertain"""
    h.ring(cx, cy, r, "core", color)
    if orn > 0:
        for k, rr in enumerate((r * 1.7, r * 2.35)):
            seg = arc_pts(cx, cy, rr, 0, 360, 120)
            # broken ring
            n = len(seg)
            on = True
            run = []
            for i, p in enumerate(seg):
                if (i // (6 + 3 * k)) % 2 == 0:
                    run.append(p)
                else:
                    if len(run) > 1:
                        h.stroke(run, "hair", color, amp=0.1)
                    run = []
            if len(run) > 1:
                h.stroke(run, "hair", color, amp=0.1)
        for i in range(4):
            a = math.radians(45 + i * 90)
            h.ring(cx + r * 3.0 * math.cos(a), cy + r * 3.0 * math.sin(a), r * 0.28, "hair", color)
    return {"top": (cx, cy - r), "bot": (cx, cy + r)}


def sig_gate(h, cx, cy, w, ht, vertical=True, color="ink", red="red", orn=1.0):
    """required gate (bowtie with a dot). vertical=True: flow runs top->bottom through the knot."""
    rng = h.rng
    if vertical:
        A = [(cx - w / 2, cy - ht / 2), (cx + w / 2, cy - ht / 2), (cx, cy)]
        B = [(cx - w / 2, cy + ht / 2), (cx + w / 2, cy + ht / 2), (cx, cy)]
    else:
        A = [(cx - w / 2, cy - ht / 2), (cx - w / 2, cy + ht / 2), (cx, cy)]
        B = [(cx + w / 2, cy - ht / 2), (cx + w / 2, cy + ht / 2), (cx, cy)]
    if orn > 0:
        for T in (A, B):
            inset = Polygon(T).buffer(-w * 0.045)
            if not inset.is_empty and inset.geom_type == "Polygon":
                lattice_fill(h, list(inset.exterior.coords)[:-1], w * 0.105, marker="mixed", weight="hair",
                             color=color, outline=False, msize=0.26)
    h.stroke(A, "core", color, closed=True)
    h.stroke(B, "core", color, closed=True)
    h.dot(cx, cy, w * 0.075, red)
    if orn > 0:
        # wing tips: asterisks; scrolls off the outer corners
        corners = [A[0], A[1], B[0], B[1]]
        for i, c in enumerate(corners):
            sx = -1 if c[0] < cx else 1
            sy = -1 if c[1] < cy else 1
            if vertical:
                curl(h, c[0], c[1], 0 if sx > 0 else 180, w * 0.16, w * 0.11, 1.35, hand=(sx * sy), weight="hair",
                     color=color)
            asterisk(h, c[0] + sx * w * 0.02, c[1] + sy * w * 0.02, w * 0.055, 8, weight="hair", color=color,
                     centre=False)
        # the knot gets a small collar
        h.ring(cx, cy, w * 0.14, "hair", red)
    if vertical:
        return {"top": (cx, cy - ht / 2), "bot": (cx, cy + ht / 2)}
    return {"l": (cx - w / 2, cy), "r": (cx + w / 2, cy)}


def sig_authority(h, cx, cy, w, ht, color="ink", orn=1.0, horns=True):
    """triangle: centre of decision, contestable"""
    T = tri_pts(cx, cy, w, ht, up=True)
    apex, br, bl = T
    if orn > 0:
        inner = Polygon(T).buffer(-w * 0.075)
        if inner.geom_type == "Polygon":
            ip = list(inner.exterior.coords)[:-1]
            lattice_fill(h, ip, w * 0.085, marker="mixed", weight="hair", color=color, msize=0.28)
        # nested triangle, thin
        T2 = tri_pts(cx, cy + ht * 0.02, w * 1.16, ht * 1.14)
        h.stroke(T2, "hair", color, closed=True)
        # base rule extended to stars
        bx0, bx1 = cx - w * 0.82, cx + w * 0.82
        by = cy + ht / 2 + ht * 0.09
        h.stroke([(bx0, by), (bx1, by)], "orn", color)
        dotted(h, [(bx0, by + ht * 0.06), (bx1, by + ht * 0.06)], w * 0.06, max(0.8, w * 0.009), color)
        asterisk(h, bx0, by, w * 0.055, 8, weight="hair", color=color)
        asterisk(h, bx1, by, w * 0.055, 8, weight="hair", color=color)
        for sgn in (-1, 1):
            curl(h, cx + sgn * w * 0.58, by, 90, ht * 0.05, w * 0.07, 1.3, hand=-sgn, weight="hair", color=color)
        if horns:
            hr = w * 0.2
            cyh = apex[1] - ht * 0.03 - hr * 0.98
            outer = arc_pts(cx, cyh, hr, -42, 222, 70)
            inner = arc_pts(cx, cyh - hr * 0.34, hr * 0.8, -36, 216, 70)
            h.fill_poly(outer + inner[::-1], color)
            asterisk(h, cx, cyh - hr * 0.25, hr * 0.26, 8, weight="orn", color="red", centre=True)
        for v in T:
            pass
    h.stroke(T, "core", color, closed=True)
    return {"top": apex, "bot": (cx, cy + ht / 2), "l": bl, "r": br}


def sig_mark(h, cx, cy, r, color="red", weight="core", branch=True, turns=1.75, hand=1, ang0=90):
    """Revision 5's mark: open, branching spiral; no central dot, open outer end, one branch."""
    pts = []
    n = 200
    a0 = math.radians(ang0)
    for i in range(n + 1):
        t = i / n
        a = a0 + hand * t * turns * 2 * math.pi
        rr = r * (0.16 + 0.84 * t)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    h.stroke(pts, weight, color)
    if branch:
        # a short branch leaving the outer turn, curving away to its own open end
        s = path_len(pts)
        p, t = point_at(pts, s * 0.72)
        nx, ny = -t[1] * hand, t[0] * hand
        q1 = (p[0] + t[0] * r * 0.35, p[1] + t[1] * r * 0.35)
        q2 = (p[0] + t[0] * r * 0.55 - nx * r * 0.42, p[1] + t[1] * r * 0.55 - ny * r * 0.42)
        q3 = (p[0] + t[0] * r * 0.45 - nx * r * 0.75, p[1] + t[1] * r * 0.45 - ny * r * 0.75)
        h.stroke(bezier(p, q1, q2, q3, 30), weight, color)
    return pts


def sig_ground(h, x0, x1, y, depth, color="ink", step=7.0):
    """generative substrate: conditions beneath. thick rule, hatching below, roots."""
    rng = h.rng
    h.stroke([(x0, y), (x1, y)], "core", color)
    h.stroke([(x0, y + 3.2), (x1, y + 3.2)], "hair", color)
    x = x0 + 3
    while x < x1 - 2:
        ln = depth * rng.uniform(0.55, 1.0)
        h.stroke([(x, y + 5), (x - ln * 0.55, y + 5 + ln)], "hair", color, amp=0.1)
        x += step * rng.uniform(0.8, 1.2)
    # a few roots
    for _ in range(int((x1 - x0) / 70)):
        rx = rng.uniform(x0 + 20, x1 - 20)
        pts = [(rx, y + 4)]
        for k in range(5):
            pts.append((pts[-1][0] + rng.uniform(-6, 6), pts[-1][1] + depth * 0.32))
        h.stroke(catmull(pts, 6), "hair", color)
        h.dot(pts[-1][0], pts[-1][1], 1.1, color)


def sig_break(h, x, y, s, color="red"):
    """a cut: struck X with star-terminals"""
    for a in (45, 135):
        r_ = math.radians(a)
        p0 = (x - s * math.cos(r_), y - s * math.sin(r_))
        p1 = (x + s * math.cos(r_), y + s * math.sin(r_))
        h.stroke([p0, p1], "core", color, amp=0.2)
        asterisk(h, p0[0] + (p0[0] - x) * 0.25, p0[1] + (p0[1] - y) * 0.25, s * 0.28, 8, weight="hair", color=color)
        asterisk(h, p1[0] + (p1[0] - x) * 0.25, p1[1] + (p1[1] - y) * 0.25, s * 0.28, 8, weight="hair", color=color)
    h.ring(x, y, s * 0.38, "hair", color)


def sig_regulation(h, cx, cy, r, color="ink", orn=1.0):
    """closed loop: returns to set point"""
    pts = arc_pts(cx, cy, r, -60, 250, 80)
    h.stroke(pts, "core", color)
    end = pts[-1]
    a = math.degrees(math.atan2(pts[-1][1] - pts[-3][1], pts[-1][0] - pts[-3][0]))
    arrowhead(h, end, a, r * 0.38, color)
    if orn > 0:
        # dial ticks and a set-point star
        for i in range(24):
            ang = math.radians(i * 15)
            r0, r1 = r * 1.18, r * (1.32 if i % 3 == 0 else 1.25)
            h.stroke([(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)),
                      (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))], "hair", color, amp=0.03)
        sp = arc_pts(cx, cy, r * 1.62, -60, -60, 1)[0]
        asterisk(h, sp[0], sp[1], r * 0.2, 8, weight="hair", color=color)
        h.ring(cx, cy, r * 0.42, "hair", color)
    return {}


def sig_bottleneck(h, cx, cy, s, color="ink", red="red", orn=1.0):
    """cut vertex: everything passes one point; fails the bypass test"""
    L = [(cx - s, cy - s * 0.55), (cx - s, cy + s * 0.55)]
    R = [(cx + s, cy - s * 0.55), (cx + s, cy + s * 0.55)]
    for p in L + R:
        h.stroke([p, (cx, cy)], "orn", color)
        h.dot(p[0], p[1], s * 0.11, color)
    h.stroke(L, "orn", color)
    h.stroke(R, "orn", color)
    if orn > 0:
        for grp, sx in ((L, -1), (R, 1)):
            tri = [grp[0], grp[1], (cx + sx * s * 0.22, cy)]
            lattice_fill(h, tri, s * 0.2, marker="x", weight="hair", color=color, outline=False)
            for p in grp:
                asterisk(h, p[0] + sx * s * 0.28, p[1], s * 0.13, 8, weight="hair", color=color)
    h.dot(cx, cy, s * 0.16, red)
    h.ring(cx, cy, s * 0.27, "hair", red)
    return {}


def sig_branch(h, x0, x1, y, color="ink", red="red", struck=False, orn=1.0):
    """additive change (branch, old kept) or substitutive (old route struck out)"""
    xm = x0 + (x1 - x0) * 0.34
    if struck:
        h.stroke([(x0, y), (xm, y)], "core", color)
        # dashed remainder
        x = xm
        while x < x1:
            h.stroke([(x + 2, y), (min(x1, x + 7), y)], "orn", color, amp=0.05)
            x += 11
        sx = xm + (x1 - xm) * 0.45
        s = (x1 - x0) * 0.1
        h.stroke([(sx - s, y - s), (sx + s, y + s)], "core", color)
        h.stroke([(sx + s, y - s), (sx - s, y + s)], "core", color)
    else:
        h.stroke([(x0, y), (x1, y)], "core", color)
    br = bezier((xm, y), (xm + (x1 - x0) * 0.24, y), (x1 - (x1 - x0) * 0.3, y - (x1 - x0) * 0.32),
                (x1, y - (x1 - x0) * 0.34), 40)
    h.stroke(br, "core", red)
    if orn > 0:
        asterisk(h, x1 + 4, y - (x1 - x0) * 0.34, (x1 - x0) * 0.06, 8, weight="hair", color=red)
        asterisk(h, x0 - 4, y, (x1 - x0) * 0.05, 8, weight="hair", color=color)
        if not struck:
            asterisk(h, x1 + 4, y, (x1 - x0) * 0.05, 8, weight="hair", color=color)
        dotted(h, offset_line(br, -(x1 - x0) * 0.05), (x1 - x0) * 0.06, 0.9, red)
    return {}


def sig_reflexive(h, cx, cy, s, color="ink", red="red", orn=1.0):
    """map -> world, and the map moves it"""
    bx, by, bw, bh = cx - s, cy - s * 0.32, s * 0.62, s * 0.62
    box = [(bx, by), (bx + bw, by), (bx + bw, by + bh), (bx, by + bh)]
    if orn > 0:
        lattice_fill(h, box, bw * 0.24, marker="dot", weight="hair", color=color, outline=False)
    h.stroke(box, "core", color, closed=True)
    ax0, ax1 = bx + bw + s * 0.08, cx + s * 0.72
    h.stroke([(ax0, cy), (ax1, cy)], "orn", color)
    arrowhead(h, (ax1, cy), 0, s * 0.16, color, "orn")
    h.dot(cx + s * 0.88, cy, s * 0.11, color)
    ret = bezier((cx + s * 0.88, cy - s * 0.16), (cx + s * 0.88, cy - s * 0.95), (bx + bw / 2, cy - s * 1.0),
                 (bx + bw / 2, by - s * 0.06), 50)
    h.stroke(ret, "core", red)
    a = math.degrees(math.atan2(ret[-1][1] - ret[-3][1], ret[-1][0] - ret[-3][0]))
    arrowhead(h, ret[-1], a, s * 0.16, red, "orn")
    if orn > 0:
        dotted(h, offset_line(ret, s * 0.09), s * 0.09, 0.8, red)
    return {}


def sig_invariant(h, cx, cy, s, color="ink", orn=1.0):
    """hard walls, one door"""
    x0, x1 = cx - s * 0.7, cx + s * 0.55
    y0, y1 = cy - s * 0.6, cy + s * 0.6
    h.stroke([(x1, y0), (x0, y0), (x0, y1), (x1, y1)], "core", color)
    h.stroke([(x1, y1), (x1, cy + s * 0.2)], "core", color)
    h.stroke([(x1, y0), (x1, cy - s * 0.2)], "core", color)
    if orn > 0:
        wall = Polygon([(x0 - s * 0.12, y0 - s * 0.12), (x1 + s * 0.02, y0 - s * 0.12), (x1 + s * 0.02, y0),
                        (x0, y0), (x0, y1), (x1 + s * 0.02, y1), (x1 + s * 0.02, y1 + s * 0.12),
                        (x0 - s * 0.12, y1 + s * 0.12)])
        for ln in hatch_lines(wall, s * 0.07, 60):
            h.stroke(ln, "hair", color, amp=0.05)
        for yy in (cy - s * 0.2, cy + s * 0.2):
            asterisk(h, x1 + s * 0.16, yy, s * 0.09, 8, weight="hair", color=color)
    return {}


def sig_boundary(h, cx, cy, r, color="ink", orn=1.0):
    """dashed circle: a commons or institution"""
    seg = arc_pts(cx, cy, r, 0, 360, 160)
    run = []
    for i, p in enumerate(seg):
        if (i // 7) % 2 == 0:
            run.append(p)
        else:
            if len(run) > 1:
                h.stroke(run, "orn", color, amp=0.1)
            run = []
    if len(run) > 1:
        h.stroke(run, "orn", color, amp=0.1)
    h.dot(cx - r * 0.33, cy + r * 0.15, r * 0.14, color)
    h.dot(cx + r * 0.3, cy - r * 0.22, r * 0.14, color)
    if orn > 0:
        h.ring(cx, cy, r * 1.22, "hair", color)
        for i in range(4):
            a = math.radians(i * 90)
            asterisk(h, cx + r * 1.22 * math.cos(a), cy + r * 1.22 * math.sin(a), r * 0.13, 8, weight="hair",
                     color=color)
    return {}


def sig_substrate_small(h, cx, cy, s, color="ink"):
    h.stroke([(cx - s, cy), (cx + s, cy)], "core", color)
    x = cx - s + 3
    while x < cx + s:
        h.stroke([(x, cy + 2.5), (x - s * 0.18, cy + 2.5 + s * 0.32)], "hair", color, amp=0.05)
        x += s * 0.16
    h.dot(cx, cy - s * 0.25, s * 0.1, color)
    return {}


def sig_pointer(h, p0, p1, color="red", dash=7, gap=5):
    """dashed pointer: an unverified attribution"""
    L = dist(p0, p1)
    n = int(L / (dash + gap))
    for i in range(n):
        a = lerp(p0, p1, i * (dash + gap) / L)
        b = lerp(p0, p1, min(1, (i * (dash + gap) + dash) / L))
        h.stroke([a, b], "orn", color, amp=0.05)
    ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    arrowhead(h, p1, ang, 11, color, "orn")
    h.ring(p0[0], p0[1], 4.5, "hair", color)


class XHand:
    """forwards to a Hand after transforming points (rotated or curved inscriptions)"""

    def __init__(self, h, tf):
        self.h, self.tf, self.rng = h, tf, h.rng

    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None):
        if closed:
            pts = list(pts) + [pts[0]]
        # densify so curved transforms bend straight segments
        from core import resample
        if len(pts) >= 2:
            pts = resample(pts, 2.0)
        self.h.stroke([self.tf(p) for p in pts], weight, color, False, amp)

    def dot(self, x, y, r, color="ink"):
        p = self.tf((x, y))
        self.h.dot(p[0], p[1], r, color)

    def ring(self, x, y, r, weight="orn", color="ink"):
        p = self.tf((x, y))
        self.h.ring(p[0], p[1], r, weight, color)

    def fill_poly(self, pts, color="ink"):
        self.h.fill_poly([self.tf(p) for p in pts], color)


def write_ring(h, text, cx, cy, r_base, a_start, size, color="ink", weight="cip", rail=False):
    """cipher written clockwise round a circle, glyph tops outward. returns end angle (deg)"""
    import cipher

    def tf(p):
        x, y = p
        ang = math.radians(a_start) + x / r_base
        rr = r_base - y
        return (cx + rr * math.cos(ang), cy + rr * math.sin(ang))

    w = cipher.write(XHand(h, tf), text, 0, 0, size, weight=weight, color=color, rail=rail)
    return a_start + math.degrees(w / r_base)


def ring_x(h, cx, cy, r_out, r_in, cells, weight="hair", color="ink", dots=True):
    """a circular band divided into cells, each with an X"""
    h.stroke(arc_pts(cx, cy, r_out, 0, 360, 180), weight, color)
    h.stroke(arc_pts(cx, cy, r_in, 0, 360, 180), weight, color)
    for i in range(cells):
        a0 = 2 * math.pi * i / cells
        a1 = 2 * math.pi * (i + 1) / cells
        p = lambda r, a: (cx + r * math.cos(a), cy + r * math.sin(a))
        h.stroke([p(r_in, a0), p(r_out, a0)], "hair", color, amp=0.05)
        h.stroke([p(r_in, a0), p(r_out, a1)], "hair", color, amp=0.05)
        h.stroke([p(r_out, a0), p(r_in, a1)], "hair", color, amp=0.05)
        if dots:
            am = (a0 + a1) / 2
            q = p((r_in + r_out) / 2, am)
            h.dot(q[0], q[1], max(0.7, (r_out - r_in) * 0.08), color)
