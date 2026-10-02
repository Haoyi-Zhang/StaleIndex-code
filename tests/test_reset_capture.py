"""Finite packet patterns must name the same reset claim throughout validation."""
import copy
import unittest

from bsci.model import Instance, Message
from bsci.certify import certify
from bsci.families import universal, verify_universal
from bsci.replay import capture_certificate, verify


class ResetCaptureTests(unittest.TestCase):
    def setUp(self):
        self.ins = Instance(2, 2, 0, (Message(0, 1, 0, 1, 1),),
                            ((1, 2),), (), ((1, 2),))
        self.rule = {'kind': 'cardinality', 'k': 1}

    def test_aggregate_cannot_consume_away_a_reset_claim(self):
        # No reset is safe, but its proof cannot cover the allowed erasure.
        proof = certify(self.ins)
        proof['optional'] = iter([[1, 2]])
        packet = {'safe': True, 'rule': self.rule, 'certificates': [proof]}
        self.assertFalse(verify_universal(self.ins, packet, expected_rule=self.rule))

    def test_nested_one_shot_pairs_cannot_change_coverage(self):
        proof = certify(self.ins)
        proof['optional'] = (iter(row) for row in [[1, 2]])
        packet = {'safe': True, 'rule': self.rule, 'certificates': [proof]}
        self.assertFalse(verify_universal(self.ins, packet, expected_rule=self.rule))

    def test_fixed_negative_one_shot_pattern_replays_same_pattern(self):
        proof = certify(self.ins, self.ins.candidates)
        self.assertFalse(proof['safe'])
        proof['optional'] = iter([[1, 2]])
        self.assertTrue(verify(self.ins, proof, expected_optional=self.ins.candidates))

    def test_negative_aggregate_one_shot_pattern_and_minimum(self):
        for minimum in (False, True):
            packet = universal(self.ins, self.rule)
            packet['certificate']['optional'] = (iter(row) for row in [[1, 2]])
            self.assertTrue(verify_universal(self.ins, packet, minimum, expected_rule=self.rule))

    def test_valid_positive_one_shot_pattern_is_not_rejected(self):
        # A redundant reset at the arrival slot does not erase that arrival.
        ins = Instance(2, 2, 0, (Message(0, 1, 0, 1, 1),),
                       ((1, 2),), (), ((1, 1),))
        packet = universal(ins, self.rule)
        packet['certificates'][0]['optional'] = iter([[1, 1]])
        self.assertTrue(verify_universal(ins, packet, expected_rule=self.rule))

    def test_capture_detaches_mutable_rows_without_mutating_packet(self):
        proof = certify(self.ins, self.ins.candidates)
        original = copy.deepcopy(proof)
        captured = capture_certificate(proof)
        self.assertEqual(proof, original)
        proof['optional'][0][1] = 1
        self.assertEqual(captured['optional'], ((1, 2),))
        self.assertTrue(verify(self.ins, captured, expected_optional=((1, 2),)))

    def test_malformed_nested_pattern_is_invalid_not_a_different_claim(self):
        for values in (iter([[1]]), iter([[True, 2]]), iter([[1, 2.0]]),
                       iter([[1, 2], [1, 2]])):
            proof = certify(self.ins)
            proof['optional'] = values
            packet = {'safe': True, 'rule': self.rule, 'certificates': [proof]}
            self.assertFalse(verify_universal(self.ins, packet, expected_rule=self.rule))

    def test_expected_pattern_still_binds_after_capture(self):
        proof = certify(self.ins, self.ins.candidates)
        proof['optional'] = iter([[1, 2]])
        self.assertFalse(verify(self.ins, proof, expected_optional=()))

    def test_full_oracle_keeps_resets_for_later_arrival_assignments(self):
        from bsci.campaign import gadget
        from bsci.oracle import exhaustive
        ins = gadget(2, [(0, 1)])
        pattern = ((2, 4),)
        expected = exhaustive(ins, pattern)
        self.assertFalse(expected['safe'])
        self.assertEqual(expected['executions'], 2)
        self.assertEqual(exhaustive(ins, iter(pattern)), expected)

    def test_full_oracle_captures_nested_one_shot_reset_pairs(self):
        from bsci.campaign import gadget
        from bsci.oracle import exhaustive
        ins = gadget(2, [(0, 1)])
        expected = exhaustive(ins, ((2, 4),))
        self.assertEqual(exhaustive(ins, (iter(row) for row in [[2, 4]])), expected)

    def test_producer_rejects_mappings_instead_of_reinterpreting_keys(self):
        for pattern in ({(1, 2): 'not an event sequence'}, [{1: 'node', 2: 'time'}]):
            with self.subTest(pattern=pattern):
                with self.assertRaises(ValueError):
                    certify(self.ins, pattern)


if __name__ == '__main__':
    unittest.main()
