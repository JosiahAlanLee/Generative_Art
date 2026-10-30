# girders scene format, version 1 (`girders-scene-1`)

One JSON file describes a whole structure. Units: metres. Axes: Z up, right-handed (Blender's). The generator
(lib/girders, pure Python) writes it; the Blender builder (studies/girders) reads it. Neither imports the other.

```json
{
  "format": "girders-scene-1",
  "seed": 1234,
  "generator": {"name": "girders", "version": "0.1.0", "params": {...}},
  "bounds": {"min": [x, y, z], "max": [x, y, z]},
  "profiles": {                       // cross-sections, referenced by beams
    "I300": {"kind": "I", "h": 0.30, "w": 0.15, "tw": 0.008, "tf": 0.012},
    "C200": {"kind": "C", "h": 0.20, "w": 0.075, "tw": 0.006, "tf": 0.010},
    "L80":  {"kind": "L", "h": 0.08, "w": 0.08, "t": 0.008},
    "BOX250": {"kind": "box", "h": 0.25, "w": 0.25, "t": 0.010},
    "TUBE120": {"kind": "tube", "d": 0.12, "t": 0.006},
    "ROD30": {"kind": "rod", "d": 0.03}
  },
  "materials": ["concrete", "steel", "steel_painted", "rust", "glass", "grating", "accent"],
  "blocks": [                         // solid masses: cores, slabs, plinths, tanks, panels
    {"id": 0, "center": [x, y, z], "size": [sx, sy, sz], "yaw": 0.0, "material": "concrete",
     "tags": ["core"], "group": 3}
  ],
  "beams": [                          // every linear member, after trusses are expanded
    {"id": 0, "a": [x, y, z], "b": [x, y, z], "profile": "I300", "roll": 0.0, "material": "steel",
     "tags": ["truss", "chord"], "group": 3}
  ],
  "details": [                        // small repeated parts, instanced by the builder
    {"kind": "bolt_plate" | "rivet_row" | "vent" | "light" | "ladder" | "railing" | "pipe_run" | "cable",
     "transform": [16 floats, column-major 4x4] , "size": [sx, sy, sz], "material": "steel", "group": 3}
  ],
  "groups": [{"id": 3, "name": "tower-03", "parent": 1}],
  "camera_hints": [{"name": "worm", "location": [x, y, z], "target": [x, y, z], "lens_mm": 24}],
  "stats": {"blocks": n, "beams": n, "details": n}
}
```

Rules:
- A beam's local frame: +X runs from `a` to `b`; the profile lies in the local YZ plane, its web along local Z when
  `roll` = 0 and the beam isn't vertical. For vertical beams, roll 0 puts the web along world X. `roll` is radians about +X.
- `yaw` on blocks is radians about world Z, about the block's centre.
- `material` must be one of `materials`. `tags` and `group` are free metadata the builder may use for colour or
  selection. Unknown keys must be ignored by readers (forward compatibility).
- Large scenes (10^5–10^6 beams) must be expected: the builder must not create one Blender object per beam.
- Files may be gzipped (`.json.gz`).

## Generator conventions (informative; not format extensions)

These notes describe what the `lib/girders` generator emits, so the Blender builder can rely on them.
The format itself is unchanged.

- **Groups**: id 0 is the site; towers are `tower-NN` (parent 0), spans are `bridge-NN`, `gantry-NN`,
  `catwalk-NN`, `pipe-rack`, `ruin-cable`, `ruin-pipe`, `ruin-stub`, `ruin-fall` (all parent 0).  Bearing
  blocks at span ends belong to the tower they sit on; the span members belong to the span group.
- **Tags** (advisory, for colour/material tweaks): `tower`/`bridge`/`gantry`/`catwalk`/`pipe_rack`/`ruin`
  plus roles like `column`, `spandrel`, `brace`, `joist`, `core`, `slab`, `plinth`, `corbel`, `deck`,
  `truss`+`chord|web|vertical|cross|lace|stringer|mast|cable`, `crane`, `rail`, `pipe`, `stair`,
  `mullion`, `purlin`, `parapet`, `vent`, `glass`, `tank`, `hook`, `knee`, `bracket`, `catwalk`.
- Beams tagged `free` or `stub` may have one end in the air (collapsed stubs, ruin props); the validator
  only requires them to be anchored at one end.  All other beams have both ends meeting blocks, the
  ground or other members.
- `material` per role: concrete (cores, slabs, plinths, corbels, pedestals), steel (most framing),
  steel_painted (pipes, stairs, cranes, tanks), rust (ruin scenes, fallen spans), glass (facade panels),
  grating (catwalk/stair decks), accent (hooks, lights).
