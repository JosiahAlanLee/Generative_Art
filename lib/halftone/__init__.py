"""Raster to pen: dithering, bitmap run tracing and Poisson stippling.

After Karsten Schmidt's thi.ng ``pixel-dither``, ``geom-trace-bitmap`` and
``poisson`` packages; see techniques/15-thing-ports and docs/THING_TECHNIQUES.md.
"""

from .dither import KERNELS, bayer, error_diffuse, masks, ordered_dither, specimen, threshold
from .poisson import poisson_sample, stratified_grid, tone_radius
from .trace import trace_runs, to_mm

__all__ = ["KERNELS", "bayer", "error_diffuse", "masks", "ordered_dither", "specimen", "threshold",
           "poisson_sample", "stratified_grid", "tone_radius", "trace_runs", "to_mm"]
