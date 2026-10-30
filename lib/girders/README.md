# lib/girders — seeded block-and-girder megastructure generator

Pure Python + numpy generator for vast industrial megastructures: concrete
cores and slabs, steel perimeter frames with X/K/chevron bracing, truss
bridges (Warren, Pratt, Howe, Vierendeel, lattice), gantry cranes, catwalks,
stairs, ladders, pipe runs, cable stays and small instanced details (bolt
plates, rivet rows, railings, vents, lights).  It emits the `girders-scene-1`
JSON format in `SCHEMA.md`, which the Blender builder in `studies/girders`
consumes; neither imports the other.

## Use

```python
from lib.girders import generate, validate, save_scene, load_scene
scene = generate(seed=7, preset="dense-core", scale="medium")
errors = validate(scene)      # [] means structurally sound
save_scene(scene, "scene.json.gz")
```

## CLI

From the repository root:

```
python -m lib.girders generate --preset NAME --seed N --scale small|medium|large \
    --out scene.json.gz [--validate] [--preview preview.png]
python -m lib.girders preview  --preset ruin --seed 7 --out preview.png
python -m lib.girders validate scene.json.gz
```

Run `python -m girders.generate --preset ... --seed ... --out ... --scale ...`
with the same flags from inside `lib/` (or with `lib` on `PYTHONPATH`).

## Presets

- **dense-core** — tall towers, heavy concrete cores, dense steel frames,
  roof tanks, high Warren/Pratt/Howe bridges.
- **bridge-field** — a field of slender towers joined by long-span trusses
  at several levels, cable-stayed centre spans, catwalks.
- **stacked-gantries** — a dense grid of squat towers stacked with gantry
  crane rails and lattice gantries at several heights, pipes everywhere.
- **ruin** — the dense-core plan decayed: rust, missing secondary members,
  sagged cables, fallen spans and collapsed roof corners; the primary
  structure still stands.

## Scales

`small` (< 2 s, ~1–3k beams), `medium` (~4–11k beams), `large`
(≈10^5 beams in ~1 s, plus ~1 s to save the gzipped file).  Generation is
deterministic: the same `(seed, preset, scale)` always yields byte-identical
files.

## Validation

`lib.girders.schema.validate(scene)` returns a list of problems (empty =
valid): format, materials/profile references, finite geometry, bounds, zero
lengths, stats, and a structural support check — every block rests on a
chain of supports down to the ground and every beam is anchored (ends meet
blocks, the ground or other members at nodes).  Beams tagged `free`/`stub`
may cantilever.  See the docstring in `schema.py` for the tolerances.

## Layout

- `presets.py` — named presets + per-scale parameters
- `scene.py` — SceneBuilder, 4×4 detail transforms, bounds, camera hints
- `site.py` — towers, bridges, gantries, catwalks, pipes, stairs, ruins
- `trusses.py` — truss expansion into chords/webs/verticals/laterals
- `generate.py` — top-level `generate()`, file I/O, CLI
- `schema.py` — validator
- `preview.py` — axonometric line-drawing PNGs (matplotlib, no Blender)
- `profiles.py` — cross-section and material libraries

Tests: `python -m pytest lib/girders/tests/` from the repository root.
