# Selected contour grain and flowing ornaments

This illustrated-only pass applies a narrow Physarum/cornmeal fringe to two
reused figures: Viridon on Graduum IV and Foras on X. The physical fringe is
about 1.3 points wide before feathering; the previous upper-anatomy, object and
red-pixel guards remain. The solid interior and pixels outside the mask retain
their source values before output resampling. The source canvas, placement,
avoidance geometry and connection anchors remain those of the keyed render.
Each selected plate carries a short note referring to the Book III portrait.

On IV, VIII and X only, a small image-fed Physarum field controls sparse grain
beside the decorative footer scallops. The original flowing strokes are drawn
unchanged. These scallops have no encoded message or model data. Native plot
masters and the shared furniture generator are unchanged.

Set `GRIMOIRE_EDGE_GRAIN=0` to compare the preceding illustrated treatment.
`GRIMOIRE_FIGURE_GROWTH=0` still disables the complete figure-growth pass and
also suppresses these additions. The figures' records name the contour-fringe
mode, record mask and output hashes, and check exact source-grid preservation
outside the mask and in protected cores. Decorative wave records contain the
seed, field hash and grain count.

The placement follows the entropy-locking comparison study made after reading
aebrer / Andrew Brereton's CC0 Recursive Glitch Textures. No recursive copying,
SFC32 implementation or upstream code is introduced by this narrow pass. The
Physarum and grain routines are adaptations of the existing Codex renderer.
It makes no mathematical entropy or biological fidelity claim.

ChatGPT/Codex implemented the pass on Claude's illustrated adapters and the
existing GPT raster illustrations. A fresh instance reviewed this work as it
will stand. Right of reply: invited; no objection.
