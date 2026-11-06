"""Historical analysis of a long-only, daily rebalanced model portfolio."""
import numpy as np
import pandas as pd
from marketlens.data import validate_prices

TRADING_DAYS = 252


def validate_weights(assets, weights):
    values = np.asarray(weights, dtype=float)
    if len(values) != len(assets) or not np.isfinite(values).all():
        raise ValueError('Provide one finite weight for each asset.')
    if (values < 0).any() or not np.isclose(values.sum(), 1, atol=1e-8, rtol=0):
        raise ValueError('Weights must be nonnegative and sum to 1.')
    return pd.Series(values, index=assets)


def summarize(returns, annual_risk_free=0.0):
    if returns.empty or not np.isfinite(returns.to_numpy()).all():
        raise ValueError('Return observations must be finite and nonempty.')
    if not np.isfinite(annual_risk_free) or annual_risk_free <= -1:
        raise ValueError('Annual risk-free rate must be finite and greater than -1.')
    wealth = (1 + returns).cumprod()
    volatility = float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS))
    daily_rf = (1 + annual_risk_free) ** (1 / TRADING_DAYS) - 1
    sharpe = float((returns.mean() - daily_rf) * TRADING_DAYS / volatility) if volatility > 1e-12 else np.nan
    peaks = wealth.cummax().clip(lower=1.0)
    return {'Total return': float(wealth.iloc[-1] - 1),
            'Annualized return': float(wealth.iloc[-1] ** (TRADING_DAYS / len(returns)) - 1),
            'Annualized volatility': volatility, 'Sharpe ratio': sharpe,
            'Max drawdown': float((wealth / peaks - 1).min())}


def analyze(prices, assets, weights, benchmark='SPY', initial_value=10000., annual_risk_free=0.):
    validate_prices(prices)
    if not assets or len(set(assets)) != len(assets):
        raise ValueError('Select unique portfolio assets.')
    if set(assets + [benchmark]) - set(prices.columns):
        raise ValueError('Dataset is missing portfolio or benchmark columns.')
    if not np.isfinite(initial_value) or initial_value <= 0:
        raise ValueError('Initial value must be positive and finite.')
    allocations = validate_weights(assets, weights)
    daily = prices.pct_change(fill_method=None).iloc[1:]
    portfolio = daily[assets].mul(allocations).sum(axis=1)
    comparison = pd.DataFrame({'Portfolio': portfolio, 'Benchmark': daily[benchmark]})
    wealth = (1 + comparison).cumprod()
    baseline = pd.DataFrame(1., index=prices.index[:1], columns=comparison.columns)
    wealth = pd.concat([baseline, wealth])
    wealth.index.name = 'Date'
    return {
        'metrics': pd.DataFrame({c: summarize(comparison[c], annual_risk_free) for c in comparison}).T,
        'asset_metrics': pd.DataFrame({a: summarize(daily[a], annual_risk_free) for a in assets}).T,
        'daily_returns': comparison, 'portfolio_value': wealth * initial_value,
        'drawdown': wealth / wealth.cummax() - 1, 'correlation': daily[assets].corr(),
    }
