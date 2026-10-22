# Local plot workbench (prototype)

Launch existing generators, inspect an SVG, and retain the recipe and artifacts
for each render. The server uses the Python standard library and plain HTML/CSS/JS;
there is no frontend build, web framework, Electron bundle or required GUI toolkit.
The generator algorithms and standalone entry points are unchanged.

## Start

From the repository root, with Python 3.10+ and Node.js 18+ on PATH:

```sh
python -m venv .venv
# Linux/macOS; on Windows use .venv\Scripts\activate
. .venv/bin/activate
python -m pip install -r studies/farm-remnants/requirements.txt
python -m workbench.server
```

Open **http://127.0.0.1:8765**. Driftless needs Node only; you can omit the Farm
requirements to try it first. Farm also needs the Cairo native library for PNG
export (see [CairoSVG installation](https://cairosvg.org/documentation/)); disable
PNG to use the SVG proof without that export dependency. Numba's first render
compiles kernels and can take longer. Keep the checkout intact: Farm imports
Infernal's geometry and vendor ray kernel.

The default output root is `.workbench/jobs/` (ignored by Git). To use another
location, including paths with spaces:

```sh
python -m workbench.server --port 8765 --output-root "/path/to/plot jobs" --timeout 3600
```

Use a single server for a given output root. It binds to IPv4 loopback only;
keep it local. Host, Origin and session-token checks guard job mutations.
It is a development server, without remote access or multi-user support.
Ctrl-C stops active jobs and closes the queue. A hard shutdown leaves an
interrupted job on the next start; render its saved recipe to retry.

## Why a localhost application?

| Choice | Advantages here | Costs |
| --- | --- | --- |
| Lightweight desktop, e.g. Python/Tk or Qt | Native file dialogs and process launching; a future installable studio window | Tk needs extra SVG rendering support; Qt adds runtime/packaging dependencies. Neither removes Node/bpy/engraving environment management. |
| Python localhost server + browser (**implemented**) | Standard-library process runner; native browser SVG proof; no JS packages or frontend build; close to Driftless's existing interface | Browser downloads replace native save dialogs; server lifecycle and local request protection need explicit handling. |

The earlier interface study supplied a direction for a paper proof, layer controls
and inspection. This prototype connects real generation/export with that workflow;
it does not embed the study's large sample drawings or claim its simulated travel
view is measured plot time. The Python adapters can later sit behind a desktop
shell without changing the generators.

## Generate, inspect, export, reopen

1. Choose Driftless or Farm; set an explicit seed and controls. Render creates a
   unique UUID folder. Jobs run one at a time; up to eight may be active/queued.
2. Select the SVG or PNG from **Preview file**. SVGs show physical dimensions,
   viewBox, drawing-element counts and labeled layers. Toggle layers and zoom to
   inspect the proof. Layer switches affect the preview only; exported originals
   always contain every layer. Browser viewing is not a physical pen simulation.
3. Download an artifact or use its displayed disk path. All artifacts and stage
   logs have download links. Original SVG, PNG and geometry are kept together.
4. **Save recipe** downloads JSON; **Load recipe** restores controls without
   rendering. Every job also retains `recipe.json` on disk. Loading one and
   rendering again creates a new output directory. History survives a restart.
5. The job record includes exact argv, runtime paths, source SHA-256 hashes,
   status and exit code. `job.log` captures stdout/stderr; its UI view shows the
   latest 64 KiB, with a full download available. Files from failed/cancelled jobs
   remain available for diagnosis. No installation, package updates or application
   launch commands are accepted from the browser.

Driftless exposes its existing page formats, landscape/bleed, palette/strength,
text zone, density, imperfection, motif weights, subject, season, light and frame.
Native travel optimization is on unless **Keep original drawing order** is checked.
`codexPlot` keeps the CLI's enforced sheet/inset rules; bleed/riso/landscape settings
that the CLI ignores remain ignored. SVG is the proof and export; no raster preview
package is needed.

Farm exposes object/comparison selection, base seed, decay and optional PNG export.
Its CLI offsets the seed by family index even with `--only`: barn +0, tractor +1,
disk harrow +2, rake +3, wagon +4. The recipe and generated JSON record both make
that distinction inspectable. Page sizes remain the generator's 190 × 140 mm
specimens and 280 × 210 mm yard. OBJ/scene JSON exports remain available. Decay
is an artistic control, not a model of elapsed years.

## Runtime configuration and Infernal

Set these environment variables **before** starting the server; each is one
executable path, not a shell command or flags. Defaults use PATH / the server Python.
Use absolute paths for virtual environments; do not use `~` inside quoted values.

| Variable | Used for |
| --- | --- |
| `WORKBENCH_NODE` | Driftless and Infernal patches (`node` by default) |
| `WORKBENCH_PYTHON` | Farm and Infernal orchestration (server Python by default) |
| `WORKBENCH_ENGRAVING_PYTHON` | Infernal NumPy scene/engraving/checks (server Python by default) |
| `WORKBENCH_BLENDER_PYTHON` | Python with the official `bpy` wheel; required for a full Blender render |
| `WORKBENCH_VPYPE` | Optional vpype executable (`vpype` by default) |

For Infernal, create the two environments described in the
[study README](../studies/infernal-landscape/README.md) using its
[engraving](../studies/infernal-landscape/requirements.txt) and
[bpy](../studies/infernal-landscape/requirements-blender.txt) requirements.
They need compatible Python/package versions, independently of the GUI server.
For example on Linux/macOS:

```sh
export WORKBENCH_ENGRAVING_PYTHON="/path/to/engraving-env/bin/python"
export WORKBENCH_BLENDER_PYTHON="/path/to/bpy-env/bin/python"
python -m workbench.server
```

The adapter invokes the existing `run.py` with case, camera, dry run, no-clay,
face-pattern and plates flags. Plates includes face patterns; tower/barn cameras
require Plates. Infernal currently has fixed scene seeds, so the GUI does **not**
pretend to offer a working seed control for it. Arbitrary task JSON/erosion presets
are outside this initial adapter.

Because Infernal uses paths relative to its source files, the adapter copies source
from `studies/infernal-landscape` and `lib` into the job's `workspace/`, preserving
repo-relative imports and vendor code. Delivered `output/`, tests and caches are
excluded. Every existing stage runs there: model → Node patches → engraving →
checks, plus native Blender ray checks for full renders. Stage logs and outputs
are downloadable in the GUI. It does not bypass a failed validation stage or
replace the orchestrator. Unrelated `INFERNAL_*` environment flags are cleared.

Dry run uses NumPy, without bpy, saved `.blend`, clay proof or native Blender
validation. Its artifacts keep the study's dry-run suffix. A successful dry run
is not a validated Blender delivery. A full render requires **a Python containing
bpy**, not the `blender` GUI executable; that is the existing `run.py` contract.
No package install is performed by the GUI.

## vpype and DrawingBot V3

**Make vpype copy** is optional and explicit. It requires a successful render and
an idle queue. Install vpype in its own environment if its dependency constraints
conflict with engraving, then point `WORKBENCH_VPYPE` at its executable. The tested
contract is vpype **1.15.0**:

```sh
vpype read original.svg linesort write original.vpype.svg
```

The fixed argv invokes no shell. The original is never overwritten; the prepared
copy and command log remain beside it. This initial preset only sorts paths within
layers (vpype may also reverse direction). It performs no line merge, simplify,
page scaling, pen mapping or plotter transmission. vpype imports/exports can change
SVG grouping, styling and curve representation; inspect the prepared file's page,
layers and linework and do a physical proof. A prepared copy cannot overwrite an
existing copy. Commands can also be run manually on downloaded SVGs.

DrawingBot V3 uses **manual file handoff**: download/open the original or inspected
prepared SVG using your installed application's supported file workflow; verify
page size, pens/layers and import behavior there. The GUI does not assume a REST
API, undocumented CLI or watched-folder integration. No DrawingBot automation or
SVG round trip was tested. Blender likewise remains available as a standalone
scene editor through its existing import/export tools.

## Tests

```sh
python -m unittest discover -s workbench/tests -v
python -m unittest discover -s lib/farm_objects/tests -v
node --check workbench/static/app.js
```

The workbench tests cover recipe validation, source isolation, separate runtime
argv, clearing inherited scene flags, path confinement, Host/Origin/token checks,
process failure/restart, cancellation, a repeated real Driftless render and a real
Farm SVG/PNG/OBJ/JSON render. Node-dependent and Farm-dependent tests skip when the
required runtime/packages are absent; inspect the test output before claiming a
render was exercised. The GUI has no effect on existing generator commands.

### Prototype verification (2026-10-22)

- All nine workbench tests and eight existing Farm tests passed; no render tests skipped.
- Browser checks exercised Driftless render/preview, SVG layer switches, vpype copy,
  generator switching and a Farm render/preview. A4 remained within 0.001 mm after
  vpype's unit conversion. Desktop and narrow-screen layouts were inspected.
- Real HTTP jobs rendered a Farm tractor and Driftless landscape. The Infernal
  `recorded_route` / `main` NumPy pipeline passed all 19 gating checks, retained two
  advisory measurements and explicitly skipped three Blender-only checks.
- The existing collection verifier passed. No native bpy render, Windows process
  cancellation, DrawingBot round trip or physical plotting was tested.
