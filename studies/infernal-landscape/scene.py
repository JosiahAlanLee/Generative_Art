"""Case selection and scene assembly shared by the Blender model and the dry run.

INFERNAL_CASE selects a compiled specimen (or `custom` with INFERNAL_INPUT),
INFERNAL_TERRAIN selects `original` or a prepared erosion state. The profile
recorded in the architecture picks the scene grammar: estate, spillway or
window. Each grammar builds through the same primitives, so the two backends
differ only in who evaluates the geometry.
"""
from pathlib import Path
import json, os
import numpy as np
from compile import compile_case, compile_document
from terrain_height import base_height, sampler

ROOT = Path(__file__).resolve().parent


def output_dir(case=None, terrain_mode=None):
    """output/<case>[-<terrain>][-plates|-face-patterns][-dryrun]: every stage of a build shares it.

    INFERNAL_DRYRUN=1 keeps a NumPy dry run beside the delivered Blender
    build instead of overwriting it, INFERNAL_FACE_PATTERNS=1 keeps the
    face-pattern comparison beside it too (see FACE-PATTERNS.md), and
    INFERNAL_PLATES=1 keeps the plate studies' scene, which adds a farmstead
    and two cameras, in its own folder (see PLATES.md); it includes the face
    patterns. patches.cjs applies the same suffixes."""
    case = case or os.environ.get('INFERNAL_CASE', 'recorded_route')
    terrain_mode = terrain_mode or os.environ.get('INFERNAL_TERRAIN', 'original')
    name = case if terrain_mode == 'original' else case + '-' + terrain_mode
    if os.environ.get('INFERNAL_PLATES') == '1': name += '-plates'
    elif os.environ.get('INFERNAL_FACE_PATTERNS') == '1': name += '-face-patterns'
    if os.environ.get('INFERNAL_DRYRUN') == '1': name += '-dryrun'
    return ROOT / 'output' / name


def context():
    case = os.environ.get('INFERNAL_CASE', 'recorded_route')
    terrain_mode = os.environ.get('INFERNAL_TERRAIN', 'original')
    out = output_dir(case, terrain_mode)
    out.mkdir(parents=True, exist_ok=True)
    A = (compile_document(json.loads(Path(os.environ['INFERNAL_INPUT']).read_text()), case)
         if os.environ.get('INFERNAL_INPUT') else compile_case(case))
    (out / 'architecture.json').write_text(json.dumps(A, indent=2))
    state = None; terrain_z = base_height
    if terrain_mode != 'original':
        source = out / 'terrain-state.npz'
        if not source.exists():
            raise FileNotFoundError('Prepare terrain with the engraving Python: python erosion.py')
        state = dict(np.load(source)); terrain_z = sampler(state)
    return dict(case=case, terrain_mode=terrain_mode, out=out, A=A, state=state, terrain_z=terrain_z)


def grid(ctx):
    if ctx['state'] is None:
        return np.linspace(-30, 30, 101), np.linspace(-20, 44, 105)
    return ctx['state']['x'], ctx['state']['y']


def profile_module(A):
    profile = A.get('scene_profile', 'estate')
    if profile == 'spillway':
        import spillway as m
    elif profile == 'window':
        import window as m
    else:
        import estate as m
    return m


def assemble(builder, ctx):
    """Terrain host, the profile's architecture, then its cameras.

    With INFERNAL_PLATES=1 the estate also receives the plate studies'
    farmstead and their two cameras, and its oaks are built as bur oaks
    (plates.py)."""
    builder.terrain_grid(*grid(ctx))
    m = profile_module(ctx['A'])
    plates_on = os.environ.get('INFERNAL_PLATES') == '1'
    if plates_on:
        if m.__name__ != 'estate':
            raise ValueError('the plate studies are composed for the estate profile only')
        import plates
        oaks = plates.use_bur_oaks(builder)       # the estate's T.oak calls now build bur oaks
    top, base, footprints, routes = m.build_scene(ctx['A'], builder)
    cameras = list(m.CAMERAS); plates_record = None
    if plates_on:
        extra, plates_record = plates.add_farmstead(builder)
        plates_record['oaks'] = oaks
        footprints = footprints + extra; cameras += plates.CAMERAS
        # The scene record's schema is unchanged; the plates' own record (the
        # farmstead's seeds, decay, placement and quilt board, and the oaks as
        # built, which draw_oaks regenerates from) sits beside it.
        (ctx['out'] / 'plates-farmstead.json').write_text(json.dumps(plates_record, indent=2, default=float))
    for name, eye, target, focal in cameras:
        builder.camera(name, eye, target, focal)
    return dict(top=top, base=base, footprints=footprints, routes=routes,
                planar_trees=getattr(m, 'PLANAR_TREES', None), plates=plates_record)
