"""Face patterns: the collection's own 2D generators on the estate's flat walls.

Off unless INFERNAL_FACE_PATTERNS=1, which also moves every stage's output to
output/<case>-face-patterns/ so the delivered plates are never overwritten.
Both patterns go through lib/face_patterns, whose frames are anchored to world
coordinates, and through the same `stroke_project` and ray visibility as every
other stroke of the plate:

- strata: the process-art `stratigraphy` section as a solid field on one
  building's limestone walls. Its level lines are bedding, continuous across
  storeys and around corners, broken where the model blanks its faults. The
  lines reserve tone like any other architecture ink, so the light hatching
  thins beneath them instead of doubling.
- quilt: a barn-quilt block on one facade, its paint roles drawn as hatch
  density (light ground blank, main paint single hatch, contrasting paint
  crosshatch). Paint replaces the wall's light, so the facade's own hatching
  is kept out of the square.

Line spacing is set from the camera: strata drop alternate beds (nested, by
level index) until neighbouring beds are at least the study's 0.22 mm family
gap apart on the page, and quilt fills choose their world spacing so they
land at a fixed page spacing.
"""
from pathlib import Path
import os
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from lib.face_patterns import (contour_on_face, hatch_polygon, level_spacing_px, lift, plane_frame,  # noqa: E402
                               stride_for_spacing, to_uv, world_spacing)
from lib.face_patterns.sources import Strata, quilt  # noqa: E402
import build as B  # noqa: E402

ENABLED = os.environ.get('INFERNAL_FACE_PATTERNS') == '1'
PX_PER_MM = 20
MIN_GAP_PX = .22 * PX_PER_MM       # the study's minimum family gap
LIFT = .004                        # strokes float 4 mm off their wall; the hatch uses 6 mm
MM = dict(strata=.085, quilt_board=.12, quilt_seam=.12, quilt_fill=.085)
# Which building and facade receive which pattern; node ids are the specimen's tasks.
STRATA = dict(node='approval', parts=(' | duration bays', ' entrance base'), bed=.28, stretch=2., cell=.02,
              seed=11, axis=(1., 0., 0.))
QUILT = dict(node='staff', pattern='ohio-star', seed=23, size=.78, border=.045, centre=.43,
             # role: (page spacing in px, hatch angles in degrees, or 'longest' to hatch
             # parallel to a patch's longest edge, so a star point tapers to its tip);
             # 4.4 px is the minimum gap
             fills={1: (4.4, (0.,)), 2: (4.4, (45., -45.)), 3: (7., (-45.,))},
             # At about 4 mm on the page, drawn paint edges read as a window grille;
             # value alone carries the star. True draws them (`boundaries`).
             paint_edges=False)


def _node(node_id):
    return next(n for n in B.D['architecture']['nodes'] if n['id'] == node_id)


def _project(polyline, width, audit):
    paths, world = B.stroke_project(polyline, return_world=True)
    audit.append(world)
    return [(q, width) for q in paths]


def strata():
    """Bedding on one building's camera-facing limestone walls."""
    node = _node(STRATA['node']); N = np.asarray(B.D['normals'])
    faces = [i for i, f in enumerate(B.FACES)
             if f['mat'] == 1 and any(f['name'].startswith(node['id'] + p) for p in STRATA['parts'])
             and abs(N[i][2]) < .05 and N[i] @ (B.EYE - f['p'].mean(0)) > 0]
    if not faces:
        return [], [], dict(faces=0)
    z = np.concatenate([B.FACES[i]['p'][:, 2] for i in faces])
    scale = (z.max() - z.min()) / 1.7       # the walls span most of the section's height
    field = Strata((node['x'], node['y'], (z.max() + z.min()) / 2), STRATA['axis'], scale,
                   stretch=STRATA['stretch'], seed=STRATA['seed'])
    step = STRATA['bed'] / scale
    frames = {i: plane_frame(B.FACES[i]['p'], N[i]) for i in faces}
    # One stride for the whole building, so a bed never stops at a face edge.
    spacing = min(level_spacing_px(field, to_uv(B.FACES[i]['p'], frames[i]), frames[i], step, .06, B.jac)
                  for i in faces)
    stride = stride_for_spacing(spacing, MIN_GAP_PX)
    paths, audit, lines = [], [], 0
    for i in faces:
        fr = frames[i]
        for k, uv in contour_on_face(field, to_uv(B.FACES[i]['p'], fr), fr, step, STRATA['cell']):
            if k % stride:
                continue
            lines += 1
            paths += _project(lift(uv, fr, LIFT), MM['strata'] * PX_PER_MM, audit)
    return paths, audit, dict(node=node['id'], faces=len(faces), section=field.params, bed_world=STRATA['bed'],
                              level_step=step, min_bed_spacing_px=round(spacing, 2), stride=stride,
                              lines=lines, paths=len(paths))


def quilt_on_facade():
    """A barn quilt centred on the portal axis of the top storey's front wall."""
    node = _node(QUILT['node']); N = np.asarray(B.D['normals'])
    walls = []
    for i, f in enumerate(B.FACES):
        if f['mat'] != 1 or not f['name'].startswith(node['id'] + ' | duration bays'):
            continue
        if np.linalg.norm(N[i] - (0, -1, 0)) > 1e-6:
            continue
        ext = np.ptp(f['p'], axis=0)
        if ext[2] > .9 and ext[0] > 2:          # a storey's wall, not its cornice band
            walls.append(i)
    if not walls:
        return [], [], [], dict(faces=0)
    i = max(walls, key=lambda k: B.FACES[k]['p'][:, 2].mean())
    p = B.FACES[i]['p']; fr = plane_frame(p, N[i])
    s = QUILT['size']; c = to_uv([[node['x'], p[0, 1], p[:, 2].min() + QUILT['centre']]], fr)[0]
    outer = c + s * np.array([(-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)])
    b = QUILT['border'] * s; inner_lo, inner = c - s / 2 + b, s - 2 * b
    place = lambda unit: inner_lo + np.asarray(unit) * inner
    block = quilt(QUILT['pattern'], QUILT['seed'])
    # The board's edge only: the painted border band is ~2 px on the page, and
    # a second line there merges with the first into a heavy frame.
    strokes = [(np.vstack([outer, outer[:1]]), MM['quilt_board'])]
    if QUILT['paint_edges']:
        # Paint edges only: seams between patches of one colour are not drawn.
        strokes += [(place(e), MM['quilt_seam']) for e in block['boundaries']]
    fills = {}
    for region, role in block['regions']:
        if role not in QUILT['fills']:
            continue
        target, angles = QUILT['fills'][role]
        if angles == 'longest':
            ring = place(np.vstack([region, region[:1]])); d = np.diff(ring, axis=0)
            e = d[np.argmax(np.linalg.norm(d, axis=1))]
            angles = (float(np.degrees(np.arctan2(e[1], e[0]))),)
        for a in angles:
            spacing = world_spacing(target, fr, outer, a, B.jac)
            lines = hatch_polygon(place(region), spacing, a)
            fills[role] = fills.get(role, 0) + len(lines)
            strokes += [(q, MM['quilt_fill']) for q in lines]
    paths, audit = [], []
    for uv, width in strokes:
        paths += _project(lift(uv, fr, LIFT), width * PX_PER_MM, audit)
    keepout = dict(face=i, frame=fr, polygon=outer)
    return paths, audit, [keepout], dict(node=node['id'], face=B.FACES[i]['name'], pattern=QUILT['pattern'],
                                         seed=QUILT['seed'], size_world=s, centre_world=lift([c], fr)[0].round(3).tolist(),
                                         fill_lines=fills, paths=len(paths))


def face_patterns():
    """Screen paths, hatch keep-outs, world audit samples and a record."""
    s_paths, s_audit, s_stats = strata()
    q_paths, q_audit, keepouts, q_stats = quilt_on_facade()
    audit = np.vstack([a for a in s_audit + q_audit if len(a)] or [np.zeros((0, 3))])
    return s_paths + q_paths, keepouts, audit, dict(strata=s_stats, quilt=q_stats, min_gap_px=MIN_GAP_PX, mm=MM)
