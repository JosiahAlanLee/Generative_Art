# Girders

Native Blender builder, look library and headless renderer for
`girders-scene-1` scenes. The geometry source is independent of the Python
generator: the Blender builder imports nothing from `lib/girders/`. The
caller-side renderer can generate a scene directly for convenience.

## Build and render

```sh
B=~/dev/blender-5.2.3-linux-x64/blender
python studies/girders/testscene.py --kind fixture --out /tmp/girders-fixture.json.gz
$B -b --python studies/girders/build.py -- \
  --scene /tmp/girders-fixture.json.gz --out /tmp/girders.blend
python studies/girders/render.py /tmp/girders-fixture.json.gz \
  --look low_sun --camera worm --res 3840x2160 --samples 128 \
  --out ~/dev/shared/codex/girders-20261030/worm

python studies/girders/render.py --preset dense-core --seed 7 --scale medium \
  --validate --look overcast --camera axon --res 3840x2160 --samples 128 \
  --out ~/dev/shared/codex/girders-20261030/dense-axon --no-exr
```

`render.py` is the caller-side CLI. It invokes Blender 5.2, builds the scene,
saves the `.blend` and writes PNG, EXR, a render log and `provenance.json`.
It accepts an existing JSON/JSON.GZ scene or `--preset/--seed/--scale`; generated
input is saved as `generated-scene.json.gz` beside the render.
Use `--preview` for a 960x540, low-sample proof. `--camera auto` chooses a
worm's-eye or orthographic camera from the scene bounds.

The builder creates three scene-wide Geometry Nodes instancers: beams, blocks
and small details. Their collections contain tiny profile/part variants by
material. A point cloud carries midpoint, orientation, scale and variation;
there is never a Blender object per structural member. This keeps a 500k-beam
stress scene as three instancer objects plus their reusable assets.

## Looks and verification

`look.py` provides `overcast`, `low_sun` and `night`. They use Cycles,
material-specific procedural wear, large soft sources, physical camera
settings, OptiX denoising, volumetric atmosphere and a mist pass. Camera hints
are honoured; names containing `axon` use an orthographic camera.

```sh
~/miniconda3/envs/hydrapy/bin/python studies/girders/verify.py \
  --out ~/dev/shared/codex/girders-20261030/verify
```

The wrapper generates the fixture, runs native Blender checks and renders one
low-resolution proof for every look. `verify_blender.py` can also be run
directly inside Blender.

## Fixture and limits

`testscene.py` is a deterministic fixture generator, not the art generator. It
produces two massing towers, a bridge truss, gantries, catwalks, rails, pipes,
cables and procedural details. `--kind stress --beams 500000` emits the large
performance fixture.

The instanced profiles are exact solid section approximations, not fabrication
models. Grating, surface wear and exposure are shader detail. Volumetric haze
is an art direction control and is not a physical atmospheric simulation.

The canonical scene contract is `lib/girders/SCHEMA.md`; the local `SCHEMA.md`
is only a pointer so the two implementations cannot drift.

## Provenance

Original procedural work for Josiah Alan-Lee, October 2026. No downloaded
models, textures or reference imagery are used. Mood references were treated
as direction only; this is not derived from a specific Landlinesart or Ge1doot
composition.
