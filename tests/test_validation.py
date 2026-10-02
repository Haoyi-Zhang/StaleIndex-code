"""Controls that the reproduction wrapper cannot accept a changed reference."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from validate import compare_pilot, compare_directory, create_workspace


class ValidationTests(unittest.TestCase):
    def test_pilot_ignores_only_declared_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.json', Path(tmp) / 'b.json'
            a.write_text(json.dumps({'cases': 2, 'cpu_seconds': 1}))
            b.write_text(json.dumps({'cases': 2, 'cpu_seconds': 4}))
            self.assertTrue(compare_pilot(a, b)['non_observational_fields_equal'])
            b.write_text(json.dumps({'cases': 3, 'cpu_seconds': 1}))
            with self.assertRaises(ValueError): compare_pilot(a, b)

    def test_directory_requires_complete_file_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a', Path(tmp) / 'b'
            a.mkdir(); b.mkdir()
            (a / 'data.csv').write_text('value\n1\n')
            with self.assertRaises(ValueError): compare_directory(a, b)
            (b / 'data.csv').write_text('value\n1\n')
            self.assertEqual(compare_directory(a, b), ['data.csv'])
            (b / 'data.csv').write_text('value\n2\n')
            with self.assertRaises(ValueError): compare_directory(a, b)

    def test_directory_checks_json_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a', Path(tmp) / 'b'
            a.mkdir(); b.mkdir()
            (a / 'data.json').write_text('{"safe":true}')
            (b / 'data.json').write_text('{ "safe": true }\n')
            self.assertEqual(compare_directory(a, b), ['data.json'])
            (b / 'data.json').write_text('{"safe":false}')
            with self.assertRaises(ValueError): compare_directory(a, b)

    def test_existing_workspace_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'evidence').mkdir()
            (root / 'evidence/result').write_text('retained')
            with self.assertRaises(ValueError): create_workspace(root, Path('evidence'))
            self.assertEqual((root / 'evidence/result').read_text(), 'retained')
            self.assertTrue(create_workspace(root, Path('fresh')).is_dir())

    def test_source_and_reference_subdirectories_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('bsci/new', 'inputs/new', 'results/campaign/new', 'results/derived/new'):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError): create_workspace(Path(tmp), Path(name))

    def test_optimized_validation_refused(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, '-O', 'validate.py'], cwd=root,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn('assertions enabled', result.stderr)


if __name__ == '__main__':
    unittest.main()
