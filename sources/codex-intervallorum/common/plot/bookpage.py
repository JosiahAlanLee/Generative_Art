"""Shared page engine for the series' ReportLab books: 7 x 10 in, the series ground, IM Fell
English, a Hand that draws the Matricis stroke vocabulary straight onto the canvas, and small
text helpers. Used by the Graduum text build and the tarot reading edition."""
import os
import random
import sys

from reportlab.lib.pagesizes import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "common", "geometry"))
from core import Wobble, arc_pts, catmull  # noqa: E402

PW, PH = 7 * inch, 10 * inch
PAPER = (0xED / 255, 0xE6 / 255, 0xD4 / 255)
INK = (0x16 / 255, 0x19 / 255, 0x18 / 255)
RED = (0xA3 / 255, 0x2B / 255, 0x24 / 255)
MM = 72 / 25.4
FONTS = os.path.join(REPO, "common", "fonts")


def fonts():
    for name, f in (("Fell", "IMFeENrm28P.ttf"), ("FellIt", "IMFeENit28P.ttf"), ("FellSC", "IMFeENsc28P.ttf"),
                    ("FellTitle", "IMFellEnglish-Regular.ttf"), ("Mono", "IBMPlexMono-Regular.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS, f)))


class PageHand:
    """the Matricis Hand interface on a ReportLab canvas; mm from a top-left origin, y down"""
    W = {"core": 0.8, "orn": 0.5, "hair": 0.28, "cip": 0.5}

    def __init__(self, c, ox, oy, rng, amp=0.07):
        self.c, self.ox, self.oy, self.rng = c, ox, oy, rng
        self.wob = Wobble(rng, amp, wl=(22 * 0.157, 61 * 0.157))
        self.amp = amp
        self.colors = {"ink": INK, "red": RED}

    def _p(self, x, y):
        return self.ox + x * MM, self.oy - y * MM

    def _poly(self, pts, weight, color):
        self.c.setStrokeColorRGB(*self.colors[color])
        self.c.setLineWidth(self.W[weight])
        self.c.setLineCap(1)
        self.c.setLineJoin(1)
        p = self.c.beginPath()
        p.moveTo(*self._p(*pts[0]))
        for q in pts[1:]:
            p.lineTo(*self._p(*q))
        self.c.drawPath(p, stroke=1, fill=0)

    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None, attrs=""):
        pts = list(pts)
        if len(pts) < 2:
            return
        if closed:
            pts = pts + [pts[0]]
        a = self.amp if amp is None else self.amp * amp / 0.5
        self._poly(self.wob(pts, a, step=0.5), weight, color)

    def straight(self, pts, weight="orn", color="ink", closed=False, attrs=""):
        pts = list(pts)
        if closed:
            pts = pts + [pts[0]]
        self._poly(pts, weight, color)

    def dot(self, x, y, r, color="ink"):
        self.c.setFillColorRGB(*self.colors[color])
        X, Y = self._p(x, y)
        self.c.circle(X, Y, max(0.25, r) * MM, stroke=0, fill=1)

    def ring(self, x, y, r, weight="orn", color="ink"):
        self.stroke(arc_pts(x, y, r, 0, 360, max(24, int(r * 14))), weight, color, amp=0.2)

    def fill_poly(self, pts, color="ink", step=0.45, ang=45):
        from core import hatch_lines
        from shapely.geometry import Polygon
        for ln in hatch_lines(Polygon(pts), step, ang):
            self.stroke(ln, "hair", color, amp=0.05)
        self.stroke(pts, "orn", color, closed=True)


def paper(c):
    c.setFillColorRGB(*PAPER)
    c.rect(0, 0, PW, PH, stroke=0, fill=1)


def wrap(text, font, size, width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(t, font, size) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def flow_rule(c, x0, y_top, width_mm, seed, n=3, red_dot=False):
    """a drifting rule in the Book I vocabulary: a few lines with curl terminals and hanging dots"""
    from core import curl_pts
    rng = random.Random(seed)
    h = PageHand(c, x0, y_top, rng)
    for i in range(n):
        y = 1.5 + i * 1.9 + rng.uniform(-0.25, 0.25)
        pts, x = [(0.0, y)], 0.0
        while x < width_mm - 12:
            x += rng.uniform(9, 16)
            pts.append((min(x, width_mm - 12), y + rng.uniform(-1.2, 1.2)))
        pts.append((width_mm - 12 + rng.uniform(0, 5), y + rng.uniform(-0.5, 0.5)))
        cp = catmull(pts, 6)
        h.stroke(cp, "hair", "ink", amp=0.35)
        ex, ey = cp[-1]
        q = curl_pts(ex, ey, 0, 1.1, 1.0, 1.25, hand=1 if i % 2 else -1)
        h.stroke(q, "hair", "ink", amp=0.2)
        h.dot(q[-1][0], q[-1][1], 0.3, "ink")
    for k in range(rng.randint(2, 3)):
        x = rng.uniform(4, width_mm - 20)
        y0 = 1.5 + (n - 1) * 1.9 + 0.4
        y1 = y0 + rng.uniform(2.5, 6.0)
        col = "red" if red_dot and k == 0 else "ink"
        h.straight([(x, y0), (x, y1)], "hair", col)
        h.dot(x, y1 + 0.3, 0.3, col)
    return 1.5 + (n - 1) * 1.9 + 7.0
