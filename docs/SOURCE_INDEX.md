# Book source index

Pinned to `JosiahAlanLee/Codex-Intervallorum@b789e03f30034bc8403f8a40aaf83842885aaad5`. All 117 Python files are retained, including validators and build/model dependencies.

Roles distinguish reusable visual code from book assembly, model support and checks. File links go to unchanged local copies. See [the technique catalog](../CATALOG.md) for artistic uses.

## [binding/backmatter.py](../sources/codex-intervallorum/binding/backmatter.py)

**book-integration**. One house style for citations, inspection notes, and preparation records.

Symbols: `clean`, `identity`, `escalationum_record`, `is_project_record`, `citation_form`, `opening_records`, `collect`, `consolidate`, `register_fonts`, `Writer`, `write`.

## [binding/bind.py](../sources/codex-intervallorum/binding/bind.py)

**book-integration**. Bind the active books into one 7 x 10 in PDF with front matter and an outline.

Symbols: `fonts`, `paper`, `wrapped_lines`, `front_matter`, `numeral`, `label`, `colophon`, `blank_leaf`, `bibliography_pages`, `add_source_page`, `bibliography_cover`, `main`.

## [binding/bind_illustrated.py](../sources/codex-intervallorum/binding/bind_illustrated.py)

**book-integration**. Bind the consolidated opening, illustrated Books III-IV, Notoria, and De Potestate et Accusatione as Book VI.

Symbols: `bibliography_pages`, `front_matter`, `colophon`.

## [binding/scribal.py](../sources/codex-intervallorum/binding/scribal.py)

**visual-technique**. Sparse pen finishing for the illustrated binding; never redraw source content.

Symbols: `seed_for`, `lines`, `text_boxes`, `clear`, `bezier`, `pen`, `scene_mount`, `finish_page`, `vector_record`, `verify`, `apply`.

## [binding/tests/test_backmatter.py](../sources/codex-intervallorum/binding/tests/test_backmatter.py)

**validation**. 

Symbols: `BackmatterTests`.

## [binding/tests/test_binding.py](../sources/codex-intervallorum/binding/tests/test_binding.py)

**validation**. Exercise binding across odd/even component lengths and an actual facing spread.

Symbols: `component`, `BindingTests`.

## [binding/tests/test_scribal.py](../sources/codex-intervallorum/binding/tests/test_scribal.py)

**validation**. Protect functional marks and retained PDF content during pen finishing.

Symbols: `ScribalTests`.

## [binding/tests/test_vellum.py](../sources/codex-intervallorum/binding/tests/test_vellum.py)

**validation**. Regression checks for content-aware paper: preserve functional marks exactly.

Symbols: `VellumTests`.

## [binding/unified.py](../sources/codex-intervallorum/binding/unified.py)

**book-integration**. Bind reading pages and rebuild a single, consistently typeset back section.

Symbols: `normalized`, `clean_source`, `front`, `citation_links`, `relink`, `relink_septimus`, `main`.

## [binding/validate.py](../sources/codex-intervallorum/binding/validate.py)

**validation**. Check the final binding, including physical spread parity and input provenance.

Symbols: `require`, `validate`.

## [binding/validate_typeset.py](../sources/codex-intervallorum/binding/validate_typeset.py)

**validation**. Validate retained body pages and the newly typeset back section.

Symbols: `normalized`, `validate`.

## [binding/vellum.py](../sources/codex-intervallorum/binding/vellum.py)

**visual-technique**. Content-aware, deterministic paper finishing for reading PDFs.

Symbols: `seed_for`, `text_record`, `text_boxes`, `protection`, `field`, `make_texture`, `png`, `add_texture`, `is_texture`, `source_images`, `source_image_info`, `identities`, `paths`, `images`, `links`, `verify_page`, `apply`.

## [books/00_accusator/build.py](../sources/codex-intervallorum/books/00_accusator/build.py)

**book-integration**. Reading edition of De Officio Accusatoris, the parable bound after the Clavis; no network at build time.

Symbols: `sha`, `plain`, `norm`, `paragraphs`, `sections`, `source_blocks`, `figures`, `references`, `fonts`, `markup`, `inscription`, `Book`, `build`.

## [books/00_accusator/validate.py](../sources/codex-intervallorum/books/00_accusator/validate.py)

**validation**. Validate the parable's reading edition: text coverage, plates, inscriptions and the end apparatus.

Symbols: `require`, `validate`.

## [books/00_matres/build.py](../sources/codex-intervallorum/books/00_matres/build.py)

**book-integration**. Reading edition of De Matribus Noctis, the parable bound before Book VI; no network at build time.

Symbols: `sha`, `plain`, `norm`, `paragraphs`, `sections`, `source_blocks`, `references`, `fonts`, `markup`, `Book`, `build`.

## [books/00_matres/validate.py](../sources/codex-intervallorum/books/00_matres/validate.py)

**validation**. Validate the parable's reading edition: text coverage, title page, bounds and the end apparatus.

Symbols: `require`, `validate`.

## [books/01_matricis/generator/cipher.py](../sources/codex-intervallorum/books/01_matricis/generator/cipher.py)

**visual-technique**. The cipher hand: a substitution alphabet built from the sketching marks, with

Symbols: `L`, `P`, `C`, `A`, `D`, `O`, `T`, `CR`, `SP`, `clean`, `measure`, `wrap`, `write`, `glyph_only`.

## [books/01_matricis_intervallorum/build.py](../sources/codex-intervallorum/books/01_matricis_intervallorum/build.py)

**book-integration**. Build the consolidated opening book from editable JSON and local assets.

Symbols: `mount_rect`, `mount_frame`, `mount_originals`, `fonts`, `markup`, `Book`, `Plate`, `question`, `outage`, `measure`, `bindings`, `questions`, `interleaf_chapter`, `interleaf_paths`, `plate_paths`, `render_plate`, `front`, `glyph_key`, `appendices`, `markdown`, `validate`, `main`.

## [books/01_matricis_intervallorum/models/gate_window/model.py](../sources/codex-intervallorum/books/01_matricis_intervallorum/models/gate_window/model.py)

**model-support**. Gate and window: a harm-accounting model in which the book's arrangement can lose.

Symbols: `Params`, `Stats`, `_stats`, `simulate_cell`, `expected_harm_deference`, `cell_rng`.

## [books/01_matricis_intervallorum/models/gate_window/report.py](../sources/codex-intervallorum/books/01_matricis_intervallorum/models/gate_window/report.py)

**model-support**. Apply the verdict rule to results.csv and write REPORT.md and region.svg.

Symbols: `fmt`, `lookup`, `key`, `frac`, `region_svg`, `render_report`, `main`.

## [books/01_matricis_intervallorum/models/gate_window/run.py](../sources/codex-intervallorum/books/01_matricis_intervallorum/models/gate_window/run.py)

**model-support**. Run the sweep once and write results.csv and manifest.json.

Symbols: `run_cells`, `write_results`, `main`.

## [books/01_matricis_intervallorum/models/gate_window/tests/test_gate_window.py](../sources/codex-intervallorum/books/01_matricis_intervallorum/models/gate_window/tests/test_gate_window.py)

**validation**. Checks on the model's arithmetic and limits, and on the verdict rule.

Symbols: `base`, `ModelArithmetic`, `synthetic`, `VerdictRule`.

## [books/01_matricis_intervallorum/models/gate_window/validate.py](../sources/codex-intervallorum/books/01_matricis_intervallorum/models/gate_window/validate.py)

**validation**. Check that results.csv regenerates from manifest.json and that REPORT.md follows it.

Symbols: `main`.

## [books/01_matricis_intervallorum/models/gate_window/verdict.py](../sources/codex-intervallorum/books/01_matricis_intervallorum/models/gate_window/verdict.py)

**model-support**. The sweep grid and the verdict rule, applied to a results table.

Symbols: `cells`, `sha256_file`, `load_rule`, `read_results`, `c_beats_a`, `a_beats_c_booked`, `_in`, `in_anchored`, `in_gate_home`, `_frac`, `apply`.

## [books/01_matricis_intervallorum/tests/test_combined.py](../sources/codex-intervallorum/books/01_matricis_intervallorum/tests/test_combined.py)

**validation**. Checks of the consolidation's source routing, identity, and cipher carriers.

Symbols: `CombinedTests`.

## [books/02_intervallorum/generator/__init__.py](../sources/codex-intervallorum/books/02_intervallorum/generator/__init__.py)

**visual-technique**. Portable manuscript, diagram, and PDF generation for Clavicula Intervallorum.

Symbols: package marker.

## [books/02_intervallorum/generator/build.py](../sources/codex-intervallorum/books/02_intervallorum/generator/build.py)

**visual-technique**. Build the book, standalone HTML, SVG plates, and an input provenance manifest.

Symbols: `register_fonts`, `markup`, `Book`, `render_plate`, `front_matter`, `html_text_page`, `build_pdf`, `appendices`, `write_html`, `write_markdown`, `main`.

## [books/02_intervallorum/generator/core.py](../sources/codex-intervallorum/books/02_intervallorum/generator/core.py)

**visual-technique**. Core drawing kit for the Clavicula Matricis plates.

Symbols: `f`, `num`, `pair`, `Doc`, `lerp`, `dist`, `rot`, `arc_pts`, `spiral_pts`, `curl_pts`, `resample`, `Wobble`, `clip_lines`, `hatch_lines`, `lattice`, `tri_pts`, `vesica`, `offset_line`, `path_len`, `point_at`, `bezier`, `catmull`, `merge`.

## [books/02_intervallorum/generator/hands.py](../sources/codex-intervallorum/books/02_intervallorum/generator/hands.py)

**visual-technique**. The three recurring hands, the later technical hand, and the record's base faces.

Symbols: `_box`, `cust`, `mhand`, `unh`, `tech`, `_runs`.

## [books/02_intervallorum/generator/marks.py](../sources/codex-intervallorum/books/02_intervallorum/generator/marks.py)

**visual-technique**. Hands (ink / cornmeal grain / plotter pen), vèvè-grammar ornament, and the

Symbols: `Hand`, `asterisk`, `curl`, `dotted`, `fringe`, `arrowhead`, `lattice_fill`, `leaf`, `band_x`, `sig_standing`, `sig_candidate`, `sig_gate`, `sig_authority`, `sig_mark`, `sig_ground`, `sig_break`, `sig_regulation`, `sig_bottleneck`, `sig_branch`, `sig_reflexive`, `sig_invariant`, `sig_boundary`, `sig_substrate_small`, `sig_pointer`, `XHand`, `write_ring`, `ring_x`.

## [books/02_intervallorum/generator/plates.py](../sources/codex-intervallorum/books/02_intervallorum/generator/plates.py)

**visual-technique**. Twelve original, deterministic SVG plates. Lettering is local font outlines.

Symbols: `Plate`, `plate_1`, `plate_2`, `plate_3`, `network`, `plate_4`, `plate_5`, `gate`, `plate_6`, `plate_7`, `plate_8`, `plate_9`, `plate_10`, `plate_11`, `plate_12`, `build_plates`.

## [books/02_intervallorum/generator/reachability.py](../sources/codex-intervallorum/books/02_intervallorum/generator/reachability.py)

**model-support**. A deliberately small, deterministic scheduling model, not an institutional simulator.

Symbols: `Task`, `Result`, `evaluate`, `specimen_cases`.

## [books/02_intervallorum/generator/refusal.py](../sources/codex-intervallorum/books/02_intervallorum/generator/refusal.py)

**model-support**. A deliberately small, deterministic model of a refusal, not a prediction about people.

Symbols: `Station`, `Outcome`, `_check`, `evaluate`, `smallest_opening_refusal`, `specimen_cases`.

## [books/02_intervallorum/generator/tx.py](../sources/codex-intervallorum/books/02_intervallorum/generator/tx.py)

**visual-technique**. The twelve-sign transcription hand (Astra's key): base mark I–XII plus a tally of 1–3 strokes.

Symbols: `normalize`, `encode`, `decode`, `codes`, `mark`, `tally`, `token_width`, `write`, `width`.

## [books/02_intervallorum/illustrated/build.py](../sources/codex-intervallorum/books/02_intervallorum/illustrated/build.py)

**book-integration**. Clavicula Intervallorum, illustrated edition.

Symbols: `R`, `fit`, `plate_3`, `plate_6`, `plate_7`, `plate_8`, `plate_12`, `render_plate`, `start`, `main`.

## [books/02_intervallorum/tests/test_portability.py](../sources/codex-intervallorum/books/02_intervallorum/tests/test_portability.py)

**validation**. 

Symbols: `PortableSourceTests`.

## [books/02_intervallorum/tests/test_reachability.py](../sources/codex-intervallorum/books/02_intervallorum/tests/test_reachability.py)

**validation**. 

Symbols: `ReachabilityTests`.

## [books/02_intervallorum/tests/test_refusal.py](../sources/codex-intervallorum/books/02_intervallorum/tests/test_refusal.py)

**validation**. 

Symbols: `RefusalTests`.

## [books/03_escalationum/generator/__init__.py](../sources/codex-intervallorum/books/03_escalationum/generator/__init__.py)

**visual-technique**. 

Symbols: package marker.

## [books/03_escalationum/generator/art.py](../sources/codex-intervallorum/books/03_escalationum/generator/art.py)

**visual-technique**. Deterministic path-only art, retaining Intervallorum's geometry and twelve marks.

Symbols: `font`, `label`, `doc`, `hand`, `l`, `rect`, `arrow`, `title`, `annotate`, `cipher`, `anchor`, `seal`, `portrait`, `matrix`, `vessel`, `clocks`, `gate`, `crumple`, `cord`, `runbook`, `office_seal`, `build_art`, `plot_export`.

## [books/03_escalationum/generator/build.py](../sources/codex-intervallorum/books/03_escalationum/generator/build.py)

**visual-technique**. Portable book build. Adapts Intervallorum's Canvas/Paragraph, SVG and manifest pipeline.

Symbols: `register`, `esc`, `key`, `pages`, `Book`, `fields`, `pdf_entry`, `build_pdf`, `entry_html`, `html_body`, `build_html`, `markdown`, `digest`, `build`.

## [books/03_escalationum/generator/core.py](../sources/codex-intervallorum/books/03_escalationum/generator/core.py)

**visual-technique**. Core drawing kit for the Clavicula Matricis plates.

Symbols: `f`, `num`, `pair`, `Doc`, `lerp`, `dist`, `rot`, `arc_pts`, `spiral_pts`, `curl_pts`, `resample`, `Wobble`, `clip_lines`, `hatch_lines`, `lattice`, `tri_pts`, `vesica`, `offset_line`, `path_len`, `point_at`, `bezier`, `catmull`, `merge`.

## [books/03_escalationum/generator/marks.py](../sources/codex-intervallorum/books/03_escalationum/generator/marks.py)

**visual-technique**. Hands (ink / cornmeal grain / plotter pen), vèvè-grammar ornament, and the

Symbols: `Hand`, `asterisk`, `curl`, `dotted`, `fringe`, `arrowhead`, `lattice_fill`, `leaf`, `band_x`, `sig_standing`, `sig_candidate`, `sig_gate`, `sig_authority`, `sig_mark`, `sig_ground`, `sig_break`, `sig_regulation`, `sig_bottleneck`, `sig_branch`, `sig_reflexive`, `sig_invariant`, `sig_boundary`, `sig_substrate_small`, `sig_pointer`, `XHand`, `write_ring`, `ring_x`.

## [books/03_escalationum/generator/reachability.py](../sources/codex-intervallorum/books/03_escalationum/generator/reachability.py)

**model-support**. A deliberately small, deterministic scheduling model, not an institutional simulator.

Symbols: `Task`, `Result`, `evaluate`, `escalation_tasks`, `executable_record`, `specimen_cases`.

## [books/03_escalationum/generator/tx.py](../sources/codex-intervallorum/books/03_escalationum/generator/tx.py)

**visual-technique**. The twelve-sign transcription hand (Astra's key): base mark I–XII plus a tally of 1–3 strokes.

Symbols: `normalize`, `encode`, `decode`, `codes`, `mark`, `tally`, `token_width`, `write`, `width`.

## [books/03_escalationum/illustrated/build.py](../sources/codex-intervallorum/books/03_escalationum/illustrated/build.py)

**book-integration**. Pseudomonarchia Escalationum, illustrated edition.

Symbols: `render_for`, `wrap_hand`, `IllBook`, `portrait_plate`, `station_ladder`, `illustrated_interlude`, `illustrated_workshop`, `entry_compact`, `entry_single`, `pages`, `build_pdf`, `draw_plain`, `main`.

## [books/03_escalationum/tests/test_book.py](../sources/codex-intervallorum/books/03_escalationum/tests/test_book.py)

**validation**. Tests of catalogue coverage, decodable seals, dependency semantics and portable output.

Symbols: `Scheduling`, `Catalogue`, `PortableOutput`.

## [books/04_graduum/build_book.py](../sources/codex-intervallorum/books/04_graduum/build_book.py)

**book-integration**. Clavicula Graduum: the book. Manuscript text from manuscript/book.json set on 7 x 10 in leaves,

Symbols: `Book`.

## [books/04_graduum/illustrated/build.py](../sources/codex-intervallorum/books/04_graduum/illustrated/build.py)

**book-integration**. Clavicula Graduum, illustrated edition: the same manuscript and pagination as build_book.py,

Symbols: `paper`, `render`, `IllBook`.

## [books/04_graduum/illustrated/plates.py](../sources/codex-intervallorum/books/04_graduum/illustrated/plates.py)

**book-integration**. Clavicula Graduum: the illustrated plates.

Symbols: `material_call`, `R`, `load`, `record`, `foot_box`, `furniture_skip`, `Leaf`, `carrier_under`, `carrier_roundtrip`, `capture_plate`, `run_build`, `plate_i`, `plate_ii`, `plate_iii`, `plate_iv`, `plate_v`, `plate_vi`, `plate_vii`, `plate_viii`, `proof_doc`, `proof_skip`, `plate_ix`, `plate_x`, `plate_xi`, `plate_xii`, `main`.

## [books/04_graduum/manuscript/make_book.py](../sources/codex-intervallorum/books/04_graduum/manuscript/make_book.py)

**book-integration**. Clavicula Graduum - manuscript skeleton (DRAFT). Writes book.json and reading-edition.md.

Symbols: `chapter`, `build`.

## [books/04_graduum/plates/i-native/tabula_i.py](../sources/codex-intervallorum/books/04_graduum/plates/i-native/tabula_i.py)

**visual-technique**. Clavicula Graduum - Tabula I - The Nine and the Seven (native vector plate).

Symbols: `station_points`, `main`.

## [books/04_graduum/plates/ii-native/tabula_ii.py](../sources/codex-intervallorum/books/04_graduum/plates/ii-native/tabula_ii.py)

**visual-technique**. Clavicula Graduum - Tabula II - The Two Watchmakers (native vector plate).

Symbols: `ten`, `timeline`, `hora`, `tempus`, `returning_trace`, `main`.

## [books/04_graduum/plates/iii-native/tabula_iii.py](../sources/codex-intervallorum/books/04_graduum/plates/iii-native/tabula_iii.py)

**visual-technique**. Clavicula Graduum - Tabula III - The Cut (native vector plate).

Symbols: `Shift`, `measurer`, `streams`, `table`, `frame_and_seam`, `main`.

## [books/04_graduum/plates/iv-native/tabula_iv.py](../sources/codex-intervallorum/books/04_graduum/plates/iv-native/tabula_iv.py)

**visual-technique**. Clavicula Graduum - Tabula IV - The Observer's Ladder (native vector plate).

Symbols: `intervals`, `bar_heights`, `panel`, `main`.

## [books/04_graduum/plates/v-native/figure.py](../sources/codex-intervallorum/books/04_graduum/plates/v-native/figure.py)

**visual-technique**. The Keeper: a hooded, hunched figure in right profile, built from control

Symbols: `edge_fn`, `robe_outline`, `head_local`, `hood_outline`, `sleeve_path`, `ribbon`, `flow_lines`, `clip_polyline`, `draw_keeper`.

## [books/04_graduum/plates/v-native/tabula_v.py](../sources/codex-intervallorum/books/04_graduum/plates/v-native/tabula_v.py)

**visual-technique**. Clavicula Graduum - Tabula V, The Dial of Seven Keepers. Native vector edition.

Symbols: `label`, `draw_dial`, `draw_ground`, `draw_cord`, `draw_furniture`, `draw_caption`, `build`.

## [books/04_graduum/plates/v-native/validate.py](../sources/codex-intervallorum/books/04_graduum/plates/v-native/validate.py)

**validation**. Structure, cipher and plot checks for the Tabula V package. Run after tabula_v.py.

Symbols: `paths`, `pts_of`, `check_structure`, `main`.

## [books/04_graduum/plates/vi-native/tabula_vi.py](../sources/codex-intervallorum/books/04_graduum/plates/vi-native/tabula_vi.py)

**visual-technique**. Clavicula Graduum - Tabula VI - The Feudal Register (native vector plate).

Symbols: `label`, `carve`, `wall_segments`, `draw_maze`, `solve`, `draw_flow`, `draw_glyphs`, `drop`, `tile`, `draw_landings`, `draw_twin_register`, `draw_furniture`, `write_shifted`, `draw_caption`, `build`.

## [books/04_graduum/plates/vi-native/validate.py](../sources/codex-intervallorum/books/04_graduum/plates/vi-native/validate.py)

**validation**. Structure, cipher and plot checks for the Tabula VI package. Run after tabula_vi.py.

Symbols: `paths`, `pts_of`, `check_structure`, `main`.

## [books/04_graduum/plates/vii-native/figures.py](../sources/codex-intervallorum/books/04_graduum/plates/vii-native/figures.py)

**visual-technique**. Small figures for the building plates: a robed office-holder with any number of

Symbols: `_flow`, `hand_up`, `robed_figure`.

## [books/04_graduum/plates/vii-native/tabula_vii.py](../sources/codex-intervallorum/books/04_graduum/plates/vii-native/tabula_vii.py)

**visual-technique**. Clavicula Graduum - Tabula VII, The Cord Without a Mount. Native vector edition.

Symbols: `label`, `litany_table`, `encode_litany`, `floor_y`, `hatch_band`, `draw_building`, `draw_top_floor`, `draw_cord`, `draw_floor_of_hands`, `draw_specimens`, `draw_furniture`, `draw_scale`, `build`.

## [books/04_graduum/plates/vii-native/validate.py](../sources/codex-intervallorum/books/04_graduum/plates/vii-native/validate.py)

**validation**. Structure, cipher and plot checks for the Tabula VII package. Run after tabula_vii.py.

Symbols: `paths`, `pts_of`, `check_structure`, `main`.

## [books/04_graduum/plates/viii-native/apparatus.py](../sources/codex-intervallorum/books/04_graduum/plates/viii-native/apparatus.py)

**visual-technique**. The handoff demons of Book III drawn as apparatus (the series rule: offices are persons

Symbols: `_box`, `_tripod`, `_hatch`, `repetiel`, `culpax`, `calmor`, `instantor`, `choraz`, `viridon`, `posthum`, `exceptor`, `velaroth`, `quarteroth`, `severion`, `redacth`, `viridon_cracked`.

## [books/04_graduum/plates/viii-native/tabula_viii.py](../sources/codex-intervallorum/books/04_graduum/plates/viii-native/tabula_viii.py)

**visual-technique**. Clavicula Graduum - Tabula VIII - The Council of the Loudest (native vector plate).

Symbols: `label`, `draw_tiers`, `draw_voices`, `draw_glyphs`, `draw_flows`, `draw_decision`, `draw_furniture`, `write_shifted`, `draw_caption`, `draw_scale`, `build`.

## [books/04_graduum/plates/viii-native/validate.py](../sources/codex-intervallorum/books/04_graduum/plates/viii-native/validate.py)

**validation**. Structure, cipher and plot checks for the Tabula VIII package. Run after tabula_viii.py.

Symbols: `paths`, `pts_of`, `check_structure`, `main`.

## [books/04_graduum/proofs/ix-gpt/build.py](../sources/codex-intervallorum/books/04_graduum/proofs/ix-gpt/build.py)

**visual-technique**. Native stroke-only A4 plate and tagged reading/key leaves. Run python build.py.

Symbols: `f`, `Drawing`, `plate`, `key_leaf`, `make_reading`, `main`.

## [books/04_graduum/proofs/ix-gpt/codec.py](../sources/codex-intervallorum/books/04_graduum/proofs/ix-gpt/codec.py)

**visual-technique**. Graduum IX: shift Matricis base signs modulo twelve; preserve tally and spaces.

Symbols: `normalize`, `encode`, `decode`, `codes`, `validate`.

## [books/04_graduum/proofs/ix-gpt/lettering.py](../sources/codex-intervallorum/books/04_graduum/proofs/ix-gpt/lettering.py)

**visual-technique**. EMS Nixish centerline serif, calibrated by measured H rather than font metadata.

Symbols: `PolyPen`, `SerifHand`.

## [books/04_graduum/proofs/ix-gpt/vendor/core.py](../sources/codex-intervallorum/books/04_graduum/proofs/ix-gpt/vendor/core.py)

**visual-technique**. Core drawing kit for the Clavicula Matricis plates.

Symbols: `f`, `num`, `pair`, `Doc`, `lerp`, `dist`, `rot`, `arc_pts`, `spiral_pts`, `curl_pts`, `resample`, `Wobble`, `clip_lines`, `hatch_lines`, `lattice`, `tri_pts`, `vesica`, `offset_line`, `path_len`, `point_at`, `bezier`, `catmull`, `merge`.

## [books/04_graduum/proofs/ix-gpt/vendor/tx.py](../sources/codex-intervallorum/books/04_graduum/proofs/ix-gpt/vendor/tx.py)

**visual-technique**. The twelve-sign transcription hand (Astra's key): base mark I–XII plus a tally of 1–3 strokes.

Symbols: `normalize`, `encode`, `decode`, `codes`, `mark`, `tally`, `token_width`, `write`, `width`.

## [books/04_graduum/proofs/x-xi-v-gpt/build.py](../sources/codex-intervallorum/books/04_graduum/proofs/x-xi-v-gpt/build.py)

**visual-technique**. Next production batch: X, XI, V. Native paths, two inks, exact second texts.

Symbols: `pts`, `arc`, `bez`, `base`, `blank`, `finish`, `prayer`, `litany_leaf`, `lifted_pen`, `keeper_dial`, `readings`, `main`.

## [books/04_graduum/proofs/x-xi-v-gpt/ciphers.py](../sources/codex-intervallorum/books/04_graduum/proofs/x-xi-v-gpt/ciphers.py)

**visual-technique**. Graduum's explicitly new office litany and ordered-path carrier.

Symbols: `prayer_encode`, `prayer_decode`, `ordered_decode`, `validate`.

## [books/04_graduum/proofs/x-xi-v-gpt/ix_codec.py](../sources/codex-intervallorum/books/04_graduum/proofs/x-xi-v-gpt/ix_codec.py)

**visual-technique**. Graduum IX: shift Matricis base signs modulo twelve; preserve tally and spaces.

Symbols: `normalize`, `encode`, `decode`, `codes`, `validate`.

## [books/04_graduum/proofs/x-xi-v-gpt/lettering.py](../sources/codex-intervallorum/books/04_graduum/proofs/x-xi-v-gpt/lettering.py)

**visual-technique**. EMS Nixish centerline serif, calibrated by measured H rather than font metadata.

Symbols: `PolyPen`, `SerifHand`.

## [books/04_graduum/proofs/x-xi-v-gpt/sheet.py](../sources/codex-intervallorum/books/04_graduum/proofs/x-xi-v-gpt/sheet.py)

**visual-technique**. Native stroke-only A4 plate and tagged reading/key leaves. Run python build.py.

Symbols: `f`, `Drawing`.

## [books/04_graduum/proofs/x-xi-v-gpt/vendor/core.py](../sources/codex-intervallorum/books/04_graduum/proofs/x-xi-v-gpt/vendor/core.py)

**visual-technique**. Core drawing kit for the Clavicula Matricis plates.

Symbols: `f`, `num`, `pair`, `Doc`, `lerp`, `dist`, `rot`, `arc_pts`, `spiral_pts`, `curl_pts`, `resample`, `Wobble`, `clip_lines`, `hatch_lines`, `lattice`, `tri_pts`, `vesica`, `offset_line`, `path_len`, `point_at`, `bezier`, `catmull`, `merge`.

## [books/04_graduum/proofs/x-xi-v-gpt/vendor/tx.py](../sources/codex-intervallorum/books/04_graduum/proofs/x-xi-v-gpt/vendor/tx.py)

**visual-technique**. The twelve-sign transcription hand (Astra's key): base mark I–XII plus a tally of 1–3 strokes.

Symbols: `normalize`, `encode`, `decode`, `codes`, `mark`, `tally`, `token_width`, `write`, `width`.

## [books/04_graduum/reading/build.py](../sources/codex-intervallorum/books/04_graduum/reading/build.py)

**book-integration**. The serif reading edition of the Graduum plates: every native plate rebuilt with

Symbols: `main`.

## [books/05_notoria/fields/physarum.py](../sources/codex-intervallorum/books/05_notoria/fields/physarum.py)

**visual-technique**. Deterministic trace fields for the Notoria: a multi-agent model after Jones (2010),

Symbols: `code_hash`, `spec_with`, `_diffuse`, `run`, `output_hash`, `manifest`, `manifest_id`, `regenerate_and_check`.

## [books/05_notoria/manuscript/check_math.py](../sources/codex-intervallorum/books/05_notoria/manuscript/check_math.py)

**validation**. Independent exact checks for the manuscript's finite counts and model consequences.

Symbols: `check`.

## [books/05_notoria/manuscript/make_book.py](../sources/codex-intervallorum/books/05_notoria/manuscript/make_book.py)

**book-integration**. Build the developmental Notoria: canonical Markdown, the five computed notae from the serif

Symbols: `leaves`, `TurnedHand`, `ring_text`, `ornament`, `rich`, `register`, `build`, `validate`.

## [books/05_notoria/plates/notae.py](../sources/codex-intervallorum/books/05_notoria/plates/notae.py)

**visual-technique**. Ars Notoria Stigmatum - the five notae as native plotter plates.

Symbols: `Nota`, `Field`, `draw_field`, `ring_text`, `standing_dots`, `legend`, `spec_legend`, `disc_frame`, `scatter_stars`, `small_disc`, `run_for`, `hidden_for`, `write_manifest`, `nota_i`, `nota_ii`, `nota_iii`, `nota_iv`, `nota_v`, `build`.

## [books/05_notoria/plates/validate.py](../sources/codex-intervallorum/books/05_notoria/plates/validate.py)

**validation**. Validate the Notoria plates: the shared structural checks (two layers, two inks, no fills,

Symbols: `validate_dir`, `main`.

## [books/05_notoria/reading/build.py](../sources/codex-intervallorum/books/05_notoria/reading/build.py)

**book-integration**. The serif reading edition of the Notoria plates: the five notae rebuilt with

Symbols: `main`.

## [books/06_disputationes/build.py](../sources/codex-intervallorum/books/06_disputationes/build.py)

**book-integration**. De Potestate et Accusatione: reading edition of Book VI; no network at build time.

Symbols: `sha`, `norm`, `paragraphs`, `parse`, `source_blocks`, `references`, `plates_meta`, `fonts`, `markup`, `Book`, `build`, `merge_with_outline`.

## [books/06_disputationes/plates/reading.py](../sources/codex-intervallorum/books/06_disputationes/plates/reading.py)

**visual-technique**. The serif reading edition of the nine plates for the bound book.

Symbols: `sha`, `main`.

## [books/06_disputationes/plates/tabulae.py](../sources/codex-intervallorum/books/06_disputationes/plates/tabulae.py)

**visual-technique**. De Potestate et Accusatione: the nine plates, native and stroke-only.

Symbols: `legend`, `boxed`, `clear_runs`, `text_box`, `dashed`, `open_ring`, `tally`, `bracket`, `finish`, `tabula_i`, `tabula_ii`, `tabula_iii`, `tabula_viii`, `gate_rows`, `tabula_iv`, `tabula_v`, `tabula_vi`, `tally_width`, `tabula_vii`, `counted_text`, `sentences`, `tabula_ix`, `main`.

## [books/06_disputationes/plates/vendor/refusal.py](../sources/codex-intervallorum/books/06_disputationes/plates/vendor/refusal.py)

**model-support**. A deliberately small, deterministic model of a refusal, not a prediction about people.

Symbols: `Station`, `Outcome`, `_check`, `evaluate`, `smallest_opening_refusal`, `specimen_cases`.

## [books/06_disputationes/plates/viplate.py](../sources/codex-intervallorum/books/06_disputationes/plates/viplate.py)

**visual-technique**. Plate furniture for Book VI, De Potestate et Accusatione.

Symbols: `free`, `runs`, `VIPlate`.

## [books/06_disputationes/validate.py](../sources/codex-intervallorum/books/06_disputationes/validate.py)

**validation**. Validate the reading edition of Book VI: inputs, trim, text coverage in order,

Symbols: `require`, `validate`.

## [books/06_tarot/book/make_book.py](../sources/codex-intervallorum/books/06_tarot/book/make_book.py)

**book-integration**. Tarot of Intervals: a reading edition in book form. Each card on a recto, its commentary on the

Symbols: `fonts`, `PageHand`, `flourish`, `margin_threads`, `cipher_strip`, `wrap`, `para`, `labelled`, `paper`, `folio`, `verso`, `light_image`, `recto`, `title_pages`, `load_cards`, `validate_initial_sources`, `main`.

## [books/06_tarot/book/validate_book.py](../sources/codex-intervallorum/books/06_tarot/book/validate_book.py)

**validation**. Validate the initial 52-illustration reading mockup, independently of its build log.

Symbols: `require`, `normalized`, `validate`, `previews`.

## [books/07_septimus/build.py](../sources/codex-intervallorum/books/07_septimus/build.py)

**book-integration**. Portable reading editions for the two parts of Septimus; no network at build time.

Symbols: `sha`, `plain`, `norm`, `paragraphs`, `clavis_sections`, `vinculis_sections`, `all_source_blocks`, `fonts`, `markup`, `glyph`, `seal`, `Book`, `gathering`, `build`.

## [books/07_septimus/clausa/build.py](../sources/codex-intervallorum/books/07_septimus/clausa/build.py)

**book-integration**. Reading edition of the Nota Clausa: Tabula, Regula and seven plates at 7 x 10 in.

Symbols: `fonts`, `inline`, `Book`, `main`.

## [books/07_septimus/clausa/validate.py](../sources/codex-intervallorum/books/07_septimus/clausa/validate.py)

**validation**. Public checks for the Nota Clausa. Needs no key and reads nothing.

Symbols: `inside`, `marks`, `digests`, `main`.

## [books/07_septimus/semiphoras/semiphoras.py](../sources/codex-intervallorum/books/07_septimus/semiphoras/semiphoras.py)

**visual-technique**. Semiphoras Vinculorum: seventy-two names from three sentences.

Symbols: `letters`, `names`, `recover`, `records`, `manifest`, `main`.

## [books/07_septimus/tests/test_semiphoras.py](../sources/codex-intervallorum/books/07_septimus/tests/test_semiphoras.py)

**validation**. 

Symbols: `SemiphorasTests`.

## [books/07_septimus/validate.py](../sources/codex-intervallorum/books/07_septimus/validate.py)

**validation**. Validate coverage and material boundaries in the generated reading editions.

Symbols: `validate`.

## [common/geometry/core.py](../sources/codex-intervallorum/common/geometry/core.py)

**visual-technique**. Core drawing kit for the Clavicula Matricis plates.

Symbols: `f`, `num`, `pair`, `Doc`, `lerp`, `dist`, `rot`, `arc_pts`, `spiral_pts`, `curl_pts`, `resample`, `Wobble`, `clip_lines`, `hatch_lines`, `lattice`, `tri_pts`, `vesica`, `offset_line`, `path_len`, `point_at`, `bezier`, `catmull`, `merge`.

## [common/geometry/marks.py](../sources/codex-intervallorum/common/geometry/marks.py)

**visual-technique**. Hands (ink / cornmeal grain / plotter pen), vèvè-grammar ornament, and the

Symbols: `Hand`, `asterisk`, `curl`, `dotted`, `fringe`, `arrowhead`, `lattice_fill`, `leaf`, `band_x`, `sig_standing`, `sig_candidate`, `sig_gate`, `sig_authority`, `sig_mark`, `sig_ground`, `sig_break`, `sig_regulation`, `sig_bottleneck`, `sig_branch`, `sig_reflexive`, `sig_invariant`, `sig_boundary`, `sig_substrate_small`, `sig_pointer`, `XHand`, `write_ring`, `ring_x`.

## [common/geometry/tx.py](../sources/codex-intervallorum/common/geometry/tx.py)

**visual-technique**. The twelve-sign transcription hand (Astra's key): base mark I–XII plus a tally of 1–3 strokes.

Symbols: `normalize`, `encode`, `decode`, `codes`, `mark`, `tally`, `token_width`, `write`, `width`.

## [common/illum/figure_growth.py](../sources/codex-intervallorum/common/illum/figure_growth.py)

**visual-technique**. Progressive image-guided Physarum masks for the illustrated figures.

Symbols: `smooth`, `resize`, `blur`, `subject`, `configure`, `protection`, `simulate`, `masks`, `edge_masks`, `contours`, `render_material`, `appearance`, `cornmeal_path`, `flowing_rule`.

## [common/illum/furniture.py](../sources/codex-intervallorum/common/illum/furniture.py)

**visual-technique**. Plate furniture for the illustrated edition, in Book I's vocabulary, drawn straight onto a

Symbols: `rgb`, `fonts`, `Hand`, `YDown`, `ground`, `specks`, `rope_frame`, `ruled_frame`, `register`, `stars`, `orn_rule`, `wave_rule`, `glyph_band`, `hand_note`, `wrap`, `spaced`, `ground_line`, `wash`, `blot`, `mark_seal`.

## [common/illum/platekit.py](../sources/codex-intervallorum/common/illum/platekit.py)

**visual-technique**. Bringing a native stroke plate into the illustrated edition.

Symbols: `_filled_dot`, `filled_dots`, `Map`, `MapHand`, `AnisoHand`, `_subpaths`, `bbox_of`, `draw_doc`, `inside`, `tmpdir`, `compact`.

## [common/illum/raster.py](../sources/codex-intervallorum/common/illum/raster.py)

**visual-technique**. Raster figures for the illustrated edition.

Symbols: `_ground`, `_smooth`, `key`, `silhouette`, `figure_box`, `place`, `place_fit_figure`, `to_page`, `figure_extent`, `red_point`, `mask_cells`, `Slot`.

## [common/illum/tests/test_figure_growth.py](../sources/codex-intervallorum/common/illum/tests/test_figure_growth.py)

**validation**. Guard the reading-order, protected-pixel and carrier boundaries.

Symbols: `FigureGrowthTests`.

## [common/plot/bookpage.py](../sources/codex-intervallorum/common/plot/bookpage.py)

**visual-technique**. Shared page engine for the series' ReportLab books: 7 x 10 in, the series ground, IM Fell

Symbols: `fonts`, `PageHand`, `paper`, `wrap`, `flow_rule`.

## [common/plot/ornament.py](../sources/codex-intervallorum/common/plot/ornament.py)

**visual-technique**. The fourth carrier: a biliteral cipher after Bacon (De augmentis, 1623), five marks

Symbols: `codes`, `bits`, `decode`, `b_fraction`, `scale_positions`, `scale_frame`.

## [common/plot/plate.py](../sources/codex-intervallorum/common/plot/plate.py)

**visual-technique**. Shared furniture for the Graduum plates: frame, title block, reserved blank, caption strip in

Symbols: `lettering`, `Plate`, `png_preview`, `_paths`, `_pts`, `_structure`, `validate`.

## [common/plot/plotkit.py](../sources/codex-intervallorum/common/plot/plotkit.py)

**visual-technique**. Stroke-only plate kit for the plotter editions: a plotter Hand over the Matricis

Symbols: `fmt`, `PlotDoc`, `PlotHand`, `SVGFont`, `OutlineFont`, `_FlattenPen`, `vertical_fill`, `voronoi_net`, `roman_year_angles`.

## [common/plot/svgimport.py](../sources/codex-intervallorum/common/plot/svgimport.py)

**visual-technique**. Import stroke geometry from the books' own SVG plates (M / l / L / a / A / Z paths)

Symbols: `_arc`, `parse_path`, `strokes_from_svg`, `place`.

## [docs/objections/tests/test_validate.py](../sources/codex-intervallorum/docs/objections/tests/test_validate.py)

**validation**. Tests for the objections register check.

Symbols: `problems`, `FormTests`, `HistoryTests`, `RegisterTests`.

## [docs/objections/validate.py](../sources/codex-intervallorum/docs/objections/validate.py)

**validation**. Check the objections register: entry form, dispositions, and append-only history.

Symbols: `_is_date`, `_split`, `parse`, `check`, `status`, `_entry_lines`, `append_only`, `main`.

## [scripts/build.py](../sources/codex-intervallorum/scripts/build.py)

**book-integration**. Build Codex Intervallorum from checked-in source inputs.

Symbols: `run`, `tests`, `main`.

## [scripts/check_project.py](../sources/codex-intervallorum/scripts/check_project.py)

**validation**. Check the migration's source inputs, local documentation links, and bound title.

Symbols: `main`.

## [scripts/proof_figure_growth.py](../sources/codex-intervallorum/scripts/proof_figure_growth.py)

**book-integration**. Build reading-size, before/after figure and Graduum material proofs.

Symbols: `main`.
