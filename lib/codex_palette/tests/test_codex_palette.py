"""Invariants for the Codex palette studies, rather than image snapshots."""
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import numpy as np
from shapely.geometry import Polygon

from lib.codex_palette import guilloche, historyflow, marbling
from lib.codex_palette.studies import (NOTA_ARENA, NOTA_V_NODES, guilloche_plate, history_plate,
                                       marbling_plate)
from lib.codex_palette.tubes import adapt, chains, disc_mesh

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / "sources/codex-intervallorum"
PREVIEWS = ROOT / "examples/previews/codex-palette"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=t@example.org",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


class HistoryFlowTests(unittest.TestCase):
    def test_classes_and_bands_from_a_small_repository(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _git(repo, "init", "-q", "-b", "main")
            (repo / "a.md").write_text("one\ntwo\nthree\n")
            _git(repo, "add", ".")
            _git(repo, "commit", "-q", "-m", "Import")
            _git(repo, "checkout", "-q", "-b", "codex/edit")
            (repo / "a.md").write_text("one\nTWO\nthree\nfour\n")
            _git(repo, "commit", "-q", "-am", "Edit two, add four")
            _git(repo, "checkout", "-q", "main")
            _git(repo, "merge", "-q", "--no-ff", "codex/edit", "-m",
                 "Merge pull request #1 from someone/codex/edit")
            _git(repo, "checkout", "-q", "-b", "other")
            (repo / "a.md").write_text("zero\none\nTWO\nthree\nfour\n")
            _git(repo, "commit", "-q", "-am", "Add zero\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
            _git(repo, "checkout", "-q", "main")
            _git(repo, "merge", "-q", "--no-ff", "other", "-m", "Merge branch other")
            record = historyflow.extract(repo, ["a.md"], "main")
        self.assertEqual(len(record["versions"]), 3)
        classes = {o["subject"]: o["class"] for o in record["origins"]}
        self.assertEqual(classes, {"Import": "base", "Edit two, add four": "codex", "Add zero": "claude"})
        lines = historyflow.versions_from_runs(record)
        self.assertEqual([len(v) for v in lines], [3, 4, 5])
        self.assertEqual(sum(l[3] for l in lines[0]), len("one\ntwo\nthree\n"))
        # "one" and "three" survive the edit; "two" does not, "TWO" and "four" begin.
        first = historyflow.transitions(lines[0], lines[1])
        self.assertEqual(first, [(0, 1, 0, 1, "base"), (2, 3, 2, 3, "base")])
        # Everything in version 2 survives into version 3, shifted down one line.
        second = historyflow.transitions(lines[1], lines[2])
        self.assertEqual(sum(i1 - i0 for i0, i1, *_ in second), 4)
        self.assertTrue(all(j0 == i0 + 1 for i0, _, j0, _, _ in second))
        plate, _ = history_plate(record)
        self.assertGreater(len(plate.strokes), 10)

    def test_recorded_input_rebuilds(self):
        record = json.loads((PREVIEWS / "history-input.json").read_text(encoding="utf-8"))
        manifest = json.loads((PREVIEWS / "manifest.json").read_text(encoding="utf-8"))
        item = next(i for i in manifest["items"] if i["study"] == "history-flow")
        plate, _ = history_plate(record, item["settings"]["spacing"])
        self.assertEqual(len(plate.strokes), item["settings"]["stroke_count"])
        self.assertEqual([v["characters"] for v in plate.metadata["versions"]],
                         [v["characters"] for v in item["settings"]["versions"]])


class TubeTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(5)
        nodes = [(20, 10), (30, 28), (10, 28)]
        self.points, self.edges, self.lengths, self.food = disc_mesh(nodes, (20, 20), 18, 3.0, self.rng)

    def test_food_nodes_are_mesh_vertices(self):
        np.testing.assert_allclose(self.points[self.food], [(20, 10), (30, 28), (10, 28)])
        self.assertTrue(np.all(self.lengths > 0))

    def test_one_step_conserves_flux(self):
        _, _, Q = adapt(self.points, self.edges, self.lengths, self.food, np.random.default_rng(1),
                        steps=1, flux=2.0)
        net = np.zeros(len(self.points))
        np.add.at(net, self.edges[:, 0], Q)
        np.add.at(net, self.edges[:, 1], -Q)
        source, sink = int(np.argmax(net)), int(np.argmin(net))
        self.assertAlmostEqual(net[source], 2.0, places=6)
        self.assertAlmostEqual(net[sink], -2.0, places=6)
        self.assertTrue({source, sink} <= set(self.food.tolist()))
        others = np.setdiff1d(np.arange(len(net)), [source, sink])
        self.assertLess(np.abs(net[others]).max(), 1e-6)

    def test_repeatable_and_positive(self):
        a = adapt(self.points, self.edges, self.lengths, self.food, np.random.default_rng(9), steps=40)[0]
        b = adapt(self.points, self.edges, self.lengths, self.food, np.random.default_rng(9), steps=40)[0]
        np.testing.assert_array_equal(a, b)
        self.assertTrue(np.all(a > 0))

    def test_chains_use_every_edge_once(self):
        found = []
        for path, _ in chains(self.edges, np.ones(len(self.edges))):
            found += [tuple(sorted(e)) for e in zip(path[:-1], path[1:])]
        self.assertEqual(sorted(found), sorted(map(tuple, self.edges)))

    def test_nota_v_inputs_match_the_book_snapshot(self):
        tree = ast.parse((SNAPSHOT / "books/05_notoria/plates/notae.py").read_text())
        runs = next(n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "RUNS")
        nodes = ast.literal_eval(runs)["v"]["nodes"]
        self.assertEqual([tuple(n[:2]) for n in nodes], list(NOTA_V_NODES))
        source = (SNAPSHOT / "books/05_notoria/fields/physarum.py").read_text()
        self.assertIn('"arena_radius": %s' % NOTA_ARENA, source)


class MarblingTests(unittest.TestCase):
    def test_selected_print_has_no_crossings_after_svg_rounding(self):
        from shapely.geometry import LineString
        from shapely.strtree import STRtree
        # The previously committed seed-7 gel-git had 29 crossing pairs.
        for variant in range(3):
            plate, _ = marbling_plate(7, variant)
            paths = [LineString(np.round(s.points, 3)) for s in plate.strokes]
            hits = STRtree(paths).query(paths, predicate="crosses")
            self.assertFalse(np.any(hits[0] < hits[1]), variant)
            self.assertTrue(all(p.is_simple for p in paths))
            self.assertEqual(plate.metadata["print_repair"]["crossing_pairs_after"], 0)

    def test_crossing_repair_preserves_ink_owner_and_most_length(self):
        from shapely.geometry import LineString
        paths, owners, report = marbling.print_paths([
            np.array([[0, 5], [10, 5]]), np.array([[5, 0], [5, 10]])])
        self.assertEqual(owners, [0, 1, 1])
        self.assertEqual(report["crossing_pairs_before"], 1)
        self.assertLess(report["removed_length_mm"], .2)
        self.assertFalse(LineString(paths[0]).crosses(LineString(paths[1])))

    def test_requested_site_count_and_invalid_sampling(self):
        for count in (1, 5, 7, 10):
            lines, tags = marbling.stone_ground(np.random.default_rng(2), (0, 0, 60, 60),
                                                count, 2, rings=2)
            self.assertEqual(len(lines), 2 * count)
            self.assertEqual(len(tags), len(lines))
        for step in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                marbling.resample([], step)

    def test_drop_moves_a_point_to_the_area_preserving_radius(self):
        out = marbling.drop([np.array([[3.0, 4.0], [3.0, 4.0001]])], (0, 0), 2.0, step=10)
        self.assertAlmostEqual(float(np.hypot(*out[0][0])), np.sqrt(25 + 4), places=6)
        self.assertEqual(len(out), 2)            # the drop adds its own outline

    def test_tine_is_a_shear_and_keeps_area(self):
        square = np.array([[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]], float)
        moved = marbling.tine([square], (15, 0), (0, 1), 6.0, 2.0, step=.05)[0]
        self.assertAlmostEqual(Polygon(moved).area, 100.0, delta=.3)

    def test_nested_boundaries_never_cross(self):
        rng = np.random.default_rng(3)
        lines, _ = marbling.stone_ground(rng, (0, 0, 60, 60), 6, 9.0, rings=2, step=.4)
        lines = marbling.comb(lines, (2, 0), (0, 1), (1, 0), 8.0, 7, 9.0, 3.0, alternate=True, step=.4)
        from shapely.geometry import LineString
        rings = [LineString(p) for p in lines]
        for i in range(len(rings)):
            for j in range(i + 1, len(rings)):
                self.assertFalse(rings[i].crosses(rings[j]), (i, j))

    def test_resample_bounds_segment_length(self):
        p = marbling.resample([np.array([[0, 0], [10, 0], [10, 3]], float)], .7)[0]
        self.assertLessEqual(np.hypot(*np.diff(p, axis=0).T).max(), .7 + 1e-12)
        np.testing.assert_allclose(p[[0, -1]], [[0, 0], [10, 3]])

    def test_plate_is_repeatable(self):
        a, b = marbling_plate(7, 1)[0].svg(), marbling_plate(7, 1)[0].svg()
        self.assertEqual(a, b)


class GuillocheTests(unittest.TestCase):
    def test_trochoid_closes(self):
        for kind in ("hypo", "epi"):
            p = guilloche.trochoid((0, 0), 96, 36, 22, kind)
            np.testing.assert_allclose(p[0], p[-1], atol=1e-9)

    def test_rim_and_rosette_counts(self):
        self.assertEqual(len(guilloche.reeded_rim((0, 0), 10, 200)), 200)
        self.assertEqual(len(guilloche.rosette((0, 0), 2, 9, 27, 18, .6, .1)), 27)

    def test_plate_from_recorded_catalogue_numbers(self):
        data = json.loads((PREVIEWS / "guilloche-input.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["tiers"]), 7)
        self.assertEqual(len(data["handoffs"]), 21)
        for t in data["tiers"]:
            self.assertEqual(t["competence"], 6 - t["authority"])
        plate, _ = guilloche_plate(data["tiers"], data["handoffs"])
        # Paimon's 200 legions appear as 200 reeds on his rim.
        reeds = [s for s in plate.strokes if len(s.points) == 2 and abs(
            np.hypot(*(s.points[1] - s.points[0])) - .9) < 1e-6]
        self.assertEqual(len(reeds), sum(int(t["legions"]) for t in data["tiers"]))

    def test_book_importer_reads_the_svg(self):
        importer = SNAPSHOT / "common/plot/svgimport.py"
        spec = importlib.util.spec_from_file_location("book_svgimport", importer)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plate = marbling_plate(7, 0)[0]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "plate.svg"
            path.write_text(plate.svg())
            imported = module.strokes_from_svg(path)
        # The SVG writes the black group, then the red group.
        from lib.process_art.drawing import INK, RED
        expected = [s for s in plate.strokes if s.color == INK] + [s for s in plate.strokes if s.color == RED]
        self.assertEqual(len(imported), len(expected))
        for (color, width, points), original in zip(imported, expected):
            self.assertEqual(color, original.color)
            self.assertAlmostEqual(width, original.width)
            np.testing.assert_allclose(points, original.points, atol=.00051)


class PackagingTests(unittest.TestCase):
    def test_pack_records_actual_revisions_and_preview_sizes(self):
        from examples import make_codex_palette as demo
        from lib.process_art.drawing import Plate
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out"
            out.mkdir()
            for k, (stem, _, _) in enumerate(demo.SELECTION):
                plate = Plate("Fixture")
                (out / f"{stem}.svg").write_text(plate.svg())
                Image.new("RGB", (240, 320), "white").save(out / f"{stem}.png")
                meta = {"study": stem, "preview_width_px": 240}
                if k != 2:
                    meta["book_revision"] = "a" * 40 if k == 0 else "b" * 40
                (out / f"{stem}.json").write_text(json.dumps(meta))
            for name in ("history-input.json", "guilloche-input.json"):
                (out / name).write_text("{}")
            manifest = demo.package(out, Path(d) / "previews")
            self.assertIsNone(manifest["book_revision"])
            self.assertEqual(manifest["book_revisions"], ["a" * 40, "b" * 40])
            self.assertEqual(manifest["preview_widths_px"], [240])
            self.assertNotIn(demo.PINNED, manifest["book_revisions"])

    def test_catalogue_resolves_a_named_revision_to_a_commit(self):
        from examples import make_codex_palette as demo
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            _git(repo, "init", "-q", "-b", "main")
            path = repo / demo.CATALOGUE
            path.parent.mkdir(parents=True)
            path.write_text('{"tiers": [], "handoffs": []}')
            _git(repo, "add", ".")
            _git(repo, "commit", "-q", "-m", "A different book revision")
            expected = subprocess.check_output(["git", "-C", d, "rev-parse", "HEAD"], text=True).strip()
            data = demo.catalogue(SimpleNamespace(codex=repo, rev="main"))
            self.assertEqual(data["book_revision"], expected)
            self.assertIn("@" + expected + ":", data["source"])


if __name__ == "__main__":
    unittest.main()
