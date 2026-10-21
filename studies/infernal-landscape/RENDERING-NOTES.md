# Rendering notes for the second pass

For whoever edits `model.py`, `engrave.py` and `checks.py` in
`studies/workshop-interiors`. The four briefs (`*.txt`, with `00-COMMON.txt`)
say what each plate must show; this says what the engraving stage has to
change to deliver it. The nine vendored bodies in `vendor/claude_hatching.py`
and `vendor/raycore.py` stay unchanged throughout; everything below is
caller-side. `light()`, `visible()`, the edge loop, the gains, the `used`
raster and the layer table are all in `engrave.py` and are open.

Reference point: the delivered `extraction-of-the-hand.svg` regenerates
byte-identically from its `scene.json` with the committed `engrave.py`, so the
baseline is reproducible and every change below can be diffed against it.

## 1. Engrave at printed size

Add to each plate's record:

```
PRINT_WIDTH_MM = {maintained-workshop: 156, empty-cabinet: 152,
                  extraction-of-the-hand: 95, office-without-a-seal: 95}
PX_PER_MM = 20
```

Master resolution = printed size × 20 (95 mm → 1900 px wide; 156 mm → 3120).
Every width and gap is then declared in mm and converted once:

```
mm = lambda v: v * PX_PER_MM
```

The 180 mm nominal master is withdrawn. The Book III plates currently print at
0.53× their master, which puts the 0.78 px hatch at 0.04 mm and the 2.1 px
gap at 0.11 mm on the page.

`FAMILIES` carries `delta` in world units; the screen spacing comes through
the Jacobian, so when `focal_px` changes with the new resolution, re-derive
delta so that the on-page gap at the subject's depth is the brief's gap:

```
delta ≈ MIN_GAP_px * z_subject / focal_px        # per plate, per family
```

Set the family `width` fields to the width that is actually written. The
first pass budgets 0.72/0.60 and writes 0.78, so the allocator plans for less
ink than it emits.

## 2. Tone budget

Current: `C_MAX .50 (.44 office), GAMMA 1.45, MIN_GAP 2.10, C_SPLIT .17`.
Measured result in 4 mm cells: darkest cell 0.36, 90th percentile 0.24, walls
≤ 0.06. The `light()` model (sun, shadow rays, AO, depth ambient) is fine; the
budget then caps it.

Second pass:

```
CH.C_MAX   = .82
CH.GAMMA   = 1.05          # 1.45 pushed every midtone toward paper
CH.C_SPLIT = .20
CH.MIN_GAP = mm(0.22)      # 4.4 px
hatch pen  = mm(0.10)      # 2.0 px, and FAMILIES widths = the same number
```

Each family is capped at `width / MIN_GAP` ≈ 0.45, so two families reach
~0.80 in a pocket, which is what the briefs' tone plans ask for.

### Deep pockets

The briefs want 0.70–0.80 in named pockets (under the gallery, inside the
cabinet panels, under the bench, the alcove corners). Two families at MIN_GAP
only just reach it, and `allocate_hatch` is written for two families
(`fam == 0` / else). Do not touch it. Run a second caller-side pass instead:

```
st2 = CH.Strokes()
CH.FAMILIES = ((.64 + .85, .030, w), (-.72 + .85, .040, w))   # rotated ~50°
for faces with mean shade d > 0.60: CH.hatch_on_face(st2, ...)
st2.finish()
used2 = used + raster of the first pass's kept hatch (same blur, same scale)
keep2 = CH.allocate_hatch(st2, shade2, used2, seen2)
```

with `shade2 = max(0, d − 0.60) / 0.40` so the second pass only supplies the
top of the range. Write both passes into layer 01.

## 3. Lighting and gains

- `SUN = unit([-8,-3,12])` has about 55° elevation; lower it to ~35° so
  vertical faces split into a lit side and a shadow side. Direction per plate
  from the brief (Workshop and Hand from the left, Office from upper left,
  Cabinet from the window side).
- The Workshop is lit from the stove. `light()` is caller code; add a local
  emitter term with its own shadow ray:

  ```
  to_l = L - P; dist = |to_l|; cos_l = max(0, n·to_l/dist)
  local = k_l * cos_l / (1 + (dist/r0)**2) * (0.05 if occluded else 1)
  out = min(1, max(.06, ambient*(1-.55*ao) + .8*direct + local))
  ```

  with `L` at the stove mouth, `r0` ≈ 2.5 world units, `k_l` ≈ 0.9.
- Gains: the wall cap of 0.30 is what makes walls a flat tint. Use 0.50, and
  for the Workshop a vignette so the night sits in the corners:

  ```
  gain_wall = 0.50 * (0.55 + 0.9 * r**2)     # r = screen distance from the
                                              # plate's focal point, 0..1
  ```

  Bookcase backing 0.60. Apparatus stays at 1.0.

## 4. Edge weights

Replace the single `width=.70 if backdrop else 1.25 if pen==0 else 1.02`:

```
zc    = max(NEAR, (V[[a,b]].mean(0) - EYE) @ FWD)
depth = clip(Z_REF / zc, 0.80, 1.30)          # Z_REF = subject depth
base  = mm(0.12) if backdrop else mm(0.25)    # silhouette weight
width = base * depth * (1.0 if silhouette else 0.64)   # crease = 0.16 mm
```

Explicit strokes (`D['strokes']`): ornament/tracery `mm(0.12)`, strands and
cords `mm(0.14)`, vermilion `mm(0.32)` (terminals `mm(0.40)`). Drop the
`weight=1.35/1.15` multipliers; widths come from the mm table.

## 5. Inks and layers

Two inks. Keep four layers for pen changes, but layer 03 becomes black:

```
('01 hatching',            ..., '#242820')
('02 structure',           ..., '#242820')
('03 ornament and tracery',..., '#242820')   # was #7b5a2b brass
('04 vermilion',           ..., '#a32b24')
```

Thin the tracery: the Office plate's brass layer (5.2 m) was longer than its
black edge layer (4.1 m). Halve the cell count in `filigree_column` and the
`Slate tracery stud` series, and drop the `Crown cellular joint` repeats to
what is visible at 95 mm.

Two near-blacks (#423e35 hatch, #242820 edges) are fine on press; on a plotter
they are the same pen.

## 6. Vermilion

- `mm(0.32)`, drawn last, one connected polyline per route.
- `curve()` tubes are already `ink_only` and never occlude, so tracery cannot
  break the route; only solid geometry does (the gate jambs split the
  Workshop route into four paths, which is correct). The check in §9 measures
  the longest such gap so a route hidden behind a shelf for 20 mm is caught.
- The route is the heaviest line on the plate; the check in §9 measures it.

## 7. Reserved regions and halos

Reserved paper uses the mechanism the glass vessel already uses: a mesh in
the BVH (so it occludes hatching behind it) with `hatch=False` (so it is not
hatched) and silhouette edges only. Apply it to: the stove mouth, the wheel's
open centre, both clerk silhouettes (Workshop); the window panes, ledger
pages, chessboard top (Cabinet); the ledger pages, the stool seat (Hand); the
recess (Office).

Halos are screen-space and go through the `used` raster that
`allocate_hatch` subtracts from its target. Note that `used` is scaled by
0.32 after the blur, so painting a halo into the same image can only remove
0.32 of coverage. Build the halo as a separate mask at value 1.0 and add it
after the scaling, so exclusion inside a halo is total:

```
halo = Image.new('L', (W//5, H//5), 0)                 # used is at 1/5 scale
ImageDraw.Draw(halo).line([...strand pts /5...], fill=255, width=int(mm(4)/5))
used = gaussian_filter(np.asarray(used)/255., .7)*.32 + (np.asarray(halo)/255.)
```

Needed for the strand sheaf (4 mm either side over the bench) and the recess
(8 mm band); the brief's halo limits are < 0.06 and < 0.08, which this
delivers with margin.

## 8. Scene changes by plate

Details are in the briefs; the geometry-level summary:

- **Workshop** — three-quarter camera from front-left, eye ~1.6 over the
  deck; two clerk silhouettes as reserved meshes with one hand stroke group
  each; stove door open with a reserved mouth; move the left shelf bank off
  the wheel's hub; floor sized to the room (no joints past the rule).
- **Cabinet** — solid side panels, top and base; solid door leaves with
  ornament on the outer faces; hatches as raised leaves over real apertures;
  window on the rear wall (mullions as beams, panes reserved) centred behind
  the cabinet; shelf banks moved to the side walls; crank and pulleys scaled
  up ~1.6×; belt on the bench; cut the foot/finial counts to what is visible.
- **Hand** — camera close from front-left; jig nearer the ledger; remove the
  arc and the floor grid; one bookcase bay; strands as `curve()` with no
  geometry in front of them; the 23rd strand ends in the air (if the author
  takes that option) and is mat 5.
- **Office** — long focal length (field ~24°), camera level with the recess;
  instruments on the shelves (ring on stand, rod, sphere, stack of rules);
  floor as a shadow band only; red terminals 4 mm long at each free cord end.

`floor(width, back, near)` should be sized to the room; for the two borderless
plates, replace the y-based ground thinning with a falloff by distance from
the subject's footprint (2-D, screen space), and clip floor joints to the
shadow region.

## 9. Checks to add (`checks.py`)

The existing checks test geometry and delivery. Add checks that test what a
reader sees, all computed on a 600 dpi binary rasterisation at
`PRINT_WIDTH_MM`:

1. **Coverage by zone.** Zones are named object sets from the brief's tone
   plan; map hatch samples to zones through the `owner` array already saved
   in `hatch-audit.npz`. Report mean coverage per zone in 4 mm cells.
2. **Hierarchy.** Assert the brief's measured order (e.g. Workshop:
   service bay > stove > bookcases > rear wall centre > deck).
3. **Reserved.** Each named reserved region < 0.02; halos below their limit.
4. **Vermilion.** Printed length in mm, number of connected paths, longest
   occlusion gap in mm, and "heaviest line on the plate" (stroke-width max over
   layers 01–03 < red width).
5. **Strands (Hand).** Each strand's minimum separation at the ledger ≥ 0.35
   mm; 22 end on distinct rules; none occluded.
6. **Page proof.** Composite the plate onto the Codex page at 1:1 with its
   caption, beside the current selection, as `proof-page.png`. This is the
   object the author reviews; the three-column contact sheet is a workshop
   record.

Record `PRINT_WIDTH_MM`, `PX_PER_MM` and the mm table in `manifest.json`.

## 10. What not to change

- The nine hashed bodies and the hash check.
- `scene.json` as the sole input to engraving, and byte-identical
  regeneration.
- The native Blender checks (camera match, 1,600 rays, per-scene geometry).
- The first-pass outputs, which stay in the record as the first pass.
