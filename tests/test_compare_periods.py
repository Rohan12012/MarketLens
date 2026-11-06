"""Period comparisons and SQL ranks using synthetic study results."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from marketlens.compare_periods import compare_periods, ROOT
from marketlens.study import WINDOWS


class ComparePeriodsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / 'study.sqlite'
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.executescript((ROOT / 'docs' / 'study-schema.sql').read_text())
            for run_id, window in [('full', 'full'), ('first', '2016-2020'), ('second', '2021-2025'), ('extra', 'full')]:
                start, end = WINDOWS[window]
                settings = json.dumps({'start_inclusive': start, 'end_exclusive': end})
                connection.execute('INSERT INTO study_runs VALUES (?, ?, ?, ?, ?, ?)',
                                   (run_id, 'same-source', 'synthetic-summary', settings, start, end))
                for allocation in ['Equal weight', 'Concentrated']:
                    for strategy in ['Buy-and-hold', 'Monthly', 'Daily']:
                        base = (1500 if strategy == 'Buy-and-hold' else 1300) if run_id == 'first' else (1200 if strategy == 'Buy-and-hold' else 1300)
                        for rate in [0, 5, 10, 25]:
                            fee = 0 if strategy == 'Buy-and-hold' else rate
                            ending = base - fee
                            connection.execute('INSERT INTO study_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                               (run_id, allocation, strategy, rate, 1000, ending,
                                                ending / 1000 - 1, .2, -.1, fee, .5))

    def test_query_selects_only_requested_runs_and_handles_ties(self):
        comparison = compare_periods(self.database, 'full', 'first', 'second')
        self.assertEqual(len(comparison), 72)
        self.assertNotIn('extra', comparison.run_id.values)
        full = comparison[(comparison.run_id == 'full') & (comparison.cost_bps == 0)]
        self.assertTrue((full.loc[full.strategy.isin(['Monthly', 'Daily']), 'return_rank'] == 1).all())
        self.assertTrue((full.loc[full.strategy == 'Buy-and-hold', 'return_rank'] == 2).all())
        first = comparison[(comparison.run_id == 'first') & (comparison.cost_bps == 10)]
        self.assertTrue((first.loc[first.strategy == 'Buy-and-hold', 'return_rank'] == 1).all())
        self.assertTrue((first.loc[first.strategy == 'Monthly', 'ending_value_reduction'] == 10).all())

    def test_period_order_is_checked(self):
        with self.assertRaisesRegex(ValueError, 'expected'):
            compare_periods(self.database, 'first', 'full', 'second')

    def test_different_source_snapshot_is_rejected(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("UPDATE study_runs SET prices_sha256 = 'other-source' WHERE run_id = 'second'")
        with self.assertRaisesRegex(ValueError, 'same source'):
            compare_periods(self.database, 'full', 'first', 'second')

    def test_unknown_run_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not found'):
            compare_periods(self.database, 'missing', 'first', 'second')
