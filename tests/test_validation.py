"""Saved validation records and accounting checks with synthetic exports."""
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from marketlens.validation import check_accounting, load_validation, source_fingerprint


class ValidationTests(unittest.TestCase):
    def test_record_is_marked_stale_after_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / 'latest.json'
            receipt.write_text(json.dumps({'source_fingerprint': 'original'}))
            with patch('marketlens.validation.RECEIPT', receipt), patch(
                'marketlens.validation.source_fingerprint', return_value='changed'
            ):
                self.assertFalse(load_validation()['is_current'])

    def test_no_saved_record_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('marketlens.validation.RECEIPT', Path(directory) / 'missing.json'):
                self.assertIsNone(load_validation())

    def test_generated_reports_do_not_change_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'app.py').write_text('print(1)\n')
            before = source_fingerprint(root)
            (root / 'reports').mkdir()
            (root / 'reports' / 'latest.json').write_text('{}')
            self.assertEqual(source_fingerprint(root), before)
            (root / 'app.py').write_text('print(2)\n')
            self.assertNotEqual(source_fingerprint(root), before)

    def test_changed_checked_file_marks_record_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / 'prices.csv'
            data.write_text('original prices')
            receipt = root / 'latest.json'
            receipt.write_text(json.dumps({'source_fingerprint': 'same',
                                           'study': {'checked_files': {str(data): hashlib.sha256(data.read_bytes()).hexdigest()}}}))
            with patch('marketlens.validation.RECEIPT', receipt), patch(
                'marketlens.validation.source_fingerprint', return_value='same'
            ):
                self.assertTrue(load_validation()['is_current'])
                data.write_text('changed prices')
                self.assertFalse(load_validation()['is_current'])

    def test_accounting_flags_an_incorrect_fee(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            case = root / 'test-run' / 'example__monthly__10bps'
            case.mkdir(parents=True)
            dates = ['2024-01-02', '2024-01-03']
            pd.DataFrame({'AAA': [5000., 5500.], 'BBB': [5000., 5500.]}, index=dates).to_csv(case / 'holdings.csv')
            pd.Series([10000., 11000.], index=dates, name='Portfolio').to_csv(case / 'portfolio_value.csv')
            log = pd.DataFrame({'value_before': [11001.], 'purchases': [499.5], 'sales': [500.5],
                                'gross_traded': [1000.], 'cost': [1.]}, index=dates[1:])
            log.to_csv(case / 'rebalance_log.csv')
            comparison = pd.DataFrame([{'run_id': 'test-run', 'allocation': 'Example', 'strategy': 'Monthly',
                                        'cost_bps': 10, 'total_return': .1}])
            self.assertEqual(check_accounting(comparison, root), 1)
            log['cost'] = 2.
            log.to_csv(case / 'rebalance_log.csv')
            with self.assertRaisesRegex(ValueError, 'fees do not reconcile'):
                check_accounting(comparison, root)
