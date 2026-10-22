# Flora research and drawing decisions

Checked 22 October 2026. The first set targets dry bluff prairie and oak
savanna in southwestern Wisconsin. Regional presence and shape references
are separate: a horticultural profile can describe a plant without establishing
its presence at a particular Driftless site.

## Local anchors

1. [Wisconsin DNR: Hogback Prairie](https://dnr.wisconsin.gov/topic/statenaturalareas/HogbackPrairie).
   A limestone-capped ridge in Crawford County. DNR specifically lists
   side-oats grama and little bluestem among its dry-prairie plants. This grounds
   the first two grasses in a southwestern Wisconsin site, not merely a state
   range map.
2. [Wisconsin DNR: Pleasant Valley Conservancy](https://dnr.wisconsin.gov/topic/statenaturalareas/PleasantValleyConservancy).
   A Driftless ridge near Black Earth with prairie, savanna, woodland and wetland
   habitats. DNR identifies bur oak, leadplant and both selected grasses here.
   Its woodland list is also useful for planning a later spring-ephemeral set.
3. [The Prairie Enthusiasts: Pleasant Valley](https://theprairieenthusiasts.org/project/pleasant-valley-conservancy/)
   and the conservancy's [plant inventory](https://pleasantvalleyconservancy.org/plant-species/)
   and [seed dates](https://pleasantvalleyconservancy.org/seed-collecting-dates/).
   The indexed inventory and seed calendar identify *Geum triflorum* at the
   site. The full inventory returned HTTP 429 during this pass; it was not
   audited as a complete flora. The dates put prairie-smoke seed collection
   in late May, which is a useful correction to treating every seed head as
   an autumn plant.
4. [Wisconsin DNR: Public Forest Lands Handbook](https://dnr.wisconsin.gov/sites/default/files/topic/ForestManagement/24605.pdf)
   describes dry and dry-mesic remnant prairie and lists bee-balm among the
   latter community’s plants. Wild bergamot's initial selection is
   regional, not a verified occurrence at the exact Hogback/Pleasant Valley
   drawing location. [USA National Phenology Network: wild bergamot](https://mynpn.usanpn.org/npnapps/species/Monarda/fistulosa)
   records Wisconsin in its range and describes persistent spent flower bases
   enclosing nutlets. The proposed compositions are habitat-informed invented
   scenes, not reconstructions of surveyed quadrats.

## Morphology translated into rules

| Species | Source used | Drawing decision |
| --- | --- | --- |
| Little bluestem | [UW–Madison Extension profile](https://hort.extension.wisc.edu/articles/little-bluestem-schizachyrium-scoparium/) | Upright bunch, narrow blades and fine-haired reproductive axes; avoid substituting big bluestem's turkey-foot silhouette |
| Side-oats grama | [Lady Bird Johnson Wildflower Center](https://www.wildflower.org/plants/result.php?id_plant=BOCU); [Missouri Botanical Garden](https://plantfinder.mobot.org/PlantFinderDetails.aspx?kempercode=g730) | Pendant short spikes consistently on one side of each upper culm |
| Leadplant | [Morton Arboretum](https://mortonarb.org/plant-and-protect/trees-and-plants/leadplant/); [US Forest Service species review](https://research.fs.usda.gov/feis/species-reviews/amocan) | Low woody architecture, many small leaflets along each compound leaf, narrow terminal flower spikes |
| Prairie smoke | [UW–Madison Extension profile](https://hort.extension.wisc.edu/articles/prairie-smoke-geum-triflorum/) | Low compound foliage, generally three nodding flowers, upright plumed fruit following pollination; separate stage settings |
| Wild bergamot | [Native Plant Trust: Go Botany](https://gobotany.nativeplanttrust.org/species/monarda/fistulosa/); [USA NPN](https://mynpn.usanpn.org/npnapps/species/Monarda/fistulosa) | Opposite toothed leaves and terminal heads; distinguish tubular flowers from a dry calyx/seed-head shorthand |
| Bur oak | [Morton Arboretum](https://mortonarb.org/plant-and-protect/trees-and-plants/bur-oak/); [Missouri Department of Conservation](https://mdc.mo.gov/discover-nature/field-guide/bur-oak-burr-oak) | Broad rounded lobes, strong central sinuses, alternate leaves and open branching |

Numeric lengths and distributions in `species.py` are **art parameters** chosen
for legible drawing. They have not been fitted to field measurements. Each
grammar exaggerates some organ sizes and omits microscopic structures. In
particular, a specimen sheet's automatic fit is not a botanical scale bar.

## Relation to this repository

- `studies/driftless-plates/engine.js` and `studies/three-gates/plants.cjs`
  already supply seeded graphic vegetation and masks. They are valuable for
  distant vegetation but do not distinguish these six species.
- `studies/terrain-symbols` already places upright symbols on evaluated
  terrain. Its parallel-plane symbols have no plant volume.
- `studies/infernal-landscape/geometry.py` supplies the reusable mesh/ink
  builder. The new adapter targets that existing interface.
- `lib/process_art/drawing.py` establishes the collection's millimetre SVG
  and physical-stroke conventions. The new renderer follows those conventions
  while retaining organ layers and 3D visibility.

This study provides reusable 3D plant surfaces plus deliberate linework.
It does not replace the established perspective renderer, native Blender
visibility checks or Driftless field-mark generator. Crosshatching a whole
scene remains the established landscape renderer's responsibility; botanical
detail here is midribs, veins, bark lines and reproductive structures.
