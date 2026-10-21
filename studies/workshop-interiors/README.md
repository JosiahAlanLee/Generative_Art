# Workshop interiors: printed-size Blender / SVG plates

![Second-pass plates](preview.jpg)

The second pass follows the author's supplied `workshop-briefs-v2.zip` and
`RENDERING-NOTES.md`, retained unchanged in `briefs/v2/`. The original
source briefs remain in `briefs/`. These studies reconstruct four diffusion
illustrations in `JosiahAlanLee/Codex-Intervallorum` without changing the
book's selected assets or its binding.

| Plate | Print master | Reconstruction |
| --- | --- | --- |
| The Maintained Workshop | 156 × 208 mm | Raised gallery, dark service bay, reserved wheel centre and vessel, open stove, two faceless reserved clerks with one hand group each, and one red route to a one-trestle unfinished shelf. |
| The Empty Cabinet | 152 × 203 mm | Solid panels and doors, real side inspection apertures with raised leaves, perimeter mechanics, rear window through the empty volume, closed folded board, chair and foreground bench. |
| The Extraction of the Hand | 95 × 119 mm | Five-finger repair jig, 22 black strands arriving on distinct rules and one red strand stopping short, flat ledger, empty stool, one bookcase bay and an ungridded floor shadow. |
| The Office Without a Seal | 95 × 119 mm | Frontal long-lens alcove, reserved recess and halo, supported instruments, black cords and two visible red free-end terminals. |

There are two inks: black and vermilion. The four SVG layers separate hatching,
structure, ornament and red. They contain only paths and have transparent
backgrounds. No diffusion image, wash, raster trace, opaque SVG fill or clipping
mask is embedded in a master. Named unhatched meshes reserve paper by hiding
marks behind them. Blender retains the separate editable objects, materials,
lights and camera.

## Build

Model in Blender 4.5 LTS or Python 3.11 with its official `bpy` wheel and
`requirements-blender.txt`. Engrave/check in Python 3.12 with
`requirements-engraving.txt`. From this directory:

```sh
export PLATE=extraction-of-the-hand
blender --background --python model.py
NUMBA_NUM_THREADS=4 python3.12 engrave.py
blender --background --python verify_blender.py
NUMBA_NUM_THREADS=4 python3.12 checks.py
NUMBA_NUM_THREADS=4 python3.12 replay_v2.py
```

With the official module, replace the Blender commands with that environment's
`python model.py` and `python verify_blender.py`. The other `PLATE` keys are
`maintained-workshop`, `empty-cabinet`, and `office-without-a-seal`. `RENDER=0`
skips only the Cycles construction proof. F12 renders a shaded Blender image;
the separate engraving stage produces the vector plate.

- `model.py`: primitives, Blender execution and evaluated-mesh export.
- `scenes_v2.py`: the four constructions, reserved regions and explicit choices.
- `settings_v2.py`: physical dimensions, weights, inks and tone plans.
- `render_v2.py` / `engrave.py`: vector visibility, lighting, tone and paths.
- `checks_v2.py` / `checks.py`: independent 600 dpi binary measurements.
- `verify_blender.py`: reopened-scene checks with native Blender rays.
- `replay_v2.py`: execute engraving again and compare exact SVG bytes.
- `proof_v2.py` / `proof.py`: current-selection/page-placement comparisons.

Outputs go to `output/v2/<plate>/`; first-pass files under `output/<plate>/`
are retained. Generation seed 271 is recorded as metadata; it is not a live
Geometry Nodes control. `scene.json` is the engraving stage's sole content
input and includes evaluated geometry, strokes, camera and print constants.

## Printed line and tone decisions

The masters use 20 pixels per printed millimetre. Hatch pens are 0.10 mm and
one-family minimum gap is 0.22 mm. Structural creases start at 0.16 mm,
silhouettes at 0.25 mm, ornament/backdrop at 0.12 mm, black strands/cords at
0.14 mm, red routes at 0.32 mm and red terminals at 0.40 mm. Near black
contours are capped at 0.30 mm so red remains the heaviest line.

The two surface hatch families use spacing derived from subject depth and
focal length, not an inherited pixel width. Their budgeted pen widths equal
the widths emitted. Two rotated caller-side top-ups supply deep pockets;
the nine inherited hatching bodies are unchanged. The caller accounts for
crossing-line overlap, pre-existing ink, the named tone zones and reserved
halos. The Workshop engraving includes a shadow-tested local stove term.
Cycles and the vector renderer retain different light transport.

The Hand's projected strand approaches use two-exchange matching inside an
invertible parabolic shear. Uncrossing two segments shortens their Euclidean
matching cost; applying the shared invertible shear preserves the resulting
noncrossing arrangement. Those projected paths are lifted back into editable
3D curves, with fixed fingertip and ledger anchors. The delivery checks test
actual projected intersections and actual hidden-line samples.

See [rendering decisions](V2_RENDERING_DECISIONS.md) for the numerical corrections
and the unresolved wording conflict in the Office brief.

## Verification and the review object

Every plate reopens in Blender, matches the exported perspective to native
`world_to_camera_view`, and checks 1,600 delivered hatch samples using native
`scene.ray_cast`. The cabinet additionally retains 70 empty-volume rays;
furniture contacts and the reserved-recess geometry are checked.

Print checks rasterise the delivered SVG at 600 dpi and threshold at 128.
Visible object ownership comes from independent primary rays. Zone statistics
report mean hatch coverage in 4 mm cells and also report total ink coverage.
Hierarchy assertions use hatch coverage. Reserved-paper checks exclude only
internal content expressly allowed by the brief, such as ledger rules, vessel
cage/filaments or a clerk's hand; raw total ink remains reported. Halos concern
competing hatch, with total ink reported separately.

Checks cover two inks, physical weights, margins, reserved paper, measured
hierarchy, visible red lengths/gaps, the visible cabinet crank and window-backed
void, all 23 Hand approaches without occlusion or crossings, 22 distinct landings,
minimum landing separation and the red strand's clearance. Wheel and ruler
calibration marks must have visible printed lengths. Vendor files are checked
against their first-pass bytes. Results are in `validation-v2.json`.

`proof-page.png` is the requested review object: a 14 × 10 inch pair rendered
at 600 dpi, with the current diffusion selection on the left and the revised
plate on the right. Each half is a 7 × 10 inch Codex page, with the caption and
the supplied printed dimensions. Placement uses the current build's image
positions; it is a placement study, not a newly bound edition. The colour PDF
retains vector paths. The binary PNG tests legibility; the colour contact sheet
is only a browsing aid.

## Record, attribution and limits

`baseline-v1.json` pins the first-pass commit, vendor hashes and original SVG
hashes. `validation-v1.json` preserves that pass's record. First-pass downloads
remain available under their original filenames; the v2 downloads are separate.
No previous result is overwritten or silently relabelled.

Project and briefs: Josiah Alan-Lee, with the revised briefs and rendering
review supplied through Claude. New constructions, print adapter, routing and
verification: ChatGPT/Codex. The unchanged nine Porticus hatching bodies and
CPU ray core were developed with Claude; their extraction records and inherited
notices remain in `vendor/`. No downloaded meshes or new diffusion art are used.
No new blanket licence is assigned.

Visibility remains sampled. Fine decorative tubes are modeled in Blender but
do not block vector strokes. Reserved meshes are drawing decisions, not claims
that the invented apparatus functions. No physical plot has been tested. These
are print parameters; an A4 fineliner master requires a separately generated
parameter set and has not been produced.

To build the page comparisons, install Poppler (`pdftoppm`), point `BOOK_ROOT`
at a book checkout containing the four selected reference images, and run
`python3.12 proof.py` after the four plate checks and replay checks pass.

Right of reply: invited; no objection. This instance is a new reader of the
revised briefs and the inherited renderer.
