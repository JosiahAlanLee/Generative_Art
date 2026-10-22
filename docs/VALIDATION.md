# Validation of this collection

## Scan portraits stipple — 22 October 2026

Prepared with Claude, in the Scan portraits environment below. This covers `studies/scan-portraits/stipple.py` and the plates rebuilt with it; `lib/halftone`, Scanned Statue v2 and every imported source file are unchanged.

| Check | Observed result |
| --- | --- |
| `python studies/scan-portraits/checks.py` | 47 passed. The seven new or extended checks: on each plate the closest dot is 0.206–0.209 mm from a line's centre, with 0.200 mm touching; each plate's dot count is within 5 % of what its light asks for (3,260, 4,967 and 3,342 dots); stipple dots lie on the ray-cast scan; on a uniform field `lib/halftone`'s sampler packs at 0.641 points per r², against the 0.64 assumed. The rest are as below, including the byte-for-byte rebuild of `lps-bust` |
| `python studies/scan-portraits/build.py` | Three A4 plates in 3 min 16 s: 44.7, 42.0 and 40.6 m of line, with estimated plots of 1.2, 1.4 and 0.9 h, of which pen lifts for dots are 14–21 minutes |
| Visual review | Faces at 14 px/mm with and without the stipple, two dot shares on each head, and the plates side by side |
| Collection verifier | 241 public snapshot files, 58 selected development-art files, 75 techniques and all local guide links |

Physical plotting was not tested.

## Scan portraits — 22 October 2026

Prepared with Claude, on Linux with Python 3.13.16 and Scanned Statue v2's pinned requirements (NumPy 2.5.3, SciPy 1.18.1, Numba 0.68.0, trimesh 5.1.1, CairoSVG 2.9.1) on two cores. This covers `studies/scan-portraits`; no imported source file and no file in Scanned Statue v2 changed.

| Check | Observed result |
| --- | --- |
| `python studies/scan-portraits/checks.py` | 40 passed. Model files match their pinned upstream hashes, and both licence files are present. Each plate is stroke-only, inside 8–202 × 10–288 mm, carries its credit, and matches its report. Head lines lie on the ray-cast scan to within 0.6 mm; ground points stay at least 0.3 mm clear. Loop subdivision keeps a flat sheet flat and its UVs aligned across a seam. Ridges and valleys land on a corrugated sheet's crests and troughs. The key light follows the cosine law on a sphere. Path ordering keeps every path and cuts travel. `lps-bust` rebuilds byte for byte from scratch |
| `python studies/scan-portraits/build.py` | Three A4 plates in 2 min 26 s: `washington-bust` 46.7 m of line, `washington-front` 44.8 m, `lps-bust` 42.3 m |
| Visual review | Plates, layer-by-layer renders and 14 px/mm crops of each face inspected; the four presets not in the build (Washington `head` and `profile`, Lee Perry-Smith `head` and `front`) rendered and inspected; a Codex 7 × 10 in sheet stays inside its extent |
| Collection verifier | 241 public snapshot files, 58 selected development-art files, 75 techniques and all local guide links |

Physical plotting was not tested.

## Workbench review fixes — 22 October 2026

Prepared with Claude, on Linux with Python 3.13 (the Infernal engraving requirements), Node 22, vpype 1.15.0 in its own environment and Chromium through Playwright. This covers `workbench/` and the Driftless CLI's new `--penWidth`; no generator algorithm changed.

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s workbench/tests -v` | 19 passed with `WORKBENCH_VPYPE` set, none skipped. Ten are new: engine and nib arguments; vpype layer numbers, allowed merges, layer-order restore and the paper-layer refusal; a copy that leaves status reads immediate and refuses renders meanwhile (stand-in vpype); a real vpype copy keeping every stroke and the layer order; instance id, history summaries and static types; restart stopping only its own leftover render; SIGTERM and SIGHUP stopping the active render |
| `node studies/driftless-plates/test.js` | 42 passed. Three are new: `--penWidth 0.35` is the default plate byte for byte, 0.5 mm redraws (e2: 21,404 strokes against 22,978) and bad widths are refused. The nine preview plates still regenerate byte for byte; 18 seed and format combinations also matched the previous CLI byte for byte |
| Other suites | `lib/farm_objects` 8 pass; `node --check workbench/static/app.js`; `python tools/verify_collection.py` (74 techniques and all local guide links) |
| Browser | A recipe with an unknown setting (`cells`) or value (`tabloid`) is refused whole; an engine 1.1 recipe renders c2 as the kept sandstone tower (the current engine draws a limestone outcrop); focus, a log selection and a scrolled-up log survive refreshes; a preview polled half written recovers when the file completes; a tab left open across a restart renders without reloading; inert settings are greyed out with the reason; zoom 100% shows A4 at 794 px wide |
| vpype copies | e2 at A4 (0.5 mm nib) and the Infernal tower plate: every stroke kept (21,404 and 31,825), line length per layer within 0.012 mm, layers in the original order (Driftless 4-tint, 2-flora, 3-accent, 1-key, restored after vpype). Layer switches work on the copies. During the 23 s copy of the 23.6 MB tower plate, status reads took 1–2 ms |
| Shutdown | SIGTERM and SIGHUP to the server stopped a running Infernal dry run and marked it cancelled. After SIGKILL, the next start stopped the leftover render and marked the job interrupted |

Not tested: Windows, a native bpy render through the workbench, DrawingBot V3 and physical plotting.

## Bur oaks — 22 October 2026

Prepared with Claude, in the same environments as the plate studies below.

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s lib/flora/tests -v` | 25 passed. The 16 new tests cover the tree, the marks and the standalone renderer, below |
| `python -m unittest discover -s studies/infernal-landscape/tests -v` | 31 passed. Three are new: the oak builder's parts are named, wound outward and never hatched; the near oak's crown clears the barn; the tree regenerated at render time is the scene's, vertex for vertex |
| Other `lib` suites | `face_patterns` 15 and `farm_objects` 8 pass |
| `python tools/verify_collection.py` | 74 techniques (with main merged) and all local guide links |
| Plates (Blender) | One scene record (`eeab83ca…`). All 24 checks pass on the main, tower and barn views; the new one, `oak_samples_visible`, re-tests 4,365, 5,414 and 9,908 samples of the oak marks, none hidden. Native Blender rays: 1,600 samples per view, none hidden. Volume foliage faces: 76,480 |
| Tone | Oaks stay lighter than buildings on every view: 0.213 against 0.220 on the barn plate, 0.243 against 0.314 on the tower plate, 0.261 against 0.483 on the main view |
| Plates (dry run) | All 21 checks pass on each view (the three Blender-only checks do not apply). Oak tones match the Blender build to 0.001; every zone is within 0.003 (the tower's furniture) |
| Unchanged outputs | Re-rendered with the final code: the delivered main SVG (`84235df0…`) and the face-pattern comparison (`7a6bb489…`) are byte-identical. `studies/wisconsin-flora/build.py` rebuilds every committed SVG, PNG and manifest byte for byte after `Drawing` gained per-layer pens |
| Review | The plates, the preview sheet and the specimen sheet were inspected at full size. Tuning on dry runs, in order: rows thinned and broken in the light; outlines opened on the lit side, ranked so a darkness asks for its fraction of openings; scaffold limbs staggered up the trunk (a single fork read as a knot); masses enlarged, flattened and lumped at three scales; crowns lightened to keep the tone rule |

The new `lib/flora` tests:

- the tree repeats by seed and varies between seeds;
- its habit: foliage tops within 10% of the height, reach within the spread,
  the trunk set into the ground and flared, four to six scaffold limbs;
- limbs taper and start inside their parent, no thicker than it;
- meshes are closed (every edge used twice) with positive volume;
- `bare` and `detail` keep the limbs;
- furrows ride the bark;
- placement moves and turns;
- bad parameters are refused;
- scallops keep their ends and bulge to one side;
- marks stay on their masses and off a nearer post;
- shade draws at least twice the row length of light;
- outlines lie within a scallop of a silhouette;
- contact shadow darkens behind nearer things;
- limb outlines are tangent to the view;
- furrows are kept by rank, darkness and room.

Only the recorded route was examined. Physical plotting was not tested.

## Plate studies — 22 October 2026

Prepared with Claude. Built with `bpy` 4.5.14 LTS in Python 3.11, and the
Infernal Landscape engraving requirements in Python 3.12: NumPy 2.2.6, Numba
0.61.2, SciPy 1.17.0, and Shapely 2.2.0, which `lib/fuzz` needs and
`requirements.txt` now lists. Node 22 builds the Driftless patches.

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s lib/face_patterns/tests -v` | 15 passed. Two are new: `cut_discs` leaves nothing inside a disc and every length outside it; `keep_where` keeps only where its test holds and reports the kept fraction |
| `python -m unittest discover -s studies/infernal-landscape/tests -v` | 28 passed. The 13 new ones in `test_plates.py` cover: the quilt board fits the wall clear of the door and rail (seed 22's gable is too short); farmstead objects, board and footprints; the board hangs in front of the siding; bases sit 5 cm into the ground; zone points stay inside their zone, off footprints and the track, keep their minimum spacing, repeat by seed and are denser at edges; flora drawings are in plate millimetres with the root at the origin; thinning keeps every second seed and every leaf; the seal's core, slot, ring and ninefold symmetry; the main view's atlas takes in the farmyard and nothing else; every farmyard plant and every footprint stands on hatched ground; close views hatch what they see inside the mesh; the edge fade |
| Other `lib` suites | `barn_quilts`, `codex_palette`, `farm_objects`, `flora`, `fuzz`, `halftone`, `numerics`, `process_art` and `sdf2d` pass |
| `python tools/verify_collection.py` | 241 public snapshot files, 58 selected development-art files, 72 techniques and all local guide links |
| Plates off | Recorded route, main camera, re-rendered with the final code: the delivered SVG (`84235df0…`) and the face-pattern comparison (`7a6bb489…`) are byte-identical to the builds before the change |
| Plates on (Blender) | One scene record (`07258dc8…`). All 23 checks pass on the main, tower and barn views. Native Blender rays: 1,600 samples per view, none hidden. Face-pattern samples re-tested: 30,313 tower, 5,143 barn, 13,625 main, none hidden |
| Plates on (dry run) | All 20 checks pass on each view; the three Blender-only checks do not apply. Zone tones are within 0.003 of the Blender build (the tower's furniture), within 0.001 elsewhere |
| Preview | `plates_preview.py`. The sheet and each plate were inspected. The first barn plate stopped hatching the ground at the main view's vignette (x = 20), right behind the tractor; the plate cameras now hatch the ground they see, out to the terrain mesh, and the main view takes in the farmyard (see PLATES.md) |

Found and fixed on the way:

- **Camera audit.** `model.py`'s audit measured the plate cameras at reference
  points off the page and reported 0.0075 px, over its 0.002 px limit. It now
  uses the points on the page, and adds points around the target when fewer
  than four are visible. The largest error is now 0.0006 px; the main and low
  cameras measure as before.
- **Native-ray verifier.** `verify_blender.py` audited the delivered folder
  for every variant. It now reads each build's own folder. Re-run on the
  face-pattern comparison: 1,600 samples, none hidden.
- **Close-camera memory.** The first tower render ran out of memory: hatch
  lines laid behind a close camera project to enormous lengths. The plate
  cameras now hatch only the ground and faces they see.
- **Numba cache.** `lib/farm_objects` loaded the study's ray kernel as
  `_farm_raycore`, while the study imports it as `raycore`. Numba's cache
  beside the file records the module name, so whichever ran second crashed
  with "No module named …". After an Infernal Landscape build, the farm
  objects' render test failed this way.
  - The farm objects now load the kernel as `raycore`, and both sides alias the
    old name so existing caches still load.
  - In a scratch copy, every order passes: farm then study, study then farm,
    and an old-style cache followed by either. The old loader fails the second
    of these.
  - The farm-remnants tractor and hay rake proofs rebuild byte-identical to
    the committed SVGs.

Only the recorded route was examined. Physical plotting was not tested.

## Face patterns — 22 October 2026

Prepared with Claude. Built with `bpy` 4.5.14 LTS in Python 3.11 and the
Infernal Landscape engraving requirements (NumPy 2.2.6, Numba 0.61.2, SciPy
1.17.0) in Python 3.12; Node 22 for the Driftless patches.

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s lib/face_patterns/tests -v` | 13 passed: frames read right/up from outside and are right-handed; coplanar faces share coordinates; lift inverts the projection; a course meets itself at a corner; exact convex and concave (L-shaped) clipping; hatching inside, evenly spaced and continuous between neighbouring polygons; height contours are courses; a blank fault seam is not bridged; screen spacing, nested stride and world spacing under an orthographic Jacobian; strata levels that reach a corner end at the same height on both walls (24 here); level beds across the axis; seams blanked and repeatable; quilt regions tile the unit square |
| `python -m unittest discover -s studies/infernal-landscape/tests -v` | 15 passed, including two new: variant output folders, and the same rule in `patches.cjs` and `run.py` |
| Other `lib` suites | `process_art`, `codex_palette`, `barn_quilts` and `numerics` pass under `requirements-process-art.txt` (they need shapely) |
| Patterns off | Recorded route, main camera: the SVG is byte-identical to the build before the change (`84235df0…`) |
| Patterns on (Blender) | Same scene record (`a88e94b4…`); all 23 checks pass, including the new `face_pattern_samples_visible` (8,949 samples, none hidden); also passes as a NumPy dry run |
| Comparison | `face_patterns_preview.py`: 247 pattern paths (0.319 m); crosshatching 214 paths (0.153 m) shorter; ink on the tower's lit walls 0.439 → 0.463, shaded 0.678 → 0.685; buildings zone 0.434 → 0.439; the sheet was inspected |

Only the recorded route's main camera was examined. Physical plotting was not tested.

## thi.ng ports — 22 October 2026

Prepared with Claude. Checked with Python 3.13.16, NumPy 2.5.3, SciPy 1.18.1, Shapely 2.2.0, ContourPy 1.4.0 and Pillow 12.3.0, without numba. This covers `lib/halftone`, `lib/fuzz`, `lib/sdf2d`, their guide, the survey in `docs/THING_TECHNIQUES.md` and `examples/make_thing_ports.py`; no imported source file changed.

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s lib/halftone/tests -v` | 17 passed: kernel weights sum to their divisor (Atkinson's 6/8 excepted) and only carry error forward; mid-grey diffuses to half black under six kernels; Atkinson lightens a 0.8 tone; three-level quantisation keeps the mean tone and its masks partition the image; Bayer matrices are permutations; ordered dithering keeps the mean; the tracer consumes every set pixel exactly once and the output rebuilds the mask; direction order, `min_len` and `max_len`; diagonal runs map to pixel coordinates; millimetre placement with and without a flipped y; uniform Poisson respects the radius and the bounds and repeats by seed; a black half is more than four times denser than a white half and every point was accepted clear of all earlier points; masks, seed points and `max_points`; one stratified point per cell; the three plates build inside the box with recorded counts; the book's `svgimport` reads a halftone plate with ink and coordinates intact |
| `python -m unittest discover -s lib/fuzz/tests -v` | 15 passed: point counts and kept end points for all six schemes; Chaikin cuts at 1/4 and 3/4 and converges to 5/6 of a square's area; DLG keeps the control points on the curve with the 9/16 − 1/16 midpoint; the cubic scheme is Lane–Riesenfeld; displacement at zero amplitude is midpoint subdivision and repeats by seed; break-point splines pass through the vertices with handles of tightness × edge; midpoint splines pass through the edge midpoints and at 2/3 reproduce the quadratic; uniform handles; closed sampling; passes jitter within bounds, a jitter-free curve still passes through the vertices, repeat by seed; resampled fuzzy lines; hatch lines lie inside the polygon at five angles, are spaced exactly, alternate direction and respect inset; jittered hatch stays within the jitter; dots fall inside; composed fills concatenate; union merges |
| `python -m unittest discover -s lib/sdf2d/tests -v` | 10 passed: circle, box, rounded box, segment, polyline exact; the polygon field equals the box field everywhere including sign, and a concave polygon's notch is outside; the ellipse is exact on its axes; plain booleans are min/max; chamfered, rounded, smooth and stepped unions never exceed the plain union and equal it where one shape dominates, and a rounded union fills the crease; intersection and subtraction variants satisfy De Morgan; translate, rotate about a centre, scale, mirror, grid repeat (periodic), mirrored repeat (alternating cells), polar repeat (six copies), offset, annular, band; contours of a circle lie on it within 0.02 mm at 0.25 mm sampling and inner levels at the expected radius; sign-tested hatching lands on the boundary, is spaced exactly, follows the angle and splits at a hole; the four plates build inside the box and repeat by seed |
| Rebuild | All twelve plates rebuild byte for byte from a second run; the seven committed SVGs match the hashes in `examples/previews/thing-ports/manifest.json` |
| Plate review | Halftone at four cells and two tone counts, six kernels, three stipple methods, fuzzy passes at four jitters straight and curved, six fills, six subdivision schemes (two not drawn: they only insert points), two apparatus and two tiling variants, reviewed individually and on the contact sheet. The specimen's ramp was lightened once so the three-level halftone's red layer no longer saturates the lower plate; the rotated arm of the apparatus was moved to rotate about its own centre; the tiling glyph is now repeated before translation |
| Existing suites and verifier | Process-art tests 21 passed; Codex palette tests 23 passed; collection verifier: 241 public snapshot files, 58 selected development-art files, 68 techniques and all local guide links |
| Weight | Halftone 41,538 strokes and 35.8 m pen-down at a 0.38 mm cell; kernels plate 42,623 strokes; stipples 7,412–8,960 dots; the other plates 28–1,823 strokes. Those two halftone SVGs (4.7–5.2 MB) and the stipple SVGs (2–3 MB) are not committed |

Licence statements in the survey were checked on 22 October 2026 against the `umbrella` root `LICENSE`, package `package.json` files, the `genart-api` licence and the `toxiclibs` `LICENSE.txt`; the items that could not be checked are listed there. Physical plotting was not tested.

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
| Independent source check | A separate agent, which had not written the notes, rechecked every book line reference against the pinned clone, fetched licence and terms pages and code licences, recounted the Leeson & Russ rows, recomputed the astrolabe radii and compared the guide with the code. Corrections applied: the Book III gate plate draws five routes, not one; the RIPEstat and RIPE Atlas terms were separated; unsourced counts for ASRS, the Scottish Survey, Old Bailey and Wellcome MS.110 were replaced or linked; the Internet Archive's *Dictionnaire infernal* licence tag was added; tube variant 0 has a spur off its loop |

Licence statements in the research notes were checked against publisher pages on 20 October 2026; the items that could not be checked are listed there. Physical plotting was not tested.
