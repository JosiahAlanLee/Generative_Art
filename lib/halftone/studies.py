"""Plate compositions for the halftone studies (170 × 220 mm, two inks).

Each study returns ``(plate, state)``: a ``lib.process_art.drawing.Plate`` and
a dict of arrays for the sidecar NPZ. Geometry is absolute millimetres, so the
book's ``svgimport`` reads it. The raster input is the synthetic specimen
from ``dither.specimen`` unless a tone array is passed.
"""
import numpy as np

from lib.process_art.drawing import INK, RED, Plate, furniture

from .dither import bayer, error_diffuse, masks, ordered_dither, resample, specimen
from .poisson import poisson_sample, stratified_grid, tone_radius
from .trace import trace_runs, to_mm

__all__ = ["halftone_plate", "kernels_plate", "stipple_plate", "KERNEL_CELLS", "STIPPLE_VARIANTS"]

BOX = (15, 22, 140, 174)

KERNEL_CELLS = ["floyd-steinberg", "atkinson", "jarvis-judice-ninke", "stucki", "sierra-lite", "bayer-8"]

STIPPLE_VARIANTS = {
    0: "uniform Poisson disc, 1.3 mm, constant dots",
    1: "tone-driven Poisson disc, 0.5–2.8 mm, dots sized by tone",
    2: "stratified grid, 1.6 mm cells, dots sized by tone",
}


def _tone(tone, cell, box):
    """The specimen (or a supplied tone array) resampled to one pixel per cell."""
    x, y, w, h = box
    width, height = int(round(w / cell)), int(round(h / cell))
    if tone is None:
        return specimen(width, height, 0)
    return resample(tone, width, height)


def _draw_traced(plate, traced, cell, origin, color, width, dot):
    segments, points = to_mm(traced, cell, origin)
    for seg in segments:
        plate.add(seg, color, width)
    for px, py in points:
        plate.ring(px, py, dot, color, width)
    return len(segments), len(points)


def spiral_dot(plate, x, y, r, color=INK, width=.12, pitch=.11):
    """A filled dot for a pen: a ring when small, otherwise an Archimedean spiral at pen pitch."""
    if r <= pitch * 1.4:
        plate.ring(x, y, max(r, .05), color, width)
        return
    turns = r / pitch
    t = np.linspace(0, 2 * np.pi * turns, max(24, int(turns * 28)))
    rad = r * t / t[-1]
    plate.add(np.column_stack([x + rad * np.cos(t), y + rad * np.sin(t)]), color, width, simplify=.012)


def halftone_plate(seed=0, kernel="floyd-steinberg", cell=.38, levels=3, serpentine=True,
                   directions=("h", "v", "d1", "d2", "p"), tone=None):
    """Error-diffused tones traced into hairline runs; the darkest tone in ink, the next in red.

    ``cell`` is the pixel pitch in millimetres. With ``levels=3`` the image is
    quantised to black, mid and white; black pixels are traced in ink and mid
    pixels in red, so the two pens carry the halftone between them.
    """
    z = _tone(tone, cell, BOX)
    q = error_diffuse(z, kernel, levels, serpentine=serpentine)
    layers = masks(q, levels)
    plate = Plate("Halftone runs")
    furniture(plate, 1)
    counts = {}
    inks = [INK, RED] + [RED] * max(0, len(layers) - 2)
    for k, (mask, color) in enumerate(zip(layers, inks)):
        traced = trace_runs(mask, directions, min_len=2, max_len=max(4, int(round(12 / cell))))
        segs, pts = _draw_traced(plate, traced, cell, BOX[:2], color, .13 if k == 0 else .12, cell * .22)
        counts[f"tone_{k}"] = {"pixels": int(mask.sum()), "segments": segs, "points": pts}
    plate.metadata = {"study": "halftone", "seed": seed, "kernel": kernel, "cell_mm": cell,
                      "levels": levels, "serpentine": serpentine, "directions": list(directions),
                      "pixels": [int(z.shape[1]), int(z.shape[0])], "counts": counts,
                      "input": "synthetic specimen" if tone is None else "supplied tone array",
                      "limits": "runs are straight between pixel centres; no contour tracing; "
                                "run order is raster order, not pen-travel order"}
    return plate, {"tone": z, "quantised": q}


def kernels_plate(seed=0, cell=.30, tone=None, kernels=None):
    """The same crop under six dithers, two columns by three rows, traced identically."""
    kernels = kernels or KERNEL_CELLS
    x0, y0, w, h = BOX
    cols, rows, gap = 2, 3, 6
    cw, ch = (w - gap * (cols - 1)) / cols, (h - gap * (rows - 1)) / rows
    width, height = int(round(cw / cell)), int(round(ch / cell))
    z = specimen(width, height, seed) if tone is None else resample(tone, width, height)
    plate = Plate("Dither kernels")
    furniture(plate, 2)
    records = []
    for i, name in enumerate(kernels[:cols * rows]):
        cx, cy = x0 + (i % cols) * (cw + gap), y0 + (i // cols) * (ch + gap)
        if name.startswith("bayer"):
            size = int(name.split("-")[1]) if "-" in name else 4
            q = ordered_dither(z, size, 2)
        else:
            q = error_diffuse(z, name, 2, serpentine=True)
        dark = masks(q, 2)[0]
        traced = trace_runs(dark, ("h", "v", "d1", "d2", "p"), 2, max_len=24)
        segs, pts = _draw_traced(plate, traced, cell, (cx, cy), INK, .12, cell * .22)
        frame = [(cx, cy), (cx + cw, cy), (cx + cw, cy + ch), (cx, cy + ch), (cx, cy)]
        plate.add(frame, RED, .10)
        records.append({"kernel": name, "column": i % cols, "row": i // cols,
                        "black_pixels": int(dark.sum()), "segments": segs, "points": pts})
    plate.metadata = {"study": "kernels", "seed": seed, "cell_mm": cell, "cells": records,
                      "reading_order": "left to right, then down; the red frames bound each crop",
                      "bayer_matrix_8": bayer(8).tolist(),
                      "input": "synthetic specimen" if tone is None else "supplied tone array"}
    return plate, {"tone": z}


def stipple_plate(seed=0, variant=1, tone=None):
    """Dots whose density, or size, carries the tone."""
    if variant not in STIPPLE_VARIANTS:
        raise ValueError(f"variant must be one of {sorted(STIPPLE_VARIANTS)}")
    rng = np.random.default_rng(seed)
    x0, y0, w, h = BOX
    bounds = (x0, y0, x0 + w, y0 + h)
    z = specimen(280, 348, seed) if tone is None else np.asarray(tone, dtype=float)

    def tone_at(p):
        u = (p[0] - x0) / w * (z.shape[1] - 1)
        v = (p[1] - y0) / h * (z.shape[0] - 1)
        return float(z[int(np.clip(round(v), 0, z.shape[0] - 1)), int(np.clip(round(u), 0, z.shape[1] - 1))])

    plate = Plate("Stipples")
    furniture(plate, 3)
    if variant == 0:
        points = poisson_sample(bounds, 1.3, rng, quality=800, iterations=2)
        radii = np.full(len(points), .16)
    elif variant == 1:
        fn, r_min = tone_radius(z, bounds, .5, 2.8, gamma=1.15)
        points = poisson_sample(bounds, fn, rng, min_radius=r_min, quality=1200, iterations=3)
        radii = np.array([.1 + .14 * (1 - tone_at(p)) for p in points])
    else:
        points = stratified_grid(bounds, 1.6, rng, separation=.6)
        radii = np.array([.04 + .52 * (1 - tone_at(p)) ** 1.3 for p in points])
    # Keep every dot inside the plate box; drop dots too small for the pen.
    keep = (points[:, 0] - radii >= x0) & (points[:, 0] + radii <= x0 + w) & \
           (points[:, 1] - radii >= y0) & (points[:, 1] + radii <= y0 + h) & (radii > .07)
    points, radii = points[keep], radii[keep]
    for (px, py), r in zip(points, radii):
        spiral_dot(plate, px, py, float(r))
    plate.metadata = {"study": "stipple", "seed": seed, "variant": variant,
                      "method": STIPPLE_VARIANTS[variant], "dots": int(len(points)),
                      "dot_radius_mm": [float(radii.min()), float(radii.max())] if len(radii) else None,
                      "input": "synthetic specimen" if tone is None else "supplied tone array",
                      "limits": "dots above 0.15 mm are spirals at 0.11 mm pitch, smaller ones rings; "
                                "candidate order; no pen-travel ordering"}
    return plate, {"tone": z, "points": points, "radii": radii}
