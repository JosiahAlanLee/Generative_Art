# Validation of this collection

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
