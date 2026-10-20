# Physarum fields and figure growth

The book contains two separate agent systems and several renderers.

Book V’s `physarum.run(spec)` returns actual recorded agent paths and trail fields. The illustrated `figure_growth.simulate(food, seed)` uses image food to drive an appearance pass. Its final flowing strokes are integrated render curves, not recorded agent trajectories. `contours` extracts level lines with marching squares; `render_material` combines those contours with directional hatching and grain.

For Book V, edit the run specification: sensor offset/angle, rotation, deposit, evaporation, spawn, arena and food nodes. For illustrated figures, use `configure`, explicit protection anchors and physical display size. The amount parameter controls a mask front; raising it is not a longer simulation. Keep source geometry and carrier marks separate from appearance.

| Technique | Use | Entry points |
| --- | --- | --- |
| **Notoria three-sensor agent fields** (`book`) | Generate reproducible deposit/sense/decay/follow/food-node plates | [physarum.py](../../sources/codex-intervallorum/books/05_notoria/fields/physarum.py)<br>[notae.py](../../sources/codex-intervallorum/books/05_notoria/plates/notae.py) |
| **Marching-squares field contours** (`book`) | Turn a scalar field into joined level curves | [figure_growth.py](../../sources/codex-intervallorum/common/illum/figure_growth.py) |
| **Image-fed progressive figure replacement** (`book`) | Move selected portions of a source figure into flow and grain | [figure_growth.py](../../sources/codex-intervallorum/common/illum/figure_growth.py) |
| **Selected contour fringe** (`book`) | Dissolve only a narrow physical edge into sketch and grain | [figure_growth.py](../../sources/codex-intervallorum/common/illum/figure_growth.py)<br>[EDGE-GRAIN-2026-10-19.md](../../sources/codex-intervallorum/docs/EDGE-GRAIN-2026-10-19.md) |
| **Selected granular hatching and flowing footer** (`book`) | Put grain beside explicitly selected structural/decorative paths | [figure_growth.py](../../sources/codex-intervallorum/common/illum/figure_growth.py)<br>[platekit.py](../../sources/codex-intervallorum/common/illum/platekit.py) |

Useful symbols are indexed in [catalog/techniques.json](../../catalog/techniques.json). Every retained Python file, including other native plate constructions, is in the [source index](../../docs/SOURCE_INDEX.md).

[Start here](../../docs/GETTING_STARTED.md) · [Recipes](../../docs/RECIPES.md) · [Full catalog](../../CATALOG.md)
