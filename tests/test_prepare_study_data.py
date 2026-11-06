"""Study download checks using a small synthetic price table."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from marketlens.prepare_study_data import prepare_study_data


class PrepareStudyDataTests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.DataFrame(
            {symbol: [100., 101., 102.] for symbol in ['AAPL', 'MSFT', 'GOOGL', 'SPY']},
            index=pd.bdate_range('2016-01-04', periods=3, name='Date'),
        )

    def test_download_uses_fixed_dates_and_records_source(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('marketlens.prepare_study_data.ROOT', Path(root)), patch(
                'marketlens.prepare_study_data.download_history', return_value=self.prices
            ) as download, contextlib.redirect_stdout(io.StringIO()):
                folder = prepare_study_data()
            download.assert_called_once_with(['AAPL', 'MSFT', 'GOOGL', 'SPY'], '2016-01-01', '2026-01-01')
            saved = pd.read_csv(folder / 'prices.csv', index_col=0, parse_dates=True)
            pd.testing.assert_frame_equal(saved, self.prices, check_freq=False)
            metadata = json.loads((folder / 'metadata.json').read_text())
            self.assertEqual(metadata['requested_start'], '2016-01-01')
            self.assertEqual(metadata['source'], 'Yahoo Finance via yfinance')

    def test_missing_initial_price_is_not_trimmed_away(self):
        self.prices.iloc[0, 0] = float('nan')
        with patch('marketlens.prepare_study_data.download_history', return_value=self.prices):
            with self.assertRaises(ValueError):
                prepare_study_data()

    def test_out_of_window_dates_are_rejected(self):
        outside = self.prices.set_axis(pd.bdate_range('2026-01-05', periods=3))
        with patch('marketlens.prepare_study_data.download_history', return_value=outside):
            with self.assertRaises(ValueError):
                prepare_study_data()
