# Additional art generators

Selected from `Librum_Quinque` commit `52430036c2cba79a53958eedc3dc340aa2a6451f`, with explicit authorization to transfer art generators into this public collection. This is an allowlist of artwork code, captions, drawing assets, stored host masks and generator documentation. Manuscript typesetters, prose source files, personal records, cases and repository history were not copied.

The files live under `sources/development-art/`, preserving their original relative layout. The original Matricis modules had absolute workspace and preview paths; these now use `portable_paths.py`, existing collection fonts and `examples/out/matricis`. `MATRICIS_OUTPUT` can select another output directory. Drawing and simulation algorithms are retained. The [manifest](../catalog/development-art-manifest.json) records source and delivered hashes and every adaptation.

## Python setup and first drawings

For Python 3.12, install the collection’s tested additional environment:

```sh
python -m pip install -r requirements-development-art.txt
python sources/development-art/books/01_matricis/generator/build_v2.py xi
python sources/development-art/books/01_matricis/plotter/build.py --output examples/out/xi-plotter --preview
```

Matricis runner choices are `ii`, `iii`, `iv`, `vi`, `viii`, `xi`, `xiii`, and `slips`. The earlier first three boards are available through `generator/preview.py 1`, `2`, or `3`. Individual `plate_*.py` modules expose `build_face()`; `front.py` exposes the title and index builders. Plate captions and invented inscriptions remain with the artwork; book prose is excluded.

## Node lattice

No npm packages are required. The generator was tested here with Node 24.19.0; the upstream record used Node 22.22.0.

```sh
node sources/development-art/common/lattice/plate.mjs --host robe --seed handoff --out examples/out/lattice.svg
node sources/development-art/common/lattice/plate.mjs --host choronzon --set dissolve=0.4 --pens study --out examples/out/lattice-dissolved.svg
node sources/development-art/common/lattice/samples.mjs
node --test sources/development-art/common/lattice/tests/lattice.test.mjs
python -m unittest discover -s sources/development-art/common/lattice/tests -v
```

Open `sources/development-art/common/lattice/node-lattice.html` directly for the interactive controls and SVG export. Eleven source silhouettes are included as masks with their art-source paths and hashes; the source raster files are not copied. The tests always verify decoded mask areas and recorded hashes. Set `GENART_BOOK_SOURCE` to a book checkout to additionally verify the raster bytes. Re-tracing uses `trace_hosts.py --repo /path/to/book`.

The three sample plot masters are reproducible outputs: run `samples.mjs` before their integration tests. Only the original manifest is retained; the generated SVGs are ignored. The upstream README describes its original full package and can refer to previews omitted here.

## Image-fed Physarum

Run `python examples/physarum_sample.py` for a small, self-contained synthetic-input example using two competing cultures and all five vector output styles.

The CLI accepts any image; start at a small grid and step count before using the original study’s production settings:

```sh
python sources/development-art/books/03_escalationum/physarum/physarum_plot.py INPUT.png -o examples/out/physarum --grid 160 --steps 150 --palette sepia --styles network,hatch,marks
```

`--cultures slate:ochre` selects faithful and feral cultures. Use an explicit palette containing those pen names, and vary `--station`, `--territories`, `--home`, `--repel` or `--attract`; `--help` documents all settings. The original pinned requirements are retained next to the tool. The root requirements provide the separately tested Python 3.12 environment; identical upstream production trajectories are not claimed across NumPy/Numba versions.

`study.py` is an optional multi-run comparison/proof builder. It requires source renders and prepared book pages; set `GENART_BOOK_SOURCE` to that book checkout. It is not needed for the standalone image-to-SVG tool.

## What was not duplicated

The private checkout also contains copies of many public-book modules and older integration variants. The existing collection already covers those drawing techniques. This addition selects the missing artwork generators; it does not replace the public snapshot with older binding, compositor or manuscript builders. The two private plotter folders contain identical converter code, so one is retained with the duplicate location recorded in the manifest.


## Validation for this import

- All eight Matricis runner modes built, including XI’s face, verso and strips. XI’s face reproduced the source drawing’s SHA-256 exactly after the path adaptations.
- All three lattice samples reproduced the upstream SVG hashes under Node 24.19.0. Seven Node tests and the Python SVG import check passed. The source-raster byte check is optional because those rasters were not copied; stored mask area and hash metadata are checked unconditionally.
- The original XI plotter’s five tests passed, including source identity, safe bounds, registration and separation of strokes.
- A small two-culture Physarum run completed and exported nonempty topo, network, fibers, hatch and marks SVGs. The initial Numba 0.68 import crashed in this runtime; the supplied Python 3.12 setup uses Numba 0.61.2, llvmlite 0.44.0 and NumPy 2.2.6, which ran successfully. This checks execution, not equivalence to the original production runs.
- The public-book snapshot remains byte-identical, and the collection verifier checks delivered hashes for the selected development-art files and all catalog links.

The original comparison study was not rebuilt and no physical plotting was tested. See [the Python symbol index](../catalog/development-art-modules.json) for individual module entry points.

`frontmatter_marks.py` extracts the reduced-letter monogram, sigil and toner-paper functions from the older folded insert. Its prose pages are excluded. The helpers include deterministic copier shadows, toner specks, clustered dropouts, a hinged guard and binding thread.
