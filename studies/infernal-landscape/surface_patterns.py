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
from lib.face_patterns import (contour_on_face, cut_discs, hatch_polygon, keep_where, level_spacing_px, lift,  # noqa: E402
                               plane_frame, stride_for_spacing, to_uv, world_spacing)
from lib.face_patterns.sources import Strata, quilt  # noqa: E402
import build as B  # noqa: E402

# The plate studies (plates.py, PLATES.md) include the face patterns and add two more.
PLATES = os.environ.get('INFERNAL_PLATES') == '1'
ENABLED = os.environ.get('INFERNAL_FACE_PATTERNS') == '1' or PLATES
PX_PER_MM = 20
MIN_GAP_PX = .22 * PX_PER_MM       # the study's minimum family gap
LIFT = .004                        # strokes float 4 mm off their wall; the hatch uses 6 mm
MM = dict(strata=.085, quilt_board=.12, quilt_seam=.12, quilt_fill=.085, seal=.12)
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
# Plate studies only. A seal on the approval tower's top storey from 2-D
# distance fields (lib/sdf2d): a ring with nine teeth smoothly joined inside it,
# around a core cut by a stepped bar, drawn as three nested level lines, as an
# incised stone would be. The strata and the wall's hatching stop around it.
SEAL = dict(node='approval', radius=.36, ring=.028, teeth=9, step=.02, cell=.004, levels=3, margin=.04)
# Plate studies only. A barn quilt on the farmstead barn's board, painted in
# jittered passes (lib/fuzz): fills keep the staff quilt's value code at its
# minimum gap, wobble by a fifth of their spacing, and lose paint where a
# smooth noise flakes them; seams between paints are hand-drawn double passes.
if PLATES:
    # Read at a close camera, the bedding is the walls' main texture: twice as
    # many beds as the estate plate (the camera check still thins them) and a
    # line between the field-mark and crease weights.
    STRATA = dict(STRATA, bed=.14)
    MM = dict(MM, strata=.12)
BARN_QUILT = dict(pattern='ohio-star', seed=23, border=.05,
                  fills={1: (4.4, (0.,)), 2: (4.4, (45., -45.)), 3: (6.6, (-45.,))},
                  jitter=.20, inset=.15, edge_passes=2, edge_jitter=.25, flakes=.55, flake_seed=7,
                  flake_cells_per_board=7)


def _node(node_id):
    return next(n for n in B.D['architecture']['nodes'] if n['id'] == node_id)


def _project(polyline, width, audit):
    paths, world = B.stroke_project(polyline, return_world=True)
    audit.append(world)
    return [(q, width) for q in paths]


def strata(exclude=None):
    """Bedding on one building's camera-facing limestone walls.

    `exclude` maps a face index to discs (uv centre, radius) the bedding
    stops around, such as the plate studies' seal."""
    exclude = exclude or {}
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
            for piece in cut_discs([uv], exclude.get(i, ())):
                paths += _project(lift(piece, fr, LIFT), MM['strata'] * PX_PER_MM, audit)
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


def _top_front_wall(node_id):
    """The highest storey wall facing -y (front) of a task building."""
    N = np.asarray(B.D['normals']); walls = []
    for i, f in enumerate(B.FACES):
        if f['mat'] != 1 or not f['name'].startswith(node_id + ' | duration bays'):
            continue
        if np.linalg.norm(N[i] - (0, -1, 0)) > 1e-6:
            continue
        ext = np.ptp(f['p'], axis=0)
        if ext[2] > .9 and ext[0] > 2:          # a storey's wall, not its cornice band
            walls.append(i)
    return max(walls, key=lambda k: B.FACES[k]['p'][:, 2].mean()) if walls else None


def seal_on_tower():
    """Nested level lines of the seal on the approval tower's top storey."""
    node = _node(SEAL['node']); i = _top_front_wall(node['id'])
    empty = dict(paths=[], audit=[], keepouts=[], exclude={}, stats=dict(faces=0))
    if i is None:
        return empty
    N = np.asarray(B.D['normals']); p = B.FACES[i]['p']; fr = plane_frame(p, N[i]); poly = to_uv(p, fr)
    if N[i] @ (B.EYE - p.mean(0)) <= 0:
        return empty
    R = SEAL['radius']
    c = to_uv([[node['x'], p[0, 1], p[:, 2].min() + .43]], fr)[0]
    import plates
    shape = plates.seal_shape(c, R, SEAL['ring'], SEAL['teeth'])

    def field(P):
        d = shape(to_uv(P, fr))
        d[d > 3 * SEAL['cell']] = np.nan        # only the seal and a rim outside its edge
        return d
    # Neighbouring levels must clear the minimum gap on this camera; coarser
    # plates double the step, so their lines are a subset of a finer plate's.
    spacing = level_spacing_px(field, poly, fr, SEAL['step'], SEAL['cell'], B.jac)
    stride = stride_for_spacing(spacing, MIN_GAP_PX)
    paths, audit, lines = [], [], 0
    for k, uv in contour_on_face(field, poly, fr, SEAL['step'], SEAL['cell']):
        if k > 0 or k % stride or k < -(SEAL['levels'] - 1) * stride:
            continue
        lines += 1
        paths += _project(lift(uv, fr, LIFT), MM['seal'] * PX_PER_MM, audit)
    t = np.linspace(0, 2 * np.pi, 49)[:-1]
    disc = c + (R + SEAL['margin']) * np.column_stack([np.cos(t), np.sin(t)])
    stats = dict(node=node['id'], face=B.FACES[i]['name'], centre_world=lift([c], fr)[0].round(3).tolist(),
                 radius=R, teeth=SEAL['teeth'], level_step=SEAL['step'] * stride, stride=stride,
                 min_level_spacing_px=round(spacing, 2), lines=lines, paths=len(paths))
    # Dressed stone: no light hatching inside the seal, and no bedding across it.
    return dict(paths=paths, audit=audit, keepouts=[dict(face=i, frame=fr, polygon=disc)],
                exclude={i: [(c, R + SEAL['margin'] + .02)]}, stats=stats)


def quilt_on_barn():
    """The barn quilt on its board: jittered fills, hand-drawn seams, flaked paint."""
    from lib.face_patterns import clip_polylines
    from lib.fuzz import fuzzy_line, hatch_fill
    import occlusion as M
    N = np.asarray(B.D['normals'])
    fronts = [i for i, f in enumerate(B.FACES) if f['name'].startswith('Barn quilt board') and N[i][1] < -.99]
    if not fronts:
        return [], [], [], dict(faces=0)
    i = fronts[0]; p = B.FACES[i]['p']; fr = plane_frame(p, N[i]); poly = to_uv(p, fr)
    if N[i] @ (B.EYE - p.mean(0)) <= 0:
        return [], [], [], dict(faces=0, facing='away')
    q = BARN_QUILT; lo, hi = poly.min(0), poly.max(0); size = float((hi - lo).min())
    b = q['border'] * size; inner_lo, inner = lo + b, size - 2 * b
    place = lambda unit: inner_lo + np.asarray(unit, float) * inner
    block = quilt(q['pattern'], q['seed'])
    rng = np.random.default_rng(q['flake_seed'])
    flake = M.noise2(q['flake_seed'], q['flake_cells_per_board'] / size)
    strokes, fills, kept = [], {}, []
    finest = None
    for region, role in block['regions']:
        if role not in q['fills']:
            continue
        target, angles = q['fills'][role]
        for a in angles:
            spacing = world_spacing(target, fr, poly, a, B.jac)
            finest = spacing if finest is None else min(finest, spacing)
            lines = hatch_fill(place(region), spacing, a, rng=rng, jitter=q['jitter'] * spacing,
                               inset=q['inset'] * spacing)
            lines, frac = keep_where(clip_polylines(lines, poly), lambda x, y: flake(x, y) < q['flakes'], spacing / 2)
            kept.append(frac); fills[role] = fills.get(role, 0) + len(lines)
            strokes += [(l, MM['quilt_fill']) for l in lines]
    seams = 0
    for e in block['boundaries'] + [np.array([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)], float)]:
        for line in fuzzy_line(place(e), rng, jitter=q['edge_jitter'] * finest, resample=2 * finest,
                               passes=q['edge_passes']):
            for piece in clip_polylines([line], poly):
                strokes.append((piece, MM['quilt_seam'])); seams += 1
    paths, audit = [], []
    for uv, width in strokes:
        paths += _project(lift(uv, fr, LIFT), width * PX_PER_MM, audit)
    stats = dict(face=B.FACES[i]['name'], pattern=q['pattern'], seed=q['seed'], size_world=round(size, 3),
                 fill_lines=fills, seam_passes=seams, paint_kept=round(float(np.mean(kept)), 3) if kept else None,
                 finest_spacing_world=round(float(finest), 4) if finest else None, paths=len(paths))
    return paths, audit, [dict(face=i, frame=fr, polygon=poly)], stats


def face_patterns():
    """Screen paths, hatch keep-outs, world audit samples and a record."""
    seal = seal_on_tower() if PLATES else None
    s_paths, s_audit, s_stats = strata(seal['exclude'] if seal else None)
    q_paths, q_audit, keepouts, q_stats = quilt_on_facade()
    paths, audits, record = s_paths + q_paths, s_audit + q_audit, dict(strata=s_stats, quilt=q_stats)
    if PLATES:
        b_paths, b_audit, b_keepouts, b_stats = quilt_on_barn()
        paths += seal['paths'] + b_paths; audits += seal['audit'] + b_audit
        keepouts += seal['keepouts'] + b_keepouts
        record.update(seal=seal['stats'], barn_quilt=b_stats)
    audit = np.vstack([a for a in audits if len(a)] or [np.zeros((0, 3))])
    return paths, keepouts, audit, dict(record, min_gap_px=MIN_GAP_PX, mm=MM)
