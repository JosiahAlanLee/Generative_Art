# Getting started

Run these commands from the repository root. Use Python 3.10 or later; this collection was checked with Python 3.12. The book requirements are broad minimum versions, not a newly locked environment.

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-book.txt
python examples/make_sampler.py
```

Open `examples/out/technique-sampler.svg` or its PNG. The six panels call the imported line hand, grain hand, lattice, transcription, Notoria agent model and robe-flow routines. The field uses small demonstration parameters; its manifest records the full specification and source hash. SVG is the editable output; its panel labels are ordinary SVG text. This sampler is not a plot master.

## Build a complete native book plate

The fonts and public source inputs needed by the native Notoria plates are included. This command uses the original agent parameters and writes its results outside the source snapshot:

```sh
python sources/codex-intervallorum/books/05_notoria/plates/notae.py i examples/out/notoria
python sources/codex-intervallorum/books/05_notoria/plates/validate.py examples/out/notoria
```

The output directory contains layered SVGs, separate ink passes, a PNG preview, run manifest and validation record. Expect the production model and its regeneration check to take longer than the small sampler.

## Generate sentence-derived names

```sh
python sources/codex-intervallorum/books/07_septimus/semiphoras/semiphoras.py
```

For your own input, pass a text file with exactly three nonempty lines, each containing 72 letters after normalization, followed by an output directory. This is an English transposition adaptation, not a historical name reconstruction.

## Turn a phrase into numbers and glyphs

These use only the Python standard library; the sampler also needs the book requirements.

```sh
python lib/numerics/aq.py "HIC ET NUNC"
python lib/numerics/xenotation.py 178 --svg examples/out/178.svg
python lib/numerics/numogram.py
python -m unittest discover -s lib/numerics/tests
python examples/make_numerics_sampler.py
```

The SVG is a stroke-only glyph sized in millimetres. The sampler draws the same glyphs through the book's ink and cornmeal hands; see [Number systems](../techniques/09-number-systems/README.md).

## Draw a landscape plate

Driftless Plates needs only a browser, or Node 18 or later for batch output:

```sh
node studies/driftless-plates/cli.js --count 6
node studies/driftless-plates/test.js
```

The SVGs land in `studies/driftless-plates/out/`, set to the Codex 7 × 10 in page. Open `studies/driftless-plates/index.html` for the interactive version; see [Landscape plates](../techniques/11-landscape-plates/README.md).

## Verify the collection

```sh
python tools/verify_collection.py
```

This verifies each imported file against both SHA-256 and the upstream Git blob identity, parses every imported Python module, checks complete Python coverage and checks navigation links. It does not rebuild the full illustrated book.

## Existing studies

Keep these environments separate from the book environment:

| Study | Setup and first run |
| --- | --- |
| [Infernal Engine](../studies/infernal-engine/README.md) | Blender 4.5 LTS; open its supplied `.blend` or follow its rebuild instructions |
| [Photophobic](../studies/photophobic/README.md) | Install its own requirements; run `python build.py hortus` from that study folder |
| [Scanned Statue v2](../studies/scanned-statue-v2/README.md) | Install its own requirements; follow its engraving or Trail First commands |

The study READMEs document their own limitations and recorded validations. They were not rebuilt during this source-organization change.
