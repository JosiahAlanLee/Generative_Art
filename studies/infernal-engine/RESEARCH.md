# References and visual directions

Research checked 20 October 2026. The included geometry and exporter are newly written; the references inform the design. These notes do not assert that the prototype reproduces any artist's algorithm or workmanship.

## What transfers to this project

| Reference | Grounded observation | Proposed use in Blender |
| --- | --- | --- |
| Zancan, Garden / Monoliths | His description traces the work to Grass.js, natural density and a pen-plotter constraint that kept the drawing focused on vector lines. | Build vegetation as visible branching structure, with variation at several scales. Let dense growth frame quiet architectural intervals. This starter only includes a small branching plant asset. |
| Yazid, Hatched Forms and Drawing with Code | In interview he discusses the feel of imperfect analog plotting; the Drawing with Code statement describes hand-drawn inputs combined with algorithmic variation and an interest in subtle distinctions across a series. | Use authored paths, restrained series variation and directional hatching. Eventually allow a few drawn guides to determine a corridor, crown or growing margin. The starter's hatch shader and SVG exporter are simpler technical studies. |
| Zancan × Yazid, (kinder)Garden, Monuments | Their project statement explicitly describes block structures, Yazid's hashed/hatched treatment and Zancan's foliage, within a plottable framework. | Architecture, growth and drawing should be separable systems that meet in a composed image. It is a particularly direct reference for a future exterior scene family. |
| Ge1doot, The Architecture of Silence | The published Turtletoy program exposes recursive weighted rules, adjustable perspective, primitive architecture, polygon visibility handling and hatching. | Give buildings an architectural grammar; treat camera projection and hidden-surface removal as part of the art system. The prototype uses independently written Geometry Nodes and a ray-tested exporter. |

These directions complement each other, but they are not one style. Zancan's botanical density and Yazid's restraint can conflict. A useful scene should decide where density belongs rather than turn every available effect on.

## Four scene families

**Built: Common ground.** A clear circulation path bisects a field of repeated storage or service towers. Pipes feed a collector at the end. Vegetation occupies the industrial site. The collector is still too small to carry every possible interpretation; consider a lower camera or a larger, stranger central mechanism for the next pass.

**Built: Hall of obligations.** A barrel vault and repeating ribs establish an interior. Every cabinet returns to the same collector. The first composition uses formal symmetry with a slightly off-axis camera. Missing bays can make the repeated order partial, but the fixed shell does not yet respond to that parameter.

**Proposed: The observatory of lag.** A circular control room observes a factory through a deep shaft. A mechanical message travels through intermediate galleries before it reaches the controller. Delayed feedback would be visible as distance, routing and interrupted sight lines. No such delay model or animation is implemented.

**Proposed: The garden of enclosure.** Terraces grow increasingly elaborate around a small central common space. New enclosures consume the walkable ground while ornament and foliage intensify. This needs a rule for accessible routes and occupied land; random towers alone do not express enclosure.

The demonic metaphor should reside in relations: what feeds what, what can be reached, what is forced to repeat, who can see an event, and where matter accumulates. Horns can be one motif, but cannot carry those relationships on their own. These are visual metaphors, not evidence for a systems-theory claim.

## Next technical choices

1. Make the service network authoritative. Generate apparatus ports, pipe routes and brackets from one graph. That prevents detached mechanisms and gives accumulation or dependency a visible form.
2. Replace uniform randomness with authored anchors, reserved negative space and bounded variants. Compare six seeds of one stable composition before adding another scene family.
3. Separate botanical growth from surface wear. A climbing system needs a surface field and attachment rules; a ground scatter is not a substitute.
4. Add camera-aware detail limits and a minimum pen spacing. Render or export at the final plate size to catch hatching that becomes a dark patch.
5. For output, retain the original `.blend`, transparent PNG and SVG independently. A raster-to-vector pass can be an additional treatment, but the scene geometry already supplies exact spatial structure for line drawing.

## Primary references

- [Zancan: Garden, Monoliths #89](https://zancan.art/Series/Garden-Monoliths/89) — artist's process statement.
- [Zancan × Yazid: (kinder)Garden, Monuments #1](https://zancan.art/Series/kinder-Garden-Monuments/1) — joint project statement.
- [Yazid: Drawing with Code](https://verse.works/series/drawing-with-code-by-Yazid) — artist's statement.
- [In Conversation with Yazid: Windows in my Soul](https://verse.works/journal/in-conversation-with-yazid-windows-in-my-soul) — interview with the artist.
- [Ge1doot: The Architecture of Silence](https://turtletoy.net/turtle/633245ecf6) — artist-published drawing and source.
- [Ge1doot: Ignition](https://www.artblocks.io/collection/ignition-by-ge1doot) — artist's description of interactive 3D structures.

The research is about transferable design principles. No reference source code is bundled in this package.
