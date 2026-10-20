"""Core drawing kit for the Clavicula Matricis plates.

Everything is plain geometry -> SVG path data. Strokes that share a style are
bucketed into one <path> so the files stay small.
"""
import math
import random

from shapely.geometry import Polygon, LineString, MultiLineString, Point
from shapely.geometry.base import BaseGeometry


def f(v):
    return f"{v:.1f}"


# ---------------------------------------------------------------- document --

def num(v):
    t = f"{v:.1f}"
    if t.endswith(".0"):
        t = t[:-2]
    if t == "-0":
        t = "0"
    if t.startswith("0."):
        t = t[1:]
    elif t.startswith("-0."):
        t = "-" + t[2:]
    return t


def pair(x, y):
    a, b = num(x), num(y)
    return a + ("" if b.startswith("-") else ",") + b


class Doc:
    def __init__(self, w, h, styles, order=None, bg=None):
        """styles: key -> dict of SVG attributes (stroke, fill, stroke-width...)"""
        self.w, self.h = w, h
        self.styles = styles
        self.order = order or list(styles.keys())
        self.d = {k: [] for k in styles}
        self.extra_before = []
        self.extra_after = []
        self.bg = bg

    def poly(self, key, pts, closed=False):
        if len(pts) < 2:
            return
        self.d[key].append(("P", [(round(x, 1), round(y, 1)) for x, y in pts], closed))

    def line(self, key, x1, y1, x2, y2):
        self.poly(key, [(x1, y1), (x2, y2)])

    def circle(self, key, x, y, r):
        self.d[key].append(("S", f"M{pair(x - r, y)}a{num(r)},{num(r)} 0 1,0 {num(2 * r)},0a{num(r)},{num(r)} 0 1,0 {num(-2 * r)},0Z"))

    def grain(self, key, x, y):
        self.d[key].append(("G", round(x, 1), round(y, 1)))

    def raw_d(self, key, d):
        self.d[key].append(("S", d))

    def _d(self, items):
        out = []
        cur = None  # current point for relative grain moves
        for it in items:
            if it[0] == "G":
                x, y = it[1], it[2]
                if cur is None:
                    out.append(f"M{pair(x, y)}h.01")
                    cur = (x, y)
                else:
                    dx, dy = round(x - cur[0], 1), round(y - cur[1], 1)
                    out.append(f"m{pair(dx, dy)}h.01")
                    cur = (cur[0] + dx, cur[1] + dy)
                cur = (cur[0] + 0.01, cur[1])
            elif it[0] == "P":
                pts, closed = it[1], it[2]
                seg = [f"M{pair(*pts[0])}l"]
                px, py = pts[0]
                rel = []
                for x, y in pts[1:]:
                    rel.append(pair(x - px, y - py))
                    px, py = x, y
                seg.append(" ".join(rel).replace(" -", "-"))
                if closed:
                    seg.append("Z")
                out.append("".join(seg))
                cur = (px, py) if not closed else pts[0]
            else:
                out.append(it[1])
                cur = None
        return "".join(out)

    def body(self):
        out = list(self.extra_before)
        for k in self.order:
            if not self.d[k]:
                continue
            attrs = " ".join(f'{a}="{v}"' for a, v in self.styles[k].items())
            out.append(f'<path {attrs} d="{self._d(self.d[k])}"/>')
        out.extend(self.extra_after)
        return "\n".join(out)

    def svg(self):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}">']
        if self.bg:
            out.append(f'<rect width="{self.w}" height="{self.h}" fill="{self.bg}"/>')
        out.extend(self.extra_before)
        for k in self.order:
            if not self.d[k]:
                continue
            attrs = " ".join(f'{a}="{v}"' for a, v in self.styles[k].items())
            out.append(f'<path {attrs} d="{self._d(self.d[k])}"/>')
        out.extend(self.extra_after)
        out.append("</svg>")
        return "\n".join(out)


# ------------------------------------------------------------- geometry ----

def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def rot(p, ang, c=(0, 0)):
    s, co = math.sin(ang), math.cos(ang)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * co - y * s, c[1] + x * s + y * co)


def arc_pts(cx, cy, r, a0, a1, n=None, ry=None):
    """degrees, y-down screen coords"""
    ry = r if ry is None else ry
    n = n or max(8, int(abs(a1 - a0) / 4))
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def spiral_pts(cx, cy, r_out, r_in, a_out, turns, hand=1, n=None):
    """from the outer end inward. angles in degrees."""
    n = n or int(60 * turns) + 10
    pts = []
    for i in range(n + 1):
        t = i / n
        a = math.radians(a_out + hand * 360 * turns * t)
        r = r_out + (r_in - r_out) * t
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def curl_pts(x0, y0, ang, stem, r, turns=1.3, hand=1, n=None):
    """A stem leaving (x0,y0) at angle `ang` (deg) that ends in an inward scroll."""
    a = math.radians(ang)
    dx, dy = math.cos(a), math.sin(a)
    px, py = x0 + dx * stem, y0 + dy * stem
    nx, ny = -dy * hand, dx * hand          # normal toward the curl side
    cx, cy = px + nx * r, py + ny * r
    phi0 = math.degrees(math.atan2(py - cy, px - cx))
    pts = [(x0, y0)] if stem > 0 else []
    pts += spiral_pts(cx, cy, r, r * 0.16, phi0, turns, hand=hand, n=n)
    return pts


def resample(pts, step):
    out = [pts[0]]
    carry = 0.0
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        L = dist(a, b)
        if L == 0:
            continue
        t = step - carry
        while t <= L:
            out.append(lerp(a, b, t / L))
            t += step
        carry = L - (t - step)
    if dist(out[-1], pts[-1]) > 0.3:
        out.append(pts[-1])
    return out


class Wobble:
    """Smooth hand tremor: perpendicular offset from a sum of sines along arc length."""

    def __init__(self, rng, amp=0.6, wl=(22, 61)):
        self.rng, self.amp, self.wl = rng, amp, wl

    def __call__(self, pts, amp=None, step=3.0):
        amp = self.amp if amp is None else amp
        if amp <= 0 or len(pts) < 2:
            return pts
        rs = resample(pts, step)
        ph = [self.rng.uniform(0, 6.283) for _ in range(3)]
        wl = [self.rng.uniform(*self.wl) for _ in range(3)]
        out = []
        s = 0.0
        for i, p in enumerate(rs):
            if i:
                s += dist(rs[i - 1], p)
            j0, j1 = max(0, i - 1), min(len(rs) - 1, i + 1)
            tx, ty = rs[j1][0] - rs[j0][0], rs[j1][1] - rs[j0][1]
            L = math.hypot(tx, ty) or 1
            nx, ny = -ty / L, tx / L
            o = amp * (0.6 * math.sin(s / wl[0] * 6.283 + ph[0]) + 0.3 * math.sin(s / wl[1] * 6.283 + ph[1])
                       + 0.25 * math.sin(s / wl[2] * 2.1 + ph[2]))
            out.append((p[0] + nx * o, p[1] + ny * o))
        return out


def clip_lines(lines, geom):
    """clip a list of 2-point segments to a shapely geometry; return polylines"""
    out = []
    for a, b in lines:
        g = LineString([a, b]).intersection(geom)
        if g.is_empty:
            continue
        if g.geom_type == "LineString":
            out.append(list(g.coords))
        elif g.geom_type == "MultiLineString":
            out.extend(list(s.coords) for s in g.geoms)
        elif g.geom_type == "GeometryCollection":
            for s in g.geoms:
                if s.geom_type == "LineString":
                    out.append(list(s.coords))
    return out


def hatch_lines(geom, step, ang_deg, offset=0.0):
    minx, miny, maxx, maxy = geom.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    R = math.hypot(maxx - minx, maxy - miny) / 2 + step
    a = math.radians(ang_deg)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    segs = []
    k = -R + (offset % step)
    while k <= R:
        px, py = cx + nx * k, cy + ny * k
        segs.append(((px - dx * R, py - dy * R), (px + dx * R, py + dy * R)))
        k += step
    return clip_lines(segs, geom)


def lattice(geom, step, ang=45):
    """diamond lattice: two hatch families; returns (lines, cell_centres)"""
    lines = hatch_lines(geom, step, ang) + hatch_lines(geom, step, -ang)
    # cell centres: lattice points offset by half a step along both families
    minx, miny, maxx, maxy = geom.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    a1, a2 = math.radians(ang), math.radians(-ang)
    n1 = (-math.sin(a1), math.cos(a1))
    n2 = (-math.sin(a2), math.cos(a2))
    # solve centre of cell (i+.5, j+.5): p.n1 = (i+.5)step + c.n1 ; p.n2 = (j+.5)step + c.n2
    det = n1[0] * n2[1] - n1[1] * n2[0]
    R = int(math.hypot(maxx - minx, maxy - miny) / step) + 2
    cents = []
    for i in range(-R, R):
        for j in range(-R, R):
            u = (i + 0.5) * step
            v = (j + 0.5) * step
            x = (u * n2[1] - n1[1] * v) / det + cx
            y = (n1[0] * v - u * n2[0]) / det + cy
            if geom.contains(Point(x, y).buffer(step * 0.18)):
                cents.append((x, y))
    return lines, cents


def tri_pts(cx, cy, w, h, up=True):
    if up:
        return [(cx, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
    return [(cx, cy + h / 2), (cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2)]


def vesica(p0, p1, w, n=24):
    """leaf shape between p0 and p1"""
    L = dist(p0, p1)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    top, bot = [], []
    for i in range(n + 1):
        t = i / n
        x = t * L
        y = w / 2 * math.sin(math.pi * t) ** 0.85
        top.append(rot((x, -y), ang))
        bot.append(rot((x, y), ang))
    top = [(p0[0] + x, p0[1] + y) for x, y in top]
    bot = [(p0[0] + x, p0[1] + y) for x, y in bot]
    return top, bot


def offset_line(pts, d):
    out = []
    for i, p in enumerate(pts):
        j0, j1 = max(0, i - 1), min(len(pts) - 1, i + 1)
        tx, ty = pts[j1][0] - pts[j0][0], pts[j1][1] - pts[j0][1]
        L = math.hypot(tx, ty) or 1
        out.append((p[0] - ty / L * d, p[1] + tx / L * d))
    return out


def path_len(pts):
    return sum(dist(pts[i - 1], pts[i]) for i in range(1, len(pts)))


def point_at(pts, s):
    """point and unit tangent at arc length s"""
    acc = 0
    for i in range(1, len(pts)):
        L = dist(pts[i - 1], pts[i])
        if acc + L >= s and L > 0:
            t = (s - acc) / L
            p = lerp(pts[i - 1], pts[i], t)
            return p, ((pts[i][0] - pts[i - 1][0]) / L, (pts[i][1] - pts[i - 1][1]) / L)
        acc += L
    a, b = pts[-2], pts[-1]
    L = dist(a, b) or 1
    return pts[-1], ((b[0] - a[0]) / L, (b[1] - a[1]) / L)


def bezier(p0, p1, p2, p3, n=60):
    out = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        out.append((mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
                    mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def catmull(pts, n=16):
    """Catmull-Rom through pts"""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    out.append(pts[-1])
    return out


def merge(w, h, parts, bg=None):
    """parts: list of (Doc, transform-string-or-None), drawn in order"""
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    if bg:
        out.append(f'<rect width="{w}" height="{h}" fill="{bg}"/>')
    for doc, tf in parts:
        if tf:
            out.append(f'<g transform="{tf}">')
        out.append(doc.body())
        if tf:
            out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)
