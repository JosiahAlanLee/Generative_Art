"""Bringing a native stroke plate into the illustrated edition.

The native plates (books/04_graduum/plates/*-native, books/05_notoria/plates) draw into a PlotDoc
in millimetres, y down. Here a plate's own generator is run with a few of its functions
replaced: the figures it would have drawn as apparatus are recorded as slots instead, and its
furniture (A4 frame, title block, caption strip, frame rule) is recorded instead of drawn. The
PlotDoc that results, which still carries every carrier the generator draws inside the plate, is
rendered onto a ReportLab canvas through a Map, and the edition adds its own furniture, washes
and the raster figures in the recorded slots. The generators' files are not touched; the plot
masters build as before.
"""
import math
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(REPO, "common", "plot"), os.path.join(REPO, "common", "geometry"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("GRADUUM_READING", "1")     # serif lettering, as the bound book

from reportlab.pdfgen.canvas import FILL_EVEN_ODD  # noqa: E402

import plotkit  # noqa: E402
from core import arc_pts  # noqa: E402
import furniture as fu  # noqa: E402

INK_HEX, RED_HEX = plotkit.INK, plotkit.RED


# ------------------------------------------------------------------- dots --

_orig_dot = plotkit.PlotHand.dot


def _filled_dot(self, x, y, r, color="ink"):
    """in the illustrated edition a dot is a dot, not a pen coil"""
    self.pdoc.layers[self.layer].append((self.colors[color], "DOT", f"{x:.3f},{y:.3f},{max(0.22, r):.3f}", ""))


def filled_dots(on=True):
    plotkit.PlotHand.dot = _filled_dot if on else _orig_dot


# -------------------------------------------------------------------- map --

class Map:
    """native mm box (x0, y0, x1, y1; y down) onto a page rectangle in points (y up), uniform
    scale, centred"""

    def __init__(self, box, rect, align="center"):
        bx0, by0, bx1, by1 = box
        rx0, ry0, rx1, ry1 = rect
        self.box, self.rect = box, rect
        self.s = min((rx1 - rx0) / (bx1 - bx0), (ry1 - ry0) / (by1 - by0))
        w, h = (bx1 - bx0) * self.s, (by1 - by0) * self.s
        self.ox = rx0 + ((rx1 - rx0) - w) / 2 - bx0 * self.s
        top = ry1 - ((ry1 - ry0) - h) / 2 if align == "center" else ry1
        self.oy = top + by0 * self.s

    def P(self, x, y):
        return self.ox + x * self.s, self.oy - y * self.s

    def R(self, x, y, w, h):
        """mm rect (x, y top-left, w, h) as page (x0, y0, w, h)"""
        X0, Y1 = self.P(x, y)
        return X0, Y1 - h * self.s, w * self.s, h * self.s

    def mm(self, X, Y):
        return (X - self.ox) / self.s, (self.oy - Y) / self.s


class MapHand(fu.Hand):
    """a furniture Hand that takes native millimetre coordinates (y down) through a Map, so
    marks.py, tx.py and ornament.py can draw onto the page in the plate's own coordinates"""

    def __init__(self, c, rng, M, amp=0.07, wscale=1.0):
        super().__init__(c, rng, amp=amp * M.s)
        self.M = M
        self.wscale = wscale

    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None, attrs="", dash=None):
        a = None if amp is None else self.amp * amp / 0.5
        super().stroke([self.M.P(*q) for q in pts], weight, color, closed, amp=a, dash=dash)

    def straight(self, pts, weight="orn", color="ink", closed=False, attrs="", dash=None):
        super().straight([self.M.P(*q) for q in pts], weight, color, closed, dash=dash)

    def dot(self, x, y, r, color="ink"):
        X, Y = self.M.P(x, y)
        super().dot(X, Y, max(0.22, r) * self.M.s, color)

    def ring(self, x, y, r, weight="orn", color="ink"):
        self.stroke(arc_pts(x, y, r, 0, 360, max(24, int(r * 14))), weight, color, amp=0.2)

    def fill_poly(self, pts, color="ink", alpha=1.0, **kw):
        super().fill_poly([self.M.P(*q) for q in pts], color, alpha)


class AnisoHand(fu.Hand):
    """native frame coordinates onto a page rectangle with separate x and y scales: for the frame
    rule, whose ticks are counted, not measured"""

    def __init__(self, c, rng, frame, rect):
        super().__init__(c, rng, amp=0.0)
        fx0, fy0, fx1, fy1 = frame
        rx0, ry0, rx1, ry1 = rect
        self.sx, self.sy = (rx1 - rx0) / (fx1 - fx0), (ry1 - ry0) / (fy1 - fy0)
        self.f = lambda x, y: (rx0 + (x - fx0) * self.sx, ry1 - (y - fy0) * self.sy)

    def straight(self, pts, weight="orn", color="ink", closed=False, attrs="", dash=None):
        super().straight([self.f(*q) for q in pts], weight, color, closed)


# ----------------------------------------------------------------- render --

_tok = re.compile(r"([MLZ])\s*([-\d.]+)?\s*,?\s*([-\d.]+)?")


def _subpaths(d):
    out, cur = [], None
    for m in _tok.finditer(d):
        op = m.group(1)
        if op == "M":
            cur = [(float(m.group(2)), float(m.group(3)))]
            out.append([cur, False])
        elif op == "L":
            cur.append((float(m.group(2)), float(m.group(3))))
        elif op == "Z":
            out[-1][1] = True
    return out


def bbox_of(d):
    xs, ys = [], []
    for pts, _ in _subpaths(d):
        for x, y in pts:
            xs.append(x)
            ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def draw_doc(c, doc, M, layers=("art", "text"), colors=None, wscale=1.8, skip=None, min_w=0.28):
    """render a PlotDoc's strokes onto the canvas through M. colors: {hex: (r, g, b) 0-255}.
    skip(bbox_mm, attrs, layer) -> True to leave a stroke out."""
    colors = colors or {INK_HEX: fu.INK, RED_HEX: fu.RED}
    n = 0
    for L in layers:
        for col, w, d, attrs in doc.layers[L]:
            rgbcol = colors.get(col, fu.INK)
            if w == "DOT":
                x, y, r = (float(v) for v in d.split(","))
                if skip and skip((x - r, y - r, x + r, y + r), attrs, L):
                    continue
                X, Y = M.P(x, y)
                c.setFillColorRGB(*fu.rgb(rgbcol))
                c.circle(X, Y, r * M.s, stroke=0, fill=1)
                n += 1
                continue
            sp = _subpaths(d)
            if skip:
                bb = bbox_of(d)
                if bb and skip(bb, attrs, L):
                    continue
            p = c.beginPath()
            for pts, closed in sp:
                p.moveTo(*M.P(*pts[0]))
                for q in pts[1:]:
                    p.lineTo(*M.P(*q))
                if closed:
                    p.close()
            if w == 0:
                c.setFillColorRGB(*fu.rgb(rgbcol))
                c.drawPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)
            else:
                c.setStrokeColorRGB(*fu.rgb(rgbcol))
                material = L == "art" and attrs.strip() == 'data-material="cornmeal"'
                # Only the illustrated caller's explicitly tagged hatching is
                # eligible. Carrier tags and the text layer never enter here.
                grain_on = material and getattr(c, "_figure_growth", {}).get("amount", 0) > 0
                c.setLineWidth(max(.20 if grain_on else min_w, w * M.s * wscale * (.65 if grain_on else 1)))
                c.setLineCap(1)
                c.setLineJoin(1)
                c.drawPath(p, stroke=1, fill=0)
                if grain_on:
                    import figure_growth
                    import hashlib
                    seed = int(hashlib.sha256(d.encode()).hexdigest()[:8], 16)
                    for pts, _ in sp:
                        count = figure_growth.cornmeal_path(c, [M.P(*q) for q in pts],
                                                          color=rgbcol, seed=seed)
                        c._cornmeal_grains = getattr(c, "_cornmeal_grains", 0) + count
            n += 1
    return n


def inside(bb, box, pad=0.0):
    x0, y0, x1, y1 = box
    return bb[0] >= x0 - pad and bb[1] >= y0 - pad and bb[2] <= x1 + pad and bb[3] <= y1 + pad


def tmpdir(tag):
    d = os.path.join(REPO, "build", "illum-plates", tag)
    os.makedirs(d, exist_ok=True)
    return d


def compact(path):
    """rewrite a PDF with unused and duplicate objects removed and streams deflated (the merged
    books otherwise carry each plate's fonts and images more than once)"""
    import fitz
    tmp = path + ".tmp"
    with fitz.open(path) as d:
        d.save(tmp, garbage=4, deflate=True, deflate_fonts=True)
    os.replace(tmp, path)
    return os.path.getsize(path)
