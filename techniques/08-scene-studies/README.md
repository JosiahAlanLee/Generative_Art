# Existing scene and scan studies

The three existing studies remain at their original paths.

Infernal Engine is the Blender Geometry Nodes starter for procedural scene construction. Photophobic combines three ray-lit scenes with surface-grown shade-seeking cultures. Scanned Statue v2 works on a Smithsonian scan, recovering contour detail and comparing engraving with Trail First sampling. These are adjacent experiments, not code imported from the book’s current main branch.

Use each study’s own environment and README. Photophobic and Scanned Statue use pinned NumPy/Numba environments; do not replace those with the book’s broad dependencies. Blender is a separate runtime. Their source attributions, manifests and existing outputs remain intact.

| Technique | Use | Entry points |
| --- | --- | --- |
| **Infernal Engine / Blender nodes** (`study`) | Construct procedural interior/exterior scene studies | [build_infernal.py](../../studies/infernal-engine/build_infernal.py)<br>[export_ink.py](../../studies/infernal-engine/export_ink.py) |
| **Ray-lit scenes with photophobic cultures** (`study`) | Grow two shade-seeking strains over scene surfaces | [mould.py](../../studies/photophobic/common/mould.py)<br>[render.py](../../studies/photophobic/porticus/render.py) |
| **Scan engraving and Trail First primitives** (`study`) | Recover mesh contours and place primitives along trails | [engrave.py](../../studies/scanned-statue-v2/engrave.py)<br>[trail_v2.py](../../studies/scanned-statue-v2/trail_v2.py)<br>[primitive_growth.py](../../studies/scanned-statue-v2/vendor/primitive_growth.py)<br>[trail_study.py](../../studies/scanned-statue-v2/vendor/trail_study.py) |

Useful symbols are indexed in [catalog/techniques.json](../../catalog/techniques.json). Every retained Python file, including other native plate constructions, is in the [source index](../../docs/SOURCE_INDEX.md).

[Start here](../../docs/GETTING_STARTED.md) · [Recipes](../../docs/RECIPES.md) · [Full catalog](../../CATALOG.md)
