"""Strategy tests with synthetic prices and hand-calculated answers."""
import unittest

import numpy as np
import pandas as pd

from marketlens.analytics import analyze
from marketlens.simulation import buy_and_hold, monthly_rebalanced, daily_rebalanced


class BuyAndHoldTests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.DataFrame(
            {'AAA': [100.0, 200.0, 100.0], 'BBB': [100.0, 100.0, 100.0]},
            index=pd.bdate_range('2024-01-01', periods=3, name='Date'),
        )

    def test_holdings_reconcile_and_weights_drift(self):
        result = buy_and_hold(self.prices, [0.5, 0.5], 1000.0)
        np.testing.assert_allclose(result['units'], [5.0, 5.0])
        np.testing.assert_allclose(result['portfolio_value'], [1000.0, 1500.0, 1000.0])
        np.testing.assert_allclose(result['weights'].iloc[1], [2 / 3, 1 / 3])
        np.testing.assert_allclose(result['weights'].sum(axis=1), 1.0)
        np.testing.assert_allclose(result['holdings'].sum(axis=1), result['portfolio_value'])
        np.testing.assert_allclose(result['daily_returns'], [0.5, -1 / 3])
        self.assertAlmostEqual(result['metrics']['Total return'], 0.0)

    def test_differs_from_daily_rebalancing(self):
        held = buy_and_hold(self.prices, [0.5, 0.5], 1000.0)
        daily = analyze(self.prices, ['AAA', 'BBB'], [0.5, 0.5], 'BBB', 1000.0)
        self.assertAlmostEqual(held['portfolio_value'].iloc[-1], 1000.0)
        self.assertAlmostEqual(daily['portfolio_value']['Portfolio'].iloc[-1], 1125.0)

    def test_fractional_units_and_zero_weight(self):
        result = buy_and_hold(self.prices, [1.0, 0.0], 1234.56)
        self.assertAlmostEqual(result['units']['AAA'], 12.3456)
        np.testing.assert_allclose(result['holdings']['BBB'], 0.0)
        np.testing.assert_allclose(result['portfolio_value'], [1234.56, 2469.12, 1234.56])

    def test_invalid_inputs_are_rejected(self):
        for capital in [0.0, -1.0, np.inf, np.nan]:
            with self.subTest(capital=capital), self.assertRaises(ValueError):
                buy_and_hold(self.prices, [0.5, 0.5], capital)
        with self.assertRaises(ValueError):
            buy_and_hold(self.prices, [0.2, 0.2])
        missing = self.prices.copy()
        missing.iloc[1, 0] = np.nan
        with self.assertRaises(ValueError):
            buy_and_hold(missing, [0.5, 0.5])

    def test_does_not_mutate_input(self):
        original = self.prices.copy(deep=True)
        buy_and_hold(self.prices, [0.5, 0.5])
        pd.testing.assert_frame_equal(self.prices, original)

    def test_buy_and_hold_has_no_recurring_turnover(self):
        result = buy_and_hold(self.prices, [0.5, 0.5])
        self.assertTrue(result['rebalance_log'].empty)
        self.assertEqual(result['total_turnover'], 0.0)
        self.assertEqual(result['rebalance_count'], 0)


class MonthlyRebalancedTests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.DataFrame(
            {'AAA': [100.0, 200.0, 100.0, 100.0], 'BBB': [100.0] * 4},
            index=pd.to_datetime(['2025-01-30', '2025-01-31', '2025-02-03', '2025-02-04']),
        ).rename_axis('Date')

    def test_month_end_trade_changes_only_future_returns(self):
        result = monthly_rebalanced(self.prices, [0.5, 0.5], 1000.0)
        np.testing.assert_allclose(result['portfolio_value'], [1000.0, 1500.0, 1125.0, 1125.0])
        np.testing.assert_allclose(result['daily_returns'], [0.5, -0.25, 0.0])
        np.testing.assert_allclose(result['holdings'].iloc[1], [750.0, 750.0])
        np.testing.assert_allclose(result['weights'].iloc[2], [1 / 3, 2 / 3])
        self.assertEqual(result['rebalance_dates'].tolist(), [pd.Timestamp('2025-01-31')])
        np.testing.assert_allclose(result['holdings'].sum(axis=1), result['portfolio_value'])

    def test_final_date_is_not_rebalanced(self):
        prices = self.prices.iloc[:3].set_axis(pd.to_datetime(['2025-01-29', '2025-01-30', '2025-01-31']))
        result = monthly_rebalanced(prices, [0.5, 0.5], 1000.0)
        self.assertEqual(len(result['rebalance_dates']), 0)
        self.assertTrue(result['rebalance_log'].empty)
        self.assertEqual(result['total_turnover'], 0.0)
        pd.testing.assert_series_equal(result['portfolio_value'], buy_and_hold(prices, [0.5, 0.5], 1000.0)['portfolio_value'])

    def test_first_observation_at_month_end_needs_no_extra_trade(self):
        prices = self.prices.iloc[:3].set_axis(pd.to_datetime(['2025-01-31', '2025-02-03', '2025-02-04']))
        result = monthly_rebalanced(prices, [0.5, 0.5], 1000.0)
        self.assertEqual(len(result['rebalance_dates']), 0)
        pd.testing.assert_frame_equal(result['holdings'], buy_and_hold(prices, [0.5, 0.5], 1000.0)['holdings'])

    def test_reuses_validation_and_preserves_input(self):
        original = self.prices.copy(deep=True)
        monthly_rebalanced(self.prices, [0.5, 0.5])
        pd.testing.assert_frame_equal(self.prices, original)
        with self.assertRaises(ValueError):
            monthly_rebalanced(self.prices, [0.8, 0.8])
        with self.assertRaises(ValueError):
            monthly_rebalanced(self.prices, [0.5, 0.5], -1000.0)

    def test_turnover_records_both_buys_and_sales(self):
        result = monthly_rebalanced(self.prices, [0.5, 0.5], 1000.0)
        trade = result['rebalance_log'].loc[pd.Timestamp('2025-01-31')]
        self.assertAlmostEqual(trade['value_before'], 1500.0)
        self.assertAlmostEqual(trade['purchases'], 250.0)
        self.assertAlmostEqual(trade['sales'], 250.0)
        self.assertAlmostEqual(trade['gross_traded'], 500.0)
        self.assertAlmostEqual(trade['one_way_turnover'], 1 / 6)
        self.assertAlmostEqual(result['total_turnover'], 1 / 6)
        self.assertEqual(result['rebalance_count'], 1)

    def test_month_end_without_weight_drift_has_zero_turnover(self):
        prices = self.prices.copy()
        prices['BBB'] = prices['AAA']
        result = monthly_rebalanced(prices, [0.5, 0.5], 1000.0)
        self.assertEqual(result['rebalance_count'], 1)
        self.assertAlmostEqual(result['rebalance_log']['gross_traded'].sum(), 0.0)
        self.assertAlmostEqual(result['total_turnover'], 0.0)

    def test_turnover_is_independent_of_initial_capital(self):
        small = monthly_rebalanced(self.prices, [0.5, 0.5], 1000.0)
        large = monthly_rebalanced(self.prices, [0.5, 0.5], 10000.0)
        self.assertAlmostEqual(small['total_turnover'], large['total_turnover'])
        self.assertAlmostEqual(large['rebalance_log']['gross_traded'].sum(),
                               10 * small['rebalance_log']['gross_traded'].sum())

    def test_cost_is_paid_from_capital_and_returns(self):
        result = monthly_rebalanced(self.prices, [0.5, 0.5], 1000.0, cost_bps=10)
        trade = result['rebalance_log'].iloc[0]
        self.assertAlmostEqual(trade['gross_traded'], 500.0)
        self.assertAlmostEqual(trade['cost'], 0.5)
        self.assertAlmostEqual(result['total_cost'], 0.5)
        np.testing.assert_allclose(result['holdings'].iloc[1], [749.75, 749.75])
        np.testing.assert_allclose(result['portfolio_value'], [1000.0, 1499.5, 1124.625, 1124.625])
        self.assertAlmostEqual(trade['sales'] - trade['purchases'], trade['cost'])
        self.assertAlmostEqual(result['portfolio_value'].iloc[1] + trade['cost'], trade['value_before'])
        self.assertAlmostEqual(result['metrics']['Total return'], 1124.625 / 1000 - 1)

    def test_unequal_targets_require_cost_adjusted_trade_amounts(self):
        result = monthly_rebalanced(self.prices, [0.8, 0.2], 1000.0, cost_bps=10)
        trade = result['rebalance_log'].iloc[0]
        # Here fee = 0.001 * (320 + 0.6 * fee), rather than simply 0.32.
        expected_cost = 0.32 / (1 - 0.0006)
        self.assertAlmostEqual(trade['cost'], expected_cost)
        self.assertAlmostEqual(trade['cost'], 0.001 * trade['gross_traded'])
        self.assertAlmostEqual(result['holdings'].iloc[1].sum() + expected_cost, 1800.0)
        np.testing.assert_allclose(result['weights'].iloc[1], [0.8, 0.2])

    def test_no_weight_drift_means_no_fee(self):
        prices = self.prices.copy()
        prices['BBB'] = prices['AAA']
        result = monthly_rebalanced(prices, [0.5, 0.5], 1000.0, cost_bps=25)
        self.assertAlmostEqual(result['total_cost'], 0.0)

    def test_invalid_cost_rates_are_rejected(self):
        for rate in [-1, np.nan, np.inf, 10000]:
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                monthly_rebalanced(self.prices, [0.5, 0.5], cost_bps=rate)

    def test_no_final_rebalance_means_no_fee(self):
        prices = self.prices.iloc[:3].set_axis(pd.to_datetime(['2025-01-29', '2025-01-30', '2025-01-31']))
        result = monthly_rebalanced(prices, [0.5, 0.5], cost_bps=25)
        self.assertEqual(result['total_cost'], 0.0)


class DailyRebalancedTests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.DataFrame(
            {'AAA': [100.0, 200.0, 100.0, 100.0], 'BBB': [100.0] * 4},
            index=pd.bdate_range('2025-01-06', periods=4, name='Date'),
        )

    def test_zero_cost_matches_existing_daily_analytics(self):
        result = daily_rebalanced(self.prices, [0.5, 0.5], 1000.0)
        existing = analyze(self.prices, ['AAA', 'BBB'], [0.5, 0.5], 'BBB', 1000.0)
        np.testing.assert_allclose(result['portfolio_value'], existing['portfolio_value']['Portfolio'])
        np.testing.assert_allclose(result['daily_returns'], existing['daily_returns']['Portfolio'])
        self.assertEqual(result['rebalance_dates'].tolist(), self.prices.index[1:-1].tolist())
        self.assertEqual(result['total_cost'], 0.0)

    def test_daily_trading_occurs_without_a_month_change(self):
        daily = daily_rebalanced(self.prices, [0.5, 0.5], 1000.0)
        monthly = monthly_rebalanced(self.prices, [0.5, 0.5], 1000.0)
        self.assertEqual(daily['rebalance_count'], 2)
        self.assertEqual(monthly['rebalance_count'], 0)
        self.assertAlmostEqual(daily['portfolio_value'].iloc[-1], 1125.0)
        self.assertAlmostEqual(monthly['portfolio_value'].iloc[-1], 1000.0)

    def test_costs_reconcile_across_multiple_trades(self):
        result = daily_rebalanced(self.prices, [0.5, 0.5], 1000.0, cost_bps=10)
        np.testing.assert_allclose(result['portfolio_value'], [1000.0, 1499.5, 1124.250125, 1124.250125])
        np.testing.assert_allclose(result['rebalance_log']['cost'], [0.5, 0.374875])
        self.assertAlmostEqual(result['total_cost'], 0.874875)
        for timestamp, trade in result['rebalance_log'].iterrows():
            self.assertAlmostEqual(result['holdings'].loc[timestamp].sum() + trade['cost'], trade['value_before'])
            self.assertAlmostEqual(trade['sales'] - trade['purchases'], trade['cost'])
            self.assertAlmostEqual(trade['cost'], trade['gross_traded'] * 0.001)

    def test_no_drift_produces_no_cost_and_no_final_trade(self):
        prices = self.prices.copy()
        prices['BBB'] = prices['AAA']
        result = daily_rebalanced(prices, [0.5, 0.5], 1000.0, cost_bps=25)
        self.assertAlmostEqual(result['total_cost'], 0.0)
        self.assertAlmostEqual(result['total_turnover'], 0.0)
        self.assertNotIn(prices.index[-1], result['rebalance_log'].index)

    def test_daily_inputs_are_validated(self):
        with self.assertRaises(ValueError):
            daily_rebalanced(self.prices, [0.5, 0.5], cost_bps=-1)
        with self.assertRaises(ValueError):
            daily_rebalanced(self.prices, [0.8, 0.8])


if __name__ == '__main__':
    unittest.main()
