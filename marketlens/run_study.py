"""Run a study window from a saved snapshot, without network access."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import uuid

import pandas as pd

from marketlens.data import load_prices
from marketlens.study import ASSETS, BENCHMARK, ALLOCATIONS, COST_RATES, START_DATE, END_DATE, WINDOWS, compare_allocations

ROOT = Path(__file__).resolve().parents[1]


def run_study(snapshot, output_root=None, *, window='full'):
    if window not in WINDOWS:
        raise ValueError(f'Choose a study window from: {", ".join(WINDOWS)}.')
    snapshot = Path(snapshot).resolve()
    price_file = snapshot / 'prices.csv'
    source = json.loads((snapshot / 'metadata.json').read_text())
    checksum = hashlib.sha256(price_file.read_bytes()).hexdigest()
    if checksum != source.get('prices_sha256'):
        raise ValueError('Snapshot checksum does not match. Use the original saved prices.')
    if (source.get('requested_start'), source.get('requested_end_exclusive')) != (START_DATE, END_DATE):
        raise ValueError('Snapshot was not requested for the fixed study dates.')
    prices = load_prices(price_file)
    if prices.index[0] < pd.Timestamp(START_DATE) or prices.index[-1] >= pd.Timestamp(END_DATE):
        raise ValueError('Snapshot contains dates outside the study window.')
    if len(prices) != source.get('rows') or list(prices.columns) != source.get('symbols'):
        raise ValueError('Snapshot rows or symbols do not match its metadata.')

    start, end = WINDOWS[window]
    prices = prices.loc[(prices.index >= pd.Timestamp(start)) & (prices.index < pd.Timestamp(end))].copy()
    results = compare_allocations(prices)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = Path(output_root or ROOT / 'reports' / 'study') / f'{stamp}-{uuid.uuid4().hex[:8]}'
    output.mkdir(parents=True, exist_ok=False)
    results['summary'].to_csv(output / 'summary.csv', index=False)
    pd.Series(results['benchmark_metrics'], name=BENCHMARK).to_csv(output / 'benchmark_metrics.csv')
    for (allocation, strategy, rate), simulation in results['simulations'].items():
        case = output / f'{allocation.lower().replace(" ", "-")}__{strategy.lower()}__{rate}bps'
        case.mkdir()
        for name in ['holdings', 'weights', 'portfolio_value', 'daily_returns', 'rebalance_log']:
            simulation[name].to_csv(case / f'{name}.csv')
    tracked = ['marketlens/study.py', 'marketlens/simulation.py', 'marketlens/analytics.py',
               'marketlens/data.py', 'marketlens/run_study.py', 'docs/analysis-brief.md']
    settings = {
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'snapshot': str(snapshot), 'prices_sha256': checksum, 'source_metadata': source,
        'window': window, 'start_inclusive': start, 'end_exclusive': end,
        'actual_first_date': str(prices.index[0].date()),
        'actual_last_date': str(prices.index[-1].date()),
        'assets': ASSETS, 'allocations': ALLOCATIONS, 'benchmark': BENCHMARK,
        'cost_rates_bps': COST_RATES, 'initial_value': 10000,
        'annual_risk_free': 0, 'annualization_days': 252,
        'initial_and_terminal_costs': 'excluded', 'cases': len(results['summary']),
        'package_versions': {name: version(name) for name in ['pandas', 'numpy']},
        'code_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in tracked},
    }
    (output / 'settings.json').write_text(json.dumps(settings, indent=2) + '\n')
    print(f'Completed {window}: {len(results["summary"])} cases on {len(prices):,} price observations.')
    print(f'Reports: {output}')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path, help='Study snapshot folder containing prices.csv and metadata.json')
    parser.add_argument('--window', choices=list(WINDOWS), default='full')
    args = parser.parse_args()
    try:
        run_study(args.snapshot, window=args.window)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f'Study failed: {exc}\n')
