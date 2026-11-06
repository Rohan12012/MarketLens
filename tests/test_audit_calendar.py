"""Calendar checks with synthetic prices on known holiday and weekday dates."""
import unittest

import pandas as pd

from marketlens.audit_calendar import audit_sessions


class CalendarAuditTests(unittest.TestCase):
    def prices(self, dates):
        return pd.DataFrame({'AAA': [100.] * len(dates)}, index=pd.to_datetime(dates))

    def test_new_year_holiday_and_weekend_are_not_missing_sessions(self):
        prices = self.prices(['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'])
        audit = audit_sessions(prices, '2024-01-01', '2024-01-08')
        self.assertTrue(audit['passed'])
        self.assertEqual(audit['expected_sessions'], 4)

    def test_date_missing_for_every_symbol_is_detected(self):
        prices = self.prices(['2024-01-02', '2024-01-04', '2024-01-05'])
        audit = audit_sessions(prices, '2024-01-01', '2024-01-08')
        self.assertFalse(audit['passed'])
        self.assertEqual(audit['missing_sessions'], ['2024-01-03'])

    def test_weekend_price_is_flagged(self):
        prices = self.prices(['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-06'])
        audit = audit_sessions(prices, '2024-01-01', '2024-01-08')
        self.assertEqual(audit['unexpected_sessions'], ['2024-01-06'])
        self.assertFalse(audit['passed'])
