"""
analytics/risk_metrics.py

Institutional risk & performance metrics.

This is the notebook's `compute_risk_metrics` function, unchanged in logic:

- Total Return       — cumulative % gain/loss over the full period
- Annualized Return  — total return rescaled to a 1-year equivalent (CAGR-style)
- Annualized Volatility — std dev of daily returns, annualized (the standard risk measure)
- Sharpe Ratio       — (annualized return - risk-free rate) / annualized volatility
- Sortino Ratio      — same idea as Sharpe, but only penalizes downside volatility
- Maximum Drawdown   — worst peak-to-trough decline in cumulative return
- Beta               — sensitivity to the benchmark's moves (market risk exposure)
- Alpha              — CAPM-style excess return after adjusting for beta exposure
"""

import numpy as np
import pandas as pd


def compute_risk_metrics(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
):
    """Compute institutional risk & performance metrics for a return series.

    Returns
    -------
    (metrics, drawdown_series) : (dict, Series)
        metrics has keys: Total Return, Annualized Return,
        Annualized Volatility, Sharpe Ratio, Sortino Ratio, Maximum
        Drawdown, Beta, Alpha.
        drawdown_series is the full peak-to-trough drawdown series, used
        for the drawdown chart.
    """
    strategy_returns = strategy_returns.dropna()
    benchmark_returns = benchmark_returns.reindex(strategy_returns.index).dropna()
    strategy_returns = strategy_returns.reindex(benchmark_returns.index).dropna()

    if len(strategy_returns) < 2:
        # Not enough overlapping data to compute meaningful statistics —
        # return NaNs rather than raising, so the UI can show "N/A" instead
        # of crashing on a too-short backtest window.
        nan_metrics = {
            k: np.nan for k in [
                "Total Return", "Annualized Return", "Annualized Volatility",
                "Sharpe Ratio", "Sortino Ratio", "Maximum Drawdown",
                "Beta", "Alpha",
            ]
        }
        return nan_metrics, pd.Series(dtype=float)

    n_days = len(strategy_returns)
    total_return = (1 + strategy_returns).prod() - 1
    annualized_return = (1 + total_return) ** (periods_per_year / n_days) - 1
    annualized_vol = strategy_returns.std() * np.sqrt(periods_per_year)

    sharpe = (
        (annualized_return - risk_free_rate) / annualized_vol
        if annualized_vol != 0 else np.nan
    )

    downside_returns = strategy_returns[strategy_returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 1 else np.nan
    sortino = (
        (annualized_return - risk_free_rate) / downside_vol
        if downside_vol and not np.isnan(downside_vol) and downside_vol != 0 else np.nan
    )

    equity = (1 + strategy_returns).cumprod()
    running_max = equity.cummax()
    drawdown_series = (equity - running_max) / running_max
    max_drawdown = drawdown_series.min()

    if benchmark_returns.std() != 0 and len(benchmark_returns) > 1:
        covariance = np.cov(strategy_returns, benchmark_returns)
        beta = covariance[0, 1] / covariance[1, 1] if covariance[1, 1] != 0 else np.nan
    else:
        beta = np.nan

    bench_total_return = (1 + benchmark_returns).prod() - 1
    bench_annualized_return = (1 + bench_total_return) ** (periods_per_year / len(benchmark_returns)) - 1
    alpha = (
        annualized_return - (risk_free_rate + beta * (bench_annualized_return - risk_free_rate))
        if not np.isnan(beta) else np.nan
    )

    metrics = {
        "Total Return": total_return,
        "Annualized Return": annualized_return,
        "Annualized Volatility": annualized_vol,
        "Sharpe Ratio": sharpe,
        "Sortino Ratio": sortino,
        "Maximum Drawdown": max_drawdown,
        "Beta": beta,
        "Alpha": alpha,
    }
    return metrics, drawdown_series
