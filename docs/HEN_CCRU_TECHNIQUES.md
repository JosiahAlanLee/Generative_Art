# HEN × CCRU: outside techniques and where their code stands

Techniques from the Hic et Nunc generative scene and the Ccru's numerics that the book does not contain, with the open-source code that implements them and whether that code can be copied into this repository. The Ccru numerics are implemented in [lib/numerics](../lib/numerics/) (see [Number systems](../techniques/09-number-systems/README.md)). Nothing else below has been imported; the entries are links.

**Copying rule.** MIT- or Apache-licensed code can be vendored with its license file and a line in [NOTICES](../NOTICES.md). A repository or gist with no license stays a link: without a license it is not open source, whatever its visibility. This repository still has no blanket license of its own.

| Technique | Code | License | In this repository |
| --- | --- | --- | --- |
| Entropy locking | aebrer's published statements and a PICO-8 gist | None stated | Named as an influence in the [catalog](../CATALOG.md); not implemented |
| HEN interactive OBJKT harness | [hicetnunc2000/hicetnunc](https://github.com/hicetnunc2000/hicetnunc) templates | MIT (repository deprecated) | None |
| Pixel sorting | [kimasendorf/ASDFPixelSort](https://github.com/kimasendorf/ASDFPixelSort) (Processing) · [kuy/asdf-pixel-sort](https://github.com/kuy/asdf-pixel-sort) (Rust port) | No license file · MIT | None |
| Physarum agent trails | [fogleman/physarum](https://github.com/fogleman/physarum) (Go) | MIT | The book's own Notoria model, plus two studies |
| Plotter path optimization | [vpype](https://github.com/abey79/vpype) | MIT | The book's own two-layer export in `plotkit` |
| CLIP-guided imagery (VQGAN+CLIP) | [nerdyrodent/VQGAN-CLIP](https://github.com/nerdyrodent/VQGAN-CLIP), after Katherine Crowson's notebook | Crowson's core and VQGAN code: MIT | None |
| Grammar text | [Tracery](https://github.com/galaxykate/tracery) (JavaScript) · [tracery](https://pypi.org/project/tracery/) (Python port) | Apache-2.0 | None |
| AQ, numogram, Tic Xenotation | [aqcalc](https://github.com/VitorGoatman/aqcalc) · [davis68/xenotation](https://github.com/davis68/xenotation) | Not checked / none stated | Implemented independently in `lib/numerics`; those projects supplied test values only |

## Notes by technique

**Entropy locking (aebrer).** A seeded generator is reseeded whenever a seed-controlled random check fires (one of his statements gives 3-in-1000 odds), so outputs fall into recursive loops and tears instead of uniform noise. His own framing is to build a system with far too much entropy and then constrain it. Credit him when a plate uses it. Sources: [Entropy-Locked Recursive Glitch Textures](https://www.raster.art/artwork/entropy-locked-recursive-glitch-textures-by-aebrer/about), [lesser infinities](https://www.raster.art/artwork/lesser-infinities-by-aebrer/about), and a minimal [PICO-8 example](https://gist.github.com/aebrer/36e1f45a07474aa24dd46f58ed703b09) in which a single conditional `srand` call is the lock.

**HEN interactive OBJKTs.** A work was a zip whose entry point is `index.html`, shown in a sandboxed iframe. HEN passed the viewer's and creator's wallet addresses as `?viewer=…&creator=…` query parameters and only allowed calls to a list of IPFS gateways and Tezos APIs (hicdex, TzKT, Better Call Dev and others). To keep an archived OBJKT runnable offline, serve it locally with those parameters and replace its network calls with recorded data. Source: the [Interactive OBJKTs wiki page](https://github.com/hicetnunc2000/hicetnunc/wiki/Interactive-OBJKTs).

**Pixel sorting (Kim Asendorf).** Sorts runs of pixels in each line by brightness or colour, with thresholds deciding where runs start and stop. The original Processing sketch has no license file, so link to it; the Rust port is MIT and can be vendored, or the algorithm can be rewritten in a few dozen lines.

**Physarum.** Already covered by the book's [Notoria three-sensor agents](../techniques/02-fields-growth/README.md) (after Jones, 2010) and by the Photophobic and Scanned Statue studies. fogleman/physarum is a compact CPU implementation that randomizes its parameters each run; it is useful as an independent comparison, not as a replacement.

**vpype.** Merges, sorts and lays out plotter paths. Do not run `linesort` or `linemerge` on a layer that carries text through drawing order: several of the book's carriers are read that way (see [Recipes](RECIPES.md)). Xenotation glyphs are read by containment and survive sorting.

**VQGAN+CLIP.** For reproducing HEN-period AI imagery with the tools of that period. Running it locally takes roughly 8 GB of GPU memory at 380 px and 10 GB at 512 px. The MIT licenses cover the code; check the terms of any pretrained checkpoint separately.

**Tracery.** Expands hand-written grammars into text: marginalia, catalog entries, registers. Keep generated text visibly separate from the book's recoverable carriers, so a reader never mistakes ornament text for an encoded message.

## Not included

Ccru prose, the Pandemonium matrix's names and descriptions, and the Ccru's numogram drawing are copyrighted texts and artwork, collected in *Ccru: Writings 1997–2003* ([Urbanomic](https://www.urbanomic.com/chapter/ccru-writings-pandemonium-commentary/)). The numogram gists circulating on GitHub reproduce that text without a license; use them as reading copies only. `lib/numerics` encodes the arithmetic rules, which are not themselves text.
