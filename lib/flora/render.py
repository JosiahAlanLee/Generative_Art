"""Orthographic plant engraving with sampled surface visibility, in millimetres.

The depth buffer is internal only. SVGs contain surviving paths, never images,
white cover shapes or clip paths. Visibility is approximate at ``pixels_per_mm``.
"""
from dataclasses import dataclass, field
from html import escape
import json
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import LineString
from .model import Stroke, unit


@dataclass
class Drawing:
    width: float
    height: float
    paths: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    widths: dict = field(default_factory=dict)      # pen per role in mm; 0.16 where unset

    def svg(self):
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" width="{self.width}mm" height="{self.height}mm" viewBox="0 0 {self.width} {self.height}">',
               '<title>Southwest Wisconsin plant study</title>',
               '<metadata>'+escape(json.dumps(self.metadata))+'</metadata>']
        for role in sorted({r for r, _ in self.paths}):
            pen = self.widths.get(role, .16)
            out.append(f'<g id="{role}" inkscape:groupmode="layer" inkscape:label="{role}" fill="none" stroke="#202b24" stroke-width="{pen:g}" stroke-linecap="round" stroke-linejoin="round">')
            for r, p in self.paths:
                if r == role:
                    out.append('<path d="M'+' L'.join(f'{x:.3f},{y:.3f}' for x, y in p)+'"/>')
            out.append('</g>')
        return '\n'.join(out+['</svg>', ''])

    def png(self, path, pixels=1400):
        k = pixels/self.width*2
        im = Image.new('RGB', (round(self.width*k), round(self.height*k)), '#f6f2e8')
        d = ImageDraw.Draw(im)
        for role, pts in self.paths:
            d.line([tuple(v) for v in pts*k], fill='#202b24', width=max(1, round(self.widths.get(role, .16)*k)))
        im.resize((pixels, round(self.height/self.width*pixels)), Image.Resampling.LANCZOS).save(path)

    def stats(self):
        return dict(paths=len(self.paths), pen_down_metres=round(sum(
            np.linalg.norm(np.diff(p, axis=0), axis=1).sum() for _, p in self.paths)/1000, 3))


def camera(azimuth=18, elevation=10):
    a, e = np.deg2rad([azimuth, elevation])
    toward = np.array([np.sin(a)*np.cos(e), -np.cos(a)*np.cos(e), np.sin(e)])
    right = np.array([np.cos(a), np.sin(a), 0])
    up = np.cross(toward, right)
    return np.array([right, -up, toward])


def raster_triangle(buf, owners, triangle, owner):
    a, b, c = triangle
    lo = np.maximum(np.floor(triangle[:, :2].min(0)).astype(int), 0)
    hi = np.minimum(np.ceil(triangle[:, :2].max(0)).astype(int), [buf.shape[1]-1, buf.shape[0]-1])
    if (hi < lo).any():
        return
    den = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den) < 1e-12:
        return
    yy, xx = np.mgrid[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
    u = ((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
    v = ((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
    w = 1-u-v; z = u*a[2]+v*b[2]+w*c[2]
    sl = np.s_[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
    hit = (u >= -1e-8)&(v >= -1e-8)&(w >= -1e-8)&(z > buf[sl])
    buf[sl][hit] = z[hit]; owners[sl][hit] = owner


def silhouettes(surface, toward, owner):
    verts, tri = surface.vertices, surface.triangles
    normal = np.cross(verts[tri[:, 1]]-verts[tri[:, 0]], verts[tri[:, 2]]-verts[tri[:, 0]])
    front = normal@toward >= 0
    edges = {}
    for face, facing in zip(tri, front):
        for a, b in zip(face, np.roll(face, -1)):
            edges.setdefault(tuple(sorted((a, b))), []).append(facing)
    selected = {edge for edge, sides in edges.items()
                if len(sides) == 1 or any(sides) != all(sides)}
    adjacent = {}
    for a, b in selected:
        adjacent.setdefault(a, set()).add(b); adjacent.setdefault(b, set()).add(a)
    paths = []
    while selected:
        a, b = min(selected); selected.remove((a, b)); chain = [a, b]
        for reverse in (False, True):
            if reverse:
                chain.reverse()
            while True:
                nxt = [v for v in sorted(adjacent[chain[-1]])
                       if tuple(sorted((chain[-1], v))) in selected]
                if not nxt:
                    break
                v = nxt[0]; selected.remove(tuple(sorted((chain[-1], v)))); chain.append(v)
        paths.append(Stroke(verts[chain], surface.role, 0, owner))
    return paths


def render(plant, width=100, height=140, *, azimuth=18, elevation=10,
           detail=1, pixels_per_mm=8, margin=7):
    if width <= 2*margin or height <= 2*margin or pixels_per_mm <= 0:
        raise ValueError('positive drawing area and pixels_per_mm required')
    if detail not in (0, 1, 2):
        raise ValueError('detail must be 0, 1 or 2')
    basis = camera(azimuth, elevation)
    allp = plant.points()@basis.T
    if not len(allp):
        return Drawing(width, height)
    lo, hi = allp[:, :2].min(0), allp[:, :2].max(0)
    scale = min((width-2*margin)/max(hi[0]-lo[0], .001),
                (height-2*margin)/max(hi[1]-lo[1], .001))
    offset = np.array([width, height])/2-(lo+hi)/2*scale
    def project(p):
        q = np.asarray(p)@basis.T
        q[:, :2] = q[:, :2]*scale+offset
        return q
    k = pixels_per_mm
    buf = np.full((int(np.ceil(height*k))+1, int(np.ceil(width*k))+1), -np.inf)
    owners = np.full(buf.shape, -1, np.int32)
    strokes = list(plant.strokes)
    for owner, surface in enumerate(plant.surfaces):
        q = project(surface.vertices); q[:, :2] *= k
        for face in surface.triangles:
            raster_triangle(buf, owners, q[face], owner)
        diameter = np.ptp(surface.vertices[:8], axis=0).max()
        if surface.silhouette and (diameter*scale >= .28 or surface.organ != 'axis'):
            strokes.extend(silhouettes(surface, basis[2], owner))
    paths = []
    # Owner identity prevents a blade erasing its own rim from pixel rounding.
    # A different, genuinely nearer organ still occludes it.
    tolerance = .20/scale
    for stroke in strokes:
        if stroke.detail > detail:
            continue
        q = project(stroke.points)
        seg = np.linalg.norm(np.diff(q[:, :2], axis=0), axis=1)
        distance = np.r_[0, np.cumsum(seg)]
        if distance[-1] < .18:
            continue
        # Preserve original vertices as well as dense samples (no corner loss).
        sample = np.unique(np.r_[distance, np.arange(0, distance[-1], .08)])
        points = np.column_stack([np.interp(sample, distance, q[:, i]) for i in range(3)])
        ij = np.rint(points[:, :2]*k).astype(int)
        valid = (ij[:, 0] >= 0)&(ij[:, 0] < buf.shape[1])&(ij[:, 1] >= 0)&(ij[:, 1] < buf.shape[0])
        ii = np.clip(ij[:, 0], 0, buf.shape[1]-1); jj = np.clip(ij[:, 1], 0, buf.shape[0]-1)
        visible = valid & ((points[:, 2] >= buf[jj, ii]-tolerance) |
                           ((owners[jj, ii] == stroke.owner)&(stroke.owner >= 0)))
        ids = np.flatnonzero(visible)
        for run in np.split(ids, np.flatnonzero(np.diff(ids) != 1)+1):
            if len(run) > 1:
                p = points[run, :2]
                if np.linalg.norm(np.diff(p, axis=0), axis=1).sum() >= .18:
                    paths.append((stroke.role, p))
    # Remove exact duplicate/reversed paths only; never merge visibility gaps.
    unique = {}
    for role, p in paths:
        p = np.round(np.asarray(LineString(p).simplify(.018).coords), 3)
        forward, reverse = p.tobytes(), p[::-1].tobytes()
        unique.setdefault((role, min(forward, reverse)), (role, p))
    drawing = Drawing(width, height, list(unique.values()),
                      dict(plant=plant.metadata, camera=dict(azimuth=azimuth, elevation=elevation),
                           detail=detail, pixels_per_mm=k, visibility='sampled surface depth',
                           minimum_path_mm=.18, pen_width_mm=.16))
    drawing.metadata['plot'] = drawing.stats()
    return drawing
