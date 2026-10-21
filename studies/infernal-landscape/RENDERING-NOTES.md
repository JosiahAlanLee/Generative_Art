# Rendering notes: Infernal Engine 0.2

These notes belong to this study. The earlier copy here was the workshop-interior
note verbatim, addressed to `studies/workshop-interiors` and four briefs that
are not in this repository; the shared numbers survive below, the rest does
not apply.

Everything here is caller-side, in `render.py`, `checks.py` and `measure.py`.
The nine vendored hatch bodies, the ray kernel, the Driftless engine and the
reachability evaluator are unchanged and hash-checked.

## Line weights and tone budget

Declared in millimetres on the printed page at 156 mm width, 20 px/mm:

| line | mm |
| --- | --- |
| hatch | 0.10 |
| minimum family gap | 0.22 |
| silhouette edge | 0.25 × depth factor 0.80–1.24 |
| crease edge | 0.16 × depth factor |
| ornament, branches | 0.12 / 0.10 |
| foliage outlines | 0.08 |
| field marks | 0.085 |
| red | 0.32, the heaviest line on the plate |

Allocator: `C_MAX .82`, `GAMMA 1.05`, `C_SPLIT .20`, `MIN_GAP = gap`, and the
budgeted family widths equal the width written to the SVG.

## Tone hierarchy

The subject leads. Gains multiply the lit darkness before allocation:

| surface | gain |
| --- | --- |
| buildings | 1.0 |
| plinths, foundations, lift landing | 0.62 — a plinth is lighter than the storeys it carries |
| fence, service supports and trays, piers | 0.55, and their edges at crease weight — furniture, not subject |
| open ground (original terrain) | 0.28 |
| open ground (eroded terrain) | 0.42 + 0.42 × slope, unchanged from the erosion study |

Oak crowns ink only their front-facing leaf polygons; visibility already hides
the rest behind them, and the back-facing ones added weight without outline.

## Red

Black records an arrangement; red marks what happened (the series' rule).
Every dependency tray is black. `compile.classify_routes` puts the red
centerline on the critical path to the target: an edge is red when the
source's finish set the target's start. A node whose start was set by its
release gets a red mark on the lift upright nearest the camera, and the edges
into it stay black because they carried slack. With no executable completion
the red follows the critical path to the first closed gate and stops. The
rule is recomputed from the record embedded in `scene.json`, so earlier scene
records need no Blender rebuild.

## What is measured

`measure.py`:

1. Zones. Every face of the scene record is projected through the plate's
   camera in painter's order, so each pixel knows which named object it shows:
   sky, terrain, building, oak, furniture, other.
2. Ink. The SVG rasterised at the master resolution; coverage in 4 mm cells.
3. Red. Each red route's projected length, visible fraction (within 3 px of a
   delivered red path) and longest hidden run, in millimetres.

`checks.py` gates on `tone_hierarchy_buildings_lead`,
`open_ground_is_the_lightest_surface`, `red_follows_critical_path` and
`red_is_heaviest_line`. Red-route visibility is recorded under `advisory`
with thresholds of 60% visible and 8 mm longest gap; it is not gating because
the remedy is geometry.

## Measured on the delivered plates

Recorded Route, main camera, before → after this revision:

| zone | mean ink before | after |
| --- | --- | --- |
| buildings | 0.377 | 0.371 |
| oaks | 0.404 | 0.223 |
| open ground | 0.097 | 0.078 |
| share of all ink on buildings | 24% | 29% |
| share of all ink on open ground | 64% | 62% |

Darkest 4 mm cell 0.56 (unchanged; the budget already delivered darks). Red:
read → approval 78% visible; approval → restore 18% visible with a 23 mm run
behind the staff building, on every plate where that edge is red.

## Open items that are not rendering

- The approval → restore tray runs behind the staff building from both saved
  cameras. It needs to go on the camera side, or higher, in `model.py`.
- Buildings are about 5% of the plate from the main camera and sky is 36%; a
  closer, lower camera is a model-side change (saved cameras are checked
  against Blender's).
- Release time shares the height axis with duration; the lighter plinth
  reduces the collision but does not remove it.
- Ridge oaks are volumetric ring clusters; the drawn Driftless oak reads
  better and could be instanced through the owner-aware buffer.

## Second scene: spillway works

[The spillway scene](SPILLWAY.md) applies those model-side suggestions with a
new graph and building grammar. It retains these line weights and the critical
path classification. Duration repeats horizontal sawtooth bays; release wait
extends an access passage, whose exposed handrail carries the release red.
The critical conduits run along the fronts. Route visibility, including the
release marker, is gating for this profile; the original estate keeps its
advisory status. The original cameras and geometry remain available.

The new terrain gain is 0.24 + 0.20 × slope; its composition still uses the
36-step incision field and actual receiver traces. Three volume trees remain,
with owner-aware Driftless oaks on the ridge. Their actual silhouette masks
now enter the zone measurements when available. `tree-zones-VIEW.npz` is audit
metadata; it is not embedded in the SVG.
