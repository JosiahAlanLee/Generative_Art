import unittest

from generator.reachability import Task, evaluate, specimen_cases


class ReachabilityTests(unittest.TestCase):
    def test_parallel_prerequisites_are_not_added(self):
        tasks = {"a": Task(4), "b": Task(6), "c": Task(2, ("a", "b"))}
        self.assertEqual(evaluate(tasks, "c").completion, 8)

    def test_shared_prerequisite_is_paid_once(self):
        tasks = {"a": Task(1, cost=3), "b": Task(1, ("a",), cost=2),
                 "c": Task(1, ("a", "b"), cost=1)}
        self.assertTrue(evaluate(tasks, "c", budget=6).feasible)
        self.assertEqual(evaluate(tasks, "c").cost, 6)

    def test_waiting_can_destroy_an_otherwise_fast_route(self):
        cases = specimen_cases()
        self.assertTrue(cases["recorded_route"].feasible)
        self.assertEqual(cases["recorded_route"].completion, 10)
        self.assertEqual(cases["rehearsed_route"].completion, 5)
        self.assertFalse(cases["late_opening"].feasible)
        self.assertFalse(cases["gate_unavailable"].feasible)

    def test_exact_deadline_is_feasible_but_later_is_not(self):
        tasks = {"a": Task(3, valid_until=3)}
        self.assertTrue(evaluate(tasks, "a", deadline=3).feasible)
        self.assertFalse(evaluate(tasks, "a", now=.1).feasible)

    def test_budget_is_a_separate_constraint(self):
        self.assertFalse(evaluate({"a": Task(1, cost=2)}, "a", budget=1).feasible)

    def test_cycles_unknown_nodes_and_invalid_data_fail_loudly(self):
        for tasks, target in [({"a": Task(1, ("a",))}, "a"),
                              ({"a": Task(1, ("missing",))}, "a"),
                              ({"a": Task(-1)}, "a")]:
            with self.subTest(tasks=tasks):
                with self.assertRaises(ValueError):
                    evaluate(tasks, target)


if __name__ == "__main__":
    unittest.main()
