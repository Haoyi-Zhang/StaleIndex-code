"""Local consistency of the corrected citation; not online or full-paper verification."""
import csv
from pathlib import Path
import unittest


class SourceAttributionTests(unittest.TestCase):
    def test_robust_temporal_cut_identity(self):
        root = Path(__file__).resolve().parents[1]
        with (root / 'bibliography-audit.csv').open(encoding='utf-8', newline='') as stream:
            audit = [row for row in csv.DictReader(stream) if row['key'] == 'robustcut']
        with (root / 'external_resources.csv').open(encoding='utf-8', newline='') as stream:
            resources = [row for row in csv.DictReader(stream) if row['id'] == 'robustcut']
        self.assertEqual(len(audit), 1)
        self.assertEqual(len(resources), 1)
        self.assertEqual(audit[0]['title'], 'Robust Temporal Cut')
        self.assertEqual(resources[0]['name'], audit[0]['title'])
        self.assertEqual(audit[0]['doi'], '10.4230/LIPIcs.SAND.2026.14')
        self.assertIn(audit[0]['doi'].split('/')[-1], resources[0]['scholarly_or_official_url'])


if __name__ == '__main__':
    unittest.main()
