"""One scene builder for every profile, written in NumPy only.

The three scene grammars (estate, spillway, window) call the primitives here.
`model.py` subclasses the builder so that every mesh is also mirrored into
Blender, where Geometry Nodes repeats the duration modules and the Displace
modifier roughens the terrain before the evaluated meshes are exported.
`dryrun.py` uses this builder on its own, so the engraving stages can be
developed and tested without a bpy installation.

Closed solids (boxes, beams, voussoirs, roof prisms, repeated modules) are
wound so that their face normals point outward. The engraver hatches only
faces whose stored normal faces the camera, so an inside-out solid loses its
hatching and its near silhouette; `outward_audit` reports any such solid.
"""
import math
import numpy as np

KINDS = ('terrain', 'box', 'beam', 'roof', 'voussoir', 'sheet', 'leaf', 'module')
CLOSED = ('box', 'beam', 'roof', 'voussoir', 'module')
MATERIALS = ('Ground', 'Limestone', 'Timber', 'Oxide', 'Roof', 'Paper', 'Foliage')
COLORS = ('#bfb79d', '#bcb29b', '#716b53', '#8d4e39', '#6e7165', '#dbceb2', '#4e6450')
STOREY = 1.04       # one complete vertical storey, including its cornice
PX_PER_MM = 20


def newell_normal(p):
    """Unit normal of a planar polygon from its vertex winding (Newell)."""
    p = np.asarray(p, float); q = np.roll(p, -1, axis=0)
    n = np.array([((p[:, 1] - q[:, 1]) * (p[:, 2] + q[:, 2])).sum(),
                  ((p[:, 2] - q[:, 2]) * (p[:, 0] + q[:, 0])).sum(),
                  ((p[:, 0] - q[:, 0]) * (p[:, 1] + q[:, 1])).sum()])
    length = np.linalg.norm(n)
    return n / length if length > 1e-12 else np.zeros(3)


def polygon_area(p):
    p = np.asarray(p, float); q = np.roll(p, -1, axis=0)
    return .5 * np.linalg.norm(np.cross(p, q).sum(axis=0))


class Module:
    """A repeatable body in local coordinates: parts keep separate vertices."""

    def __init__(self, name):
        self.name = name; self.verts = []; self.faces = []; self.mats = []; self.kinds = []

    def add(self, verts, faces, mat=1, kind='sheet'):
        """`mat` is one material index for every face, or one per face."""
        off = len(self.verts)
        self.verts.extend([tuple(map(float, v)) for v in verts])
        self.faces.extend([tuple(off + i for i in f) for f in faces])
        mats = list(mat) if isinstance(mat, (list, tuple)) else [int(mat)] * len(faces)
        if len(mats) != len(faces): raise ValueError('one material per face required')
        self.mats.extend(int(m) for m in mats); self.kinds.extend([kind] * len(faces))

    def box(self, lo, hi, mat=1):
        self.add(*box_geometry(lo, hi), mat, 'box')

    def realize(self, count, offset, location):
        """Instance the module `count` times along `offset`, as Geometry Nodes does."""
        verts = np.asarray(self.verts, float); out = []
        for k in range(count):
            out.append(verts + np.asarray(offset, float) * k + np.asarray(location, float))
        faces = [tuple(i + k * len(self.verts) for i in f) for k in range(count) for f in self.faces]
        return np.vstack(out) if out else np.zeros((0, 3)), faces, self.mats * count, self.kinds * count


def box_geometry(lo, hi):
    x, y, z = lo; X, Y, Z = hi
    return ([(x, y, z), (X, y, z), (X, Y, z), (x, Y, z), (x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z)],
            [(0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)])


def beam_geometry(a, b, r, sides):
    a, b = np.asarray(a, float), np.asarray(b, float); n = b - a; n /= np.linalg.norm(n)
    u = np.cross(n, [0, 0, 1]) if abs(n[2]) < .95 else np.cross(n, [0, 1, 0])
    u /= np.linalg.norm(u); v = np.cross(n, u)
    ring = np.array([u * np.cos(t) + v * np.sin(t) for t in np.arange(sides) * 2 * np.pi / sides]) * r
    p = np.vstack([a + ring, b + ring])
    f = [tuple(range(sides - 1, -1, -1)), tuple(range(sides, 2 * sides))]
    f += [(i, (i + 1) % sides, (i + 1) % sides + sides, i + sides) for i in range(sides)]
    return p, f


def roof_geometry(x, y, z, w, d, rise):
    """A gable prism, open underneath, with every face wound outward.

    The estate's original roof wound all four faces inward, so its camera-facing
    slope and gable were skipped by the engraver and its near eave lost its
    silhouette. The window scene carried the corrected winding locally first.
    """
    p = [(x - w / 2, y - d / 2, z), (x + w / 2, y - d / 2, z), (x, y - d / 2, z + rise),
         (x - w / 2, y + d / 2, z), (x + w / 2, y + d / 2, z), (x, y + d / 2, z + rise)]
    return p, [(0, 1, 2), (3, 5, 4), (0, 2, 5, 3), (1, 4, 5, 2)]


def voussoir_geometry(x, y, spring, w, depth, t0, t1):
    """One ring stone between angles t0 and t1, wound outward.

    The original ring stones were inside-out in every scene: their faces toward
    the camera were back-facing to the engraver, so arches drew as unhatched
    outlined rings rather than as masonry.
    """
    vs = []
    for yy in (y - depth / 2, y + depth / 2):
        for r in (w / 2 - .12, w / 2 + .12):
            vs.extend([(x + r * np.cos(a), yy, spring + r * np.sin(a)) for a in (t0, t1)])
    # 0..3: near face (y-), 4..7: far face (y+); within each, inner radius first, then outer.
    return vs, [(2, 3, 1, 0), (5, 7, 6, 4), (1, 5, 4, 0), (6, 7, 3, 2), (4, 6, 2, 0), (3, 7, 5, 1)]


class SceneBuilder:
    """Collects meshes, strokes and cameras; `export` evaluates them in NumPy."""

    def __init__(self, architecture, terrain_z, width=3120, height=2340):
        self.A = architecture; self.terrain_z = terrain_z; self.W, self.H = width, height
        self.materials = []; self.colors = []
        self.objects = []; self.strokes = []; self.cameras = {}; self.terrain = None; self.used_names = {}
        for name, col in zip(MATERIALS, COLORS):
            self.material(name, col, .88)

    def unique_name(self, name):
        """Blender's object naming: the first keeps the name, later ones get .001, .002, ..."""
        n = self.used_names.get(name, 0); self.used_names[name] = n + 1
        return name if n == 0 else f'{name}.{n:03d}'

    # ---- materials and primitives -------------------------------------------------
    def material(self, name, color, roughness=.88):
        self.materials.append(dict(name=name, color=color, roughness=roughness)); self.colors.append(color)
        return len(self.materials) - 1

    def mesh(self, name, verts, faces, mat=1, hatch=True, link=True, kind='sheet'):
        rec = dict(name=self.unique_name(name), base_name=name, verts=np.asarray(verts, float).reshape(-1, 3),
                   faces=[tuple(int(i) for i in f) for f in faces], mat=mat, hatch=bool(hatch), link=bool(link), kind=kind)
        if link:
            self.objects.append(rec)
        return rec

    def box(self, name, lo, hi, mat=1, link=True):
        return self.mesh(name, *box_geometry(lo, hi), mat, link=link, kind='box')

    def beam(self, name, a, b, r=.08, mat=2, sides=6, hatch=True):
        return self.mesh(name, *beam_geometry(a, b, r, sides), mat, hatch=hatch, kind='beam')

    def ink(self, name, pts, mm=.12, pen=0):
        self.strokes.append(dict(name=name, pts=np.asarray(pts, float).tolist(), width=mm * PX_PER_MM, ink=pen))

    def roof(self, name, x, y, z, w, d, rise=.9):
        ob = self.mesh(name, *roof_geometry(x, y, z, w, d, rise), 4, kind='roof')
        for q in np.linspace(-d / 2 + .13, d / 2 - .13, max(3, int(d / .30))):
            self.ink(name + ' standing seam', [(x - w / 2, y + q, z + .018), (x, y + q, z + rise + .018), (x + w / 2, y + q, z + .018)], .10)
        return ob

    def arch(self, name, x, y, z, w, h, depth=.20):
        """Real masonry around an empty opening. No white image masks."""
        spring = z + h - w / 2
        for side in (-1, 1):
            self.box(name + ' jamb', (x + side * w / 2 - .12, y - depth / 2, z), (x + side * w / 2 + .12, y + depth / 2, spring), 1)
        for t in np.linspace(0, np.pi, 11)[:-1]:
            self.mesh(name + ' voussoir', *voussoir_geometry(x, y, spring, w, depth, t, t + np.pi / 10), 1, kind='voussoir')

    def terrain_grid(self, gx, gy):
        """The evaluated, displaced host. All plants and marks project onto it."""
        xx, yy = np.meshgrid(gx, gy); zz = self.terrain_z(xx, yy); fs = []
        for j in range(len(gy) - 1):
            for i in range(len(gx) - 1):
                a = j * len(gx) + i; fs.extend([(a, a + 1, a + len(gx) + 1), (a, a + len(gx) + 1, a + len(gx))])
        self.terrain = self.mesh('Host terrain', np.c_[xx.ravel(), yy.ravel(), zz.ravel()], fs, 0, False, kind='terrain')
        return self.terrain

    # ---- repetition ---------------------------------------------------------------
    def module(self, name):
        return Module(name)

    def repeat(self, host_name, module, count, offset, location, *, group_name, modifier_name, props=None):
        """Realise `count` copies of a module. The Blender backend builds the
        equivalent Geometry Nodes tree; here the instancing is done directly."""
        verts, faces, mats, kinds = module.realize(count, offset, location)
        rec = self.mesh(host_name, verts, faces, mats, kind='module')
        rec.update(module=module, count=count, offset=tuple(map(float, offset)), location=tuple(map(float, location)),
                   group_name=group_name, modifier_name=modifier_name, props=dict(props or {}), face_kinds=kinds)
        return rec

    def story_nodes(self, name, cx, cy, z, w, d, count):
        """One repeatable storey, with its windows and cornice, stacked `count` times."""
        m = self.module(name + ' complete bay')
        m.box((-w / 2, -d / 2, 0), (w / 2, d / 2, .92))
        m.box((-w / 2 - .12, -d / 2 - .12, .86), (w / 2 + .12, d / 2 + .12, 1.03))
        for x in np.linspace(-w / 2 + .43, w / 2 - .43, 3):
            if abs(x) < .1: continue  # keep the portal axis free of a superposed window
            m.box((x - .20, -d / 2 - .027, .24), (x + .20, -d / 2 - .014, .69), 2)
            m.box((x - .20, d / 2 + .014, .24), (x + .20, d / 2 + .027, .69), 2)
        for y in np.linspace(-d / 2 + .42, d / 2 - .42, 3):
            m.box((w / 2 + .014, y - .19, .24), (w / 2 + .027, y + .19, .69), 2)
        self.repeat(name + ' | duration bays', m, count, (0, 0, STOREY), (cx, cy, z),
                    group_name='IE | ' + name + ' | duration repetition', modifier_name='Task duration / repeated bays',
                    props=dict(task_id=name, duration=count))
        return count * STOREY

    def oak(self, name, x, y, height, seed):
        """A branching volume tree with leaf polygons distributed in 3D crowns."""
        rng = np.random.default_rng((seed + int(self.A['seed']) - 314159) % (2 ** 32))
        root = np.array([x, y, float(self.terrain_z(x, y)) - .07]); tips = []

        def branch(a, d, length, r, level):
            b = a + d / np.linalg.norm(d) * length
            self.beam(name + ' branch', a, b, r, 2, 5, hatch=False)
            if level == 0:
                tips.append(b); return
            for j in range(3 if level > 1 else 2):
                angle = (j * 2 * np.pi / 3) + rng.uniform(-.5, .5)
                q = np.array([np.cos(angle), np.sin(angle), rng.uniform(.4, 1.3)])
                branch(b, .42 * d + q, length * rng.uniform(.55, .70), r * .55, level - 1)
        branch(root, np.array([.03, .01, 1]), height * .33, height * .035, 3)
        vs = []; fs = []
        for tip in tips:
            for _ in range(21):
                c = tip + rng.normal(0, [height * .10, height * .10, height * .06])
                normal = rng.normal(size=3); normal /= np.linalg.norm(normal)
                u = np.cross(normal, [0, 0, 1]); u /= max(np.linalg.norm(u), 1e-8); v = np.cross(normal, u)
                length = rng.uniform(.16, .29); width = length * .54
                off = len(vs)
                # Eight-sided leaf outline softens the diamond-card prototype.
                ts = np.arange(8) * np.pi / 4
                vs.extend([c + u * np.cos(t) * length + v * np.sin(t) * width for t in ts])
                fs.append(tuple(range(off, off + 8)))
        self.mesh(name + ' leaf volume', vs, fs, 6, False, kind='leaf')

    def camera(self, name, eye, target, focal):
        self.cameras[name] = dict(kind='perspective', eye=list(eye), target=list(target), focal_px=focal,
                                  principal_point=[self.W / 2, self.H / 2], resolution=[self.W, self.H])

    # ---- evaluation -----------------------------------------------------------------
    def evaluate(self):
        """Per-face arrays in object order: the NumPy equivalent of Blender's export."""
        vertices = []; faces = []; mats = []; normals = []; names = []; hatch = []; terrain_faces = []; objects = []
        for rec in self.objects:
            off = len(vertices); vertices.extend(rec['verts'].tolist())
            per_face = rec['mat'] if isinstance(rec['mat'], (list, tuple)) else [rec['mat']] * len(rec['faces'])
            for f, m in zip(rec['faces'], per_face):
                k = len(faces); faces.append([off + i for i in f]); mats.append(int(m))
                normals.append(newell_normal(rec['verts'][list(f)]).tolist())
                names.append(rec['name']); hatch.append(rec['hatch'])
                if rec is self.terrain: terrain_faces.append(k)
            objects.append(dict(name=rec['name'], kind=rec['kind'], faces=len(rec['faces'])))
        return dict(vertices=vertices, faces=faces, materials=mats, normals=normals, names=names, hatch=hatch,
                    terrain_faces=terrain_faces, objects=objects)

    def record(self, evaluated, *, footprints, routes, terrain_mode, backend, blender, terrain_modifier,
               planar_trees=None, terrain_state=None):
        """The scene record consumed by build.py, render.py, checks.py and measure.py."""
        hosts = [rec for rec in self.objects if rec['kind'] == 'module']
        counts = {o['name']: o['faces'] for o in evaluated['objects']}
        data = dict(evaluated, strokes=self.strokes, colors=list(self.colors), cameras=self.cameras,
                    blender=blender, host='Host terrain', architecture=self.A, footprints=footprints, routes=routes,
                    terrain_modifier=terrain_modifier,
                    geometry_nodes=[dict(name=h['name'], faces=counts.get(h['name'], 0)) for h in hosts])
        data['terrain_mode'] = terrain_mode
        if planar_trees is not None: data['planar_trees'] = planar_trees
        if terrain_state is not None:
            data['terrain_state'] = {k: np.asarray(terrain_state[k]).tolist() for k in ('x', 'y', 'height', 'area', 'receiver', 'fixed_mask')}
        data['backend'] = backend
        return data

    def export(self, **kw):
        kw.setdefault('backend', 'numpy'); kw.setdefault('blender', 'NumPy dry run (no Blender evaluation)')
        kw.setdefault('terrain_modifier', dict(type='none', note='Displace runs only in Blender'))
        return self.record(self.evaluate(), **kw)


def components(faces):
    """Connected components of faces over shared vertices (union-find)."""
    parent = {}

    def find(i):
        while parent.setdefault(i, i) != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for f in faces:
        for a in f[1:]:
            ra, rb = find(f[0]), find(a)
            if ra != rb: parent[rb] = ra
    groups = {}
    for k, f in enumerate(faces):
        groups.setdefault(find(f[0]), []).append(k)
    return list(groups.values())


def outward_audit(record, kinds=CLOSED):
    """Signed flux of every closed solid about its own centroid.

    For each object of a closed kind, every connected component (a box, a
    beam, one voussoir, a gable prism, each part of a repeated module) must
    satisfy sum(area * normal . (face centre - component centre)) > 0, which is
    positive for an outward-wound convex body and negative inside-out. Open
    sheets, leaves and terrain are not audited. Returns per-object results."""
    V = np.asarray(record['vertices']); N = np.asarray(record['normals'])
    by_object = {}
    for k, name in enumerate(record['names']):
        by_object.setdefault(name, []).append(k)
    kind_of = {o['name']: o['kind'] for o in record.get('objects', [])}
    out = {}
    for name, ids in by_object.items():
        if kind_of.get(name) not in kinds: continue
        faces = [record['faces'][k] for k in ids]
        inward = 0; total = 0
        for comp in components(faces):
            ks = [ids[c] for c in comp]
            verts = V[sorted({i for c in comp for i in faces[c]})]; c0 = verts.mean(0)
            flux = 0.
            for k, c in zip(ks, comp):
                p = V[faces[c]]; flux += polygon_area(p) * float(N[k] @ (p.mean(0) - c0))
            total += 1; inward += int(flux <= 0)
        out[name] = dict(kind=kind_of[name], components=total, inward=inward)
    return out
