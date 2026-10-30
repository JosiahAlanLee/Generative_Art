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
- **fault-spine** (v2) — an asymmetric industrial canyon: two irregular
  rows of tall inhabited blocks facing each other, terraced setbacks, huge
  trussed cantilevers off the rims, deep truss ribs (8–18 m) across the
  gap at several levels, draped cable nets, and more than half of the
  floor plates omitted so the secondary lattice reads through.
- **suspended-delta** (v2) — a horizontal, layered inhabited bridge
  megastructure: a squat central hub with 3–7 deck tiers radiating like a
  river delta, each tier a deep-trussed inhabited bridge ending at a
  sparse irregular buttress, cable stays and nets lacing the tops, large
  voids between the branches.

## Scales

`small` (< 2 s, ~1–11k beams), `medium` (~5–65k beams), `large`
(≈10^5 beams for the v1 presets, 250k+ for the v2 presets, in 2–4 s, plus
~1–2 s to save the gzipped file).  Generation is deterministic: the same
`(seed, preset, scale)` always yields byte-identical files.

Measured for seed 7 (generator 0.2.0 presets):

| preset            | scale  | blocks | beams  | details | secondary | glass | plates omitted |
|-------------------|--------|-------:|-------:|--------:|----------:|------:|---------------:|
| fault-spine       | small  |     90 | 11 624 |     325 |       86% |  0.0% |            71% |
| fault-spine       | medium |  1 246 | 63 066 |   1 618 |       90% |  0.4% |            74% |
| fault-spine       | large  |  2 509 | 268 493 | 12 400 |       93% |  0.5% |            64% |
| suspended-delta   | small  |     86 | 13 201 |     758 |       72% |  0.0% |            75% |
| suspended-delta   | medium |    204 | 49 755 |   2 667 |       67% |  1.0% |            79% |
| suspended-delta   | large  |    536 | 329 853 | 16 198 |       71% |  1.7% |            73% |

Large fault-spine: 8 cantilever + 26 setback groups, 22 deep truss ribs at
9.4–17.3 m depth.  Large suspended-delta: a hub tower and 7 radiating
branches of 5 tier decks each (one tier intentionally missing per branch),
8 cantilever groups, 35 deep-trussed tiers at 9.0–13.0 m depth, buttress
frames and hub tower rising past the top tier with transfer columns,
struts, knees and rakers tying every deck end in.  Both keep secondary
lattice pitch in [0.6, 1.2] m with L70/L90/TUBE90 sections (0.07–0.09 m
wide), ROD30 cable nets, and TUBE50+ pipes/rails, so the fine members read
at 4K.  Every rib/deck truss sits at its deck elevation (regression-tested
against ground-level trusses), and long members are split into <= ~2.4 m
segments so the validator stays fast on 250k+ beam scenes.

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
- `site.py` — v1 towers, bridges, gantries, catwalks, pipes, stairs, ruins
- `site_v2.py` — v2 megastructures: inhabited blocks, cantilevers, deep
  ribs, buttresses, layered decks, cable nets (fault-spine, suspended-delta)
- `trusses.py` — truss expansion into chords/webs/verticals/laterals
- `generate.py` — top-level `generate()`, file I/O, CLI
- `schema.py` — validator
- `preview.py` — axonometric line-drawing PNGs (matplotlib, no Blender)
- `profiles.py` — cross-section and material libraries

Tests: `python -m pytest lib/girders/tests/` from the repository root.
The v2 numeric guarantees live in `tests/test_girders_v2.py`; the slow
large-scene validator there runs with `GIRDERS_SLOW=1`.
