# Technique catalog

Choose by desired result. `book` means code present in the pinned public book main branch; it does not claim every retained source edition is active in the current binding. `study` means a pre-existing Generative_Art experiment. `sealed-artifact` means the public source does not include a regenerator.

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

## Scope and absent implementations

The selected contour grain notes mention aebrer / Andrew Brereton’s entropy-locking study as an influence on placement. The current book does **not** contain that recursive glitch algorithm or SFC32 implementation. Reaction–diffusion, rival-contact braids and shared-substrate proposals are also not imported implementations. Trail First and primitive growth are present in the existing statue study; the book’s image-fed growth renderer is a different program.

The source snapshot omits large raster art and edition PDFs. Every included and omitted source path is recorded in [the manifest](catalog/source-manifest.json); no private development repository was imported. The root [notices](NOTICES.md) explain attribution and inherited terms.
