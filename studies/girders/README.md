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

## Integrated generator review (2026-10-30)

The builder reads all generator profiles and all eight detail kinds, including
column-major detail transforms. Beam roll follows the schema even for downward
vertical members. Source group IDs are retained in each point cloud's
`source_group` attribute and the group hierarchy in scene property
`girders_groups`. The canonical spec remains `lib/girders/SCHEMA.md`.

Axon cameras fit the projected bounds at the requested image aspect ratio;
explicit larger `ortho_scale` hints remain valid. The bridge-field generator's
worm camera is offset along the field so the first tower does not hide its
spans. Generator catwalk decks and railings also follow their span yaw; ladders use
local Z for height, matching the renderer. These are minimal orientation and
size corrections in `lib/girders/site.py`, with a numeric regression test.
The inherited site apron and camera hints are retained. Looks add surrounding
ground, cloud-break illumination and metre-scale gravity-aligned material
runoff. The low sun illuminates the front of the structure to reveal its webs.

Immediately before every Cycles render, the renderer checks `/proc` for Rack,
`python -m gorgon.capture`, and the workstation's `capture_existing_jack.py`;
it waits in ten-second intervals while any is running. This also applies to
direct `build.py` renders and verification proofs.

Outward winding is corrected for the atmosphere box, block cubes and I-beam
profiles. The inward atmosphere previously suppressed direct sunlight, making
even lit scenes look flat. Surrounding ground uses a smooth material to avoid
distant procedural texture aliasing.

Verification now checks mesh winding and beam frames for horizontal, upward, downward and near
vertical members; source groups; and complete 16:9 axon framing. Run the commands
above with a generated scene as well as the fixture (`verify.py --scene FILE`).

## V2 art direction

`mineral` uses a graphite, mineral-grey and safety-orange palette, raking pale
sunlight, contact AO and a denser finite atmosphere for depth. `ink` is a warm
paper and graphite print treatment with the same single accent: diffuse steel,
no procedural bump or depth of field, and no denoising to erase fine members.
Both operate on the original instances; neither adds an object per member.
`--camera section` supplies a medium-height oblique perspective, while
`--camera print-axon` supplies an orthographic view fitted to the whole site.
The original camera hints and three original looks remain available.

Use the `hydrapy` Python environment (NumPy and SciPy required), for example:

```sh
~/miniconda3/envs/hydrapy/bin/python studies/girders/render.py \
  --preset fault-spine --scale large --seed 7 --look mineral --camera worm \
  --res 3840x2160 --samples 128 --validate --no-exr --out /path/to/output
```

`verify.py` now renders proofs for all five looks. Every saved render includes
its source scene, native Blender file, script hashes and camera in provenance.

The two v2 generators are `fault-spine` (stepped industrial canyon, deep
cross-ribs and cantilevers) and `suspended-delta` (radial inhabited bridges,
uneven/missing tiers, exposed transfer frames and cable nets). The large seed-7
scenes contain 268,493 / 329,853 beams and 12,400 / 16,198 details respectively;
all still pass through three Geometry Nodes instancers. See `lib/girders/README.md`
for the measured glazing, floor-omission and structural targets.

The fault-spine worm view looks along the X-axis canyon from outside its mouth.
Mineral lighting follows that view; the oblique section camera uses less haze
for its longer sight line. Delta section and print views look between branches;
print elevation follows site width so the radial plan stays visible. For a warm
photographic alternative, use `--look low_sun --camera section` on fault-spine.

Run the complete generator checks, including large support graphs, with:

```sh
GIRDERS_SLOW=1 ~/miniconda3/envs/hydrapy/bin/python -m pytest lib/girders/tests -q
```

When extending the generator, `TrussBridge.W()` uses `origin[2]` for elevation;
its `deck_z` argument alone does not translate geometry. Regression tests compare
actual rib/deck chords against deck blocks and check delta tier-end transfers.
