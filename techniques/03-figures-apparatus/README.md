# Figures, mechanisms and data plates

These are authored procedural constructions, rather than a general 3D scene generator.

The Keeper uses silhouette control curves, clipped robe flow and cellular netting. Other native plates construct watchmakers, ladders, registers, tiers and diagrams from shared strokes. Book VI combines four seeded procedural plates with five explicitly data-carrying plates. Some technical record inputs are retained; manuscript-dependent plates require their public book inputs.

Modify construction geometry before adding surface marks. Preserve attachment points, occlusion order, reserved areas and each plate’s carrier. Data plates should continue to name their record and measure; a decorative adaptation should say when it stops carrying that data.

| Technique | Use | Entry points |
| --- | --- | --- |
| **Procedural Keeper and robe flow** (`book`) | Draw a figure from control curves, ribbons and clipped cloth flow | [figure.py](../../sources/codex-intervallorum/books/04_graduum/plates/v-native/figure.py) |
| **Native mechanisms, registers and tiers** (`book`) | Construct diagrams, watchmakers and organizational apparatus | [tabula_ii.py](../../sources/codex-intervallorum/books/04_graduum/plates/ii-native/tabula_ii.py)<br>[tabula_vi.py](../../sources/codex-intervallorum/books/04_graduum/plates/vi-native/tabula_vi.py)<br>[apparatus.py](../../sources/codex-intervallorum/books/04_graduum/plates/viii-native/apparatus.py)<br>[tabula_viii.py](../../sources/codex-intervallorum/books/04_graduum/plates/viii-native/tabula_viii.py) |
| **Flows, cuts and observer ladders** (`book`) | Use fields, seams and competing partitions in diagram compositions | [tabula_iii.py](../../sources/codex-intervallorum/books/04_graduum/plates/iii-native/tabula_iii.py)<br>[tabula_iv.py](../../sources/codex-intervallorum/books/04_graduum/plates/iv-native/tabula_iv.py)<br>[plates.py](../../sources/codex-intervallorum/books/02_intervallorum/generator/plates.py) |
| **Procedural and record-driven Book VI plates** (`book`) | Distinguish seeded forms from plots carrying declared records | [tabulae.py](../../sources/codex-intervallorum/books/06_disputationes/plates/tabulae.py)<br>[viplate.py](../../sources/codex-intervallorum/books/06_disputationes/plates/viplate.py) |

Useful symbols are indexed in [catalog/techniques.json](../../catalog/techniques.json). Every retained Python file, including other native plate constructions, is in the [source index](../../docs/SOURCE_INDEX.md).

[Start here](../../docs/GETTING_STARTED.md) · [Recipes](../../docs/RECIPES.md) · [Full catalog](../../CATALOG.md)
