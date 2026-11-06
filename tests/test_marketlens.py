"""Synthetic test fixtures are arithmetic examples, not market observations."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from marketlens.analytics import analyze, summarize, validate_weights
from marketlens.data import download_prices, load_prices, parse_symbols, save_snapshot, validate_prices


class MarketLensTests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.DataFrame({'AAA': [100., 110., 99.], 'BBB': [100., 100., 100.]},
                                   index=pd.date_range('2024-01-01', periods=3, name='Date'))

    def test_known_portfolio_arithmetic(self):
        result = analyze(self.prices, ['AAA', 'BBB'], [.5, .5], benchmark='BBB')
        np.testing.assert_allclose(result['daily_returns']['Portfolio'], [.05, -.05])
        np.testing.assert_allclose(result['portfolio_value']['Portfolio'], [10000, 10500, 9975])
        self.assertAlmostEqual(result['metrics'].loc['Portfolio', 'Total return'], -.0025)
        self.assertAlmostEqual(result['metrics'].loc['Portfolio', 'Max drawdown'], -.05)

    def test_first_day_loss_counts_as_drawdown(self):
        self.assertAlmostEqual(summarize(pd.Series([-.1, 0.]))['Max drawdown'], -.1)

    def test_flat_benchmark_has_undefined_sharpe(self):
        self.assertTrue(np.isnan(summarize(pd.Series([0., 0.]))['Sharpe ratio']))

    def test_invalid_prices(self):
        for value in [np.nan, np.inf, 0, -1]:
            with self.subTest(value=value):
                frame = self.prices.copy()
                frame.iloc[1, 0] = value
                with self.assertRaises(ValueError):
                    validate_prices(frame)

    def test_dates(self):
        for index in [pd.to_datetime(['2024-01-01'] * 3), self.prices.index[::-1]]:
            with self.assertRaises(ValueError):
                validate_prices(self.prices.set_axis(index))

    def test_invalid_weights(self):
        for weights in [[.2, .2], [-.1, 1.1], [1], [np.nan, 0]]:
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                validate_weights(['AAA', 'BBB'], weights)

    def test_missing_benchmark(self):
        with self.assertRaises(ValueError):
            analyze(self.prices, ['AAA'], [1], 'MISSING')

    def test_roundtrip_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            folder = save_snapshot(self.prices, root, {'source': 'synthetic unit test'})
            pd.testing.assert_frame_equal(load_prices(folder / 'prices.csv'), self.prices, check_freq=False)
            self.assertTrue((folder / 'metadata.json').exists())

    def test_symbols(self):
        self.assertEqual(parse_symbols(' aapl,MSFT,aapl '), ['AAPL', 'MSFT'])
        with self.assertRaises(ValueError):
            parse_symbols('../bad')

    @patch('yfinance.download')
    def test_download_extracts_adjusted_close(self, mock):
        raw = self.prices.copy()
        raw.columns = pd.MultiIndex.from_product([['Close'], raw.columns])
        mock.return_value = raw
        pd.testing.assert_frame_equal(download_prices(['AAA', 'BBB'], '2024-01-01', '2024-02-01'), self.prices)
        self.assertTrue(mock.call_args.kwargs['auto_adjust'])

    @patch('yfinance.download', return_value=pd.DataFrame())
    def test_empty_download(self, mock):
        with self.assertRaises(ValueError):
            download_prices(['AAA'], '2024-01-01', '2024-02-01')

    def test_invalid_capital_and_risk_free(self):
        with self.assertRaises(ValueError):
            analyze(self.prices, ['AAA'], [1], 'BBB', initial_value=0)
        with self.assertRaises(ValueError):
            summarize(pd.Series([.1, -.1]), annual_risk_free=-1)


if __name__ == '__main__':
    unittest.main()
