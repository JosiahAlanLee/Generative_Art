# Barn quilt squares: conventions and an SVG starting point

Research date: 20 October 2026. Sources below are trail organizers, public
institutions, museum scholarship, or makers describing their own construction
methods. The generator is an independent implementation of geometric block
families. No photographs, maker diagrams, instruction text, or third-party code
are included in its artwork.

## What the sources support

The modern coordinated **quilt-trail movement** began in Adams County, Ohio,
in 2001 through Donna Sue Groves's community project. The Foundation for
Appalachian Ohio describes its goals as regional tourism, artisan support,
and preservation of old barns. This dates the trail movement; it does not date
all quilt geometry or all painted decoration on barns. [1]

Barn quilts translate quilt-block designs into painted panels. Bureau County
describes exterior paint on MDO plywood, commonly 4 or 8 feet square, and both
traditional blocks and designs meaningful to particular farm owners. Its
examples connect blocks and colors to family heritage, agriculture, hobbies,
or local place names. These are situated meanings, rather than evidence for
a universal block-to-message dictionary. [2]

The Canadian trail guide recommends simple designs, a limited number of colors,
and bold contrast for visibility. It explicitly ties detail to viewing distance
and permits original designs as well as family or historical quilt references.
Those are useful working conventions, not universal admission rules. A trail
can impose its own requirements. For instance, Bureau County specifies an
agricultural building, whereas Groves's wider movement includes businesses,
homes, and sheds. [1–3]

Chatt Hills provides a particularly useful production account: grid the board,
draw and label each colored region, then tape and paint successive areas.
It discusses plywood/MDO and a move toward lightweight aluminum-composite
sign board, whose preparation includes cleaning, light scuffing, primer,
and a painted background. It also relates complexity and contrast to road
distance. [4] The source documents that trail's practice; its durability
recommendations are not a universal comparison of every available support.

## Conventions translated into generator decisions

| Observed practice | Implementation choice |
| --- | --- |
| A square, legible painted block | Exact partitions of a square with an optional painted border |
| Drawing from quilt construction | Half-square triangles, quarter-square triangles, geese, strips, and nested squares |
| Limited, strongly separated colors | Named four-role palettes, including a brighter `roadside` palette |
| Color chosen by individual makers | Custom hex palettes and three color-role permutations |
| Taped painting on a continuous support | Crisp polygon boundaries with separate, clipped brush marks |
| Primed/coated support | Grain and scuff relief kept faint under opaque paint |
| Wear that reveals the support | Edge-biased chips with support-colored interiors |

This table contains **design inferences** from the documented practices, not
additional historical claims. Decorative pinstriping, palette names, wear
parameters, and screw-head graphics are project choices. Steel/stainless is an
optional artistic material study; the consulted material instructions provide
stronger direct support for MDO and aluminum composite. `manuscript` is intended
for page artwork, where roadside visibility is not the governing requirement.

## Block grammar and names

Scissortail Quilting's block library distinguishes Ohio Star's nine-patch
structure and provides maker references for Churn Dash, Pinwheel, and Rail
Fence. [5–8] Sara Buscaglia's Sawtooth Star tutorial identifies squares and
flying-geese units as its components. [9] These references help separate
recognizable construction families from arbitrary radial tiling.

The implemented Log Cabin is a sequential strip spiral; Flying Geese is a
two-column repeat of triangle-and-sky units; Square-in-Square recursively
joins edge midpoints. These are explicit geometric interpretations, not
claims to establish their earliest dates, a unique historical spelling, or
the canonical colorway. The generator exposes the polygons so other drawing
systems can reuse the geometry without taking the surface treatment.

## Historical boundaries relevant to later combinations

Pennsylvania Dutch **barn stars / hex signs** should receive their own source
record if added later. Patrick Donmoyer's Glencairn exhibition research documents
regional painted stars and distinguishes them from discreet protective ritual
markings inside barn doors. It also examines how the popular label “hex sign”
combined or confused different practices. Similar stars on agricultural
buildings do not by themselves establish a shared magical purpose or direct
lineage to today's quilt trails. [10]

For any future cipher work, the International Quilt Museum's account of
Underground Railroad quilt-code stories reports a family oral tradition but
no corroborating historical evidence for the proposed code. [11] A new quilt
cipher for this project should therefore be labeled a new invention. Neither
that evidentiary limit nor the generator says that no historical quilt could
ever have carried a private message.

## Implemented now; possible next experiments

The first implementation has eight families, exact reusable polygons, six
palettes, seeded marks, four support studies, painted/flat/outline SVG output,
and comparison proofs. Read the [usage guide](../../techniques/13-barn-quilts/README.md).

Possible follow-ons are separate experiments: mount a block on a Driftless
Plates barn facade; project it onto a Blender structure; cross-hatch the
same polygon partition; or confine Physarum to selected painted regions.
A broader grammar could vary legal half-square/quarter-square arrangements
under symmetry and contrast constraints. These integrations and grammar
expansions are not implemented by this first addition.

## Sources

1. [Foundation for Appalachian Ohio: Donna Sue Groves Arts & Culture Fund](https://appalachianohio.org/fund/donna-sue-groves-arts-culture-fund-for-appalachian-ohio/). First-party memorial and movement account.
2. [Bureau County, Illinois: Barn Quilts](https://bureaucounty-il.gov/barn-quilts/). County trail description, materials, scale, meanings, and its own eligibility rule.
3. [Barn Quilt Trails, Canada: Make a Barn Quilt](https://barnquilttrails.ca/how-to/designing-the-blocks/). Organizer guidance on pattern, color, and painting.
4. [Chatt Hills Barn Quilt Trail: Create a Barn Quilt](https://www.chatthillsbarnquilttrail.com/create-a-barn-quilt.html). Organizer's grid, surface-preparation, masking, and materials account.
5. [Scissortail Quilting: Ohio Star](https://scissortailquilting.com/quilt-block-library/ohio-star-quilt-block/). Maker's block construction reference.
6. [Scissortail Quilting: Churn Dash](https://scissortailquilting.com/quilt-block-library/churn-dash-quilt-block/). Maker's block construction reference.
7. [Scissortail Quilting: Pinwheel](https://scissortailquilting.com/quilt-block-library/pinwheel-quilt-block/). Maker's block construction reference.
8. [Scissortail Quilting: Rail Fence](https://scissortailquilting.com/quilt-block-library/rail-fence-quilt-block/). Maker's block construction reference.
9. [Sara Buscaglia / Farm & Folk: Sawtooth Star Quilt Tutorial](https://www.farmandfolk.com/blog/2024/7/22/sawtooth-star-quilt-tutorial). Maker's explanation of the square/geese construction.
10. [Patrick Donmoyer / Glencairn Museum: Hex Signs—Sacred and Celestial Symbolism in Pennsylvania Dutch Barn Stars](https://www.glencairnmuseum.org/newsletter/2019/3/19/hex-signs-sacred-and-celestial-symbolism-in-pennsylvania-dutch-barn-stars). Exhibition scholarship grounded in surveys and community research.
11. [International Quilt Museum / University of Nebraska–Lincoln: Underground Railroad Quilts?](https://worldquilts.quiltstudy.org/americanstory/node/123). Museum account of the code story and its evidentiary limits.
