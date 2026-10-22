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

For trees seen across a field there is a separate generator, the
[open-grown bur oak](../../studies/wisconsin-flora/README.md#open-grown-bur-oak-for-landscapes).
[`oak.py`](../../lib/flora/oak.py) builds its crooked limbs and foliage masses,
[`crown.py`](../../lib/flora/crown.py) engraves them for any camera,
[`oak_render.py`](../../lib/flora/oak_render.py) draws one tree on its own, and
the [plate studies](../../studies/infernal-landscape/PLATES.md) put it in a
landscape.

```sh
python -m lib.flora.oak_render --seed 371 --height 6.7 --out oak.svg
```

[Source research](../../studies/wisconsin-flora/RESEARCH.md) ·
[Seed variation](../../studies/wisconsin-flora/output/variation.png) ·
[Stage comparisons](../../studies/wisconsin-flora/output/stages.png)
