"""MarketLens CLI. Run python main.py --help for options."""
import argparse
import json
from pathlib import Path
import sys
from marketlens.analytics import analyze
from marketlens.data import download_history, align_history, history_window, load_prices, parse_symbols, save_snapshot

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description='MarketLens historical portfolio analytics')
    parser.add_argument('--tickers', default='AAPL,MSFT,GOOGL')
    parser.add_argument('--weights', help='Comma-separated weights summing to 1; default equal weights')
    parser.add_argument('--benchmark', default='SPY')
    parser.add_argument('--years', type=int, default=50, help='Lookback years when --start is omitted (default 50)')
    parser.add_argument('--start', help='Explicit start date overrides --years')
    parser.add_argument('--end', help='Exclusive end date; defaults to today in New York')
    parser.add_argument('--input', type=Path, help='Offline prices.csv from a MarketLens snapshot')
    parser.add_argument('--initial-value', type=float, default=10000.)
    parser.add_argument('--risk-free', type=float, default=0., help='Annual decimal rate, e.g. 0.04')
    args = parser.parse_args()
    try:
        assets = parse_symbols(args.tickers)
        benchmarks = parse_symbols(args.benchmark)
        if len(benchmarks) != 1:
            raise ValueError('Choose exactly one benchmark.')
        benchmark = benchmarks[0]
        weights = [float(w) for w in args.weights.split(',')] if args.weights else [1 / len(assets)] * len(assets)
        symbols = list(dict.fromkeys(assets + [benchmark]))
        default_start, default_end = history_window(args.years)
        start, end = args.start or default_start, args.end or default_end
        full_history = load_prices(args.input) if args.input else download_history(symbols, start, end)
        prices, coverage = align_history(full_history)
        results = analyze(prices, assets, weights, benchmark, args.initial_value, args.risk_free)
        metadata = {'source': str(args.input.resolve()) if args.input else 'Yahoo Finance via yfinance',
                    'requested_start': None if args.input else start,
                    'requested_end_exclusive': None if args.input else end,
                    'adjustment': 'provider-adjusted close; offline inputs must use the same convention'}
        snapshot = save_snapshot(prices, ROOT / 'data' / 'snapshots', metadata)
        full_history.to_csv(snapshot / 'available_history.csv', index_label='Date')
        coverage.to_csv(snapshot / 'coverage.csv', index=False)
        report = ROOT / 'reports' / snapshot.name
        report.mkdir(parents=True)
        for name, table in results.items():
            table.to_csv(report / f'{name}.csv')
        settings = {'assets': assets, 'weights': weights, 'benchmark': benchmark,
                    'initial_value': args.initial_value, 'annual_risk_free': args.risk_free,
                    'rebalancing': 'daily', 'snapshot': str(snapshot),
                    'costs_and_taxes': 'excluded', 'annualization_trading_days': 252}
        (report / 'settings.json').write_text(json.dumps(settings, indent=2) + '\n')
        print('MarketLens | historical daily rebalanced model portfolio')
        print(f'Observations: {len(prices)} | {prices.index[0].date()} to {prices.index[-1].date()}')
        print(results['metrics'].to_string(float_format=lambda x: f'{x:.4f}'))
        print('Returns, volatility, and drawdown are decimals; Sharpe is unitless.')
        print(f'Snapshot: {snapshot}\nReports: {report}')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'MarketLens error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
