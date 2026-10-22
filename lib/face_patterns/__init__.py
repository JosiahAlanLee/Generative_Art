"""Two-dimensional generators on the planar faces of 3D scenes.

See studies/infernal-landscape/FACE-PATTERNS.md for the first use.
"""

from .mapping import (Frame, clip_polyline, clip_polylines, contour_on_face, hatch_polygon, inside,
                      level_spacing_px, lift, newell_normal, plane_frame, stride_for_spacing, to_uv,
                      world_spacing)

__all__ = ["Frame", "clip_polyline", "clip_polylines", "contour_on_face", "hatch_polygon", "inside",
           "level_spacing_px", "lift", "newell_normal", "plane_frame", "stride_for_spacing", "to_uv",
           "world_spacing"]
