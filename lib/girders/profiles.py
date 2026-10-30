"""Cross-section and material libraries for the girders generator.

Profiles follow lib/girders/SCHEMA.md: a profile is a dict with a ``kind``
(I, C, L, box, tube, rod) and the dimensions the Blender builder uses to make
the unit mesh.  Sizes are chosen for a scene whose towers are 30-90 m tall,
so the smallest secondary member (ROD16, L70) still reads as a real part in a
close crop.
"""

# Cross-sections, referenced by beams.  The names are stable API: the Blender
# builder maps name -> unit mesh.
PROFILES = {
    # heavy primary framing
    "BOX500": {"kind": "box", "h": 0.50, "w": 0.50, "t": 0.025},
    "BOX350": {"kind": "box", "h": 0.35, "w": 0.35, "t": 0.018},
    "I700": {"kind": "I", "h": 0.70, "w": 0.32, "tw": 0.014, "tf": 0.025},
    "I600": {"kind": "I", "h": 0.60, "w": 0.28, "tw": 0.012, "tf": 0.022},
    "I450": {"kind": "I", "h": 0.45, "w": 0.22, "tw": 0.010, "tf": 0.018},
    "I300": {"kind": "I", "h": 0.30, "w": 0.15, "tw": 0.008, "tf": 0.012},
    # truss chords / webs / lacing
    "TUBE300": {"kind": "tube", "d": 0.30, "t": 0.012},
    "TUBE180": {"kind": "tube", "d": 0.18, "t": 0.008},
    "C250": {"kind": "C", "h": 0.25, "w": 0.085, "tw": 0.008, "tf": 0.012},
    "C180": {"kind": "C", "h": 0.18, "w": 0.070, "tw": 0.006, "tf": 0.010},
    "L120": {"kind": "L", "h": 0.12, "w": 0.12, "t": 0.010},
    "L90": {"kind": "L", "h": 0.09, "w": 0.09, "t": 0.008},
    # secondary steel
    "I240": {"kind": "I", "h": 0.24, "w": 0.12, "tw": 0.007, "tf": 0.010},
    "C160": {"kind": "C", "h": 0.16, "w": 0.060, "tw": 0.006, "tf": 0.009},
    "C120": {"kind": "C", "h": 0.12, "w": 0.050, "tw": 0.005, "tf": 0.008},
    "L70": {"kind": "L", "h": 0.07, "w": 0.07, "t": 0.006},
    # pipes, rails, cables
    "TUBE140": {"kind": "tube", "d": 0.14, "t": 0.006},
    "TUBE90": {"kind": "tube", "d": 0.09, "t": 0.004},
    "TUBE50": {"kind": "tube", "d": 0.05, "t": 0.003},
    "ROD30": {"kind": "rod", "d": 0.03},
    "ROD16": {"kind": "rod", "d": 0.016},
}

MATERIALS = ["concrete", "steel", "steel_painted", "rust", "glass", "grating", "accent"]

# Detail kinds the generator emits (the Blender builder models these parts).
DETAIL_KINDS = ("bolt_plate", "rivet_row", "vent", "light", "ladder", "railing", "pipe_run", "cable")
