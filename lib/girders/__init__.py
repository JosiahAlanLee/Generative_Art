"""Seeded generative block-and-girder megastructures.

Generates ``girders-scene-1`` JSON scenes (see SCHEMA.md) consumed by the
Blender builder in studies/girders.  Pure Python + numpy; deterministic for
a given (seed, preset, scale).

Typical use:

    from lib.girders import generate, validate, save_scene
    scene = generate(seed=7, preset="dense-core", scale="medium")
    errors = validate(scene)          # [] means structurally sound
    save_scene(scene, "scene.json.gz")

CLI: ``python -m lib.girders generate --preset ruin --seed 7 --out s.json.gz``
(run ``python -m girders.generate`` from inside ``lib/`` for the same flags).
"""

from .generate import VERSION, generate, load_scene, save_scene
from .presets import PRESETS, resolve_params
from .preview import render
from .schema import validate

__all__ = ["VERSION", "PRESETS", "generate", "load_scene", "resolve_params",
           "render", "save_scene", "validate"]
