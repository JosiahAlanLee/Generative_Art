"""Small botanical geometry vocabulary. Coordinates are metres, Z is up.

Surfaces are visibility hosts; strokes are intentional marks, not all mesh
edges. Leaves use a folded, curved ribbon, rather than a flat sprite. This
module deliberately has no Blender import or camera-dependent geometry.
"""
from dataclasses import dataclass, field
from copy import deepcopy
import json
import numpy as np


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ValueError("zero direction")
    return v / n


def frame(direction, roll=0):
    d = unit(direction)
    u = unit(np.cross(d, [0, 0, 1] if abs(d[2]) < .95 else [0, 1, 0]))
    v = np.cross(d, u)
    return d, np.cos(roll)*u + np.sin(roll)*v


def bezier(a, b, c, n=18):
    t = np.linspace(0, 1, n)[:, None]
    return (1-t)**2*np.asarray(a) + 2*(1-t)*t*np.asarray(b) + t*t*np.asarray(c)


@dataclass
class Stroke:
    points: np.ndarray
    role: str = "stem"
    detail: int = 0
    owner: int = -1


@dataclass
class Surface:
    vertices: np.ndarray
    triangles: np.ndarray
    role: str
    organ: str
    # Tubes need view-dependent silhouettes, leaves already carry their rims.
    silhouette: bool = False


@dataclass
class Plant:
    metadata: dict = field(default_factory=dict)
    strokes: list = field(default_factory=list)
    surfaces: list = field(default_factory=list)
    organs: list = field(default_factory=list)

    def line(self, points, role="stem", detail=0, owner=-1):
        p = np.asarray(points, float)
        if p.ndim != 2 or p.shape[1] != 3 or len(p) < 2 or not np.isfinite(p).all():
            raise ValueError("finite Nx3 stroke required")
        if np.linalg.norm(np.diff(p, axis=0), axis=1).sum() > 1e-10:
            self.strokes.append(Stroke(p, role, detail, owner))

    def surface(self, vertices, triangles, role, organ, silhouette=False):
        vertices = np.asarray(vertices, float)
        triangles = np.asarray(triangles, int)
        q = vertices[triangles]
        area2 = np.linalg.norm(np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0]), axis=1)
        triangles = triangles[area2 > 1e-15]
        owner = len(self.surfaces)
        self.surfaces.append(Surface(vertices, triangles, role, organ, silhouette))
        return owner

    def stem(self, points, radius=.001, end_radius=None, role="stem", bark=False):
        p = np.asarray(points, float)
        if end_radius is None:
            end_radius = radius * .48
        sides = 8
        rings = []
        for i, q in enumerate(p):
            d = p[min(i+1, len(p)-1)] - p[max(0, i-1)]
            d, u = frame(d); v = np.cross(d, u)
            r = radius + (end_radius-radius)*i/(len(p)-1)
            rings.append([q+r*(np.cos(a)*u+np.sin(a)*v)
                          for a in np.arange(sides)*2*np.pi/sides])
        verts = np.asarray(rings).reshape(-1, 3); faces = []
        for i in range(len(p)-1):
            for j in range(sides):
                a = i*sides+j; b = i*sides+(j+1)%sides
                faces.extend([(a, b, b+sides), (a, b+sides, a+sides)])
        for j in range(1, sides-1):
            faces.extend([(0, j+1, j), ((len(p)-1)*sides,
                          (len(p)-1)*sides+j, (len(p)-1)*sides+j+1)])
        owner = self.surface(verts, faces, role, "axis", True)
        # Fine herb stems retain a centre mark if their silhouette is sub-pen.
        if radius < .004:
            self.line(p, role, owner=owner)
        if bark:
            for j in (0, 2, 3, 5, 7):
                self.line(verts[j::sides], "bark", 1, owner)
        self.organs.append({"type": "axis", "base": p[0].tolist(), "tip": p[-1].tolist()})
        return p

    def leaf(self, base, direction, length, width, *, shape="oval", roll=0,
             bend=-.15, role="leaf", detail=1, veins=True):
        """Leaf blade with explicit rim, midrib, secondary veins and folded host.

        ``width`` is full blade width. Dimensions/profiles are illustrative
        parameters, not species measurements. Lobes/teeth are geometric cues.
        """
        base = np.asarray(base, float); d, side = frame(direction, roll)
        normal = unit(np.cross(d, side))
        n = 33 if shape in ("oak", "toothed", "fern") else 17
        t = np.linspace(0, 1, n)
        centre = base + t[:, None]*length*d + (t*t)[:, None]*length*bend*np.array([0, 0, 1])
        profile = np.maximum(0, np.sin(np.pi*t))**.7
        if shape == "grass":
            profile = np.sin(np.pi*(.12+.88*t))**.8
            profile[0] = .12
        elif shape == "oak":
            # Broad terminal half and a strong pair of middle sinuses.
            profile *= (.58+.42*t) * (.70+.30*np.cos(8*np.pi*t))
            profile *= 1-.70*np.exp(-((t-.43)/.065)**2)
        elif shape in ("toothed", "fern"):
            profile *= 1 - (.19 if shape == "toothed" else .43)*(np.arange(n)%2)
        profile[[0, -1]] = 0
        half = width*.5*profile
        left = centre-half[:, None]*side + (profile*width*.10)[:, None]*normal
        right = centre+half[:, None]*side + (profile*width*.10)[:, None]*normal
        verts = np.stack([left, centre, right], axis=1).reshape(-1, 3)
        faces = []
        for i in range(n-1):
            for j in (0, 1):
                a = i*3+j
                faces.extend([(a, a+3, a+4), (a, a+4, a+1)])
        owner = self.surface(verts, faces, role, shape)
        self.line(np.vstack([left, right[-2::-1]]), role, 0, owner)
        if veins:
            self.line(centre, "vein", detail, owner)
            if shape != "grass":
                for i in range(3, n-3, 4 if shape == "oak" else 3):
                    for edge in (left, right):
                        # Each segment follows the same host triangles.
                        self.line([centre[i-1], centre[i], edge[i]], "vein", 2, owner)
            else:
                self.line((centre+left)/2, "vein", 2, owner)
        self.organs.append({"type": "leaf", "shape": shape, "base": base.tolist(),
                            "length": float(length), "width": float(width)})
        return centre[-1]

    def transform(self, fn):
        """Return an independent transformed plant; preserve organ bookkeeping."""
        out = deepcopy(self)
        for s in out.strokes:
            s.points = fn(s.points)
        for s in out.surfaces:
            s.vertices = fn(s.vertices)
        for organ in out.organs:
            for key in ("base", "tip", "position"):
                if key in organ:
                    organ[key] = fn(np.asarray([organ[key]]))[0].tolist()
        return out

    def placed(self, root=(0, 0, 0), scale=1, azimuth=0):
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError("scale must be positive")
        a = np.deg2rad(azimuth)
        r = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        out = self.transform(lambda p: p @ r.T*scale + np.asarray(root))
        out.metadata["placement"] = dict(root=list(root), scale=scale, azimuth=azimuth)
        return out

    def extend(self, other):
        offset = len(self.surfaces)
        self.surfaces.extend(deepcopy(other.surfaces))
        self.strokes.extend(Stroke(s.points.copy(), s.role, s.detail,
                                   s.owner+offset if s.owner >= 0 else -1) for s in other.strokes)
        self.organs.extend(deepcopy(other.organs))

    def points(self):
        arrays = [s.vertices for s in self.surfaces] + [s.points for s in self.strokes]
        return np.vstack(arrays) if arrays else np.zeros((0, 3))

    def as_dict(self):
        return {"schema": "wisconsin-flora-1", "units": "metres", "up": "Z",
                "metadata": self.metadata, "organs": self.organs,
                "surfaces": [dict(vertices=s.vertices.tolist(), triangles=s.triangles.tolist(),
                                  role=s.role, organ=s.organ, silhouette=s.silhouette) for s in self.surfaces],
                "strokes": [dict(points=s.points.tolist(), role=s.role, detail=s.detail, owner=s.owner)
                            for s in self.strokes]}

    def save(self, path):
        path.write_text(json.dumps(self.as_dict(), separators=(",", ":"))+"\n")

    def obj(self, path):
        """Portable surface geometry; ink remains in the adjacent JSON/SVG."""
        out = ["# Wisconsin flora; metres, Z up; see source seed and model JSON"]
        offset = 1
        for i, s in enumerate(self.surfaces):
            out.append(f"o {s.role}_{i}")
            out.extend("v %.7f %.7f %.7f" % tuple(v) for v in s.vertices)
            out.extend("f %d %d %d" % tuple(f+offset) for f in s.triangles)
            offset += len(s.vertices)
        path.write_text("\n".join(out)+"\n")
