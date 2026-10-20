"""Stroke-only plate kit for the plotter editions: a plotter Hand over the Matricis
stroke model (common/geometry/core.py, marks.py, tx.py), single-stroke
lettering from the EMS Nixish SVG font, and a two-layer A4 document.

Units are millimetres throughout. Every mark is a pen stroke: dots become coils,
filled polygons become hatching, text is centreline geometry. No fills.
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "geometry"))

from core import Wobble, arc_pts, resample, dist, lerp, bezier, catmull, hatch_lines, clip_lines  # noqa: E402
import marks  # noqa: E402
import tx  # noqa: E402
from shapely.geometry import Polygon, LineString, MultiLineString, Point  # noqa: E402

INK, RED = "#161918", "#a32b24"
WEIGHTS = {"core": 0.22, "orn": 0.17, "hair": 0.12, "cip": 0.17}
UNIT = 0.157  # Matricis units (1000-wide page) to mm; scales the inherited tremor amplitudes


def fmt(v):
    t = f"{v:.2f}"
    if t.endswith("00"):
        t = t[:-3]
    elif t.endswith("0"):
        t = t[:-1]
    return t


class PlotDoc:
    """Two layers of individual stroke paths. Each stroke is its own <path>."""

    def __init__(self, w=210, h=297):
        self.w, self.h = w, h
        self.layers = {"art": [], "text": []}

    def add(self, layer, pts, color, weight, closed=False, attrs=""):
        if len(pts) < 2:
            return
        d = ["M" + fmt(pts[0][0]) + "," + fmt(pts[0][1])]
        for x, y in pts[1:]:
            d.append("L" + fmt(x) + "," + fmt(y))
        if closed:
            d.append("Z")
        self.layers[layer].append((color, WEIGHTS[weight], "".join(d), attrs))

    def add_filled(self, layer, contours, color, attrs=""):
        """one filled path of several closed contours (even-odd), for outline lettering"""
        d = []
        for pts in contours:
            if len(pts) < 3:
                continue
            d.append("M" + fmt(pts[0][0]) + "," + fmt(pts[0][1]) + "".join("L" + fmt(x) + "," + fmt(y) for x, y in pts[1:]) + "Z")
        if d:
            self.layers[layer].append((color, 0, "".join(d), attrs))

    def strokes(self, layer=None, color=None):
        out = []
        for L, items in self.layers.items():
            if layer and L != layer:
                continue
            for c, w, d, a in items:
                if color and c != color:
                    continue
                out.append((L, c, w, d, a))
        return out

    def svg(self, layers=("art", "text"), colors=(INK, RED), title="", desc=""):
        names = {"art": "Art Paths", "text": "Text Outlines"}
        ids = {"art": "art-paths", "text": "text-outlines"}
        o = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
             f'width="{self.w}mm" height="{self.h}mm" viewBox="0 0 {self.w} {self.h}" version="1.1">']
        if title:
            o.append(f"<title>{title}</title>")
        if desc:
            o.append(f"<desc>{desc}</desc>")
        for L in layers:
            o.append(f'<g id="{ids[L]}" inkscape:groupmode="layer" inkscape:label="{names[L]}" fill="none" '
                     f'stroke-linecap="round" stroke-linejoin="round">')
            for c, w, d, a in self.layers[L]:
                if c not in colors:
                    continue
                if w == 0:
                    o.append(f'<path fill="{c}" fill-rule="evenodd" stroke="none"{a} d="{d}"/>')
                else:
                    o.append(f'<path fill="none" stroke="{c}" stroke-width="{w}"{a} d="{d}"/>')
            o.append("</g>")
        o.append("</svg>")
        return "\n".join(o)


class PlotHand(marks.Hand):
    """Routes the Matricis Hand into a PlotDoc layer; dots are coils, fills are hatch."""

    def __init__(self, doc, rng, layer="art", amp=0.07):
        self.pdoc, self.layer = doc, layer
        self.rng, self.mode = rng, "ink"
        self.wob = Wobble(rng, amp, wl=(22 * UNIT, 61 * UNIT))
        self.amp = amp
        self.grain_cfg = {}
        self.colors = {"ink": INK, "red": RED}

    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None, attrs=""):
        if len(pts) < 2:
            return
        pts = list(pts)
        if closed:
            pts = pts + [pts[0]]
        a = self.amp if amp is None else self.amp * amp / 0.5   # inherited amps are in Matricis units (default 0.5)
        self.pdoc.add(self.layer, self.wob(pts, a, step=0.5), self.colors[color], weight, attrs=attrs)

    def straight(self, pts, weight="orn", color="ink", closed=False, attrs=""):
        """no tremor at all (rules, frames, ticks)"""
        pts = list(pts)
        if closed:
            pts = pts + [pts[0]]
        self.pdoc.add(self.layer, pts, self.colors[color], weight, attrs=attrs)

    def dot(self, x, y, r, color="ink"):
        r = max(0.28, r)
        turns = 1.0 + min(2.5, r * 2.2)
        n = int(30 * turns) + 6
        pts = []
        for i in range(n + 1):
            t = i / n
            a = 6.283 * turns * t
            rr = r * (1 - 0.82 * t)
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        self.pdoc.add(self.layer, pts, self.colors[color], "orn")

    def ring(self, x, y, r, weight="orn", color="ink"):
        self.stroke(arc_pts(x, y, r, 0, 360, max(24, int(r * 14))), weight, color, amp=0.2)

    def fill_poly(self, pts, color="ink", step=0.45, ang=45):
        poly = Polygon(pts)
        for ln in hatch_lines(poly, step, ang):
            self.stroke(ln, "hair", color, amp=0.05)
        self.stroke(pts, "orn", color, closed=True)


# ---------------------------------------------------------------- lettering --

class SVGFont:
    """Single-stroke SVG font (EMS family). Glyph outlines are centrelines; y is flipped."""

    def __init__(self, path):
        s = open(path, encoding="utf-8").read()
        self.upm = float(re.search(r'units-per-em="([\d.]+)"', s).group(1))
        self.adv_default = float(re.search(r'<font [^>]*horiz-adv-x="([\d.]+)"', s).group(1))
        self.glyphs = {}
        for g in re.finditer(r"<glyph ([^>]*)/>", s):
            attrs = g.group(1)
            uni = re.search(r'unicode="([^"]+)"', attrs)
            if not uni:
                continue
            ch = uni.group(1)
            ch = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), ch)
            ch = ch.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
            adv = re.search(r'horiz-adv-x="([\d.]+)"', attrs)
            d = re.search(r' d="([^"]*)"', attrs)
            self.glyphs[ch] = (float(adv.group(1)) if adv else self.adv_default, self._parse(d.group(1)) if d else [])
        hx = [p for pl in self.glyphs["H"][1] for p in pl]
        self.cap_units = max(y for _, y in hx) - min(y for _, y in hx)   # measured, not metadata
        self.base_units = min(y for _, y in hx)

    @staticmethod
    def _parse(d):
        toks = re.findall(r"[MLCZz]|-?\d*\.?\d+(?:e-?\d+)?", d)
        out, cur, pen, i = [], [], None, 0
        while i < len(toks):
            t = toks[i]
            if t == "M":
                if len(cur) > 1:
                    out.append(cur)
                pen = (float(toks[i + 1]), float(toks[i + 2]))
                cur = [pen]
                i += 3
            elif t == "L":
                pen = (float(toks[i + 1]), float(toks[i + 2]))
                cur.append(pen)
                i += 3
            elif t == "C":
                p1 = (float(toks[i + 1]), float(toks[i + 2]))
                p2 = (float(toks[i + 3]), float(toks[i + 4]))
                p3 = (float(toks[i + 5]), float(toks[i + 6]))
                cur.extend(bezier(pen, p1, p2, p3, 10)[1:])
                pen = p3
                i += 7
            elif t in "Zz":
                if cur:
                    cur.append(cur[0])
                i += 1
            else:
                i += 1
        if len(cur) > 1:
            out.append(cur)
        return out

    def width(self, text, cap, spacing=0.0):
        k = cap / self.cap_units
        return sum(self.glyphs.get(ch, self.glyphs[" "])[0] * k + spacing for ch in text) - spacing

    def write(self, h, text, x, y, cap, align="left", color="ink", weight="orn", spacing=0.0):
        """x, y = left baseline (or centre for align='center'). Returns (x0, width)."""
        k = cap / self.cap_units
        w = self.width(text, cap, spacing)
        x0 = {"left": x, "center": x - w / 2, "right": x - w}[align]
        cx = x0
        for ch in text:
            adv, polys = self.glyphs.get(ch, self.glyphs[" "])
            for pl in polys:
                pts = [(cx + px * k, y - (py - self.base_units) * k) for px, py in pl]
                h.stroke(pts, weight, color, amp=0.05)
            cx += adv * k + spacing
        return x0, w


class OutlineFont:
    """a TrueType face drawn as filled outlines, for the reading edition. Same interface as SVGFont."""

    def __init__(self, path, tracking=0.0):
        from fontTools.ttLib import TTFont
        self.tt = TTFont(path)
        self.gs = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap()
        self.upm = self.tt["head"].unitsPerEm
        self.tracking = tracking
        self._cache = {}
        hx = [p for c in self._contours("H") for p in c]
        self.cap_units = max(y for _, y in hx) - min(y for _, y in hx)
        self.base_units = min(y for _, y in hx)

    def _contours(self, ch):
        if ch in self._cache:
            return self._cache[ch]
        name = self.cmap.get(ord(ch))
        if name is None:
            self._cache[ch] = []
            return []
        g = self.gs[name]
        out, cur = [], []
        pen = _FlattenPen(out, cur)
        g.draw(pen)
        pen.close()
        self._cache[ch] = pen.out
        return pen.out

    def _adv(self, ch):
        name = self.cmap.get(ord(ch))
        return self.gs[name].width if name else self.upm * 0.25

    def width(self, text, cap, spacing=0.0):
        k = cap / self.cap_units
        return sum(self._adv(ch) * k + spacing + self.tracking * cap for ch in text) - spacing - self.tracking * cap

    def write(self, h, text, x, y, cap, align="left", color="ink", weight="orn", spacing=0.0):
        k = cap / self.cap_units
        w = self.width(text, cap, spacing)
        x0 = {"left": x, "center": x - w / 2, "right": x - w}[align]
        cx = x0
        for ch in text:
            contours = [[(cx + px * k, y - (py - self.base_units) * k) for px, py in c] for c in self._contours(ch)]
            if contours:
                h.pdoc.add_filled(h.layer, contours, h.colors[color])
            cx += self._adv(ch) * k + spacing + self.tracking * cap
        return x0, w


class _FlattenPen:
    """a fontTools pen that flattens curves to polylines"""

    def __init__(self, out, cur):
        self.out, self.cur, self.pen = [], [], None

    def moveTo(self, p):
        self.close()
        self.cur = [p]
        self.pen = p

    def lineTo(self, p):
        self.cur.append(p)
        self.pen = p

    def qCurveTo(self, *pts):
        # TrueType: implied on-curve points between consecutive off-curve points
        if pts[-1] is None:
            pts = pts[:-1] + (pts[0],)
        p0 = self.pen
        offs = list(pts[:-1])
        end = pts[-1]
        for i, c in enumerate(offs):
            nxt = offs[i + 1] if i + 1 < len(offs) else end
            e = nxt if i + 1 >= len(offs) else ((c[0] + nxt[0]) / 2, (c[1] + nxt[1]) / 2)
            for t in range(1, 9):
                u = t / 8
                self.cur.append(((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u ** 2 * e[0],
                                 (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u ** 2 * e[1]))
            p0 = e
        self.pen = end

    def curveTo(self, *pts):
        p0 = self.pen
        while len(pts) >= 3:
            p1, p2, p3 = pts[0], pts[1], pts[2]
            self.cur.extend(bezier(p0, p1, p2, p3, 10)[1:])
            p0 = p3
            pts = pts[3:]
        self.pen = p0

    def closePath(self):
        self.close()

    def endPath(self):
        self.close()

    def close(self):
        if len(self.cur) > 2:
            self.out.append(self.cur)
        self.cur = []


# --------------------------------------------------------------- utilities --

def vertical_fill(h, geom, step, rng, weight="hair", color="ink", jitter=0.25, gap_prob=0.0, gap=(1.5, 5.0)):
    """vertical drop-lines through a shapely geometry; returns the clipped polylines"""
    minx, miny, maxx, maxy = geom.bounds
    x = minx + step * 0.5
    out = []
    while x < maxx:
        xx = x + rng.uniform(-jitter, jitter) * step
        seg = LineString([(xx, miny - 1), (xx, maxy + 1)]).intersection(geom)
        parts = []
        if seg.geom_type == "LineString":
            parts = [seg]
        elif seg.geom_type == "MultiLineString":
            parts = list(seg.geoms)
        for p in parts:
            c = list(p.coords)
            if len(c) < 2:
                continue
            y0, y1 = c[0][1], c[-1][1]
            if y1 < y0:
                y0, y1 = y1, y0
            # optional random gaps along the line
            runs = [(y0, y1)]
            if gap_prob and rng.random() < gap_prob and y1 - y0 > 12:
                g0 = rng.uniform(y0 + 3, y1 - 3 - gap[1])
                gl = rng.uniform(*gap)
                runs = [(y0, g0), (g0 + gl, y1)]
            for a, b in runs:
                if b - a > 0.6:
                    pts = [(xx, a), (xx, b)]
                    h.stroke(pts, weight, color, amp=0.6)
                    out.append(pts)
        x += step
    return out


def voronoi_net(h, geom, n, rng, weight="hair", color="ink", seed_pts=None):
    """cellular net clipped to geom, drawn as the cell boundaries"""
    import shapely
    from shapely.geometry import MultiPoint
    minx, miny, maxx, maxy = geom.bounds
    pts = []
    tries = 0
    while len(pts) < n and tries < n * 50:
        tries += 1
        p = (rng.uniform(minx, maxx), rng.uniform(miny, maxy))
        if geom.contains(Point(p)) and all(dist(p, q) > 0.8 for q in pts):
            pts.append(p)
    if seed_pts:
        pts.extend(seed_pts)
    vor = shapely.voronoi_polygons(MultiPoint(pts), extend_to=geom.buffer(5), only_edges=True)
    edges = []
    for ln in (vor.geoms if hasattr(vor, "geoms") else [vor]):
        g = ln.intersection(geom)
        for part in (g.geoms if hasattr(g, "geoms") else [g]):
            if part.geom_type == "LineString" and part.length > 0.3:
                c = list(part.coords)
                h.stroke(c, weight, color, amp=0.3)
                edges.append(c)
    return edges


def roman_year_angles(values, v0, v1, a0, a1):
    """log scale: value v -> angle (degrees, y-down screen) between a0 and a1"""
    out = []
    for v in values:
        t = math.log(v / v0) / math.log(v1 / v0)
        out.append(a0 + (a1 - a0) * t)
    return out
