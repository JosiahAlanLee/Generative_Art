# Progressive figures and cornmeal

The illustrated figure compositor now has a separate appearance pass. It begins
with the unchanged first Book III figure and advances by visible placement to
0.38 at the end of that book. Graduum continues from 0.43 to 0.86 in table order,
including its two part-opening vignettes. The earlier opening and its figures
retain their current appearance. Native Notoria computations are unchanged.

The mask controls replacement, not an additional full-page overlay. One
image-fed population uses three sensors, deposition, bounded movement, diffusion
and evaporation. The source supplies food and local direction. A fixed field
and monotone spatial front increasingly assign the lower figure to a flowing
stroke and grain renderer. The curves are render paths, not agent trajectories.
This decorative model is separate from the reproducible Book V field model.
It is not a new biological or institutional claim.

The renderer retains the source silhouette, a broad upper-anatomy zone, explicit
object guards and red-pixel guards. Feathered shoulders keep protected details
connected to the rest of the figure. Protected cores are copied unchanged from
the keyed source before output resampling and the optional night-ground palette conversion. Keying,
figure extents, scale, crops, mirroring, avoidance shapes and connection anchors
continue to come from the original source, never from an eroded appearance.
Sources and source prompts are retained.

Stroke and grain size adapt to the actual printed placement. A tiny office
figure receives coarser marks rather than hairlines that disappear at page size.
Derived images are capped at 360 dpi at their actual placement, avoiding a full
native-size bitmap for every tiny office figure. Original artwork is retained.

The same ordered samples change from continuous stroke to interrupted stroke
to displaced warm grain. On Graduum VI and VIII, a dark board and Screen
compositing make the grain pale, matching the native apparatus. On IV, VI, VII
and VIII, explicit construction calls give selected bar hatching, landing
undersides, wall/slab/desk hatching and tier undersides a granular shoulder.
Their supporting centerlines remain continuous. Text, semantic ticks, maze
nodes, ground blades, reserved areas and the litany are never selected by a
generic path-length or image-noise filter.

## Reproduction and inspection

Run `python scripts/build.py --edition illustrated`. This writes the updated
omnibus, an eight-page `Codex_Intervallorum_Figure_Growth_Proof.pdf`, and an
inspection record under `binding/out/illustrated`. The proof places genuine
untreated leaves and treated leaves at the same physical size. It checks
typeset text and retained carrier/decode records for equality. The existing
Graduum round trips continue to run.

`python -m unittest discover -s common/illum/tests -v` checks deterministic
fields, monotone masks, protected pixels, the exact untreated start, and the
boundary between explicitly selected hatching and text/carriers. Each figure's
record includes its seed, source/keyed/code/field/mask/output hashes, mask
control, protected-pixel check and mark counts. The appearance cache is under
`build/figure-growth`, which is ignored.

Set `GRIMOIRE_FIGURE_GROWTH=0` to build the earlier appearance for comparison.
The new dark grounds and granular structural shoulders are disabled with it.
No plot master or encoded text is restyled by this change.

This implements the first direction from the 19 October generative study:
one scaffold, several materials. Rival-contact braids, reaction–diffusion and
shared-substrate experiments remain separate studies.

Authorship: ChatGPT/Codex implemented this pass, using Claude's illustrated
adapters and the existing GPT figure renders. A fresh instance reviewed the
result under the repository's right-of-reply procedure; no objection to this
artwork treatment or its attribution.
