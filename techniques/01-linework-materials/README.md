# Linework and materials

Start here for the book’s drawn hand: one geometric scaffold can become ink, grain or pen strokes.

Keep the seed fixed while comparing materials. `Wobble` changes the contour, while `Hand(mode="grain")` scatters material around sampled paths. The grain implementation uses compact SVG marks; it is distinct from the later raster figure-growth renderer.

Change wobble amplitude and wavelength first; then hatch spacing, grain density and perpendicular spread. Dense grains can make a large SVG even when paths are grouped.

| Technique | Use | Entry points |
| --- | --- | --- |
| **Seeded pen tremor** (`book`) | Give otherwise exact curves a stable drawn hand | [core.py](../../sources/codex-intervallorum/common/geometry/core.py) |
| **Curves, clipping and lattice hatching** (`book`) | Build curls, spirals, clipped hatch and cellular-looking fills | [core.py](../../sources/codex-intervallorum/common/geometry/core.py)<br>[marks.py](../../sources/codex-intervallorum/common/geometry/marks.py) |
| **Cornmeal / granular stroke hand** (`book`) | Render the same scaffold as dispersed grains | [marks.py](../../sources/codex-intervallorum/common/geometry/marks.py) |
| **Seeded sigils and ornament vocabulary** (`book`) | Compose stable seal cores with curls, fringes and bands | [marks.py](../../sources/codex-intervallorum/common/geometry/marks.py)<br>[art.py](../../sources/codex-intervallorum/books/03_escalationum/generator/art.py) |

Useful symbols are indexed in [catalog/techniques.json](../../catalog/techniques.json). Every retained Python file, including other native plate constructions, is in the [source index](../../docs/SOURCE_INDEX.md).

[Start here](../../docs/GETTING_STARTED.md) · [Recipes](../../docs/RECIPES.md) · [Full catalog](../../CATALOG.md)
