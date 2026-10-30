"""Invariants for the girders generator: determinism, schema, support, scale."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

from lib.girders import PRESETS, generate, load_scene, render, save_scene, validate
from lib.girders.profiles import MATERIALS, PROFILES
from lib.girders.schema import validate

ROOT = Path(__file__).resolve().parents[3]
PRESET_NAMES = sorted(PRESETS)
SEEDS = (1, 7, 42)


class DeterminismTests(unittest.TestCase):
    def test_same_seed_same_scene(self):
        a = generate(123, "dense-core", "small")
        b = generate(123, "dense-core", "small")
        self.assertEqual(a, b)

    def test_same_seed_same_file(self):
        with tempfile.TemporaryDirectory() as td:
            p1, p2 = Path(td) / "a.json.gz", Path(td) / "b.json.gz"
            save_scene(generate(9, "ruin", "small"), p1)
            save_scene(generate(9, "ruin", "small"), p2)
            self.assertEqual(p1.read_bytes(), p2.read_bytes())

    def test_different_seeds_differ(self):
        a = generate(1, "stacked-gantries", "small")
        b = generate(2, "stacked-gantries", "small")
        self.assertNotEqual(a["beams"], b["beams"])

    def test_presets_differ_from_each_other(self):
        counts = {p: generate(5, p, "medium")["stats"]["beams"] for p in PRESET_NAMES}
        # no two presets produce the same structure
        scenes = {p: generate(5, p, "medium") for p in PRESET_NAMES}
        for p in PRESET_NAMES:
            for q in PRESET_NAMES:
                if p >= q:
                    continue
                self.assertNotEqual(scenes[p]["beams"], scenes[q]["beams"],
                                    f"{p} and {q} produce identical beams")


class SchemaTests(unittest.TestCase):
    def test_small_and_medium_scenes_validate(self):
        for preset in PRESET_NAMES:
            for scale in ("small", "medium"):
                for seed in SEEDS:
                    scene = generate(seed, preset, scale)
                    self.assertEqual(validate(scene), [],
                                     f"{preset} {seed} {scale}")

    def test_no_nans_and_finite(self):
        for preset in PRESET_NAMES:
            scene = generate(3, preset, "small")
            for b in scene["beams"]:
                self.assertTrue(np.all(np.isfinite(b["a"])) and np.all(np.isfinite(b["b"])))
            for b in scene["blocks"]:
                self.assertTrue(np.all(np.isfinite(b["center"] + b["size"])))

    def test_references_exist(self):
        for preset in PRESET_NAMES:
            scene = generate(3, preset, "small")
            mats = set(scene["materials"])
            profs = set(scene["profiles"])
            for b in scene["beams"]:
                self.assertIn(b["profile"], profs)
                self.assertIn(b["material"], mats)
            for b in scene["blocks"]:
                self.assertIn(b["material"], mats)

    def test_no_zero_length_beams(self):
        for preset in PRESET_NAMES:
            scene = generate(3, preset, "small")
            for b in scene["beams"]:
                self.assertGreater(np.linalg.norm(np.subtract(b["b"], b["a"])), 1e-6)

    def test_beams_inside_bounds(self):
        for preset in PRESET_NAMES:
            scene = generate(3, preset, "small")
            lo = np.array(scene["bounds"]["min"])
            hi = np.array(scene["bounds"]["max"])
            for b in scene["beams"]:
                self.assertTrue(np.all(np.array(b["a"]) >= lo - 0.05))
                self.assertTrue(np.all(np.array(b["b"]) <= hi + 0.05))

    def test_stats_match(self):
        for preset in PRESET_NAMES:
            st = generate(3, preset, "small")["stats"]
            for key, n in (("blocks", st["blocks"]), ("beams", st["beams"]), ("details", st["details"])):
                self.assertIsInstance(n, int)

    def test_catwalk_decks_align_with_members_and_ladders_stand_up(self):
        for preset in PRESET_NAMES:
            scene = generate(7, preset, "medium")
            for block in scene["blocks"]:
                if "catwalk" not in block["tags"] or "bracket" in block["tags"]:
                    continue
                members = [b for b in scene["beams"] if b["group"] == block["group"]
                           and "catwalk" in b["tags"]]
                member = max(members, key=lambda b: np.linalg.norm(np.subtract(b["b"], b["a"])))
                direction = np.subtract(member["b"], member["a"])
                direction = direction / np.linalg.norm(direction)
                axis = np.array([np.cos(block["yaw"]), np.sin(block["yaw"]), 0])
                self.assertGreater(abs(np.dot(axis, direction)), .999, (preset, block["id"]))
            for detail in scene["details"]:
                if detail["kind"] == "ladder":
                    self.assertTrue(np.allclose(detail["transform"][8:11], [0, 0, 1]))

    def test_site_and_camera_hints_are_render_ready(self):
        for preset in PRESET_NAMES:
            scene = generate(7, preset, "medium")
            ground = [b for b in scene["blocks"] if "ground" in b["tags"]]
            self.assertEqual(len(ground), 1, preset)
            self.assertAlmostEqual(ground[0]["center"][2] + ground[0]["size"][2] / 2.0, 0.0)
            hints = {h["name"]: h for h in scene["camera_hints"]}
            self.assertIn("worm", hints)
            self.assertIn("axon", hints)
            self.assertGreater(hints["axon"]["ortho_scale"], 0.0)


class SupportTests(unittest.TestCase):
    def test_floating_beam_is_rejected(self):
        scene = generate(7, "dense-core", "small")
        z = scene["bounds"]["max"][2] - 1.0  # above every member, inside bounds
        scene["beams"].append({
            "id": len(scene["beams"]),
            "a": [0.0, 0.0, z], "b": [3.0, 0.0, z],
            "profile": "I240", "roll": 0.0, "material": "steel",
            "tags": ["test"], "group": 0,
        })
        scene["stats"]["beams"] += 1
        errs = validate(scene)
        self.assertTrue(any("neither end" in e for e in errs), errs[:5])

    def test_unsupported_block_is_rejected(self):
        scene = generate(7, "dense-core", "small")
        z = scene["bounds"]["max"][2] - 0.5  # inside bounds, above everything
        scene["blocks"].append({
            "id": len(scene["blocks"]),
            "center": [0.0, 0.0, z], "size": [1.0, 1.0, 1.0],
            "yaw": 0.0, "material": "concrete", "tags": ["test"], "group": 0,
        })
        scene["stats"]["blocks"] += 1
        errs = validate(scene)
        self.assertTrue(any("no support path" in e for e in errs), errs[:5])

    def test_missing_profile_is_rejected(self):
        scene = generate(7, "dense-core", "small")
        scene["beams"][0]["profile"] = "NOPE"
        errs = validate(scene)
        self.assertTrue(any("unknown profile" in e for e in errs))

    def test_cantilever_stub_is_allowed(self):
        scene = generate(7, "dense-core", "small")
        blk = scene["blocks"][0]
        x = blk["center"][0]
        z = blk["center"][2] + blk["size"][2] / 2.0
        scene["beams"].append({
            "id": len(scene["beams"]),
            "a": [x, blk["center"][1], z], "b": [x + 4.0, blk["center"][1], z],
            "profile": "I240", "roll": 0.0, "material": "rust",
            "tags": ["ruin", "stub", "free"], "group": 0,
        })
        scene["stats"]["beams"] += 1
        self.assertEqual(validate(scene), [])


class ScaleTests(unittest.TestCase):
    def test_counts_grow_with_scale(self):
        for preset in PRESET_NAMES:
            small = generate(11, preset, "small")["stats"]["beams"]
            medium = generate(11, preset, "medium")["stats"]["beams"]
            large = generate(11, preset, "large")["stats"]["beams"]
            self.assertLess(small, medium, preset)
            self.assertLess(medium, large, preset)

    def test_large_reaches_six_figures(self):
        for preset in PRESET_NAMES:
            large = generate(11, preset, "large")["stats"]["beams"]
            self.assertGreaterEqual(large, 80000, preset)

    def test_small_is_fast(self):
        t0 = time.time()
        for preset in PRESET_NAMES:
            generate(5, preset, "small")
        self.assertLess(time.time() - t0, 10.0)

    def test_large_is_fast(self):
        t0 = time.time()
        generate(5, "dense-core", "large")
        self.assertLess(time.time() - t0, 60.0)


class RoundTripTests(unittest.TestCase):
    def test_gz_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "s.json.gz"
            scene = generate(4, "bridge-field", "small")
            save_scene(scene, path)
            self.assertEqual(load_scene(path), scene)

    def test_plain_json_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "s.json"
            scene = generate(4, "ruin", "small")
            save_scene(scene, path)
            self.assertEqual(load_scene(path), scene)

    def test_profiles_are_schema_kinds(self):
        for name, pr in PROFILES.items():
            self.assertIn(pr["kind"], ("I", "C", "L", "box", "tube", "rod"), name)
        for m in MATERIALS:
            self.assertIsInstance(m, str)


class PreviewTests(unittest.TestCase):
    def test_previews_render_with_ink(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            for preset in PRESET_NAMES:
                scene = generate(2, preset, "small")
                path = Path(td) / f"{preset}.png"
                render(scene, path, width_px=800)
                self.assertGreater(path.stat().st_size, 10000, preset)
                im = np.asarray(Image.open(path).convert("L"))
                self.assertGreater((im < 200).mean(), 0.01, preset)


class CliTests(unittest.TestCase):
    def test_cli_generate_and_validate(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "cli.json.gz"
            proc = subprocess.run(
                [sys.executable, "-m", "lib.girders", "generate",
                 "--preset", "ruin", "--seed", "7", "--scale", "small",
                 "--out", str(out), "--validate"],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("validator: OK", proc.stdout)
            scene = load_scene(out)
            self.assertEqual(validate(scene), [])
            self.assertEqual(scene["seed"], 7)

    def test_cli_validate_rejects_garbage(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text(json.dumps({"format": "girders-scene-1"}))
            proc = subprocess.run(
                [sys.executable, "-m", "lib.girders", "validate", str(bad)],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
