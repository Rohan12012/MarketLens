"""Download and preserve validated adjusted daily close prices."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import json
import re
import uuid
import hashlib
from importlib.metadata import version
import numpy as np
import pandas as pd


def parse_symbols(text):
    symbols = list(dict.fromkeys(s.strip().upper() for s in text.split(',') if s.strip()))
    if not symbols or any(not re.fullmatch(r'[A-Z0-9^][A-Z0-9.^=-]{0,19}', s) for s in symbols):
        raise ValueError('Use comma-separated ticker symbols, such as AAPL,MSFT.')
    return symbols


def validate_prices(prices):
    if prices.empty or len(prices) < 3:
        raise ValueError('At least three price observations are required.')
    if not isinstance(prices.index, pd.DatetimeIndex) or prices.index.hasnans:
        raise ValueError('Prices must have valid dates as their index.')
    if prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError('Dates must be unique and sorted ascending.')
    if prices.columns.has_duplicates:
        raise ValueError('Ticker columns must be unique.')
    values = prices.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError('Missing, infinite, or nonpositive prices detected. No filling applied.')


def history_window(years=50, today=None):
    """Use New York's calendar date; exclude today's potentially unfinished session."""
    today = today or datetime.now(ZoneInfo('America/New_York')).date()
    if not 1 <= years <= 100:
        raise ValueError('History years must be between 1 and 100.')
    try:
        start = today.replace(year=today.year - years)
    except ValueError:
        start = today.replace(year=today.year - years, day=28)
    return start.isoformat(), today.isoformat()


def align_history(history):
    """Trim only outside shared availability; missing prices within it remain errors."""
    if history.empty or history.isna().all().any():
        raise ValueError('One or more requested symbols returned no price history.')
    if not isinstance(history.index, pd.DatetimeIndex) or history.index.hasnans:
        raise ValueError('History must have valid dates.')
    if history.index.has_duplicates or not history.index.is_monotonic_increasing or history.columns.has_duplicates:
        raise ValueError('History dates must be sorted and unique; symbols must be unique.')
    coverage = pd.DataFrame([
        {'Symbol': symbol, 'First available': history[symbol].first_valid_index(),
         'Last available': history[symbol].last_valid_index(),
         'Observations': int(history[symbol].notna().sum())}
        for symbol in history.columns
    ])
    start = coverage['First available'].max()
    end = coverage['Last available'].min()
    aligned = history.loc[start:end].copy()
    validate_prices(aligned)
    aligned.attrs['coverage'] = [
        {**row, 'First available': row['First available'].isoformat(),
         'Last available': row['Last available'].isoformat()}
        for row in coverage.to_dict('records')
    ]
    return aligned, coverage


def download_history(symbols, start, end):
    import yfinance as yf
    cache = Path(__file__).resolve().parents[1] / 'data' / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(cache))
    if date.fromisoformat(start) >= date.fromisoformat(end):
        raise ValueError('Start must be before the exclusive end date.')
    raw = yf.download(symbols, start=start, end=end, interval='1d',
                      auto_adjust=True, progress=False, threads=False, keepna=True)
    if raw is None or raw.empty:
        raise ValueError('No data returned. Check symbols, dates, and network access.')
    prices = (raw['Close'].copy() if isinstance(raw.columns, pd.MultiIndex)
              else raw[['Close']].rename(columns={'Close': symbols[0]}))
    missing = set(symbols) - set(prices.columns)
    if missing:
        raise ValueError(f'Provider omitted requested symbols: {sorted(missing)}')
    prices = prices.loc[:, symbols]
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    prices.index.name = 'Date'
    # Leading/trailing gaps can reflect different listing dates. Validate each
    # security within its own coverage before comparing their shared period.
    for symbol in prices:
        series = prices[symbol].dropna()
        if series.empty:
            raise ValueError(f'{symbol} returned no price history.')
        validate_prices(prices.loc[series.index[0]:series.index[-1], [symbol]])
    return prices


def download_prices(symbols, start, end):
    prices, _ = align_history(download_history(symbols, start, end))
    return prices


def save_snapshot(prices, root, metadata):
    validate_prices(prices)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = Path(root) / f'{stamp}-{uuid.uuid4().hex[:8]}'
    folder.mkdir(parents=True, exist_ok=False)
    prices.to_csv(folder / 'prices.csv', index_label='Date')
    details = {**metadata, 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
               'rows': len(prices), 'symbols': list(prices.columns),
               'first_observation': str(prices.index.min().date()),
               'last_observation': str(prices.index.max().date())}
    details['prices_sha256'] = hashlib.sha256((folder / 'prices.csv').read_bytes()).hexdigest()
    details['package_versions'] = {name: version(name) for name in ['pandas', 'numpy', 'yfinance']}
    if 'coverage' in prices.attrs:
        details['individual_coverage'] = prices.attrs['coverage']
    (folder / 'metadata.json').write_text(json.dumps(details, indent=2) + '\n')
    return folder


def load_prices(path):
    prices = pd.read_csv(path, index_col=0, parse_dates=True)
    prices = prices.apply(pd.to_numeric, errors='raise')
    validate_prices(prices)
    return prices
