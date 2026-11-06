"""Research page checks using synthetic SQL results."""
from itertools import product
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from marketlens.research import load_research

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


class ResearchPageTests(unittest.TestCase):
    def setUp(self):
        directory = pd.DataFrame([{'Symbol': 'AAA', 'Price symbol': 'AAA', 'Name': 'Example', 'Type': 'Stock / other'}])
        directory_patch = patch('marketlens.securities.load_directory', return_value=(directory, '2026-11-05'))
        directory_patch.start()
        self.addCleanup(directory_patch.stop)
        validation_patch = patch('marketlens.validation.load_validation', return_value=None)
        validation_patch.start()
        self.addCleanup(validation_patch.stop)
        records = []
        windows = [('2016-01-04', '2025-12-31', .3), ('2016-01-04', '2020-12-31', .2),
                   ('2021-01-04', '2025-12-31', .1)]
        for (first, last, total), allocation, strategy, rate in product(
            windows, ['Equal weight', 'Concentrated'], ['Buy-and-hold', 'Monthly', 'Daily'], [0, 5, 10, 25]
        ):
            records.append({'first_date': first, 'last_date': last, 'allocation': allocation,
                            'strategy': strategy, 'cost_bps': rate, 'total_return': total,
                            'return_rank': 1, 'volatility': .2, 'max_drawdown': -.1,
                            'total_cost': rate, 'ending_value_reduction': rate * 2})
        self.comparison = pd.DataFrame(records)

    def open_research(self):
        app = AppTest.from_file(APP).run()
        return app.switch_page('pages/1_Research_study.py').run()

    def test_saved_results_and_period_selection(self):
        with patch('marketlens.research.load_research', return_value=self.comparison):
            app = self.open_research()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.title[0].value, 'Concentration & rebalancing')
            self.assertEqual(len(app.dataframe), 2)
            self.assertEqual(len(app.dataframe[0].value), 3)
            app.selectbox(key='study_period').set_value('2021–2025').run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue((app.dataframe[0].value['Total return'] == .1).all())
            app.select_slider(key='study_cost').set_value(25).run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue((app.dataframe[0].value['Fees paid'] == 25).all())

    def test_missing_results_show_setup_message(self):
        with patch('marketlens.research.load_research', side_effect=FileNotFoundError('Missing database')):
            app = self.open_research()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.info), 1)
            self.assertEqual(len(app.dataframe), 0)

    def test_missing_database_is_not_created_by_reading(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'missing.sqlite'
            with self.assertRaises(FileNotFoundError):
                load_research(database=database)
            self.assertFalse(database.exists())

    def test_validation_tab_labels_a_stale_record(self):
        receipt = {
            'generated_at_utc': '2026-11-06T01:00:00+00:00', 'is_current': False,
            'tests': {'passed': 79, 'total': 79, 'successful': True, 'failures': 0, 'errors': 0, 'skipped': 0},
            'study': {'cases': 72, 'accounting_cases': 72,
                      'audit': {'observed_sessions': 2514, 'expected_sessions': 2514},
                      'checks': [{'check': 'SQL cases', 'status': 'Passed', 'detail': '72 cases checked.'}]},
        }
        with patch('marketlens.research.load_research', return_value=self.comparison), patch(
            'marketlens.validation.load_validation', return_value=receipt
        ):
            app = self.open_research()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any('out of date' in warning.value for warning in app.warning))
            self.assertEqual(app.metric[0].value, '79 / 79')
            self.assertEqual(len(app.table), 1)
