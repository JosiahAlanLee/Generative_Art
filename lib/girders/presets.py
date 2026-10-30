"""Named presets and per-scale parameters for the girders generator.

Each preset is a base parameter dictionary plus ``scales`` overrides for
small / medium / large.  ``resolve_params`` merges them into the effective
parameters the generator reads.  Every preset must read clearly differently:

- ``dense-core``: tall towers, heavy concrete cores, dense steel frames,
  X/K bracing, roof tanks and high Warren-truss bridges.
- ``bridge-field``: a long field of slender towers joined by long-span
  truss bridges at several levels, cable-stayed centre spans.
- ``stacked-gantries``: a dense grid of squat towers stacked with gantry
  crane rails and lattice gantries at several heights, pipes and catwalks.
- ``ruin``: the dense-core plan after decades of decay: rust, missing
  secondary members, sagged cables, broken glass and collapsed deck panels,
  but every tower still stands on its columns.
"""

PRESETS = {
    "dense-core": {
        "grid": [2, 3],
        "spacing": [36.0, 42.0],
        "jitter": 5.0,
        "footprint": [14.0, 16.5],
        "storeys": [16, 22],
        "floor_h": [3.5, 4.0],
        "bays": [4, 5],
        "core_frac": [0.42, 0.50],
        "bracing": {"south": "x", "north": "k", "west": "x", "east": "chevron"},
        "antenna": 0.4,
        "bridge": {
            "chance": 0.65, "levels": 1, "panel": [3.2, 4.6],
            "kinds": ["warren", "warren", "pratt", "howe"],
            "depth": [3.4, 4.8], "width": [4.0, 5.6],
            "cable": 0.15, "catwalk": 0.2,
        },
        "gantry": {"chance": 0.25, "levels": 1},
        "catwalk": 0.5,
        "pipe": 1.0,
        "ruin": 0.0,
        "scales": {
            "small": {"grid": [2, 3], "storeys": [6, 10], "bays_add": 0,
                      "bridge": {"levels": 1, "panel": [3.4, 5.0]},
                      "gantry": {"levels": 1}, "bracing_all": False, "bridge_mul": 0.7, "catwalk_mul": 0.6,
                      "joist_grid": False, "mullions": False, "roof_grid": False,
                      "railings": False, "stairs_full": False, "pipe_racks": False},
            "medium": {"grid": [2, 3], "storeys": [16, 22], "bays_add": 0,
                       "bridge": {"levels": 1, "panel": [3.0, 4.4]},
                       "gantry": {"levels": 1}, "bracing_all": False, "bridge_mul": 1.0, "catwalk_mul": 1.0,
                       "joist_grid": True, "mullions": True, "roof_grid": True,
                       "railings": False, "stairs_full": False, "pipe_racks": True},
            "large": {"grid": [4, 5], "storeys": [24, 32], "bays_add": 3,
                      "bridge": {"levels": 2, "panel": [2.0, 2.8]},
                      "gantry": {"levels": 2}, "bracing_all": True, "bridge_mul": 1.0, "catwalk_mul": 1.4,
                      "joist_grid": True, "mullions": True, "roof_grid": True,
                      "railings": True, "stairs_full": True, "pipe_racks": True, "joist_density": 2},
        },
    },
    "bridge-field": {
        "grid": [1, 4],
        "spacing": [56.0, 44.0],
        "jitter": 3.0,
        "footprint": [10.0, 11.0],
        "storeys": [10, 15],
        "floor_h": [3.4, 3.8],
        "bays": [2, 3],
        "core_frac": [0.30, 0.36],
        "bracing": {"south": "k", "north": "chevron", "west": "x", "east": "x"},
        "antenna": 0.0,
        "bridge": {
            "chance": 1.0, "levels": 2, "panel": [2.8, 4.0],
            "kinds": ["pratt", "howe", "warren", "lattice", "vierendeel"],
            "depth": [4.5, 6.5], "width": [4.5, 6.5],
            "cable": 0.6, "catwalk": 0.8,
        },
        "gantry": {"chance": 0.0, "levels": 0},
        "catwalk": 0.7,
        "pipe": 0.9,
        "ruin": 0.0,
        "scales": {
            "small": {"grid": [1, 4], "storeys": [3, 6], "bays_add": 0,
                      "bridge": {"levels": 1, "panel": [3.4, 5.0]},
                      "gantry": {"levels": 0}, "bracing_all": False, "bridge_mul": 0.7, "catwalk_mul": 0.6,
                      "joist_grid": False, "mullions": False, "roof_grid": False,
                      "railings": False, "stairs_full": False, "pipe_racks": False},
            "medium": {"grid": [1, 4], "storeys": [10, 15], "bays_add": 0,
                       "bridge": {"levels": 2, "panel": [2.6, 3.6]},
                       "gantry": {"levels": 0}, "bracing_all": False, "bridge_mul": 1.0, "catwalk_mul": 1.0,
                       "joist_grid": True, "mullions": True, "roof_grid": True,
                       "railings": False, "stairs_full": False, "pipe_racks": True},
            "large": {"grid": [4, 7], "storeys": [14, 20], "bays_add": 2,
                      "bridge": {"levels": 3, "panel": [2.0, 2.5], "cable": 0.8, "catwalk": 1.0},
                      "bridge": {"levels": 3, "panel": [2.0, 2.6]},
                      "gantry": {"levels": 0}, "bracing_all": True, "bridge_mul": 1.0, "catwalk_mul": 1.4,
                      "joist_grid": True, "mullions": True, "roof_grid": True,
                      "railings": True, "stairs_full": True, "pipe_racks": True, "joist_density": 2},
        },
    },
    "stacked-gantries": {
        "grid": [3, 3],
        "spacing": [30.0, 34.0],
        "jitter": 4.0,
        "footprint": [11.0, 12.5],
        "storeys": [6, 10],
        "floor_h": [3.6, 4.4],
        "bays": [2, 4],
        "core_frac": [0.34, 0.42],
        "bracing": {"south": "chevron", "north": "chevron", "west": "k", "east": "k"},
        "antenna": 0.2,
        "bridge": {
            "chance": 0.25, "levels": 1, "panel": [3.0, 4.2],
            "kinds": ["vierendeel", "lattice"],
            "depth": [3.0, 3.8], "width": [3.5, 4.5],
            "cable": 0.0, "catwalk": 0.3,
        },
        "gantry": {"chance": 1.0, "levels": 3},
        "catwalk": 1.0,
        "pipe": 1.0,
        "ruin": 0.0,
        "scales": {
            "small": {"grid": [3, 3], "storeys": [3, 4], "bays_add": 0,
                      "bridge": {"levels": 1, "panel": [3.2, 4.6]},
                      "gantry": {"levels": 2}, "bracing_all": False, "bridge_mul": 0.7, "catwalk_mul": 0.6,
                      "joist_grid": False, "mullions": False, "roof_grid": False,
                      "railings": False, "stairs_full": False, "pipe_racks": False},
            "medium": {"grid": [3, 3], "storeys": [6, 10], "bays_add": 1,
                       "bridge": {"levels": 1, "panel": [2.8, 4.0]},
                       "gantry": {"levels": 3}, "bracing_all": False, "bridge_mul": 1.0, "catwalk_mul": 1.0,
                       "joist_grid": True, "mullions": False, "roof_grid": True,
                       "railings": False, "stairs_full": False, "pipe_racks": True},
            "large": {"grid": [5, 7], "storeys": [11, 18], "bays_add": 4,
                      "bridge": {"levels": 2, "panel": [2.0, 2.8]},
                      "gantry": {"levels": 4}, "bracing_all": True, "bridge_mul": 1.0, "catwalk_mul": 1.4,
                      "joist_grid": True, "mullions": False, "roof_grid": True,
                      "railings": True, "stairs_full": True, "pipe_racks": True, "joist_density": 2},
        },
    },
    "ruin": {
        "grid": [2, 3],
        "spacing": [36.0, 42.0],
        "jitter": 6.0,
        "footprint": [13.0, 15.0],
        "storeys": [10, 16],
        "floor_h": [3.5, 4.0],
        "bays": [3, 5],
        "core_frac": [0.40, 0.48],
        "bracing": {"south": "x", "north": "x", "west": "chevron", "east": "k"},
        "antenna": 0.3,
        "bridge": {
            "chance": 0.5, "levels": 1, "panel": [3.2, 4.6],
            "kinds": ["warren", "pratt", "howe", "lattice"],
            "depth": [3.4, 4.6], "width": [4.0, 5.2],
            "cable": 0.25, "catwalk": 0.4,
        },
        "gantry": {"chance": 0.2, "levels": 1},
        "catwalk": 0.35,
        "pipe": 0.8,
        "ruin": 1.0,
        "scales": {
            "small": {"grid": [2, 3], "storeys": [3, 6], "bays_add": 0,
                      "bridge": {"levels": 1, "panel": [3.4, 5.0]},
                      "gantry": {"levels": 1}, "bracing_all": False, "bridge_mul": 0.7, "catwalk_mul": 0.6,
                      "joist_grid": False, "mullions": False, "roof_grid": False,
                      "railings": False, "stairs_full": False, "pipe_racks": False},
            "medium": {"grid": [2, 3], "storeys": [10, 16], "bays_add": 0,
                       "bridge": {"levels": 1, "panel": [3.0, 4.4]},
                       "gantry": {"levels": 1}, "bracing_all": False, "bridge_mul": 1.0, "catwalk_mul": 1.0,
                       "joist_grid": True, "mullions": True, "roof_grid": True,
                       "railings": False, "stairs_full": False, "pipe_racks": True},
            "large": {"grid": [5, 6], "storeys": [20, 26], "bays_add": 4,
                      "bridge": {"levels": 2, "panel": [2.0, 2.8]},
                      "gantry": {"levels": 2}, "bracing_all": True, "bridge_mul": 1.0, "catwalk_mul": 1.4,
                      "joist_grid": True, "mullions": True, "roof_grid": True,
                      "railings": True, "stairs_full": True, "pipe_racks": True, "joist_density": 2},
        },
    },
}


def resolve_params(preset, scale):
    """Merge a preset's base with its per-scale overrides."""
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r}; choose from {sorted(PRESETS)}")
    if scale not in ("small", "medium", "large"):
        raise ValueError(f"unknown scale {scale!r}; choose from small/medium/large")
    import copy

    base = copy.deepcopy(PRESETS[preset])
    over = base.pop("scales")[scale]
    p = copy.deepcopy(base)
    for key, val in over.items():
        if isinstance(val, dict) and isinstance(p.get(key), dict):
            merged = dict(p[key])
            merged.update(val)
            p[key] = merged
        else:
            p[key] = val
    p["preset"] = preset
    p["scale"] = scale
    p["density"] = {"primary": 0.75, "secondary": 0.45, "detail": 0.35} if scale == "small" \
        else {"primary": 1.0, "secondary": 1.0, "detail": 1.0}
    return p
