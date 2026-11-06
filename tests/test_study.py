"""Checks for the 24-case study using synthetic prices."""
import unittest

import numpy as np
import pandas as pd

from marketlens.study import compare_allocations


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.DataFrame(
            {'AAPL': [100., 200., 100., 100.], 'MSFT': [100.] * 4,
             'GOOGL': [100.] * 4, 'SPY': [100., 110., 110., 110.]},
            index=pd.to_datetime(['2025-01-30', '2025-01-31', '2025-02-03', '2025-02-04']),
        ).rename_axis('Date')

    def test_all_cases_use_same_dates_and_capital(self):
        result = compare_allocations(self.prices, 1000.)
        summary = result['summary']
        self.assertEqual(len(summary), 24)
        self.assertEqual(len(result['simulations']), 24)
        self.assertFalse(summary.duplicated(['allocation', 'strategy', 'cost_bps']).any())
        self.assertEqual(set(summary['cost_bps']), {0, 5, 10, 25})
        self.assertEqual(set(summary['first_date']), {self.prices.index[0]})
        self.assertEqual(set(summary['last_date']), {self.prices.index[-1]})
        self.assertTrue((summary['initial_value'] == 1000.).all())
        self.assertTrue((summary['return_observations'] == 3).all())

    def test_buy_and_hold_cost_scenarios_are_identical(self):
        summary = compare_allocations(self.prices)['summary']
        held = summary.loc[summary['strategy'] == 'Buy-and-hold']
        self.assertTrue((held['total_cost'] == 0).all())
        self.assertTrue((held['one_way_turnover'] == 0).all())
        self.assertTrue((held.groupby('allocation')['ending_value'].nunique() == 1).all())

    def test_benchmark_is_separate_and_arithmetic_is_known(self):
        result = compare_allocations(self.prices, 1000.)
        self.assertAlmostEqual(result['benchmark_metrics']['Total return'], 0.1)
        summary = result['summary']
        held = summary.loc[(summary['strategy'] == 'Buy-and-hold') & (summary['cost_bps'] == 0)]
        np.testing.assert_allclose(held['ending_value'], 1000.)
        np.testing.assert_allclose(held['return_difference'], -0.1)
        np.testing.assert_allclose(summary['Total return'], summary['ending_value'] / 1000. - 1)

    def test_costs_reduce_value_in_this_fixture(self):
        summary = compare_allocations(self.prices)['summary']
        for allocation in ['Equal weight', 'Concentrated']:
            monthly = summary.loc[(summary['allocation'] == allocation) & (summary['strategy'] == 'Monthly')]
            self.assertTrue((monthly['ending_value'].diff().dropna() < 0).all())

    def test_missing_asset_or_missing_price_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_allocations(self.prices.drop(columns='GOOGL'))
        missing = self.prices.copy()
        missing.iloc[1, 0] = np.nan
        with self.assertRaises(ValueError):
            compare_allocations(missing)

    def test_column_order_does_not_change_asset_allocations(self):
        expected = compare_allocations(self.prices)['summary']
        actual = compare_allocations(self.prices[self.prices.columns[::-1]])['summary']
        pd.testing.assert_frame_equal(actual, expected)


if __name__ == '__main__':
    unittest.main()
