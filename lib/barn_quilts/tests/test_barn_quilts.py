"""Topology, reproducibility, composition, and SVG portability checks."""

from dataclasses import replace
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib.barn_quilts import PATTERNS, Patch, QuiltSpec, block, render_fragment, render_svg, unique_edges

NS = "{http://www.w3.org/2000/svg}"


def area(points):
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a, b in
                   zip(points, points[1:]+points[:1])))/2


def inside(point, polygon):
    # Independent ray crossing, rather than the generator's construction rules.
    x, y = point
    yes = False
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            if x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
                yes = not yes
    return yes


class QuiltTests(unittest.TestCase):
    def test_exact_square_coverage_and_no_overlaps(self):
        rng = random.Random(487)
        for name in PATTERNS:
            for detail in (2, 4, 8):
                with self.subTest(name=name, detail=detail):
                    patches = block(name, detail=detail)
                    self.assertAlmostEqual(sum(area(p.points) for p in patches), 1, places=12)
                    self.assertTrue(all(area(p.points) > 0 for p in patches))
                    self.assertTrue(all(0 <= x <= 1 and 0 <= y <= 1 for p in patches for x, y in p.points))
                    for _ in range(600):
                        point = (rng.random(), rng.random())
                        self.assertEqual(sum(inside(point, p.points) for p in patches), 1, (name, detail, point))

    def test_shared_edge_is_split_at_t_junction(self):
        patches = [Patch(((0,0),(0.5,0),(0.5,1),(0,1)), 0),
                   Patch(((0.5,0),(1,0),(1,0.5),(0.5,0.5)), 1),
                   Patch(((0.5,0.5),(1,0.5),(1,1),(0.5,1)), 2)]
        edges = unique_edges(patches)
        shared = [e for e in edges if e[0][0] == e[1][0] == 0.5]
        self.assertEqual(len(shared), 2)
        self.assertAlmostEqual(sum(math.dist(*e) for e in shared), 1)

    def test_every_family_material_and_mode_parses(self):
        for name in PATTERNS:
            for material in ("wood", "mdo", "aluminum", "steel"):
                for mode in ("painted", "flat", "outline"):
                    with self.subTest(name=name, material=material, mode=mode):
                        spec = QuiltSpec(pattern=name, material=material, mode=mode, texture=.7, wear=.7)
                        svg = render_svg(spec)
                        root = ET.fromstring(svg)
                        self.assertEqual(root.attrib["viewBox"], "0 0 1000 1000")
                        self.assertFalse(root.findall(".//"+NS+"image"))
                        self.assertFalse(root.findall(".//"+NS+"filter"))
                        ids = [e.attrib["id"] for e in root.iter() if "id" in e.attrib]
                        self.assertEqual(len(ids), len(set(ids)))
                        for e in root.iter():
                            for v in e.attrib.values():
                                if v.startswith("url(#"):
                                    self.assertIn(v[5:-1], ids)
                        if mode == "outline":
                            self.assertFalse(root.findall(".//"+NS+"polygon"))
                            self.assertFalse(root.findall(".//"+NS+"circle"))
                        if mode != "painted":
                            self.assertNotIn("-surface\"", svg)
                            self.assertNotIn("-wear\"", svg)

    def test_surface_seed_is_repeatable_and_flat_geometry_is_seed_independent(self):
        a = QuiltSpec(pattern="sawtooth-star", seed=0)
        self.assertEqual(render_svg(a), render_svg(a))
        self.assertNotEqual(render_svg(a), render_svg(replace(a, seed=1)))
        self.assertEqual(block(a.pattern, seed=0), block(a.pattern, seed=1))
        self.assertEqual(block("random", seed=3), block("random", seed=3))

    def test_custom_palette_metadata_and_rotation(self):
        colors = ("#ffffff", "#222222", "#800000", "#ccaa00")
        spec = QuiltSpec(pattern="ohio-star", palette="random", rotation=270, colors=colors, mode="flat")
        root = ET.fromstring(render_svg(spec))
        metadata = json.loads(root.find(NS+"metadata").text)
        self.assertIn(metadata["resolved_pattern"], PATTERNS)
        self.assertEqual(metadata["spec"]["colors"], list(colors))
        self.assertIn("rotate(270 500 500)", render_svg(spec))
        fills = {e.attrib.get("fill") for e in root.iter()}
        self.assertTrue(set(colors[:3]).issubset(fills))

    def test_fragments_have_no_duplicate_ids_when_named(self):
        document = '<svg xmlns="http://www.w3.org/2000/svg">'+render_fragment(id_prefix="a")+render_fragment(id_prefix="b")+'</svg>'
        root = ET.fromstring(document)
        ids = [e.attrib["id"] for e in root.iter() if "id" in e.attrib]
        self.assertEqual(len(ids), len(set(ids)))
        with self.assertRaises(ValueError):
            render_fragment(id_prefix='a\" onload=\"alert(1)')

    def test_invalid_specs_are_rejected(self):
        for changes in ({"texture":float("nan")}, {"wear":-1}, {"texture":float("inf")},
                        {"size_mm":0}, {"border":.3}, {"rotation":45}, {"detail":1},
                        {"material":"rust"}, {"colorway":3}, {"seed":"4"},
                        {"colors":("red",)*4}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                render_svg(replace(QuiltSpec(), **changes))

    def test_cli_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"nested"/"test.svg"
            cmd = [sys.executable, str(ROOT/"lib/barn_quilts/generator.py"), "--output", str(path),
                   "--pattern", "log-cabin", "--material", "steel", "--mode", "outline"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            ET.parse(path)
            bad = subprocess.run(cmd+["--texture", "nan"], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)
            self.assertIn("finite", bad.stderr)


if __name__ == "__main__":
    unittest.main()
