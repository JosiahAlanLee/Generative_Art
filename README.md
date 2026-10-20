# Generative Art

Reusable techniques and scene studies from Josiah Alan-Lee’s book and generative artwork.

**Choose an effect in the [technique catalog](CATALOG.md), then follow its family guide.** For a first runnable result, see [Getting started](docs/GETTING_STARTED.md). [Recipes](docs/RECIPES.md) cover combining techniques and choosing an output format.

![Six techniques from the book, generated from the imported source](examples/previews/technique-sampler.png)

| I want to… | Start with |
| --- | --- |
| Change exact paths into a drawn, engraved or cornmeal hand | [Linework and materials](techniques/01-linework-materials/README.md) |
| Grow trace networks, flowing contours or a sketch-like figure edge | [Fields and figure growth](techniques/02-fields-growth/README.md) |
| Draw figures, mechanisms, tiers and systems diagrams | [Figures and apparatus](techniques/03-figures-apparatus/README.md) |
| Make meaningful script, encoded ornament or sentence-derived seals | [Ciphers and seals](techniques/04-ciphers-seals/README.md) |
| Bring a raster figure into a drawn page | [Compositing](techniques/05-compositing/README.md) |
| Export physical pen paths or single-stroke lettering | [Plotter and SVG](techniques/06-plotter-export/README.md) |
| Finish pages with vellum, specks and sparse pen flourishes | [Page finishing](techniques/07-page-finishing/README.md) |
| Build a Blender scene, a light-aware culture or a scan engraving | [Existing scene studies](techniques/08-scene-studies/README.md) |
| Turn phrases into AQ values, prime glyphs or numogram routes | [Number systems](techniques/09-number-systems/README.md) |

## Where things live

| Path | Purpose |
| --- | --- |
| `techniques/` | Guides grouped by visual operation, with source links and tuning advice |
| `examples/` | Small working examples and committed visual samplers |
| `lib/` | Small implementations written for this collection, not imported from the book: AQ, numogram and Tic Xenotation |
| `sources/codex-intervallorum/` | Unchanged source snapshot; original internal paths preserved |
| `studies/` | Existing Infernal Engine, Photophobic and Scanned Statue studies, at their original paths |
| `catalog/` | Machine-readable technique catalog, Python module index and per-file provenance |
| `docs/` | Setup, recipes, full code index, snapshot scope, validation results and [outside techniques](docs/HEN_CCRU_TECHNIQUES.md) with their license status |
| `tools/` | Snapshot import and collection verification |

The source snapshot is pinned to public book main commit [`b789e03`](https://github.com/JosiahAlanLee/Codex-Intervallorum/tree/b789e03f30034bc8403f8a40aaf83842885aaad5). It retains all 117 tracked Python modules, their selected technical inputs, fonts and source SVGs. Large raster art and edition PDFs stay in the book repository; this collection is not a complete illustrated-book distribution. See [provenance and updates](docs/PROVENANCE.md).

The existing studies use their own dependencies and build instructions. Their manifests and source attributions are retained. See [notices](NOTICES.md) before redistributing inherited work.
