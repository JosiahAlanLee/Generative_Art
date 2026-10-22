"""Close-camera plate studies: the estate with the collection's newer assets.

Off unless INFERNAL_PLATES=1 (`run.py --plates`), which writes every stage to
output/<case>-plates/ and turns the face patterns on. Two cameras are added
to the estate's own:

- `tower`: the approval tower over the open approach arch, close enough for
  the face-pattern strata to read, with a seal built from 2-D distance fields
  (lib/sdf2d) on its top storey and southwest Wisconsin flora (lib/flora) in
  the foreground.
- `barn`: a farmstead placed in the estate's open east meadow, built with
  lib/farm_objects (a decaying timber barn, an open-seat tractor and a dump
  hay rake), with a barn quilt on the barn's door end painted in jittered
  passes (lib/fuzz) and flora placed by variable-density Poisson sampling
  (lib/halftone).

This module holds the scene-time part (`add_farmstead`, `CAMERAS`), which
runs in either backend, and the render-time flora (`flora_instances`). The
patterns themselves are in surface_patterns.py. Nothing here changes the
delivered estate: without the flag no function in this file is called.
"""
from pathlib import Path
import os
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

ENABLED = os.environ.get('INFERNAL_PLATES') == '1'

# name, eye, target, focal (px on the 3120 px master), as in estate.CAMERAS
CAMERAS = [('tower', (2.4, -4.2, 8.8), (-4.7, 10.3, 4.6), 3300.),
           ('barn', (13.4, -9.4, 4.6), (16.3, 6.4, 2.75), 3450.)]

# The farmstead sits in the estate's open east meadow, clear of the near oak's
# crown (x <= 13.4) and of the task buildings. Doors and the tractor's bonnet
# face the barn camera. Seeds are the farm-remnants study's own specimens.
FARM = (dict(kind='barn', name='Farm barn', seed=22, decay=.45, at=(16.6, 8.4), rotation=0.),
        dict(kind='tractor', name='Farm tractor', seed=23, decay=.72, at=(19.9, 3.9), rotation=-2.3),
        dict(kind='hay_rake', name='Farm hay rake', seed=25, decay=.72, at=(11.6, 5.2), rotation=.2))
SINK = .05          # bases sit 5 cm into the ground: Blender's Displace moves it +-4 cm
QUILT_SIZES = (1.22, .92, .61)   # 4 ft, 3 ft and 2 ft boards; the largest that fits is used
QUILT_STANDOFF = .06             # board face in front of the siding, clear of warped boards
QUILT_THICKNESS = .03
DOOR_JAMB = 1.09 + .075          # farm_objects' door jambs: centres at +-1.09, radius .075
DOOR_RAIL = 2.63 - .035          # underside of the sliding door's rail, which spans x +-1.5


def _ground_under(ground, corners, n=7):
    """Terrain heights sampled over a footprint rectangle (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = corners
    xx, yy = np.meshgrid(np.linspace(x0, x1, n), np.linspace(y0, y1, n))
    return np.asarray(ground(xx, yy), float)


def _transform(points, at, rotation, z):
    c, s = np.cos(rotation), np.sin(rotation)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return np.asarray(points, float) @ R.T + np.array([at[0], at[1], z])


def front_quilt(record):
    """Where a square quilt board fits on the barn's door end, in barn coordinates.

    Measured from the barn's own geometry. The gable above the loft opening
    is tried first (eave from the front tie beam, loft head 0.5 above it, roof
    line from the tops of the front end boards); a barn whose loft opening
    leaves too little gable takes the board on the wall left of the door
    instead, clear of the door jamb and below the sliding door's rail (the
    slid door covers the wall to its right). Returns the board's centre x,
    bottom z, size, the front plane's y and where it hangs, or None.
    """
    V = np.asarray(record['vertices']); names = record['names']; faces = record['faces']
    # The object's own builder names parts 'tie', 'tie.001', ... (Blender's rule).
    pts = lambda base: [V[f] for f, n in zip(faces, names) if n.split('.')[0] == base]
    ends = pts('end board')
    front_y = min(p[:, 1].min() for p in ends)
    front = [p for p in ends if p[:, 1].max() < front_y + .2]
    ties = [p for p in pts('tie') if p[:, 1].mean() < front_y + .3]
    eave = float(np.median(np.concatenate([p[:, 2] for p in ties])))
    # Each front board: (centre x, top z); the top of a board follows the roof.
    boards = np.array([(p[:, 0].mean(), p[:, 2].max()) for p in front])
    roof = lambda x: np.interp(x, *boards[np.argsort(boards[:, 0])].T)
    found = dict(front_y=round(float(front_y), 4), eave=round(eave, 3))
    bottom = eave + .5 + .12
    for size in QUILT_SIZES[:2]:            # a 2 ft board on a gable reads as a plaque
        half = size / 2
        if min(roof(-half), roof(half)) >= bottom + size + .10:
            return dict(found, place='gable', centre_x=0., bottom_z=round(bottom, 3), size=size)
    left = min(p[:, 0].min() for p in front) + .08
    right = -DOOR_JAMB - .04
    for size in QUILT_SIZES:
        if right - left >= size and DOOR_RAIL - .05 - size >= .45:
            top = DOOR_RAIL - .05
            return dict(found, place='wall left of the door', centre_x=round((left + right) / 2, 3),
                        bottom_z=round(top - size, 3), size=size)
    return None


def add_farmstead(T):
    """Place the farm objects and the quilt board; returns (footprints, record).

    Runs at scene time in either backend, through the builder's own `mesh` and
    `ink`, so the Blender model and the dry run receive identical geometry.
    """
    from lib.farm_objects import make_object
    ground = T.terrain_z
    footprints, placed = [], []
    for spec in FARM:
        obj = make_object(spec['kind'], seed=spec['seed'], decay=spec['decay'])
        rec = obj.record(); V = np.asarray(rec['vertices'])
        # The footprint of the object itself, not its fallen planks.
        core = [V[f] for f, n in zip(rec['faces'], rec['names']) if 'fallen' not in n]
        P = _transform(np.vstack(core), spec['at'], spec['rotation'], 0.)
        lo, hi = P[:, :2].min(0), P[:, :2].max(0)
        heights = _ground_under(ground, (lo[0], lo[1], hi[0], hi[1]))
        # A barn's boards hang free above its sills, so it sits at the low
        # quarter of its footprint; wheels sit on the ground at the centre.
        z = float(np.percentile(heights, 25) if spec['kind'] == 'barn' else ground(*spec['at'])) - SINK
        obj.add_to(T, location=(spec['at'][0], spec['at'][1], z), rotation=spec['rotation'], name=spec['name'])
        footprints.append([float(lo[0]) - .4, float(lo[1]) - .4, float(hi[0]) + .4, float(hi[1]) + .4])
        entry = dict(kind=spec['kind'], name=spec['name'], seed=spec['seed'], decay=spec['decay'],
                     at=list(spec['at']), z=round(z, 3), rotation=spec['rotation'], parameters=obj.parameters)
        if spec['kind'] == 'barn':
            fit = front_quilt(rec)
            if fit is not None:
                s = fit['size']; y1 = fit['front_y'] - QUILT_STANDOFF; y0 = y1 - QUILT_THICKNESS
                lo3 = _transform([[fit['centre_x'] - s / 2, y0, fit['bottom_z']]], spec['at'], spec['rotation'], z)[0]
                hi3 = _transform([[fit['centre_x'] + s / 2, y1, fit['bottom_z'] + s]], spec['at'], spec['rotation'], z)[0]
                # Paper is the builder's painted-board slot; hatch stays on, the
                # quilt's keep-out removes it where paint replaces light.
                T.box('Barn quilt board', np.minimum(lo3, hi3), np.maximum(lo3, hi3), 5)
                fit.update(world_lo=[round(v, 4) for v in np.minimum(lo3, hi3)],
                           world_hi=[round(v, 4) for v in np.maximum(lo3, hi3)])
            entry['quilt_board'] = fit
        placed.append(entry)
    return footprints, dict(objects=placed)


# ---- render time: Wisconsin flora as planar instances ----------------------------
# Specimens come from lib/flora, drawn once per camera by its own renderer (its
# depth buffer resolves a plant's leaves over its own stems), then planted on
# the evaluated terrain as view-facing instances in the estate's existing
# parallel-plane compositor (occlusion.py): model rays hide them behind
# buildings, nearer plants hide farther ones. Positions are a variable-density
# Poisson-disc sample (lib/halftone): dense where mowing stops, along the fence
# and against walls, sparse in the yard, absent from the cart track. The same
# positions serve every camera; only the drawings are made per camera.
SPECIES = {   # species: (stage, specimens drawn per camera)
    'little_bluestem': ('seed', 3), 'side_oats_grama': ('seed', 2), 'wild_bergamot': ('flowering', 2),
    'prairie_smoke': ('seed', 2), 'leadplant': ('flowering', 2)}
EDGE_MIX = {'little_bluestem': .32, 'side_oats_grama': .20, 'wild_bergamot': .20, 'leadplant': .16, 'prairie_smoke': .12}
OPEN_MIX = {'little_bluestem': .30, 'prairie_smoke': .42, 'side_oats_grama': .18, 'wild_bergamot': .10}
FLORA_SEED = 1931
ZONES = (
    # The farmyard in front of the barn, and the strip between the near oak and the barn's west wall.
    dict(name='farmyard', polygon=[(9.4, -5.8), (23.4, -5.8), (23.4, 5.3), (14.0, 5.3), (13.4, 9.8), (9.4, 9.8)],
         edges=[[(9.0, .80), (14.0, 1.30)], [(14.1, 4.97), (19.1, 4.97)], [(14.1, 4.97), (14.1, 11.8)]],
         track=[(16.6, 5.0), (14.8, -6.0)], track_half_width=.95, r=(.30, 1.10)),
    # East and south of the approval tower, between it and the read building.
    dict(name='tower meadow', polygon=[(-7.0, 5.3), (-2.4, 5.3), (-2.4, 7.0), (1.7, 7.0), (1.7, 12.9), (-2.6, 12.9),
                                       (-2.6, 8.5), (-7.0, 8.5)],
         edges=[[(-7.0, 8.5), (-2.6, 8.5), (-2.6, 12.5)], [(-6.72, 5.0), (-2.88, 5.0)]],
         track=None, track_half_width=0., r=(.28, .95)),
)


def _segment_distance(p, polyline):
    a = np.asarray(polyline[:-1], float); b = np.asarray(polyline[1:], float); d = b - a
    t = np.clip(((p - a) * d).sum(1) / np.maximum((d * d).sum(1), 1e-12), 0, 1)
    return float(np.min(np.linalg.norm(p - (a + t[:, None] * d), axis=1)))


def _inside(p, polygon):
    from lib.face_patterns import inside
    return bool(inside([p], polygon)[0])


def zone_points(zone, footprints, rng):
    """Variable-density Poisson-disc sample of one zone, in world x, y."""
    from lib.halftone import poisson_sample
    poly = np.asarray(zone['polygon'], float); r0, r1 = zone['r']
    edges = [np.asarray(e, float) for e in zone['edges']]
    edge_distance = lambda p: min(_segment_distance(p, e) for e in edges)

    def radius(p):
        t = np.clip(edge_distance(p) / 1.6, 0, 1)
        return r0 + (r1 - r0) * t * t * (3 - 2 * t)

    def mask(p):
        if not _inside(p, poly):
            return False
        if any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for x0, y0, x1, y1 in footprints):
            return False
        if zone['track'] is not None and _segment_distance(p, zone['track']) < zone['track_half_width']:
            return False
        return True
    lo, hi = poly.min(0), poly.max(0)
    pts = poisson_sample((lo[0], lo[1], hi[0], hi[1]), radius, rng, min_radius=r0, mask=mask, quality=900)
    return pts, np.array([edge_distance(p) for p in pts])


def _species_for(distance, rng):
    mix = EDGE_MIX if distance < 1.2 else OPEN_MIX
    names = list(mix); w = np.array([mix[n] for n in names])
    return names[int(rng.choice(len(names), p=w / w.sum()))]


THIN_ROLES = ('seed', 'flower', 'hair')   # marks drawn one in THIN at landscape scale


def _thinned(plant, thin):
    """A copy keeping every `thin`-th seed, flower and hair mark: at about 10 mm
    a plant on the plate, hundreds of florets merge into a solid blot."""
    from copy import deepcopy
    out = deepcopy(plant); seen = {}; strokes = []
    for s in out.strokes:
        if s.role in THIN_ROLES:
            seen[s.role] = seen.get(s.role, 0) + 1
            if (seen[s.role] - 1) % thin:
                continue
        strokes.append(s)
    out.strokes = strokes
    return out


def _patch(plant, azimuth, elevation, scale, detail):
    """One specimen drawn for this camera, as a compositor patch in plate mm.

    lib/flora fits a plant to its drawing; asking for exactly the plant's
    projected extent at `scale` mm per metre (plus margins) makes the fit
    scale equal `scale`, so the drawing's units are plate millimetres and its
    root sits at the fit's offset.
    """
    from lib.flora.render import camera, render
    margin = 1.0
    q = plant.points() @ camera(azimuth, elevation).T
    lo, hi = q[:, :2].min(0), q[:, :2].max(0)
    width, height = (hi[0] - lo[0]) * scale + 2 * margin, (hi[1] - lo[1]) * scale + 2 * margin
    drawing = render(plant, width, height, azimuth=azimuth, elevation=elevation, detail=detail, margin=margin)
    origin = np.array([width, height]) / 2 - (lo + hi) / 2 * scale
    strokes, occluders = [], []
    for role, pts in drawing.paths:
        pts = np.asarray(pts, float)
        flat = pts.ravel().tolist()
        strokes.append(dict(pen=1, kind=0, pts=flat, role=role))
        closed = len(pts) > 3 and np.linalg.norm(pts[0] - pts[-1]) < .06
        # A closed rim (a leaf, a flower head) hides what is behind it; any
        # other line cuts a halo, as the Driftless stems do.
        occluders.append(dict(t='rings', rings=[flat]) if closed else dict(t='stamp', pts=flat, w=.30))
    # The specimen's convex outline: the area a reader sees as the plant, used
    # only to measure tone zones (render.py), never drawn.
    allpts = np.vstack([np.asarray(s['pts']).reshape(-1, 2) for s in strokes]) if strokes else np.zeros((0, 2))
    hull = []
    if len(allpts) >= 3:
        from scipy.spatial import ConvexHull
        try:
            hull = allpts[ConvexHull(allpts).vertices].ravel().tolist()
        except Exception:      # collinear marks have no area
            hull = []
    return dict(strokes=strokes, occluders=occluders, origin=origin.tolist(), mm_per_metre=scale,
                paths=len(strokes), hull=hull)


def flora_library(B, centre, rng, detail=0, thin=2):
    """Every specimen, drawn once for the current camera at the zones' scale."""
    from lib.flora import generate
    fh = B.FWD[:2] / np.linalg.norm(B.FWD[:2])
    azimuth = float(np.degrees(np.arctan2(-fh[0], fh[1])))      # lib/flora: right = (cos a, sin a, 0)
    to_eye = B.EYE - centre
    elevation = float(np.degrees(np.arcsin(np.clip(to_eye[2] / np.linalg.norm(to_eye), -1, 1))))
    scale = float(B.pixels_per_world(centre)) / 20               # plate mm per metre at the zones
    library = {}
    for species, (stage, count) in SPECIES.items():
        for k in range(count):
            plant = generate(species, seed=int(rng.integers(1, 10_000)), stage=stage,
                             wind=float(rng.uniform(-.35, .35)))
            plant = _thinned(plant.placed(root=(0, 0, 0), azimuth=float(rng.uniform(0, 360))), thin)
            library.setdefault(species, []).append(_patch(plant, azimuth, elevation, scale, detail))
    return library, dict(azimuth=round(azimuth, 2), elevation=round(elevation, 2), mm_per_metre=round(scale, 3),
                         detail=detail, thin=thin)


def flora_instances(B, M, footprints, width):
    """Planar Wisconsin flora for the current camera, and a record."""
    rng = np.random.default_rng(FLORA_SEED)
    placements = []
    for k, zone in enumerate(ZONES):
        pts, dist = zone_points(zone, footprints, np.random.default_rng([FLORA_SEED, k]))
        for p, d in zip(pts, dist):
            placements.append((zone['name'], p, d))
    # The drawings are made at the scale of the zones' visible centre.
    roots = np.array([[p[0], p[1], 0.] for _, p, _ in placements])
    roots[:, 2] = B.height(roots[:, 0], roots[:, 1])
    x, y, z = B.project(roots)
    on_page = (z > B.NEAR) & (x > -200) & (x < B.W + 200) & (y > -200) & (y < B.H + 200)
    centre = np.median(roots[on_page], axis=0) if on_page.any() else roots.mean(0)
    library, camera_record = flora_library(B, centre, np.random.default_rng([FLORA_SEED, 7]))
    out, counts = [], {}
    for (zone, p, d), root in zip(placements, roots):
        species = _species_for(d, rng)
        patch = library[species][int(rng.integers(len(library[species])))]
        size = float(rng.uniform(.82, 1.15))                 # specimen-to-specimen size, not age
        s = size / patch['mm_per_metre']                      # world metres per drawing mm
        root = root + np.array([0, 0, .015])
        out.append(M.Instance(patch, patch['origin'], root, s, width))
        counts[species] = counts.get(species, 0) + 1
    return out, dict(instances=len(out), species=counts, zones=[z['name'] for z in ZONES],
                     drawn_for_camera=camera_record, seed=FLORA_SEED)


def in_flora_zone(x, y):
    """True where the plate studies' flora replace the Driftless meadow plants."""
    return any(_inside((x, y), z['polygon']) for z in ZONES)


# ---- render time: where the plates build hatches the terrain ---------------------
# The estate's terrain atlas (build.Terrain: x -20..20, y -11..35) is also the
# main view's vignette, since the drawing stops along its edges. The farmyard
# reaches past its east edge, so the plates' main view adds the yard to it
# (`yard_atlas`). The plate cameras stand inside the atlas and look out past
# it, so they hatch the ground they see instead, out to the terrain mesh,
# easing the hatching away over the last metres before the mesh ends
# (`close_atlas`, `edge_fade`). Lines laid over the whole atlas would also run
# past and behind a plate camera and project to enormous screen lengths;
# `face_in_view` drops hatched faces for the same reason.

YARD = (19.5, -6.6, 24.2, 6.6)   # ground east of the atlas (x0, y0, x1, y1): the farmyard and tractor, + margins
EDGE_FADE = 6.                   # metres over which a plate camera's terrain hatching eases out


def yard_atlas(terrain):
    """Main view of the plates build: the terrain atlas plus the farmyard east of it."""
    u0, u1, v0, v1 = terrain.u0, terrain.u1, terrain.v0, terrain.v1
    x0, y0, x1, y1 = YARD
    terrain.u1 = max(u1, x1)
    terrain.domain = lambda u, v: (((u >= u0) & (u <= u1) & (v >= v0) & (v <= v1))
                                   | ((u >= x0) & (u <= x1) & (v >= y0) & (v <= y1)))
    return dict(atlas=[u0, u1, v0, v1], yard=list(YARD))


def close_atlas(B, inset=.1):
    """Plate cameras: hatch the terrain they see, out to the mesh. Returns the
    mesh's extent (x0, y0, x1, y1) for `edge_fade`."""
    lo, hi = B.TBVH[0][0], B.TBVH[1][0]            # the terrain BVH's root box
    mesh = (float(lo[0]) + inset, float(lo[1]) + inset, float(hi[0]) - inset, float(hi[1]) - inset)
    seen = visible_ground(B) or mesh
    t = B.terrain
    t.u0, t.v0 = max(mesh[0], seen[0]), max(mesh[1], seen[1])
    t.u1, t.v1 = min(mesh[2], seen[2]), min(mesh[3], seen[3])
    return mesh


def edge_fade(xy, extent, width=EDGE_FADE):
    """1 inside `extent` (x0, y0, x1, y1), easing to 0 at its edge over `width` metres."""
    xy = np.asarray(xy, float).reshape(-1, 2); x0, y0, x1, y1 = extent
    d = np.minimum.reduce([xy[:, 0] - x0, x1 - xy[:, 0], xy[:, 1] - y0, y1 - xy[:, 1]])
    t = np.clip(d / width, 0, 1)
    return t * t * (3 - 2 * t)


def visible_ground(B, margin=1.0, nx=41, ny=31):
    """World (x0, y0, x1, y1) of the terrain seen by the current camera."""
    sx, sy = np.meshgrid(np.linspace(0, B.W, nx), np.linspace(0, B.H, ny))
    origins, dirs = B.primary_rays(np.column_stack([sx.ravel(), sy.ravel()]))
    dist, hit = B.rc.first_hits(origins, dirs, 400., *B.TBVH[:6])
    ok = hit >= 0
    if not ok.any():
        return None
    P = origins[ok] + dirs[ok] * dist[ok, None]
    lo, hi = P[:, :2].min(0) - margin, P[:, :2].max(0) + margin
    return float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1])


def face_in_view(B, p, pad=60):
    """False for a face wholly off the page or reaching behind the camera."""
    x, y, z = B.project(p)
    if (z <= B.NEAR).any():
        return False
    return x.max() > -pad and x.min() < B.W + pad and y.max() > -pad and y.min() < B.H + pad


# ---- the seal's shape (drawn by surface_patterns.seal_on_tower) ----------------------

def seal_shape(centre, radius, ring=.028, teeth=9):
    """The approval seal as a 2-D signed distance field in (u, v) metres.

    lib/sdf2d: a ring band, nine rounded teeth repeated in polar sectors and
    smoothly joined inside it, and a core disc cut by a stepped bar. Built at
    the origin, as polar repeats require, then moved to `centre`.
    """
    from lib.sdf2d import sdf as S
    R = float(radius)
    crown = S.union_smooth(S.annular(S.circle(R), ring),
                           S.repeat_polar(S.rounded_box(.06, .022, .012, center=(R * .64, 0.)), teeth), .02)
    core = S.subtract_steps(S.circle(R * .34), S.box(R * .40, .028), .03, 3)
    return S.translate(S.union(crown, core), centre)
