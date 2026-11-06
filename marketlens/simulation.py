"""Holdings, rebalancing, and fees for the portfolio study."""
import numpy as np
import pandas as pd

from marketlens.analytics import summarize, validate_weights
from marketlens.data import validate_prices


def _validate_inputs(prices, weights, initial_value):
    validate_prices(prices)
    if not np.isfinite(initial_value) or initial_value <= 0:
        raise ValueError('Initial value must be positive and finite.')
    return validate_weights(list(prices.columns), weights)


def _rebalance_log(records):
    columns = ['Date', 'value_before', 'purchases', 'sales', 'gross_traded', 'one_way_turnover', 'cost']
    log = pd.DataFrame.from_records(records, columns=columns).set_index('Date')
    log.index = pd.to_datetime(log.index)
    return log.astype(float)


def _holdings_after_cost(current, targets, rate):
    """Find target holdings that leave enough capital to pay the fee."""
    value_before = float(current.sum())
    if rate == 0:
        return value_before * targets, 0.0

    # Trade sizes depend on the capital left after fees. Solve for that
    # amount so holdings plus the fee equal the capital available.
    lower, upper = 0.0, value_before / targets.sum()
    before = current.to_numpy()
    allocations = targets.to_numpy()
    for _ in range(60):
        remaining = (lower + upper) / 2
        desired = remaining * allocations
        required = desired.sum() + rate * np.abs(desired - before).sum()
        if required > value_before:
            upper = remaining
        else:
            lower = remaining
    desired = ((lower + upper) / 2) * targets
    cost = float(rate * (desired - current).abs().sum())
    return desired, cost


def buy_and_hold(prices, weights, initial_value=10000.0):
    """Buy once and keep the same fractional model units throughout.

    Pass only the assets to hold, in weight order. There are no starting or
    final sale fees, as specified in the study plan.
    """
    targets = _validate_inputs(prices, weights, initial_value)

    units = (initial_value * targets / prices.iloc[0]).rename('Model units')
    holdings = prices.mul(units, axis='columns')
    value = holdings.sum(axis=1).rename('Portfolio')
    actual_weights = holdings.div(value, axis='index')
    returns = value.pct_change(fill_method=None).iloc[1:]

    return {
        'units': units,
        'holdings': holdings,
        'portfolio_value': value,
        'weights': actual_weights,
        'daily_returns': returns,
        'metrics': summarize(returns),
        'rebalance_log': _rebalance_log([]),
        'total_turnover': 0.0,
        'rebalance_count': 0,
        'total_cost': 0.0,
    }


def _rebalanced(prices, weights, initial_value, cost_bps, frequency):
    """Apply the trading schedule and record holdings, trades, and fees."""
    targets = _validate_inputs(prices, weights, initial_value)
    if not np.isfinite(cost_bps) or not 0 <= cost_bps < 10000:
        raise ValueError('Cost must be finite and between 0 (inclusive) and 10000 basis points (exclusive).')
    rate = cost_bps / 10000
    months = prices.index.to_period('M')
    units = initial_value * targets / prices.iloc[0]
    holdings = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    holdings.iloc[0] = units * prices.iloc[0]
    rebalance_dates = []
    trading_records = []

    for position in range(1, len(prices)):
        current = units * prices.iloc[position]
        has_next_observation = position < len(prices) - 1
        should_rebalance = has_next_observation and (
            frequency == 'daily' or months[position] != months[position + 1]
        )
        if should_rebalance:
            value_before = float(current.sum())
            desired, cost = _holdings_after_cost(current, targets, rate)
            trades = desired - current
            purchases = float(trades.clip(lower=0).sum())
            sales = float(-trades.clip(upper=0).sum())
            gross_traded = purchases + sales
            trading_records.append({
                'Date': prices.index[position], 'value_before': value_before,
                'purchases': purchases, 'sales': sales, 'gross_traded': gross_traded,
                'one_way_turnover': gross_traded / (2 * value_before),
                'cost': cost,
            })
            current = desired
            units = current / prices.iloc[position]
            rebalance_dates.append(prices.index[position])
        holdings.iloc[position] = current

    value = holdings.sum(axis=1).rename('Portfolio')
    returns = value.pct_change(fill_method=None).iloc[1:]
    log = _rebalance_log(trading_records)
    return {
        'holdings': holdings,
        'portfolio_value': value,
        'weights': holdings.div(value, axis='index'),
        'daily_returns': returns,
        'metrics': summarize(returns),
        'rebalance_dates': pd.DatetimeIndex(rebalance_dates, name=prices.index.name),
        'rebalance_log': log,
        'total_turnover': float(log['one_way_turnover'].sum()),
        'rebalance_count': len(log),
        'total_cost': float(log['cost'].sum()),
    }


def monthly_rebalanced(prices, weights, initial_value=10000.0, *, cost_bps=0.0):
    """Rebalance at the last shared trading observation of each month.

    Trades follow that day's return and are skipped on the final date.
    Fees apply to purchases plus sales. Output holdings are after fees.
    Starting purchases and final liquidation are excluded from costs.
    """
    return _rebalanced(prices, weights, initial_value, cost_bps, 'monthly')


def daily_rebalanced(prices, weights, initial_value=10000.0, *, cost_bps=0.0):
    """Rebalance after each day's return, except on the final date.

    Uses the same holdings and fee accounting as monthly rebalancing.
    With zero fees, returns match the dashboard's daily model.
    """
    return _rebalanced(prices, weights, initial_value, cost_bps, 'daily')
