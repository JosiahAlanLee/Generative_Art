# Generative Art

Generative drawings, Blender scenes and reusable techniques for pen plotting and Josiah Alan-Lee’s book artwork. Work ranges from landscape and botanical studies to crosshatching, erosion, textiles and encoded ornament.

![Six techniques from the book, generated from the imported source](examples/previews/technique-sampler.png)

## Start here

| To… | Open |
| --- | --- |
| Render through a local GUI | [Plot workbench](workbench/README.md) — Driftless Plates, Farm Remnants and an Infernal pipeline adapter |
| Run a first example | [Getting started](docs/GETTING_STARTED.md) — setup and runnable commands |
| Browse projects and visual families | [Project guide](docs/README.md) — scenes, plants, techniques and research |
| Find an individual technique or source | [Technique catalog](CATALOG.md) — effects, implementation links and status |
| Combine generators and prepare output | [Recipes](docs/RECIPES.md) — workflows and output choices |

To launch the workbench from the repository root after following its [setup guide](workbench/README.md):

```sh
python -m workbench.server
```

Open <http://127.0.0.1:8765>. Each generator has its own dependencies; the workbench guide explains which runtime each one needs.

## Explore

- **Landscapes, buildings and plants:** [scene studies](docs/README.md#scene-studies) include Blender engraving, Driftless landscapes, farm remnants and southwestern Wisconsin flora.
- **Line, pattern and simulation:** [technique families](docs/README.md#technique-families) cover drawn linework, growth, process art, textiles, lettering and plotter export.
- **Drawing as sound:** [Motor counterpoint](studies/plotter-score/README.md) generates drawing paths and intended pitches from a timed motor score.
- **Background and influences:** [research and reading](docs/README.md#research-and-reading) covers plotter history, outside code, materials and source research.

## Source and reuse

The collection combines original generators with a pinned source snapshot from *Codex Intervallorum* and selected development-art imports. See [provenance](docs/PROVENANCE.md) for scope and updates, [notices](NOTICES.md) for inherited licenses and attributions, and the [repository map](docs/README.md#repository-map) for file locations.
