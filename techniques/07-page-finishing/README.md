# Paper, scribal marks and finishing

These passes work on PDF pages after composition.

The furniture module supplies specks, washes, blots, frames and handwritten notes during composition. The scribal pass adds sparse vector flourishes only where inspected paper is clear. Vellum makes a transparent mottled paper texture and protects rendered marks, text and images. Its light profile reduces pigment and compressed texture size.

Run scribal finishing before vellum. The scribal CLI requires a binding log beside its input. Keep an untreated PDF for comparison. Use a separate output for experiments and inspect both the rendered result and the preservation reports. These are PDF finishing operations, not plotter textures.

| Technique | Use | Entry points |
| --- | --- | --- |
| **Frames, paper specks, washes and hand notes** (`book`) | Unify illustrated pages with a shared visual vocabulary | [furniture.py](../../sources/codex-intervallorum/common/illum/furniture.py)<br>[bookpage.py](../../sources/codex-intervallorum/common/plot/bookpage.py) |
| **Content-aware scribal flourishes** (`book`) | Add stable vector pen trials in verified clear paper | [scribal.py](../../sources/codex-intervallorum/binding/scribal.py) |
| **Content-aware vellum and ink spots** (`book`) | Add low-frequency mottling, grain and fibres around content | [vellum.py](../../sources/codex-intervallorum/binding/vellum.py) |

Useful symbols are indexed in [catalog/techniques.json](../../catalog/techniques.json). Every retained Python file, including other native plate constructions, is in the [source index](../../docs/SOURCE_INDEX.md).

[Start here](../../docs/GETTING_STARTED.md) · [Recipes](../../docs/RECIPES.md) · [Full catalog](../../CATALOG.md)
