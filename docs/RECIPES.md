# Combining the techniques

These are construction recipes. The small sampler and native Notoria command are runnable examples; the combinations below describe how to compose the existing functions, not new implementations already supplied by this reorganization.

| Desired result | Construction order | Controls that matter | Output |
| --- | --- | --- | --- |
| One drawing in ink and cornmeal | Build the same paths; render with `marks.Hand` in ink and grain modes | Same seed, wobble, density, perpendicular spread, grain sizes | SVG for layout; adapt grains to coils for a physical pen |
| Figure dissolving into a sketch | Key source; compute image food; simulate; create protected mask; render material; composite replacement | Anchor guards, mask amount, actual display width, grain amount | Raster at placed size, then PDF composition |
| Grain confined to the figure’s edge | Use the same setup with `edge_masks`; preserve its solid interior and protected cores | Physical fringe width, feathering, mask strength | Raster/PDF; see the selected contour-grain notes |
| Robe, smoke or cloth with coherent flow | Establish a silhouette; generate `flow_lines`; clip against the shape; vary material without changing the scaffold | Shared wander, line count, spacing, clipping and outline hierarchy | SVG; stroke-only variant through `PlotHand` |
| An encoded mechanical plate | Construct apparatus; reserve its text and carrier; encode; draw; validate round trips | Carrier order, ink conventions, pen width, reserved space | Two-layer SVG and separate ink passes |
| Architectural illustration with cultures in the shade | Start with Photophobic’s scene/light bake; run its surface cultures and stroke cutting | World-space inoculation, light penalty, vein coverage and hatch compensation | Existing study SVG/proof pipeline |
| Industrial form converted into a primitive network | Produce a clear light/mask pass; use the statue study’s Trail First/primitive code as the starting point | Sampling cell size, contrast food, primitive count, support layer | SVG; requires adapting that study’s input loading |
| A phrase-derived prime seal | `aq.aq` the phrase; `xenotation.encode` the value; draw with `xenotation.draw` through `marks.Hand` or `PlotHand`; check `decode` | Phrase normalization, factor order, capsule or parens, size and weight | SVG; `PlotHand` layer for a plot |
| Vellum without texture crossing text | Compose PDF; inspect clear paper; optionally add scribal marks; run vellum with light profile | Stable page identity, content protection, seed and profile | PDF with retained text, vectors and images |
| A landscape plate behind a Codex text page | Driftless Plates at the `codex` trim with `--zone codex`; Lighten keeps the drawing in the tint pen, Fade out clears it | Zone treatment, ink strength, density, frame | SVG at the 7 × 10 in trim, or 300 dpi PNG |

## Know which units and paths you are using

| Layer | Coordinates/material | Reuse boundary |
| --- | --- | --- |
| `common/geometry` | SVG-like drawing coordinates; page size supplied by caller | Paths, mark vocabulary and `Hand` |
| `common/plot` | Millimetres; y down; separate pen layers | Native stroke geometry and centreline lettering |
| `common/illum` | ReportLab points; y up; raster pixels for source masks | Use `platekit.Map` and the existing placement helpers |
| `binding` finishing | PDF page coordinates and rendered protection masks | Preserve the source document and inspection log |
| `lib/numerics` glyphs | Unitless layout scaled by `size` into the calling hand's units | Draws through `marks.Hand` or `PlotHand`; `to_svg` writes millimetres |
| `studies/driftless-plates` | Millimetres; y down; four pen layers | Its own JavaScript engine; Codex sizes read from the snapshot and checked by its `test.js` |

## Useful controls already in the book

| Control | Effect |
| --- | --- |
| `GRIMOIRE_FIGURE_GROWTH=0` | Disables progressive figure-growth treatment and its associated additions |
| `GRIMOIRE_EDGE_GRAIN=0` | Disables the selected contour-fringe/footer additions while retaining the preceding treatment |
| `GRADUUM_READING=1` | Selects serif outline lettering for compatible reading-edition plate builds |
| `vellum.py INPUT.pdf OUTPUT.pdf --profile light --seed 17` | Uses the lighter paper-texture profile with a reproducible seed |

Environment controls apply to the original book scripts; they are not switches on every study. Illustrated edition builds require raster assets omitted from this collection. The [source index](SOURCE_INDEX.md) identifies the integration modules to inspect before adapting a complete page.

## Keep these distinctions visible

The Notoria field records actual agent trajectories. Figure-growth hatches are integrated rendering curves. Photophobic’s transported surface veins and Scanned Statue’s Trail First sampler each use their own algorithms. A similar flowing appearance does not make them interchangeable models.

A drawing can contain both decoration and encoded geometry. Keep masks, clipping, path simplification and sorting away from carrier marks unless the decoder is checked again. A xenotation glyph is read by containment and adjacency, so sorting its paths is safe; clipping or masking it is not. Use the full plot export for a physical drawing; illustrated PDF furniture includes fills, transparency and blend modes.

## Implemented process-art studies

The [process-art guide](../techniques/12-process-art/README.md) adds runnable eroded catchments, folded/faulted beds, chemically biased vein growth, and CSV-driven recurrence art. Their raw fields and millimetre strokes are separate outputs. `Plate.draw(hand)` supplies the existing ink/cornmeal Hand route; the SVG is compatible with `svgimport.strokes_from_svg()`. Further combinations with image-fed Physarum, numerics seals and architectural surfaces are described there, with implemented adapters distinguished from proposed integrations.

