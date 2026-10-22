# Technique catalog

Choose by desired result. `book` means code present in the pinned public book main branch; it does not claim every retained source edition is active in the current binding. `study` means a self-contained Generative_Art experiment under `studies/`, with its own runtime. `development-art` means art-only source selected from the private development repository at the author’s request. `sealed-artifact` means the public source does not include a regenerator. `collection` means code written for this collection rather than imported from the book.

The snapshot is `JosiahAlanLee/Codex-Intervallorum@b789e03f30034bc8403f8a40aaf83842885aaad5` (20 October 2026). Every tracked Python file is retained; source editions, helpers, model inputs and validators have explicit roles in the [source index](docs/SOURCE_INDEX.md).

## [Linework and materials](techniques/01-linework-materials/README.md)

| Technique | What to use it for | Status |
| --- | --- | --- |
| [Seeded pen tremor](sources/codex-intervallorum/common/geometry/core.py) | Give otherwise exact curves a stable drawn hand | book |
| [Curves, clipping and lattice hatching](sources/codex-intervallorum/common/geometry/core.py) | Build curls, spirals, clipped hatch and cellular-looking fills | book |
| [Cornmeal / granular stroke hand](sources/codex-intervallorum/common/geometry/marks.py) | Render the same scaffold as dispersed grains | book |
| [Seeded sigils and ornament vocabulary](sources/codex-intervallorum/common/geometry/marks.py) | Compose stable seal cores with curls, fringes and bands | book |

## [Physarum fields and figure growth](techniques/02-fields-growth/README.md)

| Technique | What to use it for | Status |
| --- | --- | --- |
| [Notoria three-sensor agent fields](sources/codex-intervallorum/books/05_notoria/fields/physarum.py) | Generate reproducible deposit/sense/decay/follow/food-node plates | book |
| [Marching-squares field contours](sources/codex-intervallorum/common/illum/figure_growth.py) | Turn a scalar field into joined level curves | book |
| [Image-fed progressive figure replacement](sources/codex-intervallorum/common/illum/figure_growth.py) | Move selected portions of a source figure into flow and grain | book |
| [Selected contour fringe](sources/codex-intervallorum/common/illum/figure_growth.py) | Dissolve only a narrow physical edge into sketch and grain | book |
| [Selected granular hatching and flowing footer](sources/codex-intervallorum/common/illum/figure_growth.py) | Put grain beside explicitly selected structural/decorative paths | book |

## [Figures, mechanisms and data plates](techniques/03-figures-apparatus/README.md)

| Technique | What to use it for | Status |
| --- | --- | --- |
| [Procedural Keeper and robe flow](sources/codex-intervallorum/books/04_graduum/plates/v-native/figure.py) | Draw a figure from control curves, ribbons and clipped cloth flow | book |
| [Native mechanisms, registers and tiers](sources/codex-intervallorum/books/04_graduum/plates/ii-native/tabula_ii.py) | Construct diagrams, watchmakers and organizational apparatus | book |
| [Flows, cuts and observer ladders](sources/codex-intervallorum/books/04_graduum/plates/iii-native/tabula_iii.py) | Use fields, seams and competing partitions in diagram compositions | book |
| [Procedural and record-driven Book VI plates](sources/codex-intervallorum/books/06_disputationes/plates/tabulae.py) | Distinguish seeded forms from plots carrying declared records | book |

## [Ciphers, lettering and seals](techniques/04-ciphers-seals/README.md)

| Technique | What to use it for | Status |
| --- | --- | --- |
| [Matricis substitution alphabet](sources/codex-intervallorum/books/01_matricis/generator/cipher.py) | Write recoverable text with dot/ring terminals | book |
| [Twelve-sign plus tally transcription](sources/codex-intervallorum/common/geometry/tx.py) | Generate script strips and circular inscriptions | book |
| [Biliteral drawing carrier](sources/codex-intervallorum/common/plot/ornament.py) | Carry five-bit letters in scale ticks or head/no-head marks | book |
| [Shifted signs, office litany and ordered paths](sources/codex-intervallorum/books/04_graduum/proofs/ix-gpt/codec.py) | Use position, form or drawing order as a text carrier | book |
| [Semiphoras 72-name transposition](sources/codex-intervallorum/books/07_septimus/semiphoras/semiphoras.py) | Generate trigrams and indexed seals from three sentences | book |
| [Nota Clausa field carrier](sources/codex-intervallorum/books/07_septimus/clausa/REGULA.md) | Inspect the public rule and sealed SVGs; validate a proposed reading | sealed-artifact |

## [Raster compositing and native plate adapters](techniques/05-compositing/README.md)

| Technique | What to use it for | Status |
| --- | --- | --- |
| [Paper keying and red-ink remap](sources/codex-intervallorum/common/illum/raster.py) | Integrate a raster figure with the page ground | book |
| [Silhouettes, anchors and native plate slots](sources/codex-intervallorum/common/illum/raster.py) | Preserve geometry while replacing illustrated appearance | book |

## [Plotter geometry and export](techniques/06-plotter-export/README.md)

| Technique | What to use it for | Status |
| --- | --- | --- |
| [Two-layer, two-ink stroke export](sources/codex-intervallorum/common/plot/plotkit.py) | Write separate art/text layers and ink passes | book |
| [Centreline and outline lettering](sources/codex-intervallorum/common/plot/plotkit.py) | Choose actual pen lettering or reading-edition outlines | book |
| [Restricted SVG stroke import](sources/codex-intervallorum/common/plot/svgimport.py) | Reuse the book’s generated seal geometry in new plates | book |
| [Timed motor counterpoint](studies/plotter-score/README.md) | Couple motor-rate voices to geometry; SVG, motion JSON, MIDI and audio auditions | study |

## [Paper, scribal marks and finishing](techniques/07-page-finishing/README.md)

| Technique | What to use it for | Status |
| --- | --- | --- |
| [Frames, paper specks, washes and hand notes](sources/codex-intervallorum/common/illum/furniture.py) | Unify illustrated pages with a shared visual vocabulary | book |
| [Content-aware scribal flourishes](sources/codex-intervallorum/binding/scribal.py) | Add stable vector pen trials in verified clear paper | book |
| [Content-aware vellum and ink spots](sources/codex-intervallorum/binding/vellum.py) | Add low-frequency mottling, grain and fibres around content | book |

## [Existing scene and scan studies](techniques/08-scene-studies/README.md)

| Technique | What to use it for | Status |
| --- | --- | --- |
| [Infernal Engine / Blender nodes](studies/infernal-engine/build_infernal.py) | Construct procedural interior/exterior scene studies | study |
| [Ray-lit scenes with photophobic cultures](studies/photophobic/common/mould.py) | Grow two shade-seeking strains over scene surfaces | study |
| [Scan engraving and Trail First primitives](studies/scanned-statue-v2/engrave.py) | Recover mesh contours and place primitives along trails | study |
| [Perspective 3D engraving with landscape strokes](studies/three-gates/README.md) | Draw structures, water and depth-ordered Driftless plants through one perspective camera | study |
| [Evaluated Blender terrain and mapped symbols](studies/terrain-symbols/README.md) | Drape 2D field marks onto displaced terrain, keep vegetation upright, and share geometry / plant occlusion with crosshatching | study |
| [2D generators on flat faces](studies/infernal-landscape/FACE-PATTERNS.md) | Draw strata, a barn quilt or any planar generator on a scene's flat walls, continuous across faces, with spacing set by the camera | collection |
| [Close-camera plate studies](studies/infernal-landscape/PLATES.md) | Combine the face patterns, a farm-objects farmstead, Wisconsin flora and three thi.ng ports in two engraved Infernal Engine plates | study |

## [Number systems](techniques/09-number-systems/README.md)

| Technique | What to use it for | Status |
| --- | --- | --- |
| [Anglossic Qabbala values](lib/numerics/aq.py) | Turn text into base-36 sums, reductions, seeds and rule numbers | collection |
| [Numogram arithmetic](lib/numerics/numogram.py) | Compute zones, currents, gates and mesh numbers; export a Graphviz graph | collection |
| [Tic Xenotation glyphs](lib/numerics/xenotation.py) | Write integers as nested prime tallies and draw them with a book hand | collection |

## Scope and absent implementations

The selected contour grain notes mention aebrer / Andrew Brereton’s entropy-locking study as an influence on placement. The current book does **not** contain that recursive glitch algorithm or SFC32 implementation. Driftless Plates seeds with `sfc32` as bryc published it; that is ordinary seeding, not entropy locking. Reaction–diffusion is newly implemented in the collection's [process-art studies](techniques/12-process-art/README.md), separately from imported source. Rival-contact braids and shared-substrate proposals remain unimplemented. Entropy locking, pixel sorting, CLIP-guided imagery and grammar text are listed with their code and license status in [HEN × CCRU techniques](docs/HEN_CCRU_TECHNIQUES.md); none of them is implemented here. Data sources and further techniques tied to the book's text, with checked terms, are in the [Codex palette research](docs/CODEX_PALETTE_RESEARCH.md); four of its leads are implemented as the [Codex palette studies](techniques/14-codex-palette/README.md). Karsten Schmidt's thi.ng and toxiclibs tools are surveyed with their licence status in [thi.ng and toxiclibs](docs/THING_TECHNIQUES.md); three groups are implemented as the [thi.ng ports](techniques/15-thing-ports/README.md), and the survey records which of his tools duplicate SciPy, Shapely and ContourPy and which do not apply to an iDraw. Trail First and primitive growth are present in the existing statue study; the book’s image-fed growth renderer is a different program.

The source snapshot omits large raster art and edition PDFs. Every included and omitted source path is recorded in [the manifest](catalog/source-manifest.json); the original public-book snapshot is separate from the later art-only development import. The root [notices](NOTICES.md) explain attribution and inherited terms.

## [Additional development generators](techniques/10-development-generators/README.md)

| Technique | Use | Source |
| --- | --- | --- |
| **Original Matricis native plates** | Generate the earlier engineering plates, folds, slips, inscriptions and title ornaments | [build_v2.py](sources/development-art/books/01_matricis/generator/build_v2.py) |
| **Matricis chalk and cornmeal grounds** | Use dark-board grain, networks and branching growth | [meal.py](sources/development-art/books/01_matricis/generator/meal.py) |
| **Legacy Tabula XI plotter conversion** | Convert the existing drawing into two-pen strokes with Hershey lettering and registration | [build.py](sources/development-art/books/01_matricis/plotter/build.py) |
| **Image-fed faithful and feral Physarum cultures** | Separate inks, grow competing or symbiotic cultures, export five vector styles | [physarum_plot.py](sources/development-art/books/03_escalationum/physarum/physarum_plot.py) |
| **Node lattice and dissolution** | Grow panes, rose windows, membranes, beaded frays and drips inside native or traced hosts | [lattice.js](sources/development-art/common/lattice/lattice.js) |

[Reduced-letter sigils and toner-stock texture](sources/development-art/books/01_matricis/generator/frontmatter_marks.py) are extracted art helpers; the source module’s prose pages are excluded.

## [Landscape plates](techniques/11-landscape-plates/README.md)

| Technique | What to use it for | Status |
| --- | --- | --- |
| [Hidden-line drawing against an occlusion mask](studies/driftless-plates/engine.js) | Draw near to far so every surviving stroke is visible, with no hidden-line pass | study |
| [Contour-strip farmland](studies/driftless-plates/engine.js) | Offset field strips down a ridge and fill them with rows, ticks, stipple, bales or woods | study |
| [Space-colonization trees and boughs](studies/driftless-plates/engine.js) | Grow branch skeletons toward crown attraction points and dress them in clustered foliage | study |
| [Tufted meadow and wildflowers](studies/driftless-plates/engine.js) | Fill a foreground in depth order with occluding grass tufts and seasonal flowers | study |
| [Ruled structures and monuments](studies/driftless-plates/engine.js) | Draw silos, barns, water towers and monuments shaded by line spacing | study |
| [Rock types and lake bluffs](studies/driftless-plates/engine.js) | Draw sandstone towers, dolomite ledges or quartzite crags, and bluffs rising from a lake | study |
| [Prairie and rock-top houses](studies/driftless-plates/engine.js) | Draw low hipped-roof houses after Wright and a house on a rock chimney with a cantilevered room | study |
| [Print hand and text clearing](studies/driftless-plates/engine.js) | Add wobble, ink skips and misregistration; fade or lighten linework inside the book's text block | study |
| [Plot export with pen-travel ordering](studies/driftless-plates/engine.js) | Write millimetre SVG with one layer per pen, ordered to shorten pen-up travel | study |

## [Process art R&D](techniques/12-process-art/README.md)

| Technique | Use | Status |
| --- | --- | --- |
| [D8 catchments and incision](lib/process_art/models.py) | Evolved terrain contours with red drainage | collection |
| [Folded and faulted stratigraphy](lib/process_art/models.py) | Interrupted age contours, marker beds and geological hatching | collection |
| [Gray–Scott × space colonization](lib/process_art/studies.py) | Chemical contours coupled to red vein growth around a reserved aperture | collection |
| [Time-series recurrence seals and textiles](lib/process_art/studies.py) | Declared data relationships with a recoverable matrix and input CSV | collection |

[Research and primary sources](docs/PROCESS_ART_RESEARCH.md) · [Selected demonstrations](examples/previews/process-art/selection.json). These are new collection studies, not installed book plates.


### [Textile scaffold and process couplings](techniques/12-process-art/TEXTILE.md)

A reusable tile grammar supplies joined curves and steps. Adaptive transport follows its graph, Gray–Scott chemistry occupies its pore compartments, and dissolution changes the material and its connectivity. The guide includes a controlled comparison, local placement API, clipped fragments and a building-surface example.

## Research and ideation

[Occult / cipher / code-art / Americana research](research/occult-americana/README.md): documented source pools, interpretive limits, ten proposed generators and four original sketches. The concept register records implementation status; these proposals are not additional production techniques.

## [Barn quilt squares](techniques/13-barn-quilts/README.md)

| Technique | Use | Status |
| --- | --- | --- |
| [Quilt-block partitions](lib/barn_quilts/generator.py) | Construct Ohio Star, Sawtooth Star, Churn Dash, Pinwheel, Log Cabin, Flying Geese, Rail Fence, and Square-in-Square | collection |
| [Painted wood and metal surfaces](lib/barn_quilts/generator.py) | Apply editable brush marks, support relief, fading, and edge chips on wood, MDO, aluminum, or steel | collection |
| [Shared-edge outline export](lib/barn_quilts/generator.py) | Split T-junctions and draw each block-partition edge once | collection |

[Source research](research/barn-quilts/README.md) · [Block sampler](examples/previews/barn-quilts/block-sampler.svg) · [Controlled material comparison](examples/previews/barn-quilts/material-comparison.svg). These are original geometric interpretations of traditional block families; no book or landscape plate is changed.

## [Codex palette](techniques/14-codex-palette/README.md)

| Technique | Use | Status |
| --- | --- | --- |
| [History Flow of Git revisions](lib/codex_palette/historyflow.py) | Columns of revisions; surviving lines carried across, classed by the commit that last changed them | collection |
| [Tero flux-adapted tubes](lib/codex_palette/tubes.py) | A tube network between fixed nodes from Kirchhoff flow and conductivity adaptation | collection |
| [Mathematical marbling on polylines](lib/codex_palette/marbling.py) | Plottable stone, gel-git and nonpareil sheets from closed-form drop and tine maps | collection |
| [Guilloché credentials](lib/codex_palette/guilloche.py) | Rose-engine rosettes, reeded rims and wave bands from declared catalogue numbers | collection |

[Research: data and techniques from the text](docs/CODEX_PALETTE_RESEARCH.md) · [Selected demonstrations](examples/previews/codex-palette/manifest.json). New collection studies, not installed book plates.

## [thi.ng ports](techniques/15-thing-ports/README.md)

| Technique | Use | Status |
| --- | --- | --- |
| [Dithered bitmap traced into pen runs](lib/halftone/trace.py) | Eleven error-diffusion kernels and Bayer screens; a bitmap consumed into horizontal, vertical and diagonal runs per pen | collection |
| [Tone-driven Poisson and stratified stipples](lib/halftone/poisson.py) | Dot density or dot size from a tone array; dart throwing with a per-candidate radius | collection |
| [Fuzzy multi-pass outlines and composable fills](lib/fuzz/fuzz.py) | Jittered redraws, straight or curved; hatching at any angle, dot screens, composed fills and pen presets | collection |
| [Subdivision curves and polygon-to-Bézier](lib/fuzz/curves.py) | Chaikin, cubic, Dyn–Levin–Gregory and displacement; break-point and midpoint cubic splines | collection |
| [2-D distance fields with blended booleans and repeats](lib/sdf2d/sdf.py) | Analytic shapes with chamfered, rounded, smooth and stepped booleans; grid, mirrored and polar repeats | collection |
| [Field contours and sign-tested hatching](lib/sdf2d/grid.py) | Nested offsets from one sampled field; depth bands hatched without a polygon | collection |

[Research: thi.ng and toxiclibs](docs/THING_TECHNIQUES.md) · [Selected demonstrations](examples/previews/thing-ports/manifest.json). Independent implementations after Karsten Schmidt's packages, not installed book plates.

## [Farm objects](techniques/16-farm-objects/README.md)

Seeded timber barns, open-seat tractors, disk harrows, dump rakes and slatted wagons. Actual mesh gaps and sag combine with surface-attached grain and corrosion, with four-layer stroke-only SVGs and shared 3D visibility. [Object study and specimens](studies/farm-remnants/README.md).

## [Southwestern Wisconsin flora](techniques/17-wisconsin-flora/README.md)

| Technique | Use | Status |
| --- | --- | --- |
| [Species-informed plant grammars](lib/flora/species.py) | Seeded stems, leaf surfaces and seasonal organs for six prairie/savanna species | collection |
| [Plant hidden-line drawing](lib/flora/render.py) | Sampled 3D visibility with organ-layered millimetre SVG | collection |
| [Landscape and Blender bridges](lib/flora/adapters.py) | Pass procedural plant geometry and ink to existing scenes | prototype |
