"""Regression checks for exact phase domains and one-shot iterable handling."""
import unittest

from bsci.star import phase_bounds, optimize, window


class PhaseInterfaceTests(unittest.TestCase):
    def test_phase_iterator_matches_list(self):
        expected = phase_bounds(4, 2, 1, 3, [0, 1, 2])
        self.assertEqual(expected, phase_bounds(4, 2, 1, 3, iter([0, 1, 2])))
        self.assertEqual(expected['bound'], 4)

    def test_window_iterator_matches_list(self):
        self.assertEqual(window(4, 2, [0, 1, 2], 4, 1),
                         window(4, 2, (x for x in [0, 1, 2]), 4, 1))

    def test_phase_integer_parameters(self):
        for index in range(4):
            for invalid in (True, 1.0, 2.5, '2', None, 0, -1):
                args = [4, 2, 1, 3]
                args[index] = invalid
                with self.subTest(index=index, invalid=invalid):
                    with self.assertRaises(ValueError):
                        phase_bounds(*args, [0, 1, 2])

    def test_phase_coordinates(self):
        for phases in ([True], [1.0], [0.5], [-1], [4], ['1'], [None]):
            with self.subTest(phases=phases):
                with self.assertRaises(ValueError): phase_bounds(4, 2, 1, 3, phases)
                with self.assertRaises(ValueError): window(4, 2, phases, 4, 1)

    def test_phase_containers(self):
        for phases in (None, 3, '', '012', {}, {0: 1}, [], iter(())):
            with self.subTest(phases=phases):
                with self.assertRaises(ValueError): phase_bounds(4, 2, 1, 3, phases)

    def test_window_invalid_phases_do_not_silently_remove_sends(self):
        with self.assertRaises(ValueError): window(4, 2, [4], 2, 0)

    def test_window_parameters_validated_at_zero_bound(self):
        for P, D in ((True, 2), (4.0, 2), (4, 0), (4, 2.0), (0, 2)):
            with self.subTest(P=P, D=D):
                with self.assertRaises(ValueError): window(P, D, [0], 0, 0)
        for B in (True, 0.0, -1):
            with self.assertRaises(ValueError): window(4, 2, [0], B, 0)
        for q in (True, 0.0, -1, 4):
            with self.assertRaises(ValueError): window(4, 2, [0], 0, q)

    def test_optimize_integer_parameters(self):
        for index in range(5):
            for invalid in (True, 1.0, 0, -1, None):
                args = [4, 2, 1, 3, 3]
                args[index] = invalid
                with self.subTest(index=index, invalid=invalid):
                    with self.assertRaises(ValueError): optimize(*args)

    def test_valid_edge_domains_preserved(self):
        self.assertEqual(phase_bounds(1, 1, 1, 1, [0])['bound'], 1)
        self.assertEqual(optimize(1, 1, 1, 1, 1)['bound'], 1)
        self.assertIsNone(phase_bounds(2, 2, 1, 2, [0])['bound'])
        empty = window(1, 1, [0], 0, 0)
        self.assertEqual(empty.messages, ())
        self.assertEqual(empty.queries, ((1, 0),))


if __name__ == '__main__':
    unittest.main()
