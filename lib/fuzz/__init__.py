"""Hand-drawn passes, composable fills and subdivision curves.

After Karsten Schmidt's thi.ng ``geom-fuzz``, ``geom-subdiv-curve`` and
``geom-splines`` packages; see techniques/15-thing-ports and
docs/THING_TECHNIQUES.md.
"""

from .curves import SCHEMES, cubic_points, cubics_to_polyline, polygon_to_cubic, subdivide
from .fuzz import (as_polygon, compose, dot_fill, dot_pen, dots_as_rings, fuzzy_line, fuzzy_polygon,
                   hatch_fill, hatch_pen, union)

__all__ = ["SCHEMES", "cubic_points", "cubics_to_polyline", "polygon_to_cubic", "subdivide",
           "as_polygon", "compose", "dot_fill", "dot_pen", "dots_as_rings", "fuzzy_line", "fuzzy_polygon",
           "hatch_fill", "hatch_pen", "union"]
