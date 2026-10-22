# Dan Catt and Makio: plotter code and where it stands

Plotter code by two artists from [awesome-plotters](https://github.com/beardicus/awesome-plotters), reviewed on 22 October 2026 for anything this collection could import. Very little qualifies. Their two MIT projects do less than code the collection already has, and their most useful plotting code is unlicensed, carries conflicting terms, or is AGPL. Nothing below has been imported; the entries are links.

**Copying rule.** As in [HEN × CCRU](HEN_CCRU_TECHNIQUES.md): MIT- or Apache-licensed code can be vendored with its license file and a line in [NOTICES](../NOTICES.md), and code with no license stays a link. This review adds two cases. AGPL code is outside the rule. Where a repository's own statements contradict its license file, treat it as unlicensed and ask the author.

## Code and license

| Source | What it holds | License | In this repository |
| --- | --- | --- | --- |
| [revdancatt/drawing-machines-101](https://github.com/revdancatt/drawing-machines-101) at `e4d462f`: `3.0.0 - Cleaning things up/3.5.0 - Moving code into Functions/tools.js` | `createSVG`, `createGCODE`, `downloadSVG`, `drawCanvas` from his plotting course | MIT, © 2026 Rev Dan Catt | Could be vendored; not needed (see notes) |
| [revdancatt/svgjoin](https://github.com/revdancatt/svgjoin) at `b2c69f7`: `index.js` | `joinPaths` (lines 20–111) and `optimisePaths` (113–178) | No license file; `package.json` has npm's default `ISC` | Link only |
| Dan Catt's artwork repositories: yyyseed, concord, HLR-example, mfing-dots-on-a-mfing-grid, 10print, flying-pigs, kiss-me-kiss-me-kiss-me, an-increasing-series-of-dots, on-chain-platforms, a-slight-case-of-overbombing | Artworks. yyyseed's `page.js` is his informal helper library (`cullOutside`, `bisectLines`, `wrapSVG`) | MIT files, contradicted by every `index.js` header and nine of the READMEs | Link only; ask him |
| [REVDANCATT Plotter Tools](https://revdancatt.com/penplotter/) | Browser tools with SVG output | None visible | Link only |
| [MAKIO135/svg5.js](https://github.com/MAKIO135/svg5.js) at `65a4e29`: `svg5.module.js` | p5-style SVG string builder with seeded random and simplex noise | MIT, © 2020 Lionel Radisson; bundles Alea and simplex-noise.js, both MIT | Could be vendored; not needed (see notes) |
| Makio's [Penplotter collection](https://observablehq.com/collection/@makio135/plotter) on Observable, with the helper notebooks [`utilities`](https://observablehq.com/@makio135/utilities) and `plotter-template` | Polygon hatching, plotter templates, `ln` 3D line drawings; most entries are finished sketches | None visible; not yet checked in a browser | Link only until a license is confirmed |
| [nornagon/saxi](https://github.com/nornagon/saxi) and [nornagon/optimize-paths](https://github.com/nornagon/optimize-paths) | AxiDraw driver and pen-travel ordering. Makio contributed `cb8f0bb`, "improve pen-up travel time" (11 May 2022) | AGPL-3.0-only | Outside the rule |

## Techniques the collection already has

| Technique | Their version | This collection |
| --- | --- | --- |
| Millimetre SVG, one Inkscape layer per pen | `createSVG` writes one layer; svg5 writes unitless pixels and plain groups | Driftless `toSVG` ([engine.js](../studies/driftless-plates/engine.js)), Photophobic `write_svg` ([physarum_plot.py](../studies/photophobic/common/physarum_plot.py)), the book's `PlotDoc` ([plotkit.py](../sources/codex-intervallorum/common/plot/plotkit.py)) |
| Nearest-neighbour pen-travel ordering with path reversal, searching from the end just drawn | svgjoin `optimisePaths`; Makio's saxi change | Driftless `orderPaths` (grid buckets); Photophobic `order_lines` (KD-tree) |
| Joining paths whose ends touch | svgjoin `joinPaths`: repeated global passes over all four end pairings | Photophobic `order_lines` joins consecutive picks within `join_tol`. Driftless `orderPaths` does not join |
| Clipping lines to a polygon | yyyseed `cullOutside`, which its own header calls unreliable | The book's `clip_lines` and `hatch_lines` on shapely geometry, holes included ([core.py](../sources/codex-intervallorum/common/geometry/core.py)); `clipped` ([drawing.py](../lib/process_art/drawing.py)) |
| Hatching polygons | The `Polygon` class in Makio's `utilities` notebook (source not seen) | The book's `hatch_lines` and `lattice`; `hatch_on_surface` and `hatch_on_face` ([claude_hatching.py](../studies/three-gates/vendor/claude_hatching.py)); Photophobic `hatch_fill` |
| Hidden lines | HLR-example: white-filled shapes laid over the lines, removed at plot time by the AxiDraw software's hidden-line removal | Driftless `Mask` draws near to far against an occlusion raster; the Blender studies share ray visibility ([Three Gates](../studies/three-gates/README.md)) |
| 3D models as hidden-line drawings | Makio's `ln` notebooks, after [fogleman/ln](https://github.com/fogleman/ln) (MIT) | The Blender-backed scene studies |

## Gaps neither source fills

- **Joining in the Driftless export.** Touching strokes leave `toSVG` as separate subpaths, so the plotter lifts between them unless its own software merges them. Photophobic's `order_lines` already shows the method; [vpype](https://github.com/abey79/vpype)'s `linemerge` (MIT) does it to any exported SVG.
- **Duplicate-segment removal across a plate.** Only the barn-quilt `unique_edges` ([generator.py](../lib/barn_quilts/generator.py)) removes shared edges, and only for its own patch geometry. vpype 1.15 has no equivalent command.
- **G-code.** Nothing in the collection writes it. See the `createGCODE` note before modelling a writer on it.
- **Exact hidden-line removal for flat drawings.** The Driftless mask is a raster of about 0.13 mm cells. [occult](https://github.com/LoicGoulefert/occult) (vpype plugin, MIT, 0.4.0) removes lines covered by later closed polygons, layer by layer, which is the vector form of Dan Catt's white-fill method.

## Notes

**drawing-machines-101.** Course code. `createSVG` writes one layer with placeholder Inkscape metadata (a fixed `inkscape:version` and `sodipodi:docname="test.svg"`), and `addMargins` is an empty stub. `createGCODE` lowers the pen to Z8 and lifts it to Z15, pauses with `M0` for a pen change, and flips Y; a machine whose pen lift is a servo command needs different moves. Driftless `toSVG` already does more than `createSVG`.

**svgjoin.** The most useful plotting code Dan Catt has published, and the one worth asking him to license. It parses only the single-path SVGs his own tools write, takes its join threshold in SVG user units, and is quadratic per pass.

**Dan Catt's artwork repositories.** Each `index.js` header says the code is his copyright and not for NFT projects. The READMEs (all but HLR-example) say the code is there for learning, and that outputs may be kept, printed and displayed for personal use but not sold or minted. Their MIT files say otherwise. This collection archives work made for NFT platforms, the use his terms exclude, so read them and don't copy them.

**svg5.js.** Useful for porting p5-style drawing code to SVG, not as a plot exporter. It writes unitless pixel sizes (millimetres need a patch to `getHTML`), plain `<g>` groups without Inkscape layer attributes and a white default fill (call `noFill()`). Coordinates keep full precision unless `precision()` is set, and its `_round` type check never runs (`!typeof n === 'number'`). Use `svg5.module.js`; `svg5.js` declares top-level `width`, `height`, `map`, `random` and `noise`. Pin the commit: the repository is at 0.2.3 and npm's latest is 0.2.2.

**Makio's notebooks.** Observable's default terms let others view, fork and import a published notebook on Observable only ([Bostock, 2018](https://talk.observablehq.com/t/copyright-and-software-licenses/364)); reuse elsewhere needs a license on the notebook. The review's tools could not display notebook licenses, so open `utilities` and `plotter-template` in a browser before taking anything. svg5's README points to the `Polygon` class in `utilities` for hatched shapes; svg5's MIT license does not cover the notebook.

**saxi and optimize-paths.** Makio's change makes the nearest-neighbour search continue from the far end of the path just chosen. Driftless `orderPaths` and Photophobic `order_lines` already do this.
