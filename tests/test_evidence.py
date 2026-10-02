"""Deliberately changed toy records must fail exact scientific comparisons."""
import json
from pathlib import Path
import tempfile
import unittest
from bsci.evidence import strict_equal, compare_derived
from validate import compare_pilot, compare_directory
from check_epoch_audit import compare

class EvidenceTests(unittest.TestCase):
    def test_strict_json_types(self):
        self.assertTrue(strict_equal({'a': [1, True, None]}, {'a': [1, True, None]}))
        for a, b in ((True, 1), (1, 1.0), ([True], [1]), ({'n': 1}, {'n': 1.0}),
                     ({'x': 1}, {'x': 1, 'y': 2}), ([1], [1, 2])):
            with self.subTest(a=a, b=b): self.assertFalse(strict_equal(a, b))

    def test_pilot_rejects_scientific_type_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a.json', Path(tmp)/'b.json'
            a.write_text('{"cases": 1, "passed": true}')
            b.write_text('{"cases": 1.0, "passed": 1}')
            with self.assertRaises(ValueError): compare_pilot(a, b)

    def test_directory_rejects_scientific_type_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'; a.mkdir(); b.mkdir()
            (a/'x.json').write_text('{"safe":true}')
            (b/'x.json').write_text('{"safe":1}')
            with self.assertRaises(ValueError): compare_directory(a, b)

    def test_derived_compares_summary_not_resource_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'; a.mkdir(); b.mkdir()
            (a/'summary.json').write_text('{"n":1,"resources":{"cpu":1}}')
            (b/'summary.json').write_text('{"n":1,"resources":{"cpu":2}}')
            self.assertTrue(compare_derived(a, b)['all_scientific_fields_equal'])
            (b/'summary.json').write_text('{"n":2,"resources":{"cpu":1}}')
            with self.assertRaises(ValueError): compare_derived(a, b)
            (b/'summary.json').write_text('{"n":1.0}')
            with self.assertRaises(ValueError): compare_derived(a, b)

    def test_derived_scaling_ignores_only_timing_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'; a.mkdir(); b.mkdir()
            (a/'scaling.csv').write_text('m,points,producer_cpu_median_ms\n8,10,1.0\n')
            (b/'scaling.csv').write_text('m,points,producer_cpu_median_ms\n8,10,3.0\n')
            self.assertTrue(compare_derived(a, b)['all_scientific_fields_equal'])
            (b/'scaling.csv').write_text('m,points,producer_cpu_median_ms\n8,11,1.0\n')
            with self.assertRaises(ValueError): compare_derived(a, b)
            (b/'scaling.csv').write_text('m,points,producer_cpu_median_ms,extra\n8,10,1.0,0\n')
            with self.assertRaises(ValueError): compare_derived(a, b)

    def test_derived_requires_exact_file_coverage_and_phase_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'; a.mkdir(); b.mkdir()
            (a/'phase-slice.csv').write_text('bound\n4\n')
            with self.assertRaises(ValueError): compare_derived(a, b)
            (b/'phase-slice.csv').write_text('bound\n5\n')
            with self.assertRaises(ValueError): compare_derived(a, b)

    def test_epoch_audit_rejects_type_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'; a.mkdir(); b.mkdir()
            for folder in (a, b):
                (folder/'summary.json').write_text('{"checked":1}')
                (folder/'cases.jsonl').write_text('{"safe":true}\n')
            self.assertTrue(compare(a, b)['all_scientific_fields_equal'])
            (b/'cases.jsonl').write_text('{"safe":1}\n')
            with self.assertRaises(ValueError): compare(a, b)

if __name__ == '__main__': unittest.main()
