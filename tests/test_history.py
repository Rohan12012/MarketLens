"""Synthetic listing/history fixtures; not actual market observations."""
from datetime import date
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from marketlens.data import align_history, history_window
from marketlens.securities import parse_directory, load_directory, search_directory

NASDAQ = '''Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
AAA|Example stock|Q|N|N|100|N|N
FUND|Example fund|G|N|N|100|Y|N
TEST|Test issue|Q|Y|N|100|N|N
File Creation Time: 0101202412:00|||||||
'''
OTHER = '''ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
CLASS.B|Class B example|N|CLASS.B|N|100|N|CLASS.B
ETF|Example ETF|P|ETF|Y|100|N|ETF
File Creation Time: 0101202412:00|||||||
'''


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.history = pd.DataFrame({'OLD': [10., 11., 12., 13., 14.],
                                     'NEW': [np.nan, np.nan, 20., 21., 22.]},
                                    index=pd.date_range('2024-01-01', periods=5, name='Date'))

    def test_shared_start_preserves_individual_coverage(self):
        aligned, coverage = align_history(self.history)
        self.assertEqual(len(aligned), 3)
        self.assertEqual(len(self.history), 5)
        self.assertEqual(coverage.iloc[0]['First available'], self.history.index[0])
        self.assertEqual(coverage.iloc[1]['First available'], self.history.index[2])
        self.assertEqual(aligned.index[0], self.history.index[2])

    def test_internal_gap_is_rejected(self):
        frame = self.history.copy()
        frame.loc[frame.index[3], 'OLD'] = np.nan
        with self.assertRaises(ValueError):
            align_history(frame)

    def test_no_overlap_or_failed_symbol_is_rejected(self):
        for values in [[np.nan] * 5, [1., 2., np.nan, np.nan, np.nan]]:
            frame = self.history.copy()
            frame['OLD'] = values
            with self.assertRaises(ValueError):
                align_history(frame)

    def test_fifty_year_window_and_leap_day(self):
        self.assertEqual(history_window(50, date(2026, 11, 5)), ('1976-11-05', '2026-11-05'))
        self.assertEqual(history_window(50, date(2024, 2, 29))[0], '1974-02-28')

    def test_directory_filters_and_share_class_symbol(self):
        nasdaq = parse_directory(NASDAQ, 'nasdaq')
        other = parse_directory(OTHER, 'other')
        self.assertEqual(nasdaq['Symbol'].tolist(), ['AAA', 'FUND'])
        self.assertEqual(other.iloc[0]['Price symbol'], 'CLASS-B')
        self.assertEqual(search_directory(other, 'example', security_type='ETF')['Symbol'].tolist(), ['ETF'])
        self.assertTrue(search_directory(other, '[bad regex').empty)
        self.assertEqual(search_directory(other, exchange='NYSE')['Symbol'].tolist(), ['CLASS.B'])

    @patch('marketlens.securities.urlopen')
    def test_directory_cache_avoids_repeat_network(self, mock):
        mock.return_value.__enter__.return_value.read.side_effect = [NASDAQ.encode(), OTHER.encode()]
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'listings.json'
            first, timestamp = load_directory(cache_path=path)
            second, cached_timestamp = load_directory(cache_path=path)
            self.assertEqual(mock.call_count, 2)
            pd.testing.assert_frame_equal(first, second)
            self.assertEqual(timestamp, cached_timestamp)

    def test_bad_directory_schema(self):
        with self.assertRaises(ValueError):
            parse_directory('bad|header\nx|y', 'other')
