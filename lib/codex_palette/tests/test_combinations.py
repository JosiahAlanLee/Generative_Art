import unittest

import numpy as np

from lib.codex_palette.combinations import revision_loom, turnover


def record(changed=True):
    return {"rev": "a" * 40, "files": ["a.md"],
            "origins": [{"class": "base"}, {"class": "direct"}],
            "versions": [
                {"commit": "a", "date": "2026-01-01T00:00:00+00:00", "subject": "Import",
                 "runs": [[0, 0, "a.md", 1, [10, 10]]]},
                {"commit": "b", "date": "2026-01-02T00:00:00+00:00", "subject": "Edit",
                 "runs": ([[0, 0, "a.md", 1, [10]], [0, 1, "a.md", 2, [10]]]
                          if changed else [[0, 0, "a.md", 1, [10, 10]]])}]}


class CombinationTests(unittest.TestCase):
    def test_turnover_counts_replacement_and_keeps_import_zero(self):
        np.testing.assert_array_equal(turnover(record()), [[0, .5]])
        np.testing.assert_array_equal(turnover(record(False)), [[0, 0]])

    def test_revision_input_changes_material_and_zero_input_is_control(self):
        _, changed = revision_loom(record(), steps=500)
        _, control = revision_loom(record(False), steps=500)
        np.testing.assert_array_equal(control["material"], control["initial"])
        self.assertGreater(float((changed["initial"] - changed["material"]).sum()), 0)
        self.assertTrue(np.all((changed["material"] >= 0) & (changed["material"] <= 1)))
        self.assertTrue(np.all(np.diff(changed["loss_history"]) >= -1e-9))


if __name__ == "__main__":
    unittest.main()
