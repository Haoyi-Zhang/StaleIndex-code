"""Local regression controls for the verifier's claim boundary and JSON types."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from bsci.model import Instance, Message
from bsci.certify import certify
from bsci.replay import verify
from bsci.families import universal, verify_universal, normalize_rule


class ClaimBindingTests(unittest.TestCase):
    def setUp(self):
        self.ins = Instance(3, 3, 0,
            (Message(0, 1, 0, 1, 1), Message(0, 2, 0, 1, 1)),
            ((1, 3), (2, 3)), (), ((1, 2), (2, 2)))
        self.one = dict(kind='cardinality', k=1)
        self.two = dict(kind='cardinality', k=2)

    def test_expected_budget_bound(self):
        packet = universal(self.ins, self.one)
        self.assertTrue(packet['safe'])
        self.assertFalse(universal(self.ins, self.two)['safe'])
        self.assertTrue(verify_universal(self.ins, packet, expected_rule=self.one))
        self.assertFalse(verify_universal(self.ins, packet, expected_rule=self.two))

    def test_default_checks_only_packet_assertion(self):
        self.assertTrue(verify_universal(self.ins, universal(self.ins, self.one)))

    def test_expected_rolling_parameters_bound(self):
        rule = dict(kind='rolling', b=1, W=2)
        packet = universal(self.ins, rule)
        self.assertTrue(verify_universal(self.ins, packet, expected_rule=rule))
        for other in (dict(kind='rolling', b=2, W=2),
                      dict(kind='rolling', b=1, W=3), self.one):
            self.assertFalse(verify_universal(self.ins, packet, expected_rule=other))

    def test_expected_fixed_pattern_bound(self):
        pattern = [(1, 2)]
        packet = certify(self.ins, pattern)
        self.assertTrue(verify(self.ins, packet, expected_optional=pattern))
        self.assertFalse(verify(self.ins, packet, expected_optional=[]))
        self.assertFalse(verify(self.ins, packet, expected_optional=[(2, 2)]))

    def test_optional_pair_integer_types(self):
        packet = certify(self.ins, [(1, 2)])
        for pair in ([True, 2], [1.0, 2], [1, 2.0], [1, True], [1, 2, 3]):
            bad = copy.deepcopy(packet); bad['optional'] = [pair]
            self.assertFalse(verify(self.ins, bad))
            with self.assertRaises(ValueError): self.ins.resets([pair])

    def test_expected_pattern_integer_types(self):
        packet = certify(self.ins, [(1, 2)])
        self.assertFalse(verify(self.ins, packet, expected_optional=[(True, 2)]))
        self.assertFalse(verify(self.ins, packet, expected_optional=[(1, 2.0)]))

    def test_memory_successor_integer_type(self):
        ins = Instance(2, 3, 0, (Message(0, 1, 0, 1, 2),), ((1, 3),))
        packet = certify(ins)
        index = next(i for i, step in enumerate(packet['steps']) if step[2] == 'mem')
        packet['steps'][index][3] = float(packet['steps'][index][3])
        self.assertFalse(verify(ins, packet))

    def test_rule_exact_schema(self):
        bad_rules = [None, {}, dict(kind='cardinality', k=True),
                     dict(kind='cardinality', k=1.0), dict(kind='cardinality', k=-1),
                     dict(kind='cardinality', k=1, W=2),
                     dict(kind='rolling', b=True, W=2), dict(kind='rolling', b=1, W=2.0),
                     dict(kind='rolling', b=1, W=0), dict(kind='unknown', k=1)]
        packet = universal(self.ins, self.one)
        for rule in bad_rules:
            with self.assertRaises(ValueError): normalize_rule(rule)
            if rule is not None:
                self.assertFalse(verify_universal(self.ins, packet, expected_rule=rule))
            bad = copy.deepcopy(packet); bad['rule'] = rule
            self.assertFalse(verify_universal(self.ins, bad))

    def test_minimum_count_integer_type(self):
        packet = universal(self.ins, self.two)
        packet['minimal_optional_count'] = 2.0
        self.assertTrue(verify_universal(self.ins, packet, expected_rule=self.two))
        self.assertFalse(verify_universal(self.ins, packet, True, expected_rule=self.two))

    def test_producer_copies_rule(self):
        rule = dict(self.one); packet = universal(self.ins, rule)
        rule['k'] = 2
        self.assertEqual(packet['rule'], self.one)

    def cli(self, command, ins, packet, *extra):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'instance.json').write_text(json.dumps(ins.to_dict()))
            (root/'packet.json').write_text(json.dumps(packet))
            return subprocess.run([sys.executable, '-m', 'bsci', command,
                str(root/'instance.json'), '--packet', str(root/'packet.json'), *extra],
                capture_output=True, text=True, timeout=10)

    def test_cli_universal_budget_is_required(self):
        result = self.cli('verify-universal', self.ins, universal(self.ins, self.one))
        self.assertEqual(result.returncode, 2)
        self.assertIn('--k is required', result.stderr)

    def test_cli_universal_budget_is_bound(self):
        packet = universal(self.ins, self.one)
        self.assertEqual(self.cli('verify-universal', self.ins, packet, '--k', '1').returncode, 0)
        result = self.cli('verify-universal', self.ins, packet, '--k', '2')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout), {'valid': False})

    def test_cli_default_fixed_pattern_is_bound(self):
        self.assertEqual(self.cli('verify', self.ins, certify(self.ins, [(1, 2)])).returncode, 1)
        self.assertEqual(self.cli('verify', self.ins, certify(self.ins)).returncode, 0)

if __name__ == '__main__':
    unittest.main()
