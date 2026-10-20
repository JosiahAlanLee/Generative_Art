# Raster compositing and native plate adapters

Use these when a figure needs to share the page’s paper and drawn apparatus.

`raster.key` measures the source ground, divides it toward white, eases borders and remaps red ink. Placement uses Multiply on light ground or Screen on a dark board. Silhouettes, extents and source anchors drive geometry; figure-growth changes appearance separately. `platekit` maps native millimetre/y-down geometry onto ReportLab point/y-up canvases.

Keep keying, geometry and appearance as separate stages. Use the keyed source for extent and connection calculations. Raster source art is intentionally omitted from this lightweight collection; obtain the named asset from the pinned book for an illustrated edition rebuild. Standalone synthetic examples do not need it.

| Technique | Use | Entry points |
| --- | --- | --- |
| **Paper keying and red-ink remap** (`book`) | Integrate a raster figure with the page ground | [raster.py](../../sources/codex-intervallorum/common/illum/raster.py) |
| **Silhouettes, anchors and native plate slots** (`book`) | Preserve geometry while replacing illustrated appearance | [raster.py](../../sources/codex-intervallorum/common/illum/raster.py)<br>[platekit.py](../../sources/codex-intervallorum/common/illum/platekit.py)<br>[plates.py](../../sources/codex-intervallorum/books/04_graduum/illustrated/plates.py) |

Useful symbols are indexed in [catalog/techniques.json](../../catalog/techniques.json). Every retained Python file, including other native plate constructions, is in the [source index](../../docs/SOURCE_INDEX.md).

[Start here](../../docs/GETTING_STARTED.md) · [Recipes](../../docs/RECIPES.md) · [Full catalog](../../CATALOG.md)
