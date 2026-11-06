"""Dashboard smoke tests use synthetic prices and no network requests."""
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from marketlens.securities import parse_directory
from marketlens.data import history_window

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


class DashboardTests(unittest.TestCase):
    def test_empty_dashboard(self):
        app = AppTest.from_file(APP).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.title[0].value, 'MarketLens')

    def test_analysis_and_invalid_weights(self):
        prices = pd.DataFrame({'AAPL': [100., 101., 99.], 'MSFT': [100., 102., 101.],
                               'GOOGL': [100., 99., 102.], 'SPY': [100., 101., 100.]},
                              index=pd.date_range('2024-01-01', periods=3, name='Date'))
        with patch('marketlens.data.download_history', return_value=prices):
            app = AppTest.from_file(APP).run()
            app.button(key='run_analysis').click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.metric), 4)
            app.text_input[1].set_value('0.1,0.1,0.1')
            app.button(key='run_analysis').click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.error), 1)
            self.assertEqual(len(app.metric), 0)

    def test_directory_search_transfers_selected_ticker(self):
        text = ('Symbol|Security Name|Test Issue|ETF\n'
                'AAA|Example company|N|N\nFUND|Example ETF|N|Y\n')
        directory = parse_directory(text, 'nasdaq')
        with patch('marketlens.securities.load_directory', return_value=(directory, '2026-11-05T12:00:00+00:00')):
            app = AppTest.from_file(APP).run()
            app.button(key='load_directory').click().run()
            app.text_input(key='security_search').set_value('Example ETF').run()
            app.multiselect(key='catalog_assets').set_value(['FUND']).run()
            next(button for button in app.button if button.label == 'Use selected assets').click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.text_input(key='portfolio_tickers').value, 'FUND')

    def test_new_listing_keeps_full_individual_history(self):
        prices = pd.DataFrame({'OLD': [100., 101., 102., 103., 104.],
                               'NEW': [float('nan'), float('nan'), 100., 101., 102.],
                               'SPY': [100., 100., 100., 100., 100.]},
                              index=pd.date_range('2024-01-01', periods=5, name='Date'))
        with patch('marketlens.data.download_history', return_value=prices) as download:
            app = AppTest.from_file(APP).run()
            app.text_input(key='portfolio_tickers').set_value('OLD,NEW')
            app.button(key='run_analysis').click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.session_state['full_history']), 5)
            self.assertEqual(len(app.session_state['analysis'][0]), 3)
            self.assertEqual(download.call_args.args[1:3], history_window())
