# thi.ng and toxiclibs: Karsten Schmidt's art tools and where their code stands — 22 October 2026

Prepared with Claude for Josiah Alan-Lee. The pass surveyed Karsten Schmidt's
(toxi) generative-art tooling — the `thi.ng/umbrella` TypeScript monorepo, the
`genart-api` platform layer, the Java `toxiclibs` (2006–2014), the Clojure-era
`thi.ng` libraries, the Houdini and Zig repositories — against this
collection's stack (Python 3.12, NumPy, SciPy, Shapely, ContourPy, Pillow,
Blender; a hand-written millimetre SVG writer; an iDraw plotter) and against
the gaps named in the [Codex palette research](CODEX_PALETTE_RESEARCH.md) and
[HEN × CCRU techniques](HEN_CCRU_TECHNIQUES.md). Three groups are implemented
as the [thi.ng ports](../techniques/15-thing-ports/README.md); the rest are
links.

**Where the code lives now.** Schmidt moved his repositories to Codeberg
during 2026. The `umbrella` and `genart-api` READMEs state that the GitHub
copies are read-only mirrors to be deleted "later this year", so the links
below point at Codeberg. `toxiclibs` was not found on Codeberg on 22 October
2026 and keeps its GitHub address.

**Copying rule.** The rule of the [HEN × CCRU list](HEN_CCRU_TECHNIQUES.md)
applies: MIT- or Apache-licensed code can be vendored with its licence file and
a line in [NOTICES](../NOTICES.md); unlicensed code stays a link. Everything in
`umbrella` is Apache-2.0 (the root `LICENSE`, every package's `package.json`
and an SPDX header in every source file; there is no `NOTICE` file).
`genart-api` is MIT. `toxiclibs` is LGPL-2.1, which the
[palette research's status words](CODEX_PALETTE_RESEARCH.md) class as
**share-alike**: a line-by-line port would carry the LGPL, an independent
implementation of the published algorithm does not. The ports below are
independent implementations written from each package's documentation and
the published formulas it cites, not translations of the TypeScript, so no
Apache notice is attached; if a file is ever translated directly, add its
copyright line and the licence to NOTICES. Licence statements were checked on
22 October 2026 by fetching the licence files and package metadata named
here; they are not a legal opinion.

| Technique | Code | Licence | In this repository |
| --- | --- | --- | --- |
| Error-diffusion kernels (Floyd–Steinberg, Jarvis–Judice–Ninke, Stucki, Burkes, Sierra, Atkinson, row/column/2-D diffusion) and Bayer screens | [pixel-dither](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/pixel-dither) | Apache-2.0 | Implemented in [`lib/halftone/dither.py`](../lib/halftone/dither.py) from the published kernel tables; `levels`, `bleed` and serpentine scanning |
| Bitmap run tracing: consume set pixels into horizontal, vertical and diagonal hairline runs, then points | [geom-trace-bitmap](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-trace-bitmap) | Apache-2.0 | Implemented in [`lib/halftone/trace.py`](../lib/halftone/trace.py) |
| Variable-density Poisson-disc by dart throwing with a random-walk retry; stratified grids | [poisson](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/poisson) | Apache-2.0 | Implemented in [`lib/halftone/poisson.py`](../lib/halftone/poisson.py); tone-driven radius for stippling |
| Fuzzy multi-pass polygons and lines; hatch and dot fills; composed fills; pen presets | [geom-fuzz](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-fuzz) | Apache-2.0 | Implemented in [`lib/fuzz/fuzz.py`](../lib/fuzz/fuzz.py); hatching at any angle through Shapely, so no shape rotation is needed |
| Subdivision curves: Chaikin, cubic (Lane–Riesenfeld), Dyn–Levin–Gregory four-point, midpoint displacement | [geom-subdiv-curve](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-subdiv-curve) | Apache-2.0 | Implemented in [`lib/fuzz/curves.py`](../lib/fuzz/curves.py); Chaikin already existed in the palette studies and the Driftless engine |
| Polygon to cubic Bézier in break-point and midpoint modes, with tightness and uniform handles | [geom-splines](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-splines) | Apache-2.0 | Implemented in [`lib/fuzz/curves.py`](../lib/fuzz/curves.py) |
| 2-D signed distance fields: primitives, chamfered/rounded/smooth/stepped booleans, grid, mirrored and polar repeats, sampling to contours | [geom-sdf](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-sdf); formulas from [Quilez](https://iquilezles.org/articles/distfunctions2d/) and [hg_sdf](https://mercury.sexy/hg_sdf/) (MIT) | Apache-2.0; MIT | Implemented in [`lib/sdf2d`](../lib/sdf2d/); contours through ContourPy; sign-tested hatching is this collection's addition |
| Recursive tessellation passes (inset, rim triangles, fans, edge splits) | [geom-tessellate](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-tessellate) | Apache-2.0 | None; a lead for plotter textures |
| Grid traversal orders: Hilbert, Z-order, spiral, diagonal, zigzag | [grid-iterators](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/grid-iterators) | Apache-2.0 | None; a lead for one-stroke hatching |
| L-systems with stochastic rules and a 2-D turtle (jitter, decay, survival probability) | [lsys](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/lsys) | Apache-2.0 | None; the [palette research](CODEX_PALETTE_RESEARCH.md) names the same gap |
| 1-D cellular automata with arbitrary kernels and generation memory (the basis of C-SCAPE) | [cellular](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/cellular) | Apache-2.0 | None; `lib/numerics/aq.py` only returns a Wolfram rule number |
| Colour themes (200+ image-derived palettes) and cosine gradients | [color-palettes](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/color-palettes), [color](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/color) | Apache-2.0 | None; relevant only to the painted barn quilts |
| Low-discrepancy sequences (Halton, Kronecker, R_d) | [lowdisc](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/lowdisc) | Apache-2.0 | Not needed: `scipy.stats.qmc` has Halton and Sobol |
| Marching squares | [geom-isoline](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-isoline) | Apache-2.0 | Already present: ContourPy and the book's own `figure_growth`, `notae` and lattice implementations |
| Delaunay/Voronoi, convex hull, line and polygon clipping, convex offset, resampling, simplification | [geom-voronoi](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-voronoi), [geom-hull](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-hull), [geom-clip-line](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-clip-line), [geom-clip-poly](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-clip-poly), [geom](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom) | Apache-2.0 | Already covered by SciPy and Shapely |
| Plotter path ordering (nearest-neighbour points and shapes) | [geom-axidraw](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/geom-axidraw) | Apache-2.0 (alpha) | Already present three times (`plotter/build.py`, `physarum_plot.py`, Driftless `orderPaths`); vpype remains the better tool, with the carrier caveat in [Recipes](RECIPES.md). The [plotter outside-code review](PLOTTER_OUTSIDE_CODE.md) maps the collection's ordering, joining and clipping code and its gaps |
| AxiDraw serial driver over the EBB protocol | [axidraw](https://codeberg.org/thi.ng/umbrella/src/branch/develop/packages/axidraw) | Apache-2.0 (alpha) | Not applicable: iDraw boards run DrawCore, a Grbl-style G-code firmware, and plot through the manufacturer's Inkscape extension |
| Platform-independent artwork API with fxhash, EditArt, Layer and URL-parameter adapters | [genart-api](https://codeberg.org/thi.ng/genart-api) | MIT | None; it is not a shim for archived works (§3) |
| Diffusion-limited aggregation along guide curves; thermal and talus-angle erosion; 2-D verlet physics; colour-theory strategies (`ColorRange`, `ColorTheme`) | [toxiclibs](https://github.com/postspectacular/toxiclibs) (Java, last commit 2014) | LGPL-2.1 | None. DLA and slumping are named gaps ([palette research](CODEX_PALETTE_RESEARCH.md), [process-art research](PROCESS_ART_RESEARCH.md)); write them from the papers, not from this code |
| Declarative mesh grammars, LuxRender export, Houdini HDAs (SVG import, DLA in VEX, phyllotaxis) | [morphogen](https://codeberg.org/thi.ng/morphogen), [luxor](https://github.com/thi-ng/luxor), [houdini](https://codeberg.org/thi.ng/houdini) | Apache-2.0 | None; reference only. Schmidt has no Blender code |

## 1. Notes by technique

**Dithering and run tracing** ([halftone](../techniques/15-thing-ports/README.md)).
A dithered bitmap is the halftone; the tracer turns it into pen runs by eating
pixels in a fixed direction order, so a solid block becomes parallel dashes
and a dithered mid-tone becomes dashes that follow the dither's own grain. Run
order is raster order, which for horizontal runs is already short pen travel;
nothing is sorted, so a traced carrier keeps its order. The kernel table is
public arithmetic; Atkinson's divisor is larger than its weights' sum on
purpose. This collection had no dither or halftone stage before: raster input
went through skeletonisation (`physarum_plot.py`) or threshold masks (`trace_hosts.py`).

**Poisson stipples.** Dart throwing with the exclusion radius evaluated at the
candidate is slower than Bridson's algorithm for a uniform radius and simpler
for a tone-driven one; it is not weighted Voronoi stippling (Secord 2002),
which the palette research lists as an open lead, but it is the usual first
half of that pipeline. A later point with a small radius may sit inside an
earlier point's larger radius; the tests state this asymmetry.

**Fuzzy passes and fills.** `geom-fuzz` draws each pass from a freshly
jittered copy and can smooth it through the jittered vertices, which is the
sketch look the book's `Wobble` (one stable tremor along one pass) does not
give. Hatching here clips with Shapely at any angle; `geom-fuzz` offers three
directions and rotates the shape instead. Fills compose by concatenation.

**Subdivision and splines.** Dyn–Levin–Gregory keeps the control points on
the curve; Chaikin and the cubic scheme pull inside (Chaikin's limit area is
5/6 of a square's). Midpoint displacement with a decaying amplitude is the
torn-edge scheme. The break-point spline passes through the vertices with
tangents along the neighbour chord, the midpoint spline through the edge
midpoints; at tightness 2/3 the latter is the degree-elevated quadratic.

**Distance fields.** Shapes stay analytic until sampled; booleans with
chamfer, round, smooth or stepped joins and grid, mirrored and polar repeats
follow hg_sdf. A field sampled at 0.25 mm over the plate and contoured at
several iso values gives nested offsets without polygon offsetting; the same
field hatched by sign in depth bands gives a hatched solid with no polygon at
all, which is the 2-D half of the "SDF hatching" lead. Polar repeats fold the
plane into one sector, so a shape that is not symmetric about the sector axis
shows seams; `geom-sdf` has the same property. The ellipse is Quilez's
approximation, exact only on its axes.

## 2. Leads not taken

Tessellation passes, Hilbert and Z-order hatching, L-systems and the kernel
cellular automata are small and Apache-licensed; they were left for a later
pass. `color-palettes` is a data asset (JSON themes) that could be vendored
with its licence for the barn quilts. From `toxiclibs`, the guide-curve DLA
and the thermal/talus erosion (Musgrave's rule) answer two named gaps; the
verlet engine would give cloth and strand plates. All three are textbook
algorithms and should be written from the papers.

## 3. Re-running archived fxhash and Hic et Nunc works

`genart-api` is the wrong direction for the archive. Its adapters translate
from the `$genart` object *to* a platform (fxhash, EditArt, Layer, URL
parameters) for works written against `$genart`; nothing in it polyfills the
fxhash globals that an archived sketch calls (`fxhash`, `fxrand`, `$fx.rand`,
`fxpreview`, `$fx.features`, `$fx.params`). Its fxhash adapter reseeds its own
SFC32 from `$fx.hash` rather than wrapping `$fx.rand`, so even a
`$genart`-based work does not reproduce an fxhash iteration's random stream.
Its `offline` time provider (a fixed timebase in place of
`requestAnimationFrame`) is the one piece worth copying in shape.

What an archived sketch needs is a short `$fx` polyfill injected before it
runs (Playwright `addInitScript` or a wrapper page): the 51-character base-58
hash, SFC32 seeded from the hash the way fxhash's snippet did it, `$fx.rand`
and `fxrand`, `$fx.context = "standalone"`, `$fx.preview()` resolving a promise
the harness waits on before its screenshot, `$fx.features()` written to a JSON
sidecar, `$fx.params()`/`getParam()` returning defaults or a supplied set, and
a fixed-timebase `requestAnimationFrame`. The HEN harness is described in the
[HEN × CCRU notes](HEN_CCRU_TECHNIQUES.md). The fxhash boilerplate repositories
hold the original snippet to copy semantics from; their licence was not checked
in this pass. The public `main` of this repository holds no `projects/` folder
although `.gitattributes` protects one and two study READMEs refer to it;
whether the archive is local or unpublished was not determined here.

## 4. Not settled in this pass

- Whether `toxiclibs`, `luxor`, `shadergraph` and `ndarray` have Codeberg copies (the listing's second page was not readable).
- The exact deletion date of the GitHub mirrors.
- The licence of the fxhash boilerplate repositories (for the polyfill's seeding semantics).
- Which iDraw generation the author owns; the DrawCore statement comes from current UUNA TEK models and third-party plotter software, and an early EBB-based unit would change the driver note.
- `geom-sdf`'s own choice of saddle handling in its marching squares; this collection uses ContourPy's.
