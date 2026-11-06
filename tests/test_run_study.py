"""Export and input checks for the study command, using synthetic prices."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from marketlens.data import save_snapshot
from marketlens.run_study import run_study


class RunStudyTests(unittest.TestCase):
    def make_snapshot(self, root):
        prices = pd.DataFrame(
            {symbol: [100., 110., 100.] for symbol in ['AAPL', 'MSFT', 'GOOGL', 'SPY']},
            index=pd.bdate_range('2016-01-04', periods=3, name='Date'),
        )
        return save_snapshot(prices, root / 'data', {
            'source': 'synthetic test', 'requested_start': '2016-01-01',
            'requested_end_exclusive': '2026-01-01',
        })

    def test_exports_all_cases_with_reproducibility_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = self.make_snapshot(root)
            with contextlib.redirect_stdout(io.StringIO()):
                output = run_study(snapshot, root / 'reports')
            summary = pd.read_csv(output / 'summary.csv')
            self.assertEqual(len(summary), 24)
            self.assertEqual(len(list(output.glob('*/rebalance_log.csv'))), 24)
            self.assertEqual(len(list(output.glob('*/holdings.csv'))), 24)
            settings = json.loads((output / 'settings.json').read_text())
            self.assertEqual(settings['cases'], 24)
            self.assertEqual(settings['initial_value'], 10000)
            self.assertIn('marketlens/simulation.py', settings['code_sha256'])

    def test_changed_price_file_is_rejected_before_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = self.make_snapshot(root)
            with (snapshot / 'prices.csv').open('a') as file:
                file.write('\n')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                run_study(snapshot, root / 'reports')
            self.assertFalse((root / 'reports').exists())

    def test_wrong_requested_period_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = self.make_snapshot(root)
            path = snapshot / 'metadata.json'
            metadata = json.loads(path.read_text())
            metadata['requested_start'] = '2024-01-01'
            path.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'study dates'):
                run_study(snapshot, root / 'reports')

    def test_subperiod_uses_only_its_dates_and_resets_capital(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dates = pd.to_datetime(['2020-12-29', '2020-12-30', '2020-12-31',
                                    '2021-01-04', '2021-01-05', '2021-01-06'])
            prices = pd.DataFrame({s: [100., 110., 120., 200., 210., 220.]
                                   for s in ['AAPL', 'MSFT', 'GOOGL', 'SPY']}, index=dates).rename_axis('Date')
            snapshot = save_snapshot(prices, root / 'data', {
                'requested_start': '2016-01-01', 'requested_end_exclusive': '2026-01-01',
            })
            with contextlib.redirect_stdout(io.StringIO()):
                first = run_study(snapshot, root / 'reports', window='2016-2020')
                second = run_study(snapshot, root / 'reports', window='2021-2025')
            for folder, expected_return, first_date in [(first, .2, '2020-12-29'), (second, .1, '2021-01-04')]:
                summary = pd.read_csv(folder / 'summary.csv')
                self.assertTrue((summary['price_observations'] == 3).all())
                self.assertTrue((summary['first_date'] == first_date).all())
                self.assertTrue((summary['initial_value'] == 10000).all())
                self.assertAlmostEqual(summary.iloc[0]['Total return'], expected_return)
            settings = json.loads((second / 'settings.json').read_text())
            self.assertEqual(settings['window'], '2021-2025')
            self.assertEqual(settings['start_inclusive'], '2021-01-01')

    def test_empty_subperiod_creates_no_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = self.make_snapshot(root)
            with self.assertRaises(ValueError):
                run_study(snapshot, root / 'reports', window='2021-2025')
            self.assertFalse((root / 'reports').exists())
