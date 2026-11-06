"""A source response must not be mistaken for verified market prices."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from marketlens.data import save_snapshot
from marketlens.price_verification import prepare_sample, record_probe


class PriceVerificationTests(unittest.TestCase):
    def test_sample_keeps_reference_values_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config').mkdir()
            plan = {'symbols': ['AAA'], 'dates': ['2024-01-02', '2024-01-03', '2024-01-04']}
            (root / 'config' / 'price-check-sample.json').write_text(json.dumps(plan))
            prices = pd.DataFrame({'AAA': [100., 101., 102.]}, index=pd.to_datetime(plan['dates']))
            snapshot = save_snapshot(prices, root / 'data', {'source': 'synthetic test'})
            with patch('marketlens.price_verification.ROOT', root):
                output, _, count = prepare_sample(snapshot)
            sample = pd.read_csv(output / 'price-check-sample.csv')
            self.assertEqual(count, 3)
            self.assertTrue(sample.reference_close.isna().all())
            self.assertTrue(sample.difference.isna().all())
            self.assertEqual(set(sample.status), {'Not verified'})

    def test_html_with_http_200_is_not_a_verified_price(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('marketlens.price_verification.ROOT', root), patch('marketlens.price_verification.urlopen') as request:
                response = request.return_value.__enter__.return_value
                response.status = 200
                response.headers = {'Content-Type': 'text/html'}
                response.read.return_value = b'<html>Browser verification required</html>'
                result = record_probe(root, 'test-checksum', 12)
            self.assertEqual(result['status'], 'Not verified')
            self.assertEqual(result['verified_observations'], 0)
            self.assertIn('non-CSV', result['detail'])

    def test_csv_still_requires_a_confirmed_adjustment_basis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('marketlens.price_verification.ROOT', root), patch('marketlens.price_verification.urlopen') as request:
                response = request.return_value.__enter__.return_value
                response.status = 200
                response.headers = {'Content-Type': 'text/csv'}
                response.read.return_value = b'Date,Open,High,Low,Close,Volume\n2024-01-02,1,1,1,1,100\n'
                result = record_probe(root, 'test-checksum', 12)
            self.assertEqual(result['verified_observations'], 0)
            self.assertIn('adjustment basis', result['detail'])
