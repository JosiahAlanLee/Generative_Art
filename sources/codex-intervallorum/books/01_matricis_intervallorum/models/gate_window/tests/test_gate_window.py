"""Checks on the model's arithmetic and limits, and on the verdict rule.

    python -m unittest discover -s books/01_matricis_intervallorum/models/gate_window/tests -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from model import Params, cell_rng, expected_harm_deference, simulate_cell  # noqa: E402
import verdict  # noqa: E402

N = 20000


def base(**kw) -> Params:
    d = dict(eps=0.3, delta=0.5, phi=0.0, lam=0.3, sigma=0.75, d=0.1, h_wrong=1.0, h_window=3.0)
    d.update(kw)
    return Params(**d)


class ModelArithmetic(unittest.TestCase):
    def test_deference_matches_closed_form(self):
        for eps in (0.05, 0.3, 0.6):
            for h_wrong in (0.1, 3.0):
                p = base(eps=eps, h_wrong=h_wrong)
                s = simulate_cell(p, N, cell_rng(1, 0))["B"]
                self.assertAlmostEqual(s.harm, expected_harm_deference(p), delta=0.03 * expected_harm_deference(p) + 0.01)
                self.assertAlmostEqual(s.n_wrong, eps / (1 - eps), delta=0.05)

    def test_gate_with_no_latency_and_no_review_is_deference(self):
        p = base(lam=0.0, delta=0.0, phi=0.0)
        s = simulate_cell(p, N, cell_rng(2, 0))
        self.assertAlmostEqual(s["A"].harm, s["B"].harm, places=9)
        self.assertAlmostEqual(s["C"].harm, s["B"].harm, places=9)

    def test_bounded_gate_sits_between_its_limits(self):
        # With the window already spent, C waits for nothing and equals B.
        p = base(d=1.0)
        s = simulate_cell(p, N, cell_rng(3, 0))
        self.assertAlmostEqual(s["C"].T, s["B"].T, places=9)
        # With a negligible latency, C reviews everything and equals A up to the latency itself.
        p = base(lam=1e-6, sigma=0.1)
        s = simulate_cell(p, N, cell_rng(4, 0))
        self.assertAlmostEqual(s["C"].harm, s["A"].harm, delta=1e-3)

    def test_gate_harm_rises_with_latency(self):
        harms = []
        for lam in (0.03, 0.3, 3.0):
            harms.append(simulate_cell(base(lam=lam), N, cell_rng(5, 0))["A"].harm)
        self.assertTrue(harms[0] < harms[1] < harms[2])

    def test_a_perfect_fast_gate_beats_deference_when_wrong_actions_are_dear(self):
        p = base(eps=0.5, delta=1.0, phi=0.0, lam=0.01, sigma=0.1, h_wrong=10.0)
        s = simulate_cell(p, N, cell_rng(6, 0))
        self.assertLess(s["A"].harm, s["B"].harm)
        self.assertLess(s["C"].harm, s["B"].harm)

    def test_a_slow_blind_gate_loses_to_deference(self):
        p = base(eps=0.1, delta=0.0, phi=0.0, lam=3.0, h_wrong=0.5)
        s = simulate_cell(p, N, cell_rng(7, 0))
        self.assertGreater(s["A"].harm, s["B"].harm)
        self.assertGreater(s["A"].harm, s["C"].harm)

    def test_booked_harm_counts_wrong_actions_only(self):
        p = base()
        s = simulate_cell(p, N, cell_rng(8, 0))
        for arr in ("A", "B", "C"):
            self.assertAlmostEqual(s[arr].booked, p.h_wrong * s[arr].n_wrong, places=9)

    def test_runs_are_reproducible(self):
        p = base()
        a = simulate_cell(p, 2000, cell_rng(9, 17))
        b = simulate_cell(p, 2000, cell_rng(9, 17))
        self.assertEqual(a["A"].harm, b["A"].harm)
        self.assertEqual(a["C"].p_late, b["C"].p_late)

    def test_nothing_truncated_in_the_grid_corners(self):
        p = base(eps=0.6, phi=0.25, delta=0.95, lam=10.0)
        s = simulate_cell(p, N, cell_rng(10, 0))
        self.assertEqual(s["A"].truncated, 0.0)


def synthetic(fn) -> list[dict]:
    rows = []
    for cell in verdict.cells():
        r = dict(cell)
        hA, hC, bA, bC = fn(cell)
        r.update(harm_A=hA, harm_C=hC, harm_B=hC, booked_A=bA, booked_C=bC, booked_B=bC)
        for a in ("A", "B", "C"):
            r[f"truncated_{a}"] = 0.0
        rows.append(r)
    return rows


class VerdictRule(unittest.TestCase):
    def setUp(self):
        self.rule = verdict.load_rule()

    def test_rigged_when_c_always_wins(self):
        rows = synthetic(lambda c: (2.0, 1.0, 0.0, 0.0))
        self.assertEqual(verdict.apply(rows, self.rule)["outcome"], "1_rigged")

    def test_fails_when_a_always_wins(self):
        rows = synthetic(lambda c: (1.0, 2.0, 0.0, 0.0))
        self.assertEqual(verdict.apply(rows, self.rule)["outcome"], "3_fails")

    def test_fails_when_c_wins_only_at_lowest_eps(self):
        rows = synthetic(lambda c: (2.0, 1.0, 0.0, 0.0) if c["eps"] <= 0.05 else (1.0, 2.0, 0.0, 0.0))
        self.assertEqual(verdict.apply(rows, self.rule)["outcome"], "3_fails")

    def test_region_when_the_window_decides(self):
        def fn(c):
            # C wins where the gate is slow or blind; A holds where the gate is fast and sharp.
            if c["lam"] >= 0.3 or c["delta"] <= 0.25:
                return (2.0, 1.0, 0.0, 0.0)
            return (1.0, 2.0, 0.0, 0.0)
        rows = synthetic(fn)
        out = verdict.apply(rows, self.rule)
        self.assertEqual(out["outcome"], "2_region")
        self.assertGreaterEqual(out["frac_gate_home_A_holds"], 0.25)

    def test_numerical_thresholds_come_from_the_recorded_rule(self):
        # Changing executable data changes the outcome, without changing Python.
        rows = synthetic(lambda c: (1.0, 2.0, 0.0, 0.0))
        self.assertEqual(verdict.apply(rows, self.rule)["outcome"], "3_fails")
        self.rule["thresholds"]["rigged_all_c"] = 0.0
        self.assertEqual(verdict.apply(rows, self.rule)["outcome"], "1_rigged")

    def test_anchored_region_is_a_strict_subset(self):
        rows = synthetic(lambda c: (1.0, 1.0, 0.0, 0.0))
        out = verdict.apply(rows, self.rule)
        self.assertLess(out["anchored_cells"], out["cells"])
        self.assertGreater(out["anchored_cells"], 0)
        self.assertGreater(out["gate_home_cells"], 0)


if __name__ == "__main__":
    unittest.main()
