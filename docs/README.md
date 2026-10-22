# Project guide

[Repository home](../README.md) · [Getting started](GETTING_STARTED.md) · [Technique catalog](../CATALOG.md) · [Recipes](RECIPES.md) · [Local workbench](../workbench/README.md)

Browse by what you want to make. Each project or family guide contains its setup, controls, examples and limitations. The catalog goes deeper into individual effects and source files.

## Scene studies

| Project | What it explores |
| --- | --- |
| [Driftless Plates](../studies/driftless-plates/README.md) | Hidden-line landscape plates, with a browser interface and Node batch renderer |
| [Farm Remnants](../studies/farm-remnants/README.md) | Decaying barns, old tractors and abandoned farm implements |
| [Southwestern Wisconsin flora](../studies/wisconsin-flora/README.md) | Six seeded species grammars: little bluestem, side-oats grama, leadplant, prairie smoke, wild bergamot and bur oak; shared 3D geometry for camera views, organ layers and landscapes |
| [Infernal Engine](../studies/infernal-engine/README.md) | The original Blender scene study |
| [Infernal landscape](../studies/infernal-landscape/README.md) | Task graphs expressed as buildings, combined with Driftless marks, 3D trees and print-sized engraving |
| [The Three Gates](../studies/three-gates/README.md) | Architecture, water, surface-aware crosshatching and depth-ordered plant strokes through one perspective camera |
| [Terrain symbols](../studies/terrain-symbols/README.md) | 2D field marks draped onto a displaced hillside, with upright symbols and shared occlusion |
| [Workshop interiors](../studies/workshop-interiors/README.md) | Four editable Blender interiors and layered, stroke-only SVGs based on the workshop briefs |
| [Photophobic](../studies/photophobic/README.md) | Light-aware culture studies |
| [Scanned Statue v2](../studies/scanned-statue-v2/README.md) | Scan engraving and Trail First workflows |
| [Motor counterpoint](../studies/plotter-score/README.md) | Drawing form and intended motor pitches generated from one timed score |

### Landscape comparisons and integrations

| Study | Focus |
| --- | --- |
| [Face patterns](../studies/infernal-landscape/FACE-PATTERNS.md) | Map 2D strata, quilts and hatching onto flat 3D walls |
| [Plate studies](../studies/infernal-landscape/PLATES.md) | Close-camera compositions combining face patterns, farm objects, Wisconsin flora and thi.ng ports |
| [Erosion comparison](../studies/infernal-landscape/EROSION.md) | Three matched exposures with runoff, cut banks, protected building sites and shared ray visibility |
| [Spillway works](../studies/infernal-landscape/SPILLWAY.md) | A five-hall scene with duration bays, a release-wait passage, front-routed conduits and two verified cameras |

## Technique families

### Line, image and output

| Guide | Use it for |
| --- | --- |
| [Linework and materials](../techniques/01-linework-materials/README.md) | Drawn, engraved and cornmeal stroke hands |
| [Fields and figure growth](../techniques/02-fields-growth/README.md) | Trace networks, flowing contours and sketch-like figure edges |
| [Compositing](../techniques/05-compositing/README.md) | Bring raster figures into drawn pages |
| [Plotter and SVG](../techniques/06-plotter-export/README.md) | Physical pen paths, ink layers and single-stroke lettering |
| [Page finishing](../techniques/07-page-finishing/README.md) | Vellum, specks and sparse pen flourishes |
| [thi.ng ports](../techniques/15-thing-ports/README.md) | Raster halftones, stipples, sketchy passes, curves and distance-field figures |

### Scenes and objects

| Guide | Use it for |
| --- | --- |
| [Figures and apparatus](../techniques/03-figures-apparatus/README.md) | Figures, mechanisms, tiers and systems diagrams |
| [Scene studies](../techniques/08-scene-studies/README.md) | Find the existing Blender, culture and scan workflows |
| [Landscape plates](../techniques/11-landscape-plates/README.md) | Hidden-line landscapes sized to the book’s pages |
| [Farm objects](../techniques/16-farm-objects/README.md) | Generative barns, tractors and implements |
| [Wisconsin flora](../techniques/17-wisconsin-flora/README.md) | Reusable plant grammars for plotter and landscape work |

### Pattern, systems and script

| Guide | Use it for |
| --- | --- |
| [Ciphers and seals](../techniques/04-ciphers-seals/README.md) | Meaningful script, encoded ornament and sentence-derived seals |
| [Number systems](../techniques/09-number-systems/README.md) | AQ values, prime glyphs and numogram routes |
| [Development generators](../techniques/10-development-generators/README.md) | Original Matricis plates, two-culture Physarum, the XI plotter converter and an interactive node lattice |
| [Process art](../techniques/12-process-art/README.md) | Eroded catchments, folded strata, chemistry coupled to vein growth and CSV-driven recurrence marks |
| [Barn quilts](../techniques/13-barn-quilts/README.md) | Eight geometric block families on painted wood or metal, with adjustable wear and shared-edge outlines |
| [Codex palette](../techniques/14-codex-palette/README.md) | Manuscript revision history, slime-mould tube networks, marbled endpapers and guilloché seals |

For combined techniques, see the [textile/process comparison](../techniques/12-process-art/TEXTILE.md) for shared-port patterns, transport, chemistry and dissolution, and [three combination trials](../techniques/14-codex-palette/COMBINATIONS.md) for quilts, chemical growth, marbling and history-driven dissolution.

## Research and reading

| Reading | Scope |
| --- | --- |
| [Generative art and the pen plotter](GENERATIVE_ART_AND_PLOTTERS.md) | A sourced history and practical introduction to what plotting can do |
| [Process-art research](PROCESS_ART_RESEARCH.md) | Primary sources behind erosion, strata, chemistry and recurrence studies |
| [Barn quilt conventions and materials](../research/barn-quilts/README.md) | Pattern, support and paint research |
| [Codex palette research](CODEX_PALETTE_RESEARCH.md) | Manuscript concepts, public datasets and terms checked for the palette studies |
| [thi.ng and toxiclibs](THING_TECHNIQUES.md) | Karsten Schmidt’s tools, license status, implemented ports and archived fxhash requirements |
| [Outside plotter code](PLOTTER_OUTSIDE_CODE.md) | Plotter-oriented code review and integration leads |
| [Outside techniques](HEN_CCRU_TECHNIQUES.md) | Additional influences and their license status |
| [Occult print, cipher systems, code art and weird Americana](../research/occult-americana/README.md) | Thirteen source groups, ten generator concepts and four original sketches; research and ideation |

## Repository map

| Path | Purpose |
| --- | --- |
| [`workbench/`](../workbench/README.md) | Local browser GUI and generator adapters |
| [`techniques/`](../techniques/) | Visual-operation guides with source links and tuning advice |
| [`studies/`](../studies/) | Standalone projects, each with its own dependencies and build instructions |
| [`examples/`](../examples/) | Runnable examples and committed visual samplers |
| [`lib/`](../lib/) | Reusable implementations written for this collection |
| [`sources/`](../sources/) | Imported book snapshot and selected development-art generators |
| [`catalog/`](../catalog/) | Machine-readable techniques, module indexes and per-file provenance |
| [`research/`](../research/) | Source surveys and generator concepts |
| [`docs/`](./) | Setup, recipes, research and collection documentation |
| [`tools/`](../tools/) | Snapshot import and collection verification |

## Provenance and validation

The public book snapshot is pinned to [`b789e03`](https://github.com/JosiahAlanLee/Codex-Intervallorum/tree/b789e03f30034bc8403f8a40aaf83842885aaad5). It retains all 117 tracked Python modules, their selected technical inputs, fonts and source SVGs. Large raster art and edition PDFs stay in the book repository; the collection is not a complete illustrated-book distribution.

The selected development-art imports are documented separately; book manuscripts, personal records and repository history are excluded from those imports. Study manifests and source attributions remain with their projects.

- [Provenance and updates](PROVENANCE.md)
- [Development-art scope](DEVELOPMENT_ART.md) and [manifest](../catalog/development-art-manifest.json)
- [Full source index](SOURCE_INDEX.md)
- [Recorded validation results](VALIDATION.md)
- [License and attribution notices](../NOTICES.md)

Add project links to the appropriate section here; keep the repository home focused on starting points.
