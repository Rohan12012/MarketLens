"""Download the study prices: python -m marketlens.prepare_study_data."""
from pathlib import Path

import pandas as pd

from marketlens.data import download_history, save_snapshot, validate_prices
from marketlens.study import ASSETS, BENCHMARK, START_DATE, END_DATE

ROOT = Path(__file__).resolve().parents[1]


def prepare_study_data():
    prices = download_history(ASSETS + [BENCHMARK], START_DATE, END_DATE)
    # This fixed study must not silently lose an asset's early observations.
    validate_prices(prices)
    if prices.index[0] < pd.Timestamp(START_DATE) or prices.index[-1] >= pd.Timestamp(END_DATE):
        raise ValueError('Provider returned dates outside the requested study window.')
    metadata = {
        'source': 'Yahoo Finance via yfinance',
        'requested_start': START_DATE,
        'requested_end_exclusive': END_DATE,
        'adjustment': 'auto_adjust=True; adjusted daily closes',
        'study_brief': 'docs/analysis-brief.md',
        'missing_price_policy': 'Reject missing cells; no filling or row removal.',
    }
    folder = save_snapshot(prices, ROOT / 'data' / 'study', metadata)
    print(f'Saved {len(prices):,} price observations for {", ".join(prices.columns)}.')
    print(f'Actual coverage: {prices.index[0].date()} to {prices.index[-1].date()}')
    print(f'Missing cells: {int(prices.isna().sum().sum())}')
    print(f'Snapshot: {folder}')
    return folder


if __name__ == '__main__':
    prepare_study_data()
