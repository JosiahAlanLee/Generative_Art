# Farm objects and structural decay

[Study, specimens and rebuild instructions](../../studies/farm-remnants/README.md)

A seeded 3D library for wooden barns, open-seat tractors, disk harrows, dump
rakes and slatted wagons. Decay acts on the actual construction and on attached
surface marks: missing panels, ragged plank ends, sag, tire checking, bent teeth
and steel corrosion. The same objects can be placed in the repository's existing
SceneBuilder and rendered from different directions.

- [Object API](../../lib/farm_objects/objects.py): `make_object`, `FarmObject.add_to`, `write_obj`.
- [SVG engraving](../../lib/farm_objects/render.py): `render_svg`, four explicit pen layers and shared BVH occlusion.
- [Blender adapter](../../lib/farm_objects/blender.py): import full records into a new collection; native execution remains unverified.
- [Farmyard SVG](../../studies/farm-remnants/output/farmyard.svg).

These are original composite forms, not scans or traced equipment designs.
