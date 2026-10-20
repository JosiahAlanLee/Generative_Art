"""Plate furniture for the illustrated edition, in Book I's vocabulary, drawn straight onto a
ReportLab canvas: the ruled and roped frame with black corner blocks, glyph bands in the
twelve-mark hand along a frame edge, red hand-notes with leaders, register marks, scattered
asterisks, washes, and the Matricis paper specks.

Coordinates are PDF points, origin bottom-left, unless a function says otherwise. Strokes go
through the shared Wobble (common/geometry/core.py) so a rule here has the same hand as a rule
in Book I. Nothing here is meant for the plotter: fills, alpha and blend modes are used freely.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(REPO, "common", "geometry"), os.path.join(REPO, "common", "plot")):
    if p not in sys.path:
        sys.path.insert(0, p)

from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402

from core import Wobble, arc_pts, catmull, curl_pts, bezier  # noqa: E402
import marks  # noqa: E402
import tx  # noqa: E402

MM = 72 / 25.4
FONTS = os.path.join(REPO, "common", "fonts")

# the series palette, with Book I's secondary inks for washes
PAPER = (237, 230, 212)
INK = (22, 25, 24)
RED = (163, 43, 36)
SEPIA = (90, 67, 49)        # Matricis #5a4331
OCHRE = (184, 154, 106)     # Matricis #b89a6a
UMBER = (109, 95, 75)       # Matricis #6d5f4b
SLATE = (74, 86, 92)        # the renders' slate cells
VERDIGRIS = (98, 122, 96)   # Book I's green layer
DARK = (28, 24, 19)         # Matricis #1c1813, dark plates
LIGHT = (235, 225, 200)     # light ink on dark plates


def rgb(c, a=1.0):
    return tuple(v / 255 for v in c)


def fonts():
    for name, f in (("Fell", "IMFeENrm28P.ttf"), ("FellIt", "IMFeENit28P.ttf"), ("FellSC", "IMFeENsc28P.ttf"),
                    ("FellTitle", "IMFellEnglish-Regular.ttf"), ("Mono", "IBMPlexMono-Regular.ttf"),
                    ("Hand", "SueEllenFrancisco-Regular.ttf"), ("Pica", "IMFePIrm28P.ttf"),
                    ("PicaIt", "IMFePIit28P.ttf"), ("DMSerif", "DMSerifDisplay-Regular.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS, f)))


class Hand:
    """the Book I Hand interface on a ReportLab canvas, in points, origin bottom-left, y up.
    marks.py and tx.py draw in a y-down box; use YDown for them."""
    W = {"core": 0.9, "orn": 0.55, "hair": 0.3, "cip": 0.5, "heavy": 1.4}

    def __init__(self, c, rng, amp=0.18, colors=None):
        self.c, self.rng = c, rng
        self.wob = Wobble(rng, amp, wl=(3.5, 9.5))
        self.amp = amp
        self.colors = {"ink": INK, "red": RED, "sepia": SEPIA, "ochre": OCHRE, "umber": UMBER,
                       "slate": SLATE, "green": VERDIGRIS, "light": LIGHT, "paper": PAPER, "dark": DARK}
        if colors:
            self.colors.update(colors)
        self.weight_scale = 1.0

    def col(self, color):
        return rgb(self.colors[color]) if isinstance(color, str) else rgb(color)

    def _poly(self, pts, weight, color, dash=None):
        c = self.c
        c.setStrokeColorRGB(*self.col(color))
        c.setLineWidth((self.W[weight] if isinstance(weight, str) else weight) * self.weight_scale)
        c.setLineCap(1)
        c.setLineJoin(1)
        if dash:
            c.setDash(*dash)
        p = c.beginPath()
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        c.drawPath(p, stroke=1, fill=0)
        if dash:
            c.setDash()

    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None, dash=None):
        pts = list(pts)
        if len(pts) < 2:
            return
        if closed:
            pts = pts + [pts[0]]
        a = self.amp if amp is None else amp
        L = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
        a = min(a, L / 40.0)
        step = max(0.12, min(1.5, L / 30.0))
        self._poly(self.wob(pts, a, step=step) if a > 0.01 else pts, weight, color, dash)

    def straight(self, pts, weight="orn", color="ink", closed=False, dash=None):
        pts = list(pts)
        if closed:
            pts = pts + [pts[0]]
        self._poly(pts, weight, color, dash)

    def dot(self, x, y, r, color="ink"):
        self.c.setFillColorRGB(*self.col(color))
        self.c.circle(x, y, max(0.25, r), stroke=0, fill=1)

    def ring(self, x, y, r, weight="orn", color="ink"):
        self.stroke(arc_pts(x, y, r, 0, 360, max(24, int(r * 3))), weight, color, amp=min(0.25, r * 0.03))

    def fill_poly(self, pts, color="ink", alpha=1.0):
        c = self.c
        c.saveState()
        c.setFillColorRGB(*self.col(color))
        if alpha < 1:
            c.setFillAlpha(alpha)
        p = c.beginPath()
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        c.restoreState()


class YDown:
    """adapter for marks.py / tx.py, which draw in a y-down unit box: (x, y) in mm from a
    top-left origin at (ox, oy) points, scaled by k points per unit"""

    def __init__(self, hand, ox, oy, k=MM):
        self.h, self.ox, self.oy, self.k = hand, ox, oy, k
        self.rng = hand.rng

    def P(self, x, y):
        return self.ox + x * self.k, self.oy - y * self.k

    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None):
        self.h.stroke([self.P(*q) for q in pts], weight, color, closed, amp=None if amp is None else amp * 0.4)

    def straight(self, pts, weight="orn", color="ink", closed=False, attrs=""):
        self.h.straight([self.P(*q) for q in pts], weight, color, closed)

    def dot(self, x, y, r, color="ink"):
        self.h.dot(*self.P(x, y), r * self.k, color)

    def ring(self, x, y, r, weight="orn", color="ink"):
        self.h.stroke([self.P(*q) for q in arc_pts(x, y, r, 0, 360, max(24, int(r * 14)))], weight, color, amp=0.1)

    def fill_poly(self, pts, color="ink", **kw):
        self.h.fill_poly([self.P(*q) for q in pts], color)


# ------------------------------------------------------------------ paper --

def ground(c, w, h, color=PAPER):
    c.setFillColorRGB(*rgb(color))
    c.rect(0, 0, w, h, stroke=0, fill=1)


def specks(c, w, h, seed, n=46, color=PAPER, avoid=None):
    """Book I's paper: sparse soft specks, a few a shade darker than the ground, some lighter"""
    rng = random.Random(f"specks-{seed}")
    c.saveState()
    for i in range(n):
        x, y = rng.uniform(4, w - 4), rng.uniform(4, h - 4)
        r = rng.choice([0.5, 0.6, 0.7, 0.9, 1.1, 1.4, 1.9, 2.4]) * rng.uniform(0.8, 1.2)
        k = rng.uniform(0.94, 0.975) if rng.random() < 0.8 else rng.uniform(1.01, 1.025)
        col = tuple(min(1, v / 255 * k) for v in color)
        c.setFillColorRGB(*col)
        c.setFillAlpha(rng.uniform(0.55, 0.95))
        c.circle(x, y, r, stroke=0, fill=1)
    c.restoreState()


# ---------------------------------------------------------------- frames --

def rope_frame(h, x0, y0, x1, y1, gap=4.2, corner=7.5, hatch=2.1, color="ink", corners=True, inner=True):
    """Book I's plate frame: two ruled lines with a diagonal rope between, black corner blocks
    with a paper asterisk, and a hairline inner rule"""
    rng = h.rng
    for d in (0.0, gap):
        h.stroke([(x0 - d, y0 - d), (x1 + d, y0 - d), (x1 + d, y1 + d), (x0 - d, y1 + d)], "orn", color, closed=True, amp=0.12)
    # rope: short diagonals between the two lines, all four sides
    for (ax, ay, bx, by, nx, ny) in ((x0, y0, x1, y0, 0, -1), (x1, y0, x1, y1, 1, 0), (x1, y1, x0, y1, 0, 1), (x0, y1, x0, y0, -1, 0)):
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        n = int(L / hatch)
        for i in range(1, n):
            t = i * hatch
            px, py = ax + ux * t, ay + uy * t
            q0 = (px + nx * 0.6, py + ny * 0.6)
            q1 = (px + nx * (gap - 0.6) + ux * hatch * 0.9, py + ny * (gap - 0.6) + uy * hatch * 0.9)
            h.straight([q0, q1], "hair", color)
    if inner:
        h.stroke([(x0 + 2.2, y0 + 2.2), (x1 - 2.2, y0 + 2.2), (x1 - 2.2, y1 - 2.2), (x0 + 2.2, y1 - 2.2)], "hair", color, closed=True, amp=0.1)
    if corners:
        for (cx, cy) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ox = cx - gap / 2 + (-1 if cx == x0 else 1) * 0.0
            oy = cy - gap / 2 + (-1 if cy == y0 else 1) * 0.0
            s = corner
            px, py = (cx - gap - 0.4 if cx == x0 else cx - s + gap + 0.4), (cy - gap - 0.4 if cy == y0 else cy - s + gap + 0.4)
            h.c.setFillColorRGB(*h.col(color))
            h.c.rect(px, py, s, s, stroke=0, fill=1)
            ax_, ay_ = px + s / 2, py + s / 2
            for k in range(4):
                a = math.radians(22 + k * 45)
                h.straight([(ax_ - 2.6 * math.cos(a), ay_ - 2.6 * math.sin(a)), (ax_ + 2.6 * math.cos(a), ay_ + 2.6 * math.sin(a))], 0.45, "paper")


def ruled_frame(h, x0, y0, x1, y1, color="ink", ticks=0):
    """a lighter frame: a ruled double line, optional graduation inside"""
    h.stroke([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "orn", color, closed=True, amp=0.1)
    h.stroke([(x0 + 2, y0 + 2), (x1 - 2, y0 + 2), (x1 - 2, y1 - 2), (x0 + 2, y1 - 2)], "hair", color, closed=True, amp=0.1)
    if ticks:
        for side in range(4):
            if side % 2 == 0:
                y = y0 + 2 if side == 0 else y1 - 2
                k = 1 if side == 0 else -1
                x = x0 + 2 + ticks
                i = 0
                while x < x1 - 2:
                    h.straight([(x, y), (x, y + k * (2.4 if i % 10 == 0 else 1.2))], "hair", color)
                    x += ticks
                    i += 1
            else:
                x = x0 + 2 if side == 3 else x1 - 2
                k = 1 if side == 3 else -1
                y = y0 + 2 + ticks
                i = 0
                while y < y1 - 2:
                    h.straight([(x, y), (x + k * (2.4 if i % 10 == 0 else 1.2), y)], "hair", color)
                    y += ticks
                    i += 1


def register(h, x, y, r=4.5, color="ink"):
    h.ring(x, y, r * 0.55, "hair", color)
    h.straight([(x - r, y), (x + r, y)], "hair", color)
    h.straight([(x, y - r), (x, y + r)], "hair", color)


def stars(h, box, n, seed, avoid=(), color="ink", rmin=1.4, rmax=2.6):
    """scattered small asterisks, Book I's star field, clear of the avoided rectangles"""
    rng = random.Random(f"stars-{seed}")
    x0, y0, x1, y1 = box
    yd = YDown(h, 0, 0, 1.0)
    placed = 0
    tries = 0
    while placed < n and tries < n * 40:
        tries += 1
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if any(a[0] - 4 < x < a[2] + 4 and a[1] - 4 < y < a[3] + 4 for a in avoid):
            continue
        r = rng.uniform(rmin, rmax)
        for k in range(3):
            a = math.radians(rng.uniform(0, 60) + k * 60)
            h.straight([(x - r * math.cos(a), y - r * math.sin(a)), (x + r * math.cos(a), y + r * math.sin(a))], "hair", color)
        h.dot(x, y, 0.35, color)
        placed += 1


def orn_rule(h, cx, y, width, color="ink"):
    """asterisk - band of crossed cells - asterisk, Book I's heading rule"""
    w = width
    x0, x1 = cx - w / 2 + 7, cx + w / 2 - 7
    h.straight([(x0, y - 2.0), (x1, y - 2.0)], "hair", color)
    h.straight([(x0, y + 2.0), (x1, y + 2.0)], "hair", color)
    n = max(4, int((x1 - x0) / 5.5))
    step = (x1 - x0) / n
    for i in range(n):
        a, b = x0 + i * step, x0 + (i + 1) * step
        h.straight([(a, y - 2.0), (b, y + 2.0)], "hair", color)
        h.straight([(a, y + 2.0), (b, y - 2.0)], "hair", color)
    for x in (x0 - 4.2, x1 + 4.2):
        for k in range(4):
            a = math.radians(k * 45 + 10)
            h.straight([(x - 3 * math.cos(a), y - 3 * math.sin(a)), (x + 3 * math.cos(a), y + 3 * math.sin(a))], "hair", color)


def wave_rule(h, x0, x1, y, color="umber", seed=0):
    """the looping scallop at the foot of Book I's plates"""
    rng = random.Random(f"wave-{seed}")
    x = x0
    while x < x1 - 18:
        w = rng.uniform(16, 22)
        pts = [(x + t * w, y - 2.4 * math.sin(math.pi * t)) for t in [i / 16 for i in range(17)]]
        h.stroke(pts, "hair", color, amp=0.1)
        mx = x + w * rng.uniform(0.35, 0.65)
        q = curl_pts(mx, y - 1.8, 90, 1.2, 1.1, 1.3, hand=1)
        h.stroke(q, "hair", color, amp=0.05)
        x += w + rng.uniform(2.5, 5)


# ------------------------------------------------------------- lettering --

def glyph_band(h, text, x, y, length, size=4.6, shift=0, angle=0, color="ink", align="start", rail=True):
    """a passage in the twelve-mark hand along a frame edge: base marks advanced by `shift`,
    drawn in a y-down box of `size` points; angle in degrees about (x, y). Repeats the passage,
    separated by a three-dot stop, until the length is filled. Returns the passage actually set."""
    c = h.c
    c.saveState()
    c.translate(x, y)
    c.rotate(angle)
    yd = YDown(h, 0, size * 0.5, size)       # unit box = one mark; y-down
    words = tx.encode(text)
    cx = 0.0
    set_words = []
    gap = 0.55
    stop = 1.4
    i = 0
    if rail:
        h.straight([(0, -size * 0.62), (length, -size * 0.62)], "hair", color)
    while True:
        w = words[i % len(words)]
        ww = sum(tx.token_width(t, 1) for (b, t) in w)
        if (cx + ww) * size > length:
            break
        for (b, t) in w:
            tx.mark(yd, (b - 1 + shift) % 12 + 1, cx, 0, 1, "hair", color)
            tx.tally(yd, t, cx, 0, 1, color)
            cx += tx.token_width(t, 1)
        set_words.append(i % len(words))
        cx += gap
        i += 1
        if i % len(words) == 0:
            for k in range(3):
                yd.dot(cx + 0.18 + k * 0.32, 0.5, 0.07, color)
            cx += stop
    c.restoreState()
    return " ".join(tx.decode([words[j]]) for j in set_words)


def hand_note(h, lines, x, y, size=10.5, color="red", leader=None, align="left", lead=1.05, rotate=0.0):
    """a red note in Book I's hand (Sue Ellen Francisco). leader: [(x, y)...] ending at the thing
    noted; drawn as a wavering line with a small open ring at the end."""
    c = h.c
    c.saveState()
    c.setFillColorRGB(*h.col(color))
    c.setFont("Hand", size)
    c.translate(x, y)
    c.rotate(rotate)
    for i, ln in enumerate(lines):
        yy = -i * size * lead
        if align == "left":
            c.drawString(0, yy, ln)
        elif align == "right":
            c.drawRightString(0, yy, ln)
        else:
            c.drawCentredString(0, yy, ln)
    c.restoreState()
    if leader:
        pts = catmull(leader, 10) if len(leader) > 2 else leader
        h.stroke(pts, "hair", color, amp=0.25)
        ex, ey = pts[-1]
        h.ring(ex, ey, 1.4, "hair", color)


def wrap(text, font, size, width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(t, font, size) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def spaced(c, text, x, y, font, size, spacing=1.5, align="left", color=INK):
    """letter-spaced small caps, as Book I's running heads"""
    c.setFont(font, size)
    c.setFillColorRGB(*rgb(color))
    w = sum(pdfmetrics.stringWidth(ch, font, size) for ch in text) + spacing * (len(text) - 1)
    if align == "right":
        x -= w
    elif align == "center":
        x -= w / 2
    for ch in text:
        c.drawString(x, y, ch)
        x += pdfmetrics.stringWidth(ch, font, size) + spacing
    return w


def ground_line(h, x0, x1, y, depth=7.0, color="ink"):
    """Book I's ground: a ruled line with leaning hatch beneath"""
    yd = YDown(h, 0, 0, 1.0)
    h.stroke([(x0, y), (x1, y)], "orn", color, amp=0.15)
    x = x0 + 2
    rng = h.rng
    while x < x1 - 2:
        d = depth * rng.uniform(0.6, 1.0)
        h.straight([(x, y - 0.8), (x - d * 0.55, y - d)], "hair", color)
        x += rng.uniform(2.6, 3.8)


def wash(h, pts, color, alpha=0.18, blend="Multiply"):
    c = h.c
    c.saveState()
    if blend:
        c.setBlendMode(blend)
    h.fill_poly(pts, color, alpha)
    c.restoreState()


def blot(h, cx, cy, r, color, alpha=0.12, seed=0, lobes=9):
    """an irregular soft wash, for a tinted ground behind a figure"""
    rng = random.Random(f"blot-{seed}")
    pts = []
    k = [rng.uniform(0.82, 1.12) for _ in range(lobes)]
    for i in range(72):
        a = 2 * math.pi * i / 72
        t = i / 72 * lobes
        j = int(t) % lobes
        f = t - int(t)
        rr = r * (k[j] * (1 - f) + k[(j + 1) % lobes] * f)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a) * 1.0))
    wash(h, pts, color, alpha)


def mark_seal(h, base, x, y, s, color="ink", tally_n=0):
    """one twelve-mark sign as a seal, s points across, top-left at (x, y)"""
    yd = YDown(h, x, y, s)
    tx.mark(yd, base, 0, 0, 1, "orn", color)
    if tally_n:
        tx.tally(yd, tally_n, 0, 0, 1, color)
