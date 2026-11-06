"""CLI export tests using a synthetic local price file."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
import main


class CLITests(unittest.TestCase):
    def test_offline_exports_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'synthetic_test_input.csv'
            pd.DataFrame({'AAA': [100., 110., 99.], 'BBB': [100., 100., 100.]},
                         index=pd.date_range('2024-01-01', periods=3, name='Date')).to_csv(source)
            args = ['main.py', '--input', str(source), '--tickers', 'AAA', '--benchmark', 'BBB']
            with patch.object(main, 'ROOT', root), patch('sys.argv', args), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main.main(), 0)
            snapshots = list((root / 'data' / 'snapshots').iterdir())
            self.assertEqual(len(snapshots), 1)
            metadata = json.loads((snapshots[0] / 'metadata.json').read_text())
            self.assertEqual(len(metadata['prices_sha256']), 64)
            report = root / 'reports' / snapshots[0].name
            metrics = pd.read_csv(report / 'metrics.csv', index_col=0)
            self.assertAlmostEqual(metrics.loc['Portfolio', 'Total return'], -.01)
            self.assertEqual(len(list(report.glob('*.csv'))), 6)
            self.assertEqual(json.loads((report / 'settings.json').read_text())['rebalancing'], 'daily')
