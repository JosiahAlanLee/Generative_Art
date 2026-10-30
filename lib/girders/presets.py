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
- ``fault-spine`` (v2): an asymmetric industrial canyon of tall inhabited
  stepped blocks, huge cantilevers and deep truss ribs spanning the gap.
- ``suspended-delta`` (v2): a layered inhabited bridge megastructure
  radiating from a hub, hung on sparse buttresses with cable stays and nets.
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
    "fault-spine": {
        "v2": "fault-spine",
        "blocks_per_row": [8, 8],
        "storeys_south": [15, 21],
        "storeys_north": [9, 14],
        "row_gap": [4.5, 6.0],
        "block_w": [26.0, 30.0],
        "block_d": [18.0, 22.0],
        "gap": [16.0, 26.0],
        "jitter": 2.0,
        "floor_h": [3.9, 4.3],
        "setback_stacks": 2,
        "slab_keep": 0.35,
        "glass_rate": 0.12,
        "pitch": 0.7,
        "split": 2.4,
        "bay": 4.4,
        "shrink_w": 4.5,
        "shrink_d": 4.5,
        "diag_rate": 0.05,
        "splice_rate": 0.075,
        "rib_levels": 3,
        "rib_depth": [8.0, 18.0],
        "rib_width": [4.5, 6.5],
        "rib_kinds": ["warren", "pratt", "lattice"],
        "rib_panel": [2.8, 3.4],
        "cantilevers": 6,
        "cant_len": [12.0, 26.0],
        "cant_w": [6.0, 9.0],
        "cant_depth": [3.5, 5.5],
        "scales": {
            "small": {"blocks_per_row": [2, 3], "storeys_south": [5, 8],
                      "storeys_north": [3, 6], "gap": [12.0, 18.0],
                      "pitch": 1.0, "split": 3.2, "setback_stacks": 1,
                      "rib_levels": 1, "cantilevers": 2, "cant_len": [10.0, 16.0],
                      "block_w": [20.0, 24.0], "block_d": [13.0, 16.0],
                      "splice_rate": 0.03},
            "medium": {"blocks_per_row": [4, 5], "storeys_south": [10, 14],
                       "storeys_north": [6, 9], "gap": [14.0, 22.0],
                       "pitch": 0.85, "split": 2.8, "setback_stacks": 1,
                       "rib_levels": 2, "cantilevers": 3,
                       "block_w": [24.0, 28.0], "block_d": [16.0, 19.0],
                       "splice_rate": 0.03},
            "large": {"blocks_per_row": [8, 8], "storeys_south": [15, 21],
                      "storeys_north": [9, 14], "gap": [16.0, 26.0],
                      "pitch": 0.7, "split": 2.4, "setback_stacks": 2,
                      "rib_levels": 3, "cantilevers": 6,
                      "splice_rate": 0.075},
        },
    },
    "suspended-delta": {
        "v2": "suspended-delta",
        "branches": 7,
        "tiers": 6,
        "tier_h": 15.0,
        "deck_z0": 15.0,
        "branch_len": [120.0, 170.0],
        "deck_w": [15.0, 18.0],
        "truss_depth": [9.0, 14.0],
        "deck_kinds": ["warren", "lattice", "pratt"],
        "deck_panel": [2.6, 3.2],
        "floors_in": [2.6, 5.4],
        "buttress_w": [7.0, 9.5],
        "buttress_over": [4.0, 18.0],
        "mast_h": [10.0, 16.0],
        "buttress_extra": 2,
        "tower_w": 0.32,
        "skip_tiers": 1,
        "hub_w": [24.0, 30.0],
        "hub_blocks": [[0.85, 0.75, 16.0], [0.55, 0.60, 12.0], [0.35, 0.42, 10.0]],
        "slab_keep": 0.35,
        "glass_rate": 0.22,
        "pitch": 0.65,
        "split": 2.2,
        "diag_rate": 0.06,
        "splice_rate": 0.08,
        "cantilevers": 8,
        "cant_depth": [3.0, 4.5],
        "scales": {
            "small": {"branches": 3, "tiers": 2, "branch_len": [55.0, 80.0],
                      "deck_w": [10.0, 12.0], "truss_depth": [8.0, 9.5],
                      "tier_h": 11.0, "deck_z0": 14.0, "buttress_over": [4.0, 12.0],
                      "buttress_extra": 0, "cantilevers": 1, "skip_tiers": 0,
                      "hub_w": [18.0, 22.0], "pitch": 1.0, "split": 3.0,
                      "floors_in": [2.4, 4.8], "splice_rate": 0.04,
                      "slab_keep": 0.30, "glass_rate": 0.10},
            "medium": {"branches": 4, "tiers": 3, "branch_len": [90.0, 125.0],
                       "deck_w": [12.0, 15.0], "truss_depth": [9.0, 11.0],
                       "tier_h": 12.0, "deck_z0": 15.0, "buttress_over": [4.0, 14.0],
                       "buttress_extra": 1, "cantilevers": 2, "skip_tiers": 0,
                       "hub_w": [20.0, 26.0], "pitch": 0.8, "split": 2.6,
                       "floors_in": [2.5, 5.0], "splice_rate": 0.04,
                       "glass_rate": 0.14},
            "large": {"branches": 7, "tiers": 6, "branch_len": [120.0, 170.0],
                      "deck_w": [15.0, 18.0], "truss_depth": [9.0, 14.0],
                      "tier_h": 15.0, "deck_z0": 15.0, "buttress_over": [4.0, 18.0],
                      "buttress_extra": 2, "cantilevers": 8, "skip_tiers": 1,
                      "hub_w": [24.0, 30.0], "pitch": 0.65, "split": 2.2,
                      "floors_in": [2.6, 5.4], "splice_rate": 0.08},
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
