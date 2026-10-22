# Plotter geometry and export

Use this family for real pen paths, layered SVG and single-stroke lettering.

`PlotDoc` keeps art and text in separate layers; `PlotHand` turns dots into coils and filled regions into hatching. `SVGFont` uses EMS Nixish centreline paths. `OutlineFont` is the reading-edition alternative and uses filled glyph outlines. `svgimport` handles the restricted SVG vocabulary produced by these plates.

Check physical pen width and page units, then inspect the exported ink passes. Filled reading-edition glyphs and raster compositing are not plot masters. Run the plate validators to check reserved space, layers, inks and carrier round trips; no physical plotter result is claimed by this import.

| Technique | Use | Entry points |
| --- | --- | --- |
| **Two-layer, two-ink stroke export** (`book`) | Write separate art/text layers and ink passes | [plotkit.py](../../sources/codex-intervallorum/common/plot/plotkit.py)<br>[plate.py](../../sources/codex-intervallorum/common/plot/plate.py) |
| **Centreline and outline lettering** (`book`) | Choose actual pen lettering or reading-edition outlines | [plotkit.py](../../sources/codex-intervallorum/common/plot/plotkit.py)<br>[lettering.py](../../sources/codex-intervallorum/books/04_graduum/proofs/ix-gpt/lettering.py) |
| **Restricted SVG stroke import** (`book`) | Reuse the book’s generated seal geometry in new plates | [svgimport.py](../../sources/codex-intervallorum/common/plot/svgimport.py) |

Useful symbols are indexed in [catalog/techniques.json](../../catalog/techniques.json). Every retained Python file, including other native plate constructions, is in the [source index](../../docs/SOURCE_INDEX.md).

Before importing plotter code from other artists, check [Dan Catt and Makio: plotter code and where it stands](../../docs/PLOTTER_OUTSIDE_CODE.md): it maps their tools to the collection's own export, ordering, clipping and hatching code, with each license.

[Start here](../../docs/GETTING_STARTED.md) · [Recipes](../../docs/RECIPES.md) · [Full catalog](../../CATALOG.md)
