"""Numeric guarantees for the v2 girders megastructures.

The v2 presets (``fault-spine``, ``suspended-delta``) make measurable
promises that the v1 tower presets do not; these tests pin them down.  The
targets come from the design brief:

- large scenes: >= 250k beams, >= 10k details
- glass <= 3% of blocks (no curtain walls)
- >= 20% of beams tagged ``secondary``
- >= 8 cantilever or setback groups
- deep connecting trusses with depths in [8, 18] m
- >= 50% of the optional floor plates omitted (structure exposed)
- secondary lattice pitch in [0.6, 1.2] m with section widths 0.06-0.14 m
- cables are ROD30 and pipes TUBE50+ so rails/pipes/cable nets read at 4K

Structural validity for small/medium scenes is covered by
``SchemaTests`` in test_girders.py (it iterates over every preset); the
full large-scene validator is slow by design, so it runs behind the
``GIRDERS_SLOW`` environment variable and is exercised in CI when set.
"""

import os
import unittest

import numpy as np

from lib.girders import PRESETS, generate
from lib.girders.profiles import PROFILES

V2_PRESETS = ("fault-spine", "suspended-delta")
SEED = 7

# profiles whose smallest section dimension lies in [0.06, 0.14] m
_LATTICE_OK = {"L70", "L90", "TUBE90"}


def _section_width(profile):
    pr = PROFILES[profile]
    if pr["kind"] == "L":
        return min(pr["h"], pr["w"])
    if pr["kind"] == "tube":
        return pr["d"]
    return min(pr.get("h", 9.0), pr.get("w", 9.0))


class LargeScaleTargets(unittest.TestCase):
    """The brief's numeric targets, checked at ``large`` scale."""

    def test_beams_and_details_targets(self):
        for preset in V2_PRESETS:
            scene = generate(SEED, preset, "large")
            self.assertGreaterEqual(len(scene["beams"]), 250_000, preset)
            self.assertGreaterEqual(len(scene["details"]), 10_000, preset)
            self.assertEqual(scene["stats"]["beams"], len(scene["beams"]), preset)
            self.assertEqual(scene["stats"]["details"], len(scene["details"]), preset)

    def test_glass_stays_below_three_percent(self):
        for preset in V2_PRESETS:
            scene = generate(SEED, preset, "large")
            blocks = scene["blocks"]
            glass = sum(1 for b in blocks if b.get("material") == "glass")
            self.assertLessEqual(glass / len(blocks), 0.03, preset)
            self.assertLessEqual(scene["stats"]["glass_frac"], 0.03, preset)

    def test_secondary_beams_are_at_least_a_fifth(self):
        for preset in V2_PRESETS:
            scene = generate(SEED, preset, "large")
            beams = scene["beams"]
            secondary = sum(1 for b in beams if "secondary" in (b.get("tags") or ()))
            self.assertGreaterEqual(secondary / len(beams), 0.20, preset)

    def test_cantilever_and_setback_groups(self):
        for preset in V2_PRESETS:
            scene = generate(SEED, preset, "large")
            names = [g["name"] for g in scene["groups"]]
            cant = sum(1 for n in names if n.startswith("cantilever"))
            setback = sum(1 for n in names if n.startswith("setback"))
            self.assertGreaterEqual(cant + setback, 8, preset)
            self.assertEqual(cant, scene["stats"]["cantilever_groups"], preset)
            self.assertEqual(setback, scene["stats"]["setback_groups"], preset)

    def test_deep_trusses_are_8_to_18_metres(self):
        for preset in V2_PRESETS:
            scene = generate(SEED, preset, "large")
            st = scene["stats"]
            self.assertGreaterEqual(st["deep_trusses"], 8, preset)
            self.assertGreaterEqual(st["truss_depth_min"], 8.0, preset)
            self.assertLessEqual(st["truss_depth_max"], 18.0, preset)

    def test_floor_plate_omission_exposes_structure(self):
        for preset in V2_PRESETS:
            scene = generate(SEED, preset, "large")
            st = scene["stats"]
            self.assertGreater(st["floor_slots"], 20, preset)
            self.assertGreaterEqual(st["floor_omission"], 0.50, preset)
            self.assertEqual(st["floor_kept"], round(st["floor_slots"] * (1 - st["floor_omission"])),
                             preset)

    def test_secondary_lattice_pitch_and_sections(self):
        for preset in V2_PRESETS:
            scene = generate(SEED, preset, "large")
            pitch = scene["stats"]["lattice_pitch"]
            self.assertGreaterEqual(pitch, 0.6, preset)
            self.assertLessEqual(pitch, 1.2, preset)
            lattice = [b for b in scene["beams"]
                       if "lattice" in (b.get("tags") or ())]
            self.assertGreater(len(lattice), 1000, preset)
            for b in lattice:
                self.assertIn(b["profile"], _LATTICE_OK, (preset, b["profile"]))
                self.assertGreaterEqual(_section_width(b["profile"]), 0.06, preset)
                self.assertLessEqual(_section_width(b["profile"]), 0.14, preset)

    def test_cables_and_pipes_read_at_4k(self):
        for preset in V2_PRESETS:
            scene = generate(SEED, preset, "large")
            cables = [b for b in scene["beams"]
                      if "cable" in (b.get("tags") or ())]
            self.assertGreater(len(cables), 20, preset)
            for b in cables:
                self.assertEqual(b["profile"], "ROD30", (preset, b["profile"]))
            pipes = [b for b in scene["beams"] if "pipe" in (b.get("tags") or ())]
            for b in pipes:
                self.assertIn(b["profile"], ("TUBE50", "TUBE90", "TUBE140"),
                              (preset, b["profile"]))

    def test_no_tower_grid_or_curtain_walls(self):
        for preset in V2_PRESETS:
            scene = generate(SEED, preset, "large")
            self.assertFalse(any("tower" in (b.get("tags") or ())
                                 for b in scene["beams"]), preset)
            self.assertFalse(any("tower" in (b.get("tags") or ())
                                 for b in scene["blocks"]), preset)
            glass = [b for b in scene["blocks"] if b.get("material") == "glass"]
            # glazing is bays and strips, never a wall: keep it under 3%
            self.assertLessEqual(len(glass) / len(scene["blocks"]), 0.03, preset)


class V2DeterminismTests(unittest.TestCase):
    def test_same_seed_same_scene(self):
        for preset in V2_PRESETS:
            self.assertEqual(generate(123, preset, "medium"),
                             generate(123, preset, "medium"), preset)

    def test_different_seeds_differ(self):
        for preset in V2_PRESETS:
            a = generate(1, preset, "small")
            b = generate(2, preset, "small")
            self.assertNotEqual(a["beams"], b["beams"], preset)

    def test_small_and_medium_scenes_validate(self):
        # cheap structural re-check scoped to the v2 presets
        from lib.girders.schema import validate
        for preset in V2_PRESETS:
            for scale in ("small", "medium"):
                for seed in (7, 42):
                    self.assertEqual(validate(generate(seed, preset, scale)), [],
                                     (preset, seed, scale))


@unittest.skipUnless(os.environ.get("GIRDERS_SLOW") == "1",
                     "set GIRDERS_SLOW=1 to run the slow large-scene validator")
class SlowLargeValidation(unittest.TestCase):
    """The full support-check on ~300k-beam scenes (minutes each)."""

    def test_large_scenes_validate(self):
        from lib.girders.schema import validate
        for preset in V2_PRESETS:
            self.assertEqual(validate(generate(SEED, preset, "large")), [], preset)


if __name__ == "__main__":
    unittest.main()
