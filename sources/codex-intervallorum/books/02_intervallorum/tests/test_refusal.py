import unittest

from generator.refusal import Station, evaluate, smallest_opening_refusal, specimen_cases


BASE = Station(operators=7, stoppage_threshold=4, replacement_capacity=2,
               replacement_time=3, grant_time=10, grant_cost=6, stoppage_rate=1)


class RefusalTests(unittest.TestCase):
    def test_no_refusal_is_needed_when_the_grant_is_in_time(self):
        early = Station(7, 4, 2, 3, grant_time=3, grant_cost=6, stoppage_rate=1)
        outcome = evaluate(early, 0, deadline=4)
        self.assertTrue(outcome.route_open)
        self.assertEqual(outcome.named, ())

    def test_a_refusal_below_the_threshold_names_one_person_and_changes_nothing(self):
        for refusers in (1, 3):
            with self.subTest(refusers=refusers):
                outcome = evaluate(BASE, refusers, deadline=4)
                self.assertFalse(outcome.route_open)
                self.assertEqual(outcome.named, (1,))
                self.assertEqual(outcome.authority_at, 10)

    def test_a_stopped_station_opens_the_route_when_the_stoppage_outweighs_the_grant(self):
        outcome = evaluate(BASE, 4, deadline=4)
        self.assertTrue(outcome.route_open)
        self.assertEqual(outcome.authority_at, 0)
        self.assertEqual(outcome.named, ())

    def test_replacement_before_the_deadline_defeats_the_refusal_and_names_everyone(self):
        cases = specimen_cases()
        self.assertFalse(cases["station_replaced"].route_open)
        self.assertEqual(cases["station_replaced"].named, tuple(range(1, 8)))
        self.assertTrue(cases["replacement_too_slow"].route_open)

    def test_a_cheap_stoppage_is_borne_and_the_grant_stays_late(self):
        outcome = specimen_cases()["cheap_stoppage"]
        self.assertFalse(outcome.route_open)
        self.assertEqual(outcome.authority_at, 10)
        self.assertEqual(outcome.named, ())

    def test_the_smallest_opening_refusal_is_the_threshold_here(self):
        self.assertEqual(smallest_opening_refusal(BASE, deadline=4), 4)
        self.assertIsNone(smallest_opening_refusal(Station(7, 4, 7, 3, 10, 6, 1), deadline=4))

    def test_a_refusal_after_the_deadline_cannot_open_it(self):
        costly = Station(7, 4, 2, 3, grant_time=10, grant_cost=6, stoppage_rate=2)
        outcome = evaluate(costly, 7, deadline=4, refuse_at=5)
        self.assertEqual(outcome.authority_at, 5)
        self.assertFalse(outcome.route_open)

    def test_invalid_inputs_fail_loudly(self):
        bad = [
            (Station(7, 0, 2, 3, 10, 6, 1), 1),
            (Station(7, 8, 2, 3, 10, 6, 1), 1),
            (BASE, 8),
            (BASE, -1),
            (Station(7, 4, 2, float("nan"), 10, 6, 1), 4),
            (Station(7, 4, 2, 3, 10, -1, 1), 4),
        ]
        for station, refusers in bad:
            with self.subTest(station=station, refusers=refusers):
                with self.assertRaises(ValueError):
                    evaluate(station, refusers, deadline=4)
        with self.assertRaises(ValueError):
            evaluate(BASE, 4, deadline=4, refuse_at=11)


if __name__ == "__main__":
    unittest.main()
