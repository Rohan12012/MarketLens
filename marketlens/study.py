"""Compare the study allocations, strategies, and cost rates."""
import pandas as pd

from marketlens.analytics import summarize
from marketlens.data import validate_prices
from marketlens.simulation import buy_and_hold, monthly_rebalanced, daily_rebalanced

ASSETS = ['AAPL', 'MSFT', 'GOOGL']
BENCHMARK = 'SPY'
START_DATE = '2016-01-01'
END_DATE = '2026-01-01'
WINDOWS = {'full': (START_DATE, END_DATE),
           '2016-2020': ('2016-01-01', '2021-01-01'),
           '2021-2025': ('2021-01-01', '2026-01-01')}
ALLOCATIONS = {'Equal weight': [1 / 3, 1 / 3, 1 / 3],
               'Concentrated': [0.8, 0.1, 0.1]}
COST_RATES = (0, 5, 10, 25)
STRATEGIES = {'Buy-and-hold': buy_and_hold, 'Monthly': monthly_rebalanced,
              'Daily': daily_rebalanced}


def compare_allocations(prices, initial_value=10000.0):
    """Run all 24 cases on the supplied adjusted prices.

    Use one shared date window. Metrics include fees and assume a 0% risk-free
    rate. The difference from SPY is a total-return difference, not alpha.
    Return the summary and each simulation's holdings and trade log.
    """
    required = ASSETS + [BENCHMARK]
    if not set(required).issubset(prices.columns):
        raise ValueError(f'Study requires price columns: {", ".join(required)}.')
    panel = prices.loc[:, required].copy()
    validate_prices(panel)
    benchmark_metrics = summarize(panel[BENCHMARK].pct_change(fill_method=None).iloc[1:])
    records, simulations = [], {}
    for allocation, weights in ALLOCATIONS.items():
        for strategy, simulate in STRATEGIES.items():
            for cost_bps in COST_RATES:
                options = {} if strategy == 'Buy-and-hold' else {'cost_bps': cost_bps}
                result = simulate(panel[ASSETS], weights, initial_value, **options)
                simulations[(allocation, strategy, cost_bps)] = result
                records.append({
                    'allocation': allocation, 'strategy': strategy, 'cost_bps': cost_bps,
                    'first_date': panel.index[0], 'last_date': panel.index[-1],
                    'price_observations': len(panel), 'return_observations': len(panel) - 1,
                    'initial_value': initial_value,
                    'ending_value': float(result['portfolio_value'].iloc[-1]),
                    **result['metrics'], 'total_cost': result['total_cost'],
                    'one_way_turnover': result['total_turnover'],
                    'rebalance_count': result['rebalance_count'],
                    'benchmark_total_return': benchmark_metrics['Total return'],
                    'return_difference': result['metrics']['Total return'] - benchmark_metrics['Total return'],
                })
    return {'summary': pd.DataFrame.from_records(records), 'simulations': simulations,
            'benchmark_metrics': benchmark_metrics}
