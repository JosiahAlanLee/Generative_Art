"""Clavicula Graduum - Tabula III - The Cut (native vector plate).

The Measurer of Absences, antlered, holds an empty frame out to the seam. Everything on the
left of the seam moves: a current of flowing lines runs into the frame and stops at the red
line. Everything on the right is written down: a ruled table whose cells carry the fourth
carrier. The figure stands on both sides of the cut, drawn in the Keeper's own stroke
vocabulary from the Tabula V figure library, translated.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "common", "plot"))
sys.path.insert(0, os.path.join(REPO, "books", "04_graduum", "plates", "v-native"))
from plate import Plate, validate  # noqa: E402
from plotkit import catmull, lerp, Polygon, LineString, Point, voronoi_net  # noqa: E402
import figure as fig  # noqa: E402
import marks  # noqa: E402

DX, DY = -50.0, 5.0            # the Keeper's figure, moved left to stand at the seam
SEAM = 105.0
FRAME_BOX = (98.0, 89.0, 25.0, 32.0)       # x, y, w, h: the empty frame held out to the seam
TABLE = (112.0, 80.0, 194.0, 226.0, 6, 20)  # x0, y0, x1, y1, cols, rows
STREAM_Y = (80.0, 220.0)


class Shift:
    """a hand that draws everything moved by (DX, DY)"""

    def __init__(self, h):
        self.h, self.rng = h, h.rng

    def _t(self, pts):
        return [(x + DX, y + DY) for x, y in pts]

    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None, attrs=""):
        self.h.stroke(self._t(pts), weight, color, closed, amp, attrs)

    def straight(self, pts, weight="orn", color="ink", closed=False, attrs=""):
        self.h.straight(self._t(pts), weight, color, closed, attrs)

    def dot(self, x, y, r, color="ink"):
        self.h.dot(x + DX, y + DY, r, color)

    def ring(self, x, y, r, weight="orn", color="ink"):
        self.h.ring(x + DX, y + DY, r, weight, color)


def measurer(P):
    """the Keeper's body without bars or dial; antlers on the hood; the sleeve holds the frame"""
    H, rng = Shift(P.art), P.rng
    robe = Polygon(fig.robe_outline()).buffer(0)
    hc = (117.5, 92.5)
    hood = Polygon(fig.hood_outline(hc)).buffer(0)
    sl_l, sl_r, sl_c = fig.ribbon(fig.sleeve_path(), 8.5, 4.2)
    sleeve = Polygon(sl_l + sl_r[::-1]).buffer(0)
    body = robe.difference(hood.buffer(0.5)).difference(sleeve.buffer(0.7))
    # the fall of the robe
    for pts in fig.flow_lines(robe, rng, 103, 211.2, 46, wander=0.11):
        for seg in fig.clip_polyline(pts, body):
            H.stroke(seg, "hair", "ink", amp=0.35)
    for k in range(30):
        x = rng.uniform(95, 135)
        y0 = 212.4 + 1.2 * math.sin((x - 93) / 43 * 6.283)
        y1 = y0 + rng.uniform(1.0, 9.0)
        H.stroke([(x, y0), (x, y1)], "hair", "ink", amp=0.4)
        H.dot(x, y1 + 0.4, 0.3, "ink")
    for part in (body.geoms if hasattr(body, "geoms") else [body]):
        H.stroke(list(part.exterior.coords), "orn", "ink", amp=0.5)
    # sleeve
    for k in range(9):
        u = (k + 0.5) / 9
        H.stroke([lerp(a, b, u) for a, b in zip(sl_l, sl_r)], "hair", "ink", amp=0.4)
    H.stroke(sl_l, "orn", "ink", amp=0.4)
    H.stroke(sl_r, "orn", "ink", amp=0.4)
    H.stroke([sl_l[-1], sl_r[-1]], "orn", "ink", amp=0.2)
    # hood, net on the crown, drape below
    hood_pts = fig.hood_outline(hc)
    H.stroke(hood_pts, "core", "ink", amp=0.4)
    opening = Polygon([fig.head_local((5.2 + 5.6 * math.cos(math.radians(a)), 0.8 + 8.2 * math.sin(math.radians(a))), hc) for a in range(0, 360, 8)])
    cloth = Polygon(hood_pts).buffer(-0.9).difference(opening.buffer(0.8))
    crown_zone = Polygon([fig.head_local(p, hc) for p in ((-14, -16), (14, -16), (14, -7), (-14, -7))])
    voronoi_net(H, cloth.intersection(crown_zone), 24, rng, "hair", "ink")
    hminy, hmaxy = cloth.bounds[1], cloth.bounds[3]
    for pts in fig.flow_lines(cloth.difference(crown_zone), rng, hminy, hmaxy + 1, 16, wander=0.08, step=1.0):
        for seg in fig.clip_polyline(pts, cloth.difference(crown_zone.buffer(0.3))):
            H.stroke(seg, "hair", "ink", amp=0.35)
    # the face: the profile with no eye drawn; the Measurer measures absences
    prof = [(5.0, -6.4), (6.9, -3.6), (9.6, -0.4), (7.4, 1.1), (8.0, 3.0), (6.3, 5.2), (3.4, 7.2), (0.6, 8.0)]
    H.stroke(catmull([fig.head_local(p, hc) for p in prof], 8), "core", "ink", amp=0.3)
    ex, ey = fig.head_local((3.8, -2.9), hc)
    H.ring(ex, ey, 1.05, "orn", "ink")
    H.stroke([fig.head_local((1.4, -4.9), hc), fig.head_local((5.6, -5.2), hc)], "hair", "ink", amp=0.2)
    # antlers: two branching beams from the crown, drawn in the page frame
    for sgn in (-1, 1):
        root = fig.head_local((1 + sgn * 4.5, -13), hc)
        beam = [root, (root[0] + sgn * 2.5 + 1.5, root[1] - 8), (root[0] + sgn * 6 + 3, root[1] - 15), (root[0] + sgn * 8 + 5, root[1] - 22)]
        c = catmull(beam, 8)
        H.stroke(c, "core", "ink", amp=0.3)
        for t, side, ln in ((0.35, -1, 7), (0.6, 1, 6), (0.8, -1, 5)):
            q = c[int(t * (len(c) - 1))]
            tine = [q, (q[0] + sgn * side * 2.5, q[1] - ln * 0.6), (q[0] + sgn * side * 4.0 + sgn * 1.0, q[1] - ln)]
            H.stroke(catmull(tine, 5), "orn", "ink", amp=0.3)
            H.dot(tine[-1][0], tine[-1][1], 0.3, "ink")
        H.dot(c[-1][0], c[-1][1], 0.35, "ink")
    # what the streams must avoid, in page coordinates
    def t(poly):
        return Polygon([(x + DX, y + DY) for x, y in poly.exterior.coords])
    ant = Polygon([(hc[0] + DX - 12, hc[1] + DY - 40), (hc[0] + DX + 22, hc[1] + DY - 40), (hc[0] + DX + 22, hc[1] + DY - 10), (hc[0] + DX - 12, hc[1] + DY - 10)])
    return t(robe).union(t(hood)).union(t(sleeve)).buffer(1.6).union(ant)


def streams(P, avoid):
    """the left of the seam moves: a current of lines running into the frame and stopping at the seam"""
    h, rng = P.art, P.rng
    fx, fy, fw, fh = FRAME_BOX
    y0, y1 = STREAM_Y
    n = 30
    for k in range(n):
        y = y0 + (y1 - y0) * (k + 0.5) / n
        in_frame = fy + 1.5 < y < fy + fh - 1.5
        x_end = SEAM - 0.8 if in_frame else fx - 3.0
        pts = [(16.0, y)]
        x = 16.0
        while x < x_end - 6:
            x += rng.uniform(9, 14)
            pts.append((min(x, x_end - 3), y + rng.uniform(-2.2, 2.2) * (1 - abs(2 * (y - y0) / (y1 - y0) - 1)) ** 0.5))
        pts.append((x_end, y + rng.uniform(-0.6, 0.6)))
        c = catmull(pts, 6)
        geom = LineString(c).difference(avoid)
        for part in (geom.geoms if hasattr(geom, "geoms") else [geom]):
            if part.length > 2:
                h.stroke(list(part.coords), "hair", "ink", amp=0.4)


def table(P):
    """the right of the seam is written down: a ruled table; each cell a mark of the fourth carrier"""
    h = P.art
    x0, y0, x1, y1, cols, rows = TABLE
    cw, rh = (x1 - x0) / cols, (y1 - y0) / rows
    for c in range(cols + 1):
        h.straight([(x0 + c * cw, y0), (x0 + c * cw, y1)], "hair" if c else "orn", "ink")
    for r in range(rows + 1):
        h.straight([(x0, y0 + r * rh), (x1, y0 + r * rh)], "hair" if r else "orn", "ink")
    bl = P.bits()
    i = 0
    for r in range(rows):
        for c in range(cols):
            b = bl[i] if i < len(bl) else (1 if P.rng.random() < 0.3 else 0)
            if b:
                cx, cy = x0 + (c + 0.5) * cw, y0 + (r + 0.5) * rh
                h.stroke([(cx - 1.6, cy + 1.0), (cx + 1.6, cy - 1.0)], "orn", "ink", amp=0.15)
                P.tag_last(h, "cell", i)
            i += 1
    P.mark_carrier("the table's cells, row by row from the top-left", "a tick = b, empty = a", i, tag="cell")


def frame_and_seam(P):
    h = P.art
    fx, fy, fw, fh = FRAME_BOX
    h.stroke([(fx, fy), (fx + fw, fy), (fx + fw, fy + fh), (fx, fy + fh)], "core", "ink", closed=True, amp=0.2)
    h.stroke([(fx + 1.2, fy + 1.2), (fx + fw - 1.2, fy + 1.2), (fx + fw - 1.2, fy + fh - 1.2), (fx + 1.2, fy + fh - 1.2)], "hair", "ink", closed=True, amp=0.2)
    # the seam: one red line, the whole height, through the frame
    h.stroke([(SEAM, 76), (SEAM, 228)], "orn", "red", amp=0.08)
    # the substrate under the moving side: conditions beneath
    marks.sig_ground(h, 16, 92, 222, 6.0, step=5.0)


def main(out_dir):
    P = Plate("III", "The Cut", "A LEVEL IS A RECORD THAT OUTLIVES ITS DYNAMICS", "iii-the-cut",
              "The left moved. The right was written down.", 3, "THE RECORD KEEPS PACE", 1973,
              strap="RATE DEPENDENT / RATE INDEPENDENT")
    avoid = measurer(P)
    fx, fy, fw, fh = FRAME_BOX
    avoid = avoid.union(Polygon([(16, 216), (92, 216), (92, 234), (16, 234)]))
    streams(P, avoid)
    table(P)
    frame_and_seam(P)
    P.label("THE MEASURER OF ABSENCES", 16, 78, 2.5)
    P.label("WRITTEN DOWN", 194, 78, 2.5, "right")
    P.label("THE CUT", SEAM, 232.5, 2.5, "center")
    P.furniture()
    P.caption_strip()
    P.export(out_dir, {"seam_x": SEAM, "frame": FRAME_BOX, "table": TABLE})


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
    main(out)
    validate(out)
