# Southwestern Wisconsin flora

[Six seeded species studies](../../studies/wisconsin-flora/README.md), with
regional source notes, repeatable variants, discrete seasonal organs and
transparent pen-path SVG output.

![Specimens](../../studies/wisconsin-flora/output/specimens.png)

The reusable API lives in [lib/flora](../../lib/flora). It generates actual 3D
surfaces and deliberate ink, supports multiple camera angles, and includes
bridges to Blender and the Infernal Landscape SceneBuilder. See the study's
verification limits before using the Blender adapter.

```sh
python -m lib.flora side_oats_grama --seed 83 --detail 0 --model
```

[Source research](../../studies/wisconsin-flora/RESEARCH.md) ·
[Seed variation](../../studies/wisconsin-flora/output/variation.png) ·
[Stage comparisons](../../studies/wisconsin-flora/output/stages.png)
