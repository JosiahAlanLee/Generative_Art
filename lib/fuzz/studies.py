"""Plate compositions for the fuzz studies (170 × 220 mm, two inks)."""
from math import cos, pi, sin

import numpy as np
from shapely.geometry import Polygon

from lib.process_art.drawing import INK, RED, Plate, furniture

from .curves import SCHEMES, cubics_to_polyline, polygon_to_cubic, subdivide
from .fuzz import compose, dot_pen, dots_as_rings, fuzzy_line, fuzzy_polygon, hatch_fill, hatch_pen

__all__ = ["passes_plate", "fills_plate", "subdivision_plate"]

BOX = (15, 22, 140, 174)


def _blob(cx, cy, r, rng, n=9, rough=.22):
    """An irregular closed polygon of ``n`` vertices around (cx, cy)."""
    t = np.linspace(0, 2 * pi, n, endpoint=False) + rng.uniform(-.12, .12, n)
    rr = r * (1 + rng.uniform(-rough, rough, n))
    return np.column_stack([cx + rr * np.cos(t), cy + rr * np.sin(t)])


def _shapes(cx, cy, size, rng):
    """A blob, a rectangle and a triangle around a centre; the same trio in every cell."""
    s = size
    blob = _blob(cx - s * .55, cy, s * .34, rng)
    rect = np.array([(cx + s * .12, cy - s * .36), (cx + s * .62, cy - s * .36),
                     (cx + s * .62, cy + s * .02), (cx + s * .12, cy + s * .02)])
    tri = np.array([(cx + s * .14, cy + s * .14), (cx + s * .66, cy + s * .2), (cx + s * .36, cy + s * .46)])
    return [blob, rect, tri]


def passes_plate(seed=0):
    """The same three shapes drawn exact, then with one to three fuzzy passes of rising jitter.

    Row by row: exact polygons; one curved pass with 0.25 mm jitter; two passes
    at 0.4 mm; three passes at 0.6 mm. The left column keeps straight edges
    (``curve=False``), the right column smooths each pass through its jittered
    vertices.
    """
    rng = np.random.default_rng(seed)
    x0, y0, w, h = BOX
    cols, rows, gap = 2, 4, 5
    cw, ch = (w - gap) / cols, (h - gap * 3) / rows
    plate = Plate("Fuzzy passes")
    furniture(plate, 1)
    settings = [(0, 0.0), (1, .25), (2, .4), (3, .6)]
    base = np.random.default_rng(seed + 1)
    shapes = _shapes(0, 0, min(cw, ch), base)
    records = []
    for r, (passes, jitter) in enumerate(settings):
        for c, curve in enumerate((False, True)):
            cx, cy = x0 + c * (cw + gap) + cw / 2, y0 + r * (ch + gap) + ch / 2
            count = 0
            for shape in shapes:
                pts = shape + [cx, cy]
                if passes == 0:
                    plate.add(np.vstack([pts, pts[:1]]), INK, .16)
                    count += 1
                    continue
                for line in fuzzy_polygon(pts, rng, passes, jitter, curve=curve, samples=8):
                    plate.add(line, INK, .13, simplify=.01)
                    count += 1
            frame = [(cx - cw / 2, cy - ch / 2), (cx + cw / 2, cy - ch / 2), (cx + cw / 2, cy + ch / 2),
                     (cx - cw / 2, cy + ch / 2), (cx - cw / 2, cy - ch / 2)]
            plate.add(frame, RED, .10)
            records.append({"row": r, "column": c, "passes": passes, "jitter_mm": jitter,
                            "curve": curve, "strokes": count})
    plate.metadata = {"study": "passes", "seed": seed, "cells": records,
                      "reading_order": "rows: exact, 1, 2, 3 passes; left column straight, right curved"}
    return plate, {"shapes": np.vstack(shapes)}


def fills_plate(seed=0):
    """Six fills on the same blob: hatch at two angles, jittered hatch, cross hatch, dots, composed."""
    rng = np.random.default_rng(seed)
    x0, y0, w, h = BOX
    cols, rows, gap = 2, 3, 6
    cw, ch = (w - gap) / cols, (h - gap * 2) / rows
    plate = Plate("Composable fills")
    furniture(plate, 2)
    base = np.random.default_rng(seed + 7)
    blob = _blob(0, 0, min(cw, ch) * .4, base, n=11, rough=.18)
    fills = [
        ("hatch 45°, 1.1 mm", lambda poly, g: hatch_fill(poly, 1.1, 45)),
        ("hatch 160°, 0.8 mm, inset 0.6", lambda poly, g: hatch_fill(poly, .8, 160, inset=.6)),
        ("hatch 30°, jitter 0.25", lambda poly, g: hatch_fill(poly, 1.0, 30, g, jitter=.25)),
        ("cross hatch pen, two passes", hatch_pen(1.4, 60, passes=2, jitter=.1, cross=True)),
        ("dot screen 1.3 mm", dot_pen(1.3, radius=.14, jitter=.3)),
        ("hatch 100° + dots, composed", compose(lambda poly, g: hatch_fill(poly, 1.6, 100, g, jitter=.12),
                                                  dot_pen(1.7, radius=.12, jitter=.4))),
    ]
    records = []
    for i, (label, fill) in enumerate(fills):
        cx, cy = x0 + (i % cols) * (cw + gap) + cw / 2, y0 + (i // cols) * (ch + gap) + ch / 2
        pts = blob + [cx, cy]
        poly = Polygon(pts)
        lines = fill(poly, rng)
        for line in lines:
            plate.add(line, INK, .12, simplify=.01)
        # The outline is a two-pass fuzzy edge in red, drawn after the fill.
        for line in fuzzy_polygon(pts, rng, 2, .2, curve=True, samples=8):
            plate.add(line, RED, .13, simplify=.01)
        records.append({"cell": i, "fill": label, "lines": len(lines)})
    plate.metadata = {"study": "fills", "seed": seed, "cells": records,
                      "reading_order": "left to right, then down"}
    return plate, {"blob": blob}


DRAWN_SCHEMES = ("chaikin", "cubic", "dlg", "displace")


def subdivision_plate(seed=0):
    """Four schemes on the same rough octagon, one to four iterations nested; the control polygon in red.

    ``midpoint`` and ``thirds`` only insert points, so they are not drawn.
    """
    x0, y0, w, h = BOX
    cols, rows, gap = 2, 2, 8
    cw, ch = (w - gap) / cols, (h - gap) / rows
    plate = Plate("Subdivision schemes")
    furniture(plate, 3)
    base = np.random.default_rng(seed + 3)
    control = _blob(0, 0, min(cw, ch) * .44, base, n=8, rough=.3)
    records = []
    for i, scheme in enumerate(DRAWN_SCHEMES):
        cx, cy = x0 + (i % cols) * (cw + gap) + cw / 2, y0 + (i // cols) * (ch + gap) + ch / 2
        pts = control + [cx, cy]
        plate.add(np.vstack([pts, pts[:1]]), RED, .12)
        counts = []
        for k in range(1, 5):
            shrink = 1 - .14 * (k - 1)
            p = (pts - [cx, cy]) * shrink + [cx, cy]
            curve = subdivide(p, scheme, k, closed=True, rng=np.random.default_rng(seed + 11 + k), amplitude=.18)
            closed = np.vstack([curve, curve[:1]])
            plate.add(closed, INK, .13 if scheme != "displace" else .11, simplify=.005)
            counts.append(int(len(curve)))
        records.append({"cell": i, "scheme": scheme, "points_after_1_to_4": counts})
    plate.metadata = {"study": "subdivision", "seed": seed, "cells": records,
                      "schemes_not_drawn": [s for s in SCHEMES if s not in DRAWN_SCHEMES],
                      "reading_order": "chaikin, cubic / dlg, displace; four iterations as shrinking copies, "
                                       "the outermost is one iteration"}
    return plate, {"control": control}
