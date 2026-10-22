"""Plate compositions for the 2-D distance-field studies (170 × 220 mm, two inks)."""
import numpy as np

from lib.process_art.drawing import INK, RED, Plate, furniture

from . import sdf
from .grid import contours, hatch_by_sign, levels, sample

__all__ = ["apparatus_plate", "tiling_plate", "APPARATUS_VARIANTS", "TILING_VARIANTS"]

BOX = (15, 22, 140, 174)
BOUNDS = (BOX[0], BOX[1], BOX[0] + BOX[2], BOX[1] + BOX[3])

APPARATUS_VARIANTS = {0: "nested inner contours every 2 mm, two red outer offsets",
                      1: "sign-tested hatching in 4 mm bands, alternating 45° and 135°"}
TILING_VARIANTS = {0: "mirrored grid of a stepped glyph, 18 mm period, clipped to a rounded frame",
                   1: "nine-fold polar repeat of the glyph around an annular ring"}


def apparatus_shape():
    """A vessel from booleans: smooth body, rounded neck, chamfered port, stepped notch."""
    body = sdf.union_smooth(sdf.circle(30, (85, 96)), sdf.rounded_box(21, 34, 7, (85, 122)), 12)
    with_neck = sdf.union_round(body, sdf.box(7, 24, (85, 52)), 5)
    with_port = sdf.subtract_chamfer(with_neck, sdf.circle(11, (111, 122)), 4)
    with_notch = sdf.subtract_steps(with_port, sdf.box(24, 7, (58, 146)), 7, 3)
    arm = sdf.rotate(sdf.box(20, 3, (108, 66)), -35, center=(108, 66))
    return sdf.union_round(with_notch, arm, 4)


def apparatus_plate(seed=0, variant=0, resolution=.25):
    if variant not in APPARATUS_VARIANTS:
        raise ValueError(f"variant must be one of {sorted(APPARATUS_VARIANTS)}")
    f = apparatus_shape()
    plate = Plate("Distance-field apparatus")
    furniture(plate, 1)
    values, xs, ys = sample(f, BOUNDS, resolution)
    deepest = -float(values.min())
    records = {}
    if variant == 0:
        isos = [0.0] + [-2.0 * k for k in range(1, int(deepest // 2) + 1)]
        bands = levels(values, xs, ys, isos, simplify=.02)
        for iso, lines in bands.items():
            for line in lines:
                plate.add(line, INK, .16 if iso == 0 else .11)
        outer = levels(values, xs, ys, [3.0, 6.0], simplify=.02)
        for iso, lines in outer.items():
            for line in lines:
                plate.add(line, RED, .10)
        records = {"inner_isos": isos, "outer_isos": [3.0, 6.0],
                   "contour_count": int(sum(len(v) for v in bands.values()) + sum(len(v) for v in outer.values()))}
    else:
        for line in contours(values, xs, ys, 0.0, simplify=.02):
            plate.add(line, INK, .16)
        count = 0
        k = 0
        while 4.0 * k < deepest:
            band = sdf.band(f, 4.0 * k, 4.0 * (k + 1))
            angle = 45.0 if k % 2 == 0 else 135.0
            lines = hatch_by_sign(band, BOUNDS, .9 + .15 * k, angle, step=.2)
            for line in lines:
                plate.add(line, INK, .11)
            count += len(lines)
            k += 1
        for line in contours(values, xs, ys, 3.0, simplify=.02):
            plate.add(line, RED, .10)
        records = {"bands": k, "band_width_mm": 4.0, "hatch_lines": count}
    plate.metadata = {"study": "apparatus", "seed": seed, "variant": variant,
                      "method": APPARATUS_VARIANTS[variant], "resolution_mm": resolution,
                      "deepest_mm": round(deepest, 3), **records,
                      "shape": "union_smooth(circle, rounded_box, 12); union_round(neck box, 5); "
                               "subtract_chamfer(port circle, 4); subtract_steps(notch box, 7, 3); "
                               "union_round(rotated arm, 3)"}
    return plate, {"field": values, "xs": xs, "ys": ys}


def glyph():
    """A small stepped union of a circle and a rotated bar, centred on the origin."""
    return sdf.union_steps(sdf.circle(3.2), sdf.rotate(sdf.box(6.5, 1.4), 30), 2.6, 4)


def tiling_plate(seed=0, variant=0, resolution=.2):
    if variant not in TILING_VARIANTS:
        raise ValueError(f"variant must be one of {sorted(TILING_VARIANTS)}")
    cx, cy = BOX[0] + BOX[2] / 2, BOX[1] + BOX[3] / 2
    plate = Plate("Distance-field tilings")
    furniture(plate, 2)
    if variant == 0:
        frame = sdf.rounded_box(BOX[2] / 2 - 4, BOX[3] / 2 - 4, 14, (cx, cy))
        tiles = sdf.translate(sdf.repeat_mirror(sdf.scale(glyph(), 1.15), 15.0), (cx, cy))
        shape = sdf.intersect(tiles, sdf.offset(frame, -3))
        values, xs, ys = sample(shape, BOUNDS, resolution)
        bands = levels(values, xs, ys, [0.0, -1.2], simplify=.02)
        for iso, lines in bands.items():
            for line in lines:
                plate.add(line, INK, .14 if iso == 0 else .10)
        fv, _, _ = sample(frame, BOUNDS, resolution)
        for line in contours(fv, xs, ys, 0.0, simplify=.02):
            plate.add(line, RED, .12)
        records = {"period_mm": 15.0, "glyph_scale": 1.15, "isos": [0.0, -1.2],
                   "contour_count": int(sum(len(v) for v in bands.values()))}
    else:
        ring = sdf.annular(sdf.circle(44, (cx, cy)), 9)
        petals = sdf.repeat_polar(sdf.translate(sdf.scale(glyph(), 2.2), (cx + 44, cy)), 9, (cx, cy))
        shape = sdf.union_smooth(ring, petals, 4)
        values, xs, ys = sample(shape, BOUNDS, resolution)
        isos = [0.0, -1.5, -3.0, -4.5, -6.0]
        bands = levels(values, xs, ys, isos, simplify=.02)
        for iso, lines in bands.items():
            for line in lines:
                plate.add(line, INK, .15 if iso == 0 else .10)
        core = sdf.repeat_polar(sdf.translate(sdf.scale(glyph(), 1.1), (cx + 22, cy)), 9, (cx, cy))
        cv, _, _ = sample(core, BOUNDS, resolution)
        for line in contours(cv, xs, ys, 0.0, simplify=.02):
            plate.add(line, RED, .12)
        records = {"fold": 9, "isos": isos, "contour_count": int(sum(len(v) for v in bands.values()))}
    plate.metadata = {"study": "tiling", "seed": seed, "variant": variant, "method": TILING_VARIANTS[variant],
                      "resolution_mm": resolution, **records,
                      "glyph": "union_steps(circle 3.2, box 6.5 × 1.4 rotated 30°, r 2.6, 4 steps)"}
    return plate, {"field": values, "xs": xs, "ys": ys}
