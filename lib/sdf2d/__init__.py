"""Two-dimensional signed distance fields for pen drawing.

After Karsten Schmidt's thi.ng ``geom-sdf`` package, with the primitive and
operator formulas of Inigo Quilez and Mercury's hg_sdf; see
techniques/15-thing-ports and docs/THING_TECHNIQUES.md.
"""

from . import sdf
from .grid import band_count, contours, hatch_by_sign, levels, sample
from .sdf import (annular, band, box, circle, ellipse, field, intersect, intersect_chamfer, intersect_round,
                  intersect_smooth, intersect_steps, mirror_x, mirror_y, offset, polygon, polyline, repeat,
                  repeat_mirror, repeat_polar, rotate, rounded_box, scale, segment, subtract, subtract_chamfer,
                  subtract_round, subtract_smooth, subtract_steps, translate, triangle, union, union_chamfer,
                  union_round, union_smooth, union_steps)

__all__ = ["sdf", "band_count", "contours", "hatch_by_sign", "levels", "sample"] + sdf.__all__
