"""Checks for lib/numerics. Run from the repository root:
python -m unittest discover -s lib/numerics/tests -v
"""
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aq  # noqa: E402
import numogram as ng  # noqa: E402
import xenotation as tx  # noqa: E402


class AQTests(unittest.TestCase):
    def test_aqcalc_reference_values(self):
        # The aqcalc library's own checks.
        self.assertEqual(aq.aq("Hello, World!"), 214)
        self.assertEqual(aq.aq("###"), 0)

    def test_base36_values(self):
        self.assertEqual([aq.char_value(c) for c in "09AZaz"], [0, 9, 10, 35, 10, 35])
        self.assertIsNone(aq.char_value("-"))
        self.assertEqual(aq.aq("2026"), 2 + 0 + 2 + 6)
        self.assertEqual(aq.aq("HIC ET NUNC"), 47 + 43 + 88)

    def test_case_spacing_and_accents_do_not_change_values(self):
        self.assertEqual(aq.aq("hic et nunc"), aq.aq("H.I.C-E T\nNUNC"))
        self.assertEqual(aq.aq("café"), aq.aq("CAFE"))
        self.assertEqual(aq.aq(""), 0)

    def test_words(self):
        self.assertEqual(aq.words("Hic et Nunc"), [("Hic", 47), ("et", 43), ("Nunc", 88)])
        self.assertEqual(aq.words("0 ###"), [("0", 0)])

    def test_reduction_and_cumulation(self):
        self.assertEqual(aq.reduce(214), 7)
        self.assertEqual(aq.reduce(0), 0)
        self.assertEqual(aq.reduce(9), 9)
        self.assertEqual(aq.reduction_chain(99), [99, 18, 9])
        self.assertEqual([aq.cumulate(n) for n in range(10)], [0, 1, 3, 6, 10, 15, 21, 28, 36, 45])
        for n in range(1, 500):
            self.assertEqual(aq.reduce(n), 1 + (n - 1) % 9)

    def test_rule_and_matches(self):
        self.assertTrue(0 <= aq.rule("anything at all") <= 255)
        self.assertEqual(aq.rule("Hello, World!"), 214)
        # AB = 10 + 11 = 21 = L; the numeral "21" is 2 + 1, not 21.
        self.assertEqual(aq.matches("AB", ["BA", "C", "AC", "L", "21"]), ["BA", "L"])


class NumogramTests(unittest.TestCase):
    def test_syzygies_are_nine_sum_twins(self):
        self.assertEqual(sorted(z for p in ng.SYZYGIES for z in p), list(range(10)))
        for lo, hi in ng.SYZYGIES:
            self.assertEqual(lo + hi, 9)
            self.assertEqual(ng.syzygy(lo), hi)
            self.assertEqual(ng.pair(hi), (lo, hi))

    def test_currents_are_differences(self):
        self.assertEqual({p: ng.current(p[0]) for p in ng.SYZYGIES},
                         {(0, 9): 9, (1, 8): 7, (2, 7): 5, (3, 6): 3, (4, 5): 1})
        for z in ng.ZONES:
            self.assertEqual(ng.current(z), ng.current(ng.syzygy(z)))

    def test_regions(self):
        # Central syzygies feed each other in a three-step cycle.
        central = [(1, 8), (2, 7), (4, 5)]
        targets = {p: ng.pair(ng.current(p[0])) for p in central}
        self.assertEqual(set(targets.values()), set(central))
        self.assertEqual(targets[(4, 5)], (1, 8))
        self.assertEqual(targets[(1, 8)], (2, 7))
        self.assertEqual(targets[(2, 7)], (4, 5))
        # The upper and lower syzygies fold back into one of their own zones.
        self.assertIn(ng.current(3), ng.WARP)
        self.assertIn(ng.current(0), ng.PLEX)
        self.assertEqual([ng.region(z) for z in ng.ZONES],
                         ["plex", "time-circuit", "time-circuit", "warp", "time-circuit",
                          "time-circuit", "warp", "time-circuit", "time-circuit", "plex"])
        self.assertEqual(ng.follow_currents(4, 6), [4, 1, 7, 5, 1, 7, 5])
        self.assertEqual(ng.follow_currents(6, 3), [6, 3, 3, 3])
        self.assertEqual(ng.follow_currents(0, 3), [0, 9, 9, 9])

    def test_gates_and_channels(self):
        self.assertEqual([ng.channel(z) for z in ng.ZONES],
                         [(0, 0), (1, 1), (3, 3), (6, 6), (10, 1), (15, 6), (21, 3), (28, 1), (36, 9), (45, 9)])
        self.assertEqual(ng.follow_channels(7, 2), [7, 1, 1])

    def test_cycles(self):
        self.assertEqual(ng.binodecimal_cycle(12), [1, 2, 4, 8, 7, 5] * 2)
        self.assertEqual(sorted(ng.binodecimal_cycle()), list(ng.TIME_CIRCUIT))
        self.assertEqual(ng.quintuplicative_cycle(), [1] + ng.binodecimal_cycle()[:0:-1])

    def test_mesh_numbering(self):
        spans = ng.net_spans()
        self.assertEqual(len(spans), 45)
        # Order printed in the Pandemonium Matrix extract: 1::0, 2::0, 2::1, 3::0, ...
        self.assertEqual(spans[:4], [(1, 0), (2, 0), (2, 1), (3, 0)])
        self.assertEqual((ng.mesh(1, 0), ng.mesh(2, 1), ng.mesh(3, 0), ng.mesh(9, 8)), (0, 2, 3, 44))
        for m in range(45):
            self.assertEqual(ng.mesh(*ng.net_span(m)), m)
            self.assertEqual(ng.phase(m), ng.net_span(m)[0])
        self.assertEqual(ng.mesh(0, 9), ng.mesh(9, 0))
        with self.assertRaises(ValueError):
            ng.mesh(4, 4)

    def test_dot_export(self):
        dot = ng.to_dot()
        self.assertTrue(dot.startswith("digraph numogram {"))
        self.assertEqual(dot.count("label=\"current"), 5)
        self.assertEqual(dot.count("label=\"gate"), 10)
        self.assertEqual(ng.to_dot(gates=False).count("label=\"gate"), 0)

    def test_rejects_non_zones(self):
        for bad in (-1, 10, 3.5):
            with self.assertRaises(ValueError):
                ng.current(bad)


class RecordingHand:
    """Stands in for marks.Hand / plotkit.PlotHand: records stroke calls."""

    def __init__(self):
        self.calls = []

    def stroke(self, pts, weight="orn", color="ink", closed=False, amp=None):
        self.calls.append((list(pts), weight, color, closed))


class XenotationTests(unittest.TestCase):
    KNOWN = {2: ":", 3: "(:)", 4: "::", 5: "((:))", 6: ":(:)", 7: "(::)", 8: ":::",
             9: "(:)(:)", 10: ":((:))", 11: "(((:)))", 12: "::(:)", 13: "(:(:))"}

    def test_known_values(self):
        for n, s in self.KNOWN.items():
            self.assertEqual(tx.encode(n), s)
            self.assertEqual(tx.decode(s), n)

    def test_nullary(self):
        self.assertEqual(tx.encode(1, "nullary"), "")
        self.assertEqual(tx.encode(2, "nullary"), "()")
        self.assertEqual(tx.encode(3, "nullary"), "(())")
        # word.site's canonical example: (())() is the canonical form of ()(()).
        self.assertEqual(tx.encode(6, "nullary", "descending"), "(())()")
        self.assertEqual(tx.decode("()(())", "nullary"), tx.decode("(())()", "nullary"), 6)

    def test_round_trips(self):
        for n in range(2, 3000):
            for order in ("ascending", "descending"):
                self.assertEqual(tx.decode(tx.encode(n, order=order)), n)
                self.assertEqual(tx.decode(tx.encode(n, "nullary", order), "nullary"), n)
        self.assertEqual(tx.decode(""" (::)
                                       (:) """), 21)

    def test_term_order_does_not_change_value(self):
        self.assertEqual(tx.decode("(:)::"), tx.decode("::(:)"))

    def test_primes(self):
        self.assertEqual([tx.nth_prime(k) for k in range(1, 11)], [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
        self.assertEqual(tx.prime_index(7919), 1000)
        # Nested brackets climb the prime-indexed primes: 2, 3, 5, 11, 31, 127, ...
        self.assertEqual([tx.decode("(" * d + ":" + ")" * d) for d in range(6)], [2, 3, 5, 11, 31, 127])

    def test_rejects_malformed_strings(self):
        for bad in ("", "()", "(:", ":)", "(:))", "x", "(:)a"):
            with self.assertRaises(ValueError):
                tx.decode(bad)
        with self.assertRaises(ValueError):
            tx.encode(1)
        with self.assertRaises(ValueError):
            tx.prime_index(9)

    def test_stats(self):
        self.assertEqual(tx.stats(tx.encode(360)), {"tics": 6, "enclosures": 4, "depth": 2})

    def test_layout_matches_the_string(self):
        for n in (2, 9, 13, 360, 1000, 2023):
            s = tx.encode(n)
            for style, per_enclosure in (("capsule", 1), ("parens", 2)):
                g = tx.layout(s, style=style)
                tics = [p for p, closed in g["strokes"] if len(p) == 2]
                self.assertEqual(len(tics), s.count(":"))
                self.assertEqual(len(g["strokes"]) - len(tics), per_enclosure * s.count("("))
                for points, _ in g["strokes"]:
                    for u, v in points:
                        self.assertGreaterEqual(u, -1e-9)
                        self.assertLessEqual(u, g["width"] + 1e-9)
                        self.assertLessEqual(abs(v), g["height"] / 2 + 1e-9)

    def test_nullary_glyphs(self):
        self.assertEqual(tx.layout("")["strokes"], [])
        circle = tx.layout("()")
        self.assertEqual(len(circle["strokes"]), 1)
        self.assertAlmostEqual(circle["width"], circle["height"])

    def test_draw_uses_the_hand_interface(self):
        hand = RecordingHand()
        w, h = tx.draw(hand, 360, 10, 20, 5, weight="hair", color="red")
        self.assertEqual(len(hand.calls), 6 + 4)
        self.assertTrue(all(call[1:3] == ("hair", "red") for call in hand.calls))
        xs = [x for pts, *_ in hand.calls for x, _ in pts]
        ys = [y for pts, *_ in hand.calls for _, y in pts]
        self.assertAlmostEqual(min(xs), 10)
        self.assertLessEqual(max(xs), 10 + w + 1e-9)
        self.assertGreaterEqual(min(ys), 20 - 1e-9)
        self.assertLessEqual(max(ys), 20 + h + 1e-9)

    def test_svg_is_stroke_only(self):
        svg = tx.to_svg(360)
        self.assertEqual(svg.count("<path "), 10)
        self.assertIn('fill="none"', svg)
        self.assertTrue(re.search(r'width="[\d.]+mm"', svg))


if __name__ == "__main__":
    unittest.main()
