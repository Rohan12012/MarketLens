"""Run the SQL against a temporary database with synthetic study results."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

import pandas as pd

from marketlens.store_study import store_study, compare_costs


class StoreStudyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.report = root / 'test-run'
        self.report.mkdir()
        self.database = root / 'study.sqlite'
        records = []
        for allocation in ['Equal weight', 'Concentrated']:
            for strategy in ['Buy-and-hold', 'Monthly', 'Daily']:
                for rate in [0, 5, 10, 25]:
                    multiplier = {'Buy-and-hold': 0, 'Monthly': 2, 'Daily': 5}[strategy]
                    baseline = 2000 + (100 if allocation == 'Concentrated' else 0)
                    ending = baseline - rate * multiplier
                    records.append({
                        'allocation': allocation, 'strategy': strategy, 'cost_bps': rate,
                        'initial_value': 1000, 'ending_value': ending, 'Total return': ending / 1000 - 1,
                        'Annualized volatility': .2, 'Max drawdown': -.1,
                        'total_cost': rate if multiplier else 0, 'one_way_turnover': .5 if multiplier else 0,
                    })
        self.summary = pd.DataFrame(records)
        self.summary.to_csv(self.report / 'summary.csv', index=False)
        settings = {'allocations': {'Equal weight': [], 'Concentrated': []},
                    'cost_rates_bps': [0, 5, 10, 25], 'cases': 24,
                    'prices_sha256': 'synthetic-test-input',
                    'actual_first_date': '2024-01-02', 'actual_last_date': '2024-12-31'}
        (self.report / 'settings.json').write_text(json.dumps(settings))

    def test_import_is_repeatable_without_duplicate_rows(self):
        store_study(self.report, self.database)
        store_study(self.report, self.database)
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM study_runs').fetchone()[0], 1)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM study_results').fetchone()[0], 24)
        self.summary.loc[0, 'ending_value'] = 1234
        self.summary.to_csv(self.report / 'summary.csv', index=False)
        with self.assertRaisesRegex(ValueError, 'different results'):
            store_study(self.report, self.database)

    def test_sql_matches_baselines_by_allocation_and_strategy(self):
        run_id = store_study(self.report, self.database)
        rows = compare_costs(self.database, run_id)
        self.assertEqual(len(rows), 6)
        for row in rows:
            expected = {'Buy-and-hold': 0, 'Monthly': 20, 'Daily': 50}[row['strategy']]
            self.assertAlmostEqual(row['ending_value_reduction'], expected)
        self.assertEqual(compare_costs(self.database, "unknown' OR 1=1 --"), [])

    def test_database_constraint_failure_rolls_back_the_run(self):
        self.summary.loc[0, 'total_cost'] = -1
        self.summary.to_csv(self.report / 'summary.csv', index=False)
        with self.assertRaises(sqlite3.IntegrityError):
            store_study(self.report, self.database)
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM study_runs').fetchone()[0], 0)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM study_results').fetchone()[0], 0)
