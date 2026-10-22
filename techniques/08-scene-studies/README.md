# Existing scene and scan studies

The three original studies remain at their original paths.

Infernal Engine is the Blender Geometry Nodes starter for procedural scene construction. Photophobic combines three ray-lit scenes with surface-grown shade-seeking cultures. Scanned Statue v2 works on a Smithsonian scan, recovering contour detail and comparing engraving with Trail First sampling. These are adjacent experiments, not code imported from the book’s current main branch.

[Scan portraits](../../studies/scan-portraits/README.md) turns Scanned Statue v2's engine on two Creative Commons heads, the Smithsonian's CC0 Washington bust and Lee Perry-Smith's CC BY scan, for portrait plates that fill an A4 sheet. It imports that study's ray kernels, mesh level sets and suggestive contours unchanged.

Driftless Plates, the landscape plate generator, is also a study; its techniques have their own guide, [Landscape plates](../11-landscape-plates/README.md).

[The Three Gates](../../studies/three-gates/README.md) joins the 3D and landscape approaches in a lower three-quarter view. Its projection, rays and hatch-spacing Jacobian share one perspective camera. Plant silhouettes hide farther plants and model strokes, while the mesh hides vegetation behind the structure. The vegetation is still drawn on parallel vertical planes and does not cast shadows.

Use each study’s own environment and README. Photophobic and Scanned Statue use pinned NumPy/Numba environments; do not replace those with the book’s broad dependencies. Blender is a separate runtime. Their source attributions, manifests and existing outputs remain intact.

| Technique | Use | Entry points |
| --- | --- | --- |
| **Infernal Engine / Blender nodes** (`study`) | Construct procedural interior/exterior scene studies | [build_infernal.py](../../studies/infernal-engine/build_infernal.py)<br>[export_ink.py](../../studies/infernal-engine/export_ink.py) |
| **Infernal Engine 0.2 / task graph estates** (`study`) | Generate buildings from durations, prerequisites, release times and unavailable gates; combine volume trees with Driftless strokes | [task compiler](../../studies/infernal-landscape/compile.py)<br>[geometry builder](../../studies/infernal-landscape/geometry.py)<br>[Blender backend](../../studies/infernal-landscape/model.py)<br>[engraving and reproduction](../../studies/infernal-landscape/README.md) |
| **Ray-lit scenes with photophobic cultures** (`study`) | Grow two shade-seeking strains over scene surfaces | [mould.py](../../studies/photophobic/common/mould.py)<br>[render.py](../../studies/photophobic/porticus/render.py) |
| **Scan engraving and Trail First primitives** (`study`) | Recover mesh contours and place primitives along trails | [engrave.py](../../studies/scanned-statue-v2/engrave.py)<br>[trail_v2.py](../../studies/scanned-statue-v2/trail_v2.py)<br>[primitive_growth.py](../../studies/scanned-statue-v2/vendor/primitive_growth.py)<br>[trail_study.py](../../studies/scanned-statue-v2/vendor/trail_study.py) |
| **Scan portraits** (`study`) | Draw a CC head scan as an A4 portrait plate: a soft key, fill and occlusion per vertex; section hatching with a cross family chosen per point for its angle; stipple between the lines in the light half-tones, placed by the thi.ng Poisson-disc port; ridge and valley lines; a ruled ground with a halo; a vignette | [portrait.py](../../studies/scan-portraits/portrait.py)<br>[stipple.py](../../studies/scan-portraits/stipple.py)<br>[creases.py](../../studies/scan-portraits/creases.py)<br>[light.py](../../studies/scan-portraits/light.py)<br>[ground.py](../../studies/scan-portraits/ground.py)<br>[subdivide.py](../../studies/scan-portraits/subdivide.py) |
| **Perspective engraving with landscape occlusion** (`study`) | Combine modeled structures, water and rooted plant drawings through one camera | [render.py](../../studies/three-gates/render.py)<br>[build.py](../../studies/three-gates/build.py)<br>[occlusion.py](../../studies/three-gates/occlusion.py) |
| **2D generators on flat faces** (`collection`) | Put strata, a barn quilt or any planar generator on a scene's flat walls: world-anchored frames, clipping, contours of solid fields, camera-set spacing, tone reserved and paint kept out of the light hatching | [mapping.py](../../lib/face_patterns/mapping.py)<br>[sources.py](../../lib/face_patterns/sources.py)<br>[Infernal Engine comparison](../../studies/infernal-landscape/FACE-PATTERNS.md) |
| **Close-camera plate studies** (`study`) | Put the farm-objects barn, tractor and hay rake into the estate, plant Wisconsin flora by variable-density Poisson sampling, and draw a sdf2d seal and a fuzz-painted barn quilt through two close cameras | [plates.py](../../studies/infernal-landscape/plates.py)<br>[surface_patterns.py](../../studies/infernal-landscape/surface_patterns.py)<br>[PLATES.md](../../studies/infernal-landscape/PLATES.md) |
| **Workshop interiors from recorded briefs** (`study`) | Build four editable Blender interiors and export surface hatching with hidden-line visibility | [model.py](../../studies/workshop-interiors/model.py)<br>[engrave.py](../../studies/workshop-interiors/engrave.py)<br>[verification and scene notes](../../studies/workshop-interiors/README.md) |

Useful symbols are indexed in [catalog/techniques.json](../../catalog/techniques.json). Every retained Python file, including other native plate constructions, is in the [source index](../../docs/SOURCE_INDEX.md).

[Start here](../../docs/GETTING_STARTED.md) · [Recipes](../../docs/RECIPES.md) · [Full catalog](../../CATALOG.md)
