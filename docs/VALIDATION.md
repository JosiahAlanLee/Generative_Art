# Validation of this collection

## Palette repair and combination studies — 20 October 2026

Prepared with ChatGPT/Codex. The palette's 23 tests pass, including rounded
marbling geometry for seed 7 at all three stages, a two-ink crossing repair,
requested drop counts, named Git-ref resolution, mixed-revision pack metadata,
and a history-driven dissolution/control comparison. The selected gel-git
drawing goes from 29 crossing path pairs to zero. Its explicit print repair
removes about 1.29 m of crowded path, recorded in the sidecar; this is not a
claim that the discretized fluid analogy preserves exact topology.

All three combination SVGs import through the book importer with their recorded
stroke counts (555, 589, 384); hashes, finite numeric arrays and page bounds
pass. The contact sheet and repaired marbling were visually reviewed. Original
history, tube and guilloché SVGs are unchanged. The unchanged tube simulation
was not rerun; its exact stored SVG was re-rasterized for the refreshed contact
sheet. Collection provenance and local guide links pass with 61 techniques.
The concurrent Three Gates merge is retained as the PR base; its renderer was
not rerun. Physical plotting and full book binding were not tested.

Checked on 20 October 2026 with Python 3.12. This records the import/organization change, not a new validation of the three pre-existing scene studies or the whole illustrated edition.

| Check | Observed result |
| --- | --- |
| Imported bytes and complete Python coverage | 241 files match upstream SHA-256 and Git blob identities; all 117 tracked Python modules retained and parsed |
| Catalog and authored navigation | 30 unique technique entries; 8 family guides; all checked local links resolve |
| Six-panel sampler | SVG, PNG and manifest generated; visual inspection passed; repeat SVG and manifest identical |
| Production Notoria I | Built 2,048 strokes, including 1,118 art and 930 text strokes; 12.9 m measured pen-down length |
| Notoria plate validation | All five exported SVG passes passed; caption and hidden carrier round trips passed; margins and reserved blank passed |
| Notoria field regeneration | Code hash, recomputed manifest identifier and regenerated field matched; frame carries the correct identifier |
| Existing figure-growth suite | 5 tests passed: deterministic field, monotone masks, protected pixels, selected fringe and carrier/decorative boundaries |
| Existing vellum suite | 11 tests passed: protection, repeatability, light profile, exact source preservation and double-application checks |
| Existing scribal suite | 8 tests passed: clear paper, text/cipher protection, page identity and preservation checks |
| Semiphoras command | Generated all 72 names and passed its round trip |

Native Notoria outputs used for these checks are generated under `examples/out/` and are not committed. The committed preview is a small demonstration, not a reproduction of the book plates. Physical plotting was not tested. The existing Blender, Photophobic and statue build records remain as supplied; those studies were not rerun.

## Number systems addition

Checked on 20 October 2026 with Python 3.13. This covers `lib/numerics`, its guide and the numerics sampler; no imported source file changed.

| Check | Observed result |
| --- | --- |
| Unit tests (`python -m unittest discover -s lib/numerics/tests`) | 25 passed: aqcalc reference values, base-36 values, reduction and cumulation; syzygies, currents, regions, gates, cycles and all 45 mesh numbers; known xenotations 2–13, nullary forms, and round trips for 2–2,999 in both modes and both factor orders |
| Glyph geometry | Tic and enclosure counts match the string; every point lies inside the reported box; `draw()` stays inside the size it returns |
| Book hands | The sampler draws through `marks.Hand` in ink and grain modes; through `plotkit.PlotHand`, 178 = `:(:::(:))` exported 9 strokes in open-arc style |
| Numerics sampler | SVG, PNG and manifest generated; visual inspection passed; repeat SVG and manifest identical |
| Collection verifier | 241 unchanged source files, all 117 Python modules, 33 techniques and all local guide links |

Physical plotting was not tested.

## Driftless Plates addition

Checked on 20 October 2026 with Node 22 and Chromium through Playwright. This covers `studies/driftless-plates` and its guide; no imported or development-art source file changed.

| Check | Observed result |
| --- | --- |
| `node studies/driftless-plates/test.js` | 26 passed: the Codex page, text block (in three builders), plot sheet and extent, and four inks match the snapshot lines; the six preview plates regenerate byte for byte; three A4 plot masters stay within 8–202 × 10–288 mm; text blocks land correctly at trim, on a spread and with bleed; `index.html` is the current build |
| Page in Chromium, 390 px and 1,360 px wide | Plates drew with no script errors and no horizontal overflow; new plate, contact sheet, keep, zoom, the three Codex formats and the text block worked; SVG and PNG downloads saved |
| Exported files | SVG 177.8 mm wide with four pen layers, rasterized by librsvg; PNG 2,100 × 3,000 px with 300 dpi recorded |
| Pen-travel ordering | Pen-up travel across the six preview plates fell from 664 m in drawing order to 111 m |
| Collection verifier | 241 public snapshot files, 58 selected development-art files, 46 techniques and all local guide links |

Physical plotting was not tested.

## Process-art R&D

Checked on 20 October 2026 with Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0,
ContourPy 1.3.3 and Shapely 2.2.0. This addition is separate from the retained
source snapshots and preserves the concurrent Driftless Plates addition.

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s lib/process_art/tests -v` | 10 passed: strictly descending drainage, outlet runoff conservation, terrain evolution, chemical reproducibility/bounds, growth genealogy/step lengths, known recurrence pairs, missing-window row identity, constant/invalid series, book SVG import, and actual book ink/cornmeal Hand integration |
| Candidate review | 16 first-round and 24 second-round candidates rendered; selected tissue outlines refined analytically; eight final plates reviewed individually and as a contact sheet |
| Export | Each selected plate has a 2000-pixel PNG, alpha PNG, stroke-only SVG, numeric NPZ and parameter JSON; exact synthetic input CSVs accompany recurrence art |
| Scope | No preserved source file changed. No book text, cipher carrier, art slot or binding changed. No full book rebuild or physical plotting performed |

The companion ZIP includes the editable drawings, process states and selection
reasons. `examples/package_process_art.py` rebuilds the selected set. Full
upstream-byte verification requires the complete collection checkout; local
verification here covers authored changes and exported compatibility.


## Textile/process component study

Checked on 20 October 2026 using the process-art environment above.

| Check | Observed result |
| --- | --- |
| Process-art test suite | 17 passed, including seven new checks for shared tile ports, Kirchhoff balance and prescribed source/drain flows, conservative blocked diffusion, bounded/reproducible chemistry, irreversible material loss, geometric component clipping and seeded motif changes |
| Controlled comparison | Same seeded scaffold in all four modes; selected dissolution run changes four-neighbor pore components from 236 to 113 at the declared raster resolution/threshold |
| Demonstration | Four comparison panels, an architectural placement, three fragments and four borderless component SVGs; PNG/alpha versions, numeric states, settings and source fingerprints included |
| Visual review | Contact sheet and individual panel/context images inspected; plinth strokes and texture geometrically occluded by the building silhouette |

The tests cover model and interface properties. The material rates are illustrative; physical plotting and a full book binding were not performed. References and implementation choices are in [the textile guide](../techniques/12-process-art/TEXTILE.md).

## Driftless Plates 1.2

Checked on 20 October 2026 with Node 22 and Chromium through Playwright. This covers rock types, lake bluffs and the two houses in `studies/driftless-plates`; no imported or development-art source file changed.

| Check | Observed result |
| --- | --- |
| `node studies/driftless-plates/test.js` | 39 passed: the Codex geometry checks; the nine preview plates regenerate byte for byte; six A4 plot masters, including lake bluffs, a rock-top house and a quartzite crag, stay within 8–202 × 10–288 mm; the text-block and build checks; the six engine 1.1 preview plates draw the same geometry with `compat: '1.1'` |
| Compatibility with 1.1 | 48 of 48 seeds across four formats drew identical geometry under engine 1.1 and under 1.2 with `compat: '1.1'`; without it, 24 of 48 drew differently |
| Page in Chromium | No script errors or horizontal overflow at 390 px and 1,360 px; a plate kept under 1.1 redrew as kept; the Rock control and the three new subjects drew; SVG and PNG downloads saved |
| Generation time | Over 92 plates, median 187 ms and slowest 431 ms in Node; the largest had 24,627 strokes |
| Collection verifier | 241 public snapshot files, 58 selected development-art files, 53 techniques and all local guide links |

Physical plotting was not tested.

## Codex palette

Checked on 20 October 2026 with Python 3.13.16, NumPy 2.5.3, SciPy 1.18.1, Shapely 2.2.0, ContourPy 1.4.0, Pillow 12.3.0 and Git 2.43.0. This covers `lib/codex_palette`, its guide, the research notes and `examples/make_codex_palette.py`; no imported source file changed.

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s lib/codex_palette/tests -v` | 16 passed: History Flow classes, line survival and band spans on a constructed repository with a base import, a `codex/` merge and a Claude trailer; rebuild from the recorded input; tube mesh vertices, exact Kirchhoff balance at the source, the sink and every other node, repeatability and chain coverage; Nota V's nodes and arena against the snapshot's `notae.py` and `physarum.py`; drop radius, tine area, no crossings after drops and a gel-git comb, the resampling bound, repeatability; trochoid closure, reed and pass counts, one reed per office legion; the book's `svgimport` reads a marbled sheet with ink, width and coordinates intact |
| Recorded inputs | All four selected SVGs rebuild byte for byte from `examples/previews/codex-palette/` without a book clone; their hashes match `manifest.json` |
| Book clone | `--codex` on public book main `b789e03` reads five drawn revisions of nine manuscripts in under 4 s and reproduces the recorded inputs |
| Candidate review | Tube settings γ 0.85–1.8 and flux 0.2–2.0 at 1,200 and 2,400 steps, drawn as strands and as outlined vessels; marbling at the stone, gel-git and nonpareil stages; History Flow at version and time spacing; the four selections reviewed individually and side by side |
| Existing suites and verifier | Process-art tests: 17 passed. Collection verifier: 241 public snapshot files, 58 selected development-art files, 60 techniques and all local guide links |

Licence statements in the research notes were checked against publisher pages on 20 October 2026; the items that could not be checked are listed there. Physical plotting was not tested.
