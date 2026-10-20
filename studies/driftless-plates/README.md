# Driftless Plates

![Six preview plates: a bur oak, a ring monument, a sandstone tower, a farmstead in an arched window, a text-block clearing and an A4 plot master](preview.jpg)

A seeded generator of hidden-line landscape plates, made in October 2026 as background material for the book and for the pen plotter. Its subjects are the Driftless: contour-strip fields, coulees and rivers, bur oaks and white pines, silos, barns and round bales, sandstone towers, and an occasional geometric monument. Its density and vegetation follow Zancan's plotter landscapes; its ruled buildings and print imperfections follow Yazid's *Hashed Cities*. No code from either artist is used.

Every plate is drawn front to back against an occlusion mask, so the SVG holds only visible lines and can go straight to a plotter. By default a plate is set to the Codex Intervallorum page.

## Use

Open `index.html` in a browser. It needs no server or install; the interface fonts load from Google Fonts when online and fall back to system faces offline.

- **Scene:** subject, season, light and frame, each on Auto or fixed; Flora, Land, Built and Sky weights that blend those motifs within one scene; density and imperfection.
- **Ink:** ten palettes, ink strength (mixes every ink toward the paper, for plates behind text), nib width and a risograph-style colour offset.
- **Page:** trim, orientation, bleed, and a text area that either fades the linework or moves it into the tint ink.
- **Export:** SVG and 300 dpi PNG, path ordering for pen-up travel, a plot-time estimate and the plate's traits.

Batch rendering needs Node 18 or later:

```sh
node cli.js --count 12                                   # Codex page, Codex inks, into out/
node cli.js --seeds e2,f1 --zone codex --zone-mode tint  # lighten the Codex text block
node cli.js --count 6 --format codexPlot                 # A4 plot masters
node cli.js --help                                       # every option
node test.js                                             # the checks below
```

After editing `src/` or `engine.js`, run `node build.js` to rebuild `index.html`, then `node make_preview.js` to refresh `manifest.json` and this preview. The preview needs `sharp` (`npm install sharp`); without it the manifest is still written.

## Codex sizes

The page geometry is read from the pinned book snapshot in [`sources/codex-intervallorum`](../../sources/codex-intervallorum/) and kept in one record, `CODEX` in `engine.js`. `test.js` re-reads the lines below and fails if the book's values and the record diverge, so a snapshot update that changes the page shows up here.

| Setting | Value | Read from |
| --- | --- | --- |
| `codex` trim | 7 × 10 in, 177.8 × 254 mm, no bleed | `binding/bind.py`: `PW, PH = 504.0, 720.0`. `binding/validate.py` rejects any other page size |
| Text block | 52–452 pt across, 55–638 pt above the foot; 18.3–159.5 mm across and 28.9–234.6 mm down | The frame shared by `books/07_septimus/build.py` (Clavis, De Vinculis), `books/00_accusator/build.py` and `books/00_matres/build.py` |
| `codexSpread` | 14 × 10 in, one text block per page | Two `codex` pages. The source frames are not mirrored, so both blocks sit 52 pt from their page's left edge |
| `codexPlot` | A4; every stroke within 8–202 mm across and 10–288 mm down; no bleed or colour offset | `common/plot/plate.py`: `W, H = 210, 297` and its `within_page_with_8mm_margin` check |
| `codex` palette | paper `#ede6d4`, ink `#161918`, red `#a32b24`, mute `#5a4331` | `common/plot/plate.py` `PAPER`; `common/plot/plotkit.py` `INK, RED`; `binding/backmatter.py` `MUTE` |

The books do not share one text block. Book VI sets 66–452 pt with claim tags hanging at 59 pt, and Graduum and the Tarot use mirrored inner and outer margins. Those settings are not offered here. Other trims scale the Codex block in proportion.

Placing a plate in a binding is not automated; the generator only writes files.

## Output

- **SVG:** millimetre units, one Inkscape/AxiDraw layer per pen: `1-key`, `2-flora`, `3-accent`, `4-tint`. The seed and every setting are stored in `<metadata>`.
- **Two-ink plotting:** the book's plate convention uses black and red pens. Plot layers 1, 2 and 4 in black and layer 3 in red. In the Codex palette the tint layer is the book's mute brown on screen and in PDFs.
- **PNG:** 300 dpi, with the resolution written into the file.

## How a plate is drawn

1. **Compose:** season, light, subject, frame and horizon from the seed and the motif weights.
2. **Terrain:** three to eight ridge bands from far to near, each given a treatment such as contour-strip fields, forest, hatched hillside, river or prairie. One or two bands are drawn in more detail than the rest.
3. **Drawing order:** nearest first. The frame, an overhanging bough, then each band's objects and surface. Every element clips its lines against the mask and then fills its own silhouette into it.
4. **Sky:** last, behind everything: sun or moon, clouds, ruled or dashed lines, wind or rays.
5. **Hand:** a final pass adds wobble, ink skips, overshoot on ruled lines and the text-area treatment. On plot masters it then clips to the safe extent.

| Part | Where in `engine.js` |
| --- | --- |
| Composition | `compose`, `computeFrame` |
| Terrain bands and treatments | `buildBands`, `farm`, `forestBand`, `hatchBand`, `waterBand`, `rockFaces` |
| Foreground grass and flowers | `tallGround`, `tuft`, `plant` |
| Trees | `colonize`, `drawBranches`, `oak`, `pine`, `bough`, `foliageCluster` |
| Structures | `silo`, `barn`, `house`, `waterTower`, `rockTower`, `monument`, `poleLine` |
| Sky | `drawSky`, `sun`, `moon`, `clouds`, `windLines` |
| Hand and text area | `post`, `textZone` |
| SVG and path ordering | `toSVG`, `orderPaths` |

## Reproducibility

A seed with the same settings and engine version draws the same plate. `test.js` regenerates the six plates in `plates.json` and compares their SVG hashes with `manifest.json`. That holds within one JavaScript engine: `Math.sin`, `Math.exp` and the like are not required to round identically everywhere, so another browser can shift a plate slightly.

## Limits

- Physical plotting was not tested.
- Cumulus clouds read as cartoonish, and the hatched-hillside treatment comes out heavy on some seeds.
- Fade out leaves a few specks inside the text area. Lighten keeps every line, drawn in the tint pen.
- Plates run from about 4,000 to more than 20,000 strokes. The plot-time estimate assumes 25 mm/s and a quarter second per pen lift.

## Sources

- Zancan's plotter work and the `trees.js` program behind his daily plotting from 2021: [Tree_Line at bitforms gallery](https://artguide.artforum.com/?p=919587).
- Yazid's simulated print imperfections, after Grace C. Hertlein's *City Painting*: [Hashed Cities on raster.art](https://www.raster.art/artwork/hashed-cities-by-yazid/about).
- Tree growth by space colonization: Runions, Lane and Prusinkiewicz, [Modeling Trees with a Space Colonization Algorithm](https://www.algorithmicbotany.org/papers/colonization.egwnp2007.html) (2007).
- Seeding: `xmur3` and `sfc32` as published in bryc's [PRNGs.md](https://github.com/bryc/code/blob/master/jshash/PRNGs.md), public domain. `sfc32` comes from the PractRand suite. This is plain seeding, not aebrer's entropy locking.
- Noise: 2D simplex noise written after Stefan Gustavson's [Simplex noise demystified](https://cgvr.cs.uni-bremen.de/teaching/cg_literatur/simplexnoise.pdf) (2005).
