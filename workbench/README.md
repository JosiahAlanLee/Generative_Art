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
Ctrl-C, `kill` (SIGTERM) and closing the terminal window (SIGHUP) all stop the
active job and close the queue. If the server dies without that chance (a force
quit, a crash), the next start marks the job interrupted and, on Linux and macOS,
stops its render if that process is still running; it only stops a process whose
command line names the job's folder. Render the saved recipe to retry. An open
browser tab picks up a restarted server's new session on its next refresh.

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
2. Select the SVG or PNG from **Preview file**. SVGs show the sheet size in mm,
   viewBox, drawing-element and stroke counts and labeled layers. The sheet is
   drawn with its edge outlined. **Fit** shows the whole sheet; 100% is its
   physical size on screen (96 px per inch) and 200–800% enlarge from there.
   Layer switches affect the preview only; exported originals always contain
   every layer. Browser viewing is not a physical pen simulation. A file still
   being written is shown once it is complete.
3. Download an artifact or use its displayed disk path. All artifacts and stage
   logs have download links. Original SVG, PNG and geometry are kept together.
4. **Save recipe** downloads JSON; **Load recipe** restores controls without
   rendering. A recipe with a setting or value the form cannot show is refused
   whole rather than loaded without it. Selecting a job in the history shows its
   proof and log; **Use these settings** loads its recipe into the controls.
   Every job also retains `recipe.json` on disk. Rendering again creates a new
   output directory. History survives a restart.
5. The job record includes exact argv, runtime paths, source SHA-256 hashes,
   status and exit code. `job.log` captures stdout/stderr; its UI view shows the
   latest 64 KiB, with a full download available. Files from failed/cancelled jobs
   remain available for diagnosis. No installation, package updates or application
   launch commands are accepted from the browser.

Driftless exposes its existing page formats, landscape/bleed, palette/strength,
nib, text zone, density, imperfection, motif weights, subject, season, light and
frame, and the engine version. **Nib (mm)** is the page's nib width, passed as
`--penWidth`; it changes hatch spacing and occlusion, not only the stroke, so a
plate for a 0.5 mm pen has different lines. **Engine 1.1** passes `--compat 1.1`,
which redraws plates kept under engine 1.1 as they were (sandstone only, so Rock
is disabled). Native travel optimization is on unless **Keep original drawing
order** is checked. `codexPlot` keeps the CLI's enforced sheet/inset rules, so
landscape, bleed and riso are disabled for it. Settings with no effect in the
current combination are greyed out with the reason. SVG is the proof and export;
no raster preview package is needed.

Farm exposes object/comparison selection, base seed, decay and optional PNG export.
Its CLI offsets the seed by family index even with `--only`: barn +0, tractor +1,
disk harrow +2, rake +3, wagon +4. The recipe and generated JSON record both make
that distinction inspectable. Page sizes remain the generator's 190 × 140 mm
specimens and 280 × 210 mm yard. OBJ/scene JSON exports remain available. Decay
is an artistic control, not a model of elapsed years; the comparison always draws
decay 0, 0.38 and 0.9, so the control is disabled for it.

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
face-pattern and plates flags. Plates includes face patterns, so ticking Plates
unticks them; tower/barn cameras require Plates and are disabled without it; Skip
clay preview is disabled for dry runs, which make no clay preview. History entries
name the case, camera, Plates and dry run. Infernal currently has fixed scene seeds, so the GUI does **not**
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
an idle queue; the button says why when it is unavailable, including when vpype is
not installed. Install vpype in its own environment if its dependency constraints
conflict with engraving, then point `WORKBENCH_VPYPE` at its executable. The tested
contract is vpype **1.15.0**:

```sh
vpype read --no-crop original.svg linesort write --format svg --dont-set-date original.vpype.svg.part
```

The fixed argv invokes no shell. The original is never overwritten; the prepared
copy and command log remain beside it, and the copy is selected for inspection
when it is ready. The preset only sorts paths within layers (vpype may also
reverse a path). It performs no line merge, simplify, page scaling, pen mapping or
plotter transmission, and it keeps every line:

- `--no-crop`: vpype otherwise crops to the sheet. A Driftless A4 plate can draw a
  few tenths of a millimetre past its edges (seed e2: about 20 cm of line, 23
  strokes of it entirely); the copy keeps it, as the original has it. Crop in vpype
  yourself if your plotter needs it.
- Layer order: vpype writes layers in number order, which would put Driftless's
  `1-key` first and `4-tint` last. The workbench puts the layers back in the
  original's document order afterwards (Driftless: tint, flora, accent, key).
- vpype reads every layer whose label starts with the same number as one layer.
  Same-ink layers merge as one pen, e.g. the Infernal plates' three `02 …` layers
  (noted in the copy's log). A merge across inks, or with a layer that has no
  stroke, is refused: in particular a plate rendered with **Include paper
  rectangle**, whose `0-paper` layer vpype would read into `1-key` and plot as a
  frame.
- vpype runs without blocking the workbench: status, logs and previews keep
  updating, and new renders are refused until the copy is done.

vpype imports/exports can still change SVG grouping, styling (stroke widths that
vary within a layer become one width) and curve representation; inspect the
prepared file's page, layers and linework and do a physical proof. A prepared copy
cannot overwrite an existing copy. Commands can also be run manually on downloaded
SVGs.

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

The workbench tests cover recipe validation (including the engine and nib
arguments), source isolation, separate runtime argv, clearing inherited scene
flags, path confinement, Host/Origin/token checks, the server instance id, the
short history list and fixed static content types, process failure/restart,
cancellation, a repeated real Driftless render and a real Farm SVG/PNG/OBJ/JSON
render. For vpype they cover the layer-number rule, which merges are allowed, the
layer-order restore, the paper-layer refusal and that status reads stay
immediate during a copy (with a stand-in vpype); with `WORKBENCH_VPYPE` or
`vpype` on PATH, a real copy keeps every stroke and the layer order. On Linux and
macOS they check that SIGTERM and SIGHUP stop the active render and that a
restart stops only its own leftover render. Node-, Farm-, vpype- and
POSIX-dependent tests skip when those are absent; inspect the test output before
claiming a render was exercised. The GUI has no effect on existing generator
commands; the Driftless CLI gained `--penWidth`, and without it draws as before.

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

### Review fixes (2026-10-22)

- 19 workbench tests passed with vpype 1.15.0 configured, none skipped; Driftless
  `test.js` 42 passed (three new nib checks; the preview plates still regenerate
  byte for byte).
- Browser checks (Chromium): a recipe with an unknown setting or value is refused;
  an engine 1.1 recipe renders seed c2 as the kept sandstone tower; a 0.5 mm nib
  renders e2 with 21,404 strokes instead of 22,978. Focus, a log selection and a
  scrolled-up log survive refreshes; a preview caught half written recovers when the
  file completes; a tab left open across a server restart renders without reloading.
- vpype copies of e2 (A4) and the Infernal tower plate kept every stroke and line
  length (to 0.01 mm per layer) and the original layer order; layer switches work on
  them; status reads took about 2 ms during the 23 s copy of the 23.6 MB tower plate.
- SIGTERM and SIGHUP to the server stopped a running Infernal dry run; after SIGKILL,
  the next start stopped the leftover render and marked the job interrupted.
- Not tested: Windows, a native bpy render, DrawingBot, physical plotting.
