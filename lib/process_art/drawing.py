"""Millimetre polylines shared by SVG, PNG and the existing book Hands.

No fonts, clip paths, transforms, fills, or embedded images in the art SVG.
"""
from dataclasses import dataclass, field
from html import escape

import contourpy
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import LineString, Polygon

INK, RED = "#161918", "#a32b24"


@dataclass
class Stroke:
    points: np.ndarray
    color: str = INK
    width: float = .13


@dataclass
class Plate:
    title: str
    width: float = 170
    height: float = 220
    strokes: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add(self, points, color=INK, width=.13, simplify=.025):
        p = np.asarray(points, dtype=float)
        if len(p) < 2:
            return
        if p.ndim != 2 or p.shape[1] != 2 or not np.isfinite(p).all():
            raise ValueError("finite Nx2 path required")
        if (p < 0).any() or (p[:, 0] > self.width).any() or (p[:, 1] > self.height).any():
            raise ValueError("path outside plate")
        if simplify and len(p) > 3:
            p = np.asarray(LineString(p).simplify(simplify).coords)
        if len(p) > 1 and np.linalg.norm(np.diff(p, axis=0), axis=1).sum() > .12:
            self.strokes.append(Stroke(p, color, width))

    def ring(self, x, y, r, color=INK, width=.13):
        t = np.linspace(0, 2*np.pi, max(36, int(r*9)))
        self.add(np.column_stack([x+r*np.cos(t), y+r*np.sin(t)]), color, width)

    def svg(self):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}mm" '
               f'height="{self.height}mm" viewBox="0 0 {self.width} {self.height}">',
               f'<title>{escape(self.title)}</title>',
               '<desc>Process-art study. Coordinates and stroke widths in millimetres. '
               'See the sidecar JSON for process parameters and data provenance.</desc>']
        for color, label in [(INK, "ink"), (RED, "red")]:
            out.append(f'<g id="{label}" fill="none" stroke-linecap="round" stroke-linejoin="round">')
            for s in self.strokes:
                if s.color != color:
                    continue
                d = "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in s.points)
                out.append(f'<path fill="none" stroke="{color}" stroke-width="{s.width:.3f}" d="{d}"/>')
            out.append("</g>")
        return "\n".join(out + ["</svg>", ""])

    def png(self, path, pixels=2000, transparent=False):
        k = pixels/self.width
        # Supersampling preserves the hairlines at thumbnail and placed size.
        scale = 2
        size = (pixels*scale, round(self.height*k*scale))
        image = Image.new("RGBA", size, (0, 0, 0, 0) if transparent else "#f4f0e6")
        d = ImageDraw.Draw(image)
        for s in self.strokes:
            points = [(x*k*scale, y*k*scale) for x, y in s.points]
            d.line(points, fill=s.color, width=max(1, round(s.width*k*scale)), joint="curve")
        image = image.resize((pixels, round(self.height*k)), Image.Resampling.LANCZOS)
        image.save(path, dpi=(k*25.4, k*25.4))

    def draw(self, hand, origin=(0, 0), scale=1):
        """Replay through marks.Hand or PlotHand (origin/scale in caller units)."""
        for s in self.strokes:
            p = s.points*scale + np.asarray(origin)
            weight = "core" if s.width >= .22 else "hair" if s.width < .14 else "orn"
            hand.stroke(p.tolist(), weight=weight, color="red" if s.color == RED else "ink", amp=0)


def contours(plate, field, levels, box=(15, 22, 140, 174), mask=None, color=INK, width=.12):
    """Joined marching contours, optionally masked before geometry extraction."""
    z = np.asarray(field)
    if mask is not None:
        z = np.ma.array(z, mask=~mask)
    cg = contourpy.contour_generator(z=z, name="serial", corner_mask=False)
    x, y, w, h = box
    for level in levels:
        for points in cg.lines(float(level)):
            p = points / [field.shape[1]-1, field.shape[0]-1]
            plate.add(p*[w, h] + [x, y], color, width)


def clipped(plate, points, polygon, color=INK, width=.13):
    """Geometric clipping happens before export, so the book importer sees it."""
    g = LineString(points).intersection(polygon)
    if g.is_empty:
        return
    parts = list(g.geoms) if hasattr(g, "geoms") else [g]
    for part in parts:
        if part.geom_type == "LineString":
            plate.add(np.asarray(part.coords), color, width)


def furniture(plate, number):
    """Sparse registration-like furniture; no encoded or purported ancient text."""
    plate.add([(10, 13), (10, 8), (24, 8)], width=.16)
    plate.add([(146, 8), (160, 8), (160, 13)], width=.16)
    plate.add([(10, 207), (10, 212), (24, 212)], width=.16)
    plate.add([(146, 212), (160, 212), (160, 207)], width=.16)
    plate.add([(72, 207), (98, 207)], width=.10)
    for i in range(number):
        plate.ring(85+(i-(number-1)/2)*2.4, 211, .38, RED, .14)


def specimen_polygon(box=(15, 22, 140, 174), count=400):
    x, y, w, h = box
    t = np.linspace(0, 2*np.pi, count)
    r = 1 + .025*np.sin(7*t) + .014*np.sin(13*t)
    return Polygon(np.column_stack([x+w/2 + w*.48*r*np.cos(t), y+h/2 + h*.48*r*np.sin(t)]))
