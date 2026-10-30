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


def _groups_by_name(scene):
    return {g["name"]: g["id"] for g in scene["groups"]}


def _deck_geometry(scene, gid):
    """Deck axis, extent, elevation and width of a rib/deck group.

    Reconstructed from the truss chords (always complete, unlike the deck
    plate blocks, which the density gate may drop) and the deck blocks
    (for the width).
    """
    chords = [b for b in scene["beams"] if b["group"] == gid
              and "chord" in b["tags"]]
    assert len(chords) > 8, "group has no chord truss"
    longest = max(chords, key=lambda b: np.linalg.norm(np.subtract(b["b"], b["a"])))
    u = np.subtract(longest["b"][:2], longest["a"][:2])
    u = u / np.linalg.norm(u)
    ss = [min(np.array(b["a"][:2]) @ u, np.array(b["b"][:2]) @ u) for b in chords]
    s_min, s_max = min(ss), max(ss)
    deck_z = min(min(b["a"][2], b["b"][2]) for b in chords)
    blocks = [b for b in scene["blocks"] if b["group"] == gid
              and "deck" in b["tags"]]
    width = max(b["size"][1] for b in blocks) if blocks else None
    return u, s_min, s_max, deck_z, width


class TrussElevationTests(unittest.TestCase):
    """Every rib/deck truss sits at its deck elevation, never at ground."""

    def _check(self, preset, scale):
        scene = generate(SEED, preset, scale)
        names = _groups_by_name(scene)
        checked = 0
        for g in scene["groups"]:
            if not (g["name"].startswith("rib-") or g["name"].startswith("deck-")):
                continue
            chords = [b for b in scene["beams"] if b["group"] == g["id"]
                      and "chord" in b["tags"]]
            self.assertGreater(len(chords), 8, g["name"])
            zs = [z for b in chords for z in (b["a"][2], b["b"][2])]
            chord_min, chord_max = min(zs), max(zs)
            _, _, _, deck_z, _ = _deck_geometry(scene, g["id"])
            self.assertAlmostEqual(chord_min, deck_z, delta=0.6, msg=g["name"])
            self.assertGreater(chord_min, 6.0, g["name"])
            self.assertLessEqual(chord_max - deck_z, 18.0 + 0.6, g["name"])
            checked += 1
        self.assertGreater(checked, 0, preset)

    def test_fault_spine_ribs_sit_at_deck_elevation(self):
        self._check("fault-spine", "medium")

    def test_delta_tiers_sit_at_deck_elevation(self):
        self._check("suspended-delta", "medium")

    def test_large_scenes_have_no_ground_level_trusses(self):
        for preset in V2_PRESETS:
            scene = generate(SEED, preset, "large")
            for g in scene["groups"]:
                if not (g["name"].startswith("rib-") or g["name"].startswith("deck-")):
                    continue
                chords = [b for b in scene["beams"] if b["group"] == g["id"]
                          and "chord" in b["tags"]]
                zs = [z for b in chords for z in (b["a"][2], b["b"][2])]
                self.assertGreater(min(zs), 6.0, (preset, g["name"]))


class TierConnectionTests(unittest.TestCase):
    """Connecting steel physically reaches both ends of every deck tier."""

    def _check(self, scale):
        scene = generate(SEED, "suspended-delta", scale)
        for g in scene["groups"]:
            if not g["name"].startswith("deck-"):
                continue
            gid = g["id"]
            u, s_min, s_max, deck_z, _ = _deck_geometry(scene, gid)

            def s_of(b):
                return (np.array(b["a"][:2]) + np.array(b["b"][:2])) @ u / 2.0

            # stringers span the inhabited floors end to end
            stringers = [b for b in scene["beams"] if b["group"] == gid
                         and "stringer" in b["tags"]]
            self.assertGreaterEqual(len(stringers), 4, g["name"])
            str_s = sorted(s_of(b) for b in stringers)
            self.assertLessEqual(str_s[0], s_min + 1.5, g["name"])
            self.assertGreaterEqual(str_s[-1], s_max - 1.5, g["name"])
            # struts and knees (they live in the buttress/hub groups) reach
            # the deck's own ends
            def near_end(b, s_end, tol=2.5):
                return (abs(np.array(b["a"][:2]) @ u - s_end) < tol or
                        abs(np.array(b["b"][:2]) @ u - s_end) < tol)

            for kind, s_end in (("strut", s_max), ("strut", s_min), ("knee", s_max)):
                members = [b for b in scene["beams"] if kind in b["tags"]]
                near = sum(1 for b in members if near_end(b, s_end))
                self.assertGreaterEqual(near, 2, (g["name"], kind, round(s_end, 1)))

    def test_medium_tiers_are_tied_at_both_ends(self):
        self._check("medium")

    def test_large_tiers_are_tied_at_both_ends(self):
        self._check("large")

    def test_buttress_frames_reach_the_upper_tiers(self):
        scene = generate(SEED, "suspended-delta", "large")
        deck_zs = [_deck_geometry(scene, g["id"])[3]
                   for g in scene["groups"] if g["name"].startswith("deck-")]
        self.assertGreater(len(deck_zs), 10)
        transfer_tops = []
        for g in scene["groups"]:
            if g["name"].startswith("buttress-"):
                cols = [b for b in scene["beams"] if b["group"] == g["id"]
                        and "transfer" in b["tags"]]
                corners = [b for b in scene["beams"] if b["group"] == g["id"]
                           and b["tags"][1:3] == ["buttress", "column"]]
                transfer_tops += [max(b["a"][2], b["b"][2]) for b in cols]
                if corners and int(g["name"].split("-")[1]) <= 7:
                    top = max(max(b["a"][2], b["b"][2]) for b in corners)
                    self.assertGreaterEqual(top, max(deck_zs) + 3.0, g["name"])
        self.assertGreaterEqual(max(transfer_tops), max(deck_zs) - 0.5)
        # the hub tower rises above the top tier
        tower = _groups_by_name(scene).get("hub-tower")
        self.assertIsNotNone(tower)
        cols = [b for b in scene["beams"] if b["group"] == tower
                and "column" in b["tags"]]
        top = max(max(b["a"][2], b["b"][2]) for b in cols)
        self.assertGreaterEqual(top, max(deck_zs) + 4.0)


class DeltaTierVarietyTests(unittest.TestCase):
    """Large delta tiers vary in extent and width, with one tier missing."""

    def test_tier_variety_and_missing_tier(self):
        scene = generate(SEED, "suspended-delta", "large")
        nt = scene["generator"]["params"]["tiers"]
        by_branch = {}
        for g in scene["groups"]:
            if not g["name"].startswith("deck-"):
                continue
            branch = int(g["name"][5:7]) // 10
            _, s_min, s_max, _, width = _deck_geometry(scene, g["id"])
            by_branch.setdefault(branch, []).append((s_min, s_max, width))
        for branch, tiers in sorted(by_branch.items()):
            self.assertEqual(len(tiers), nt - 1, (branch, nt))
            starts = [t[0] for t in tiers]
            ends = [t[1] for t in tiers]
            widths = [t[2] for t in tiers]
            self.assertGreaterEqual(max(starts) - min(starts), 8.0, branch)
            self.assertGreaterEqual(max(ends) - min(ends), 8.0, branch)
            self.assertGreaterEqual(max(widths) / min(widths), 1.2, branch)
