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

## Review of PRs #22–#25 (Claude, 22 October 2026)

The three scenes rebuilt here with `bpy==4.5.14` and the pinned engraving
environment, and reproduced the committed plates exactly before any change.

**Inside-out solids.** The estate `roof()` wound all four faces inward, and
`arch()` wound every voussoir inward, in every scene. The engraver hatches
only faces whose stored normal faces the camera, and `structure()` keeps an
edge only if one of its faces does, so the estate roofs had no hatching on
either visible slope and no near eave, and every arch (estate portals and
approach arch, spillway portals and the permit's waiting frames, the mill
door) drew as an unhatched ring of outlines over hatched wall. PR #25 fixed
the roof for the window only, as a local function. Both windings are outward
in the shared `geometry.py`; the diff against the previous model is exactly
the flipped normals of 16 estate roof faces and 60 voussoir faces per arch,
nothing else. `closed_solids_face_outward` now gates every plate: the signed
flux of each closed solid about its own centroid, per connected component,
so a repeated module's parts and each ring stone are checked separately.

**One builder, two backends.** The three grammars (`estate.py`, `spillway.py`,
`window.py`) call the same primitives; `model.py` mirrors them into Blender
and `dryrun.py` evaluates them in NumPy. Blender's realised Geometry Nodes
repetition is compared with the builder's instancing on every build and
recorded in `blender-checks.json` (`realised_matches_numpy`, float32 error
about 1e-6). The dry run differs from the delivered model only by the
terrain's Displace modifier (up to 0.036 units), which stays in Blender.

**The window plate is now measured.** Zones `aperture` (the reveal) and
`water` join the estate's; the bridge counts as furniture. Main camera: mill
0.384 mean ink, oaks 0.301, aperture 0.153, open ground 0.154, sky 0.009.
The mill leads the view, which gates. The footbridge measures 0.537, darker
than the mill: sixty plank beams at crease weight, close to the eye, with the
depth factor at its 1.24 cap. By the series' rule furniture stays lighter
than the subject; this is advisory because the remedy is geometry (fewer or
thinner planks near the sill, or planks as ink lines rather than beams).

**Thin furniture reads dark by construction.** The spillway's furniture zone
(posts, trays, revetment stakes) measures 0.69 mean ink over 1.5% of the
plate: a beam a few pixels wide is mostly its two silhouette edges. Compare
such zones by area and cell percentiles, not by mean.

**Still open from the previous review.** The estate's approval → restore tray
remains 18% visible from the main camera (advisory); the spillway answered
the camera and height-axis items with a new scene rather than by moving the
estate's services. A roof placed by Python does not follow the `Bays` socket
when it is edited in Blender; the socket identifier is now recorded per host
(`bays_socket`), so a driver on the roof's Z could read it. That is a
model-side change and is not made here.

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
