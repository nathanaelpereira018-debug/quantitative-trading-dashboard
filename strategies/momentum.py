"""
strategies/momentum.py

Time-Series (Absolute) Momentum strategy.

Logic: look back `lookback_window` trading days. If the asset's total
return over that window is positive (it has been trending up), go long for
the next day; otherwise stay flat. This is the single-asset analogue of the
classic momentum effect — trade in the direction of recent price behavior,
rather than ranking multiple assets against each other (which requires a
cross-sectional universe, out of scope for a single-ticker dashboard).

Reference: Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum" —
documents that assets' own recent returns predict their near-term future
returns across many asset classes.
"""

import pandas as pd


STRATEGY_NAME = "Momentum Strategy"

STRATEGY_LIMITATIONS = (
    "Momentum strategies suffer sharp, sudden drawdowns during momentum "
    "crashes (fast reversals after a sustained trend, e.g. early 2009), are "
    "sensitive to the chosen lookback window, and can generate excessive "
    "turnover if the window is short. As implemented here, this is a single-"
    "asset time-series signal, not a cross-sectional ranking across many "
    "stocks, so it captures trend persistence but not relative strength "
    "versus peers."
)


def generate_signals(df: pd.DataFrame, lookback_window: int = 90, **_ignored) -> pd.DataFrame:
    """Generate long/flat signals from trailing-window momentum.

    Parameters
    ----------
    df : DataFrame with at least a 'Close' column.
    lookback_window : number of trading days used to measure momentum.

    Returns
    -------
    DataFrame with an added 'momentum_return' (trailing window return) and
    'signal' (0/1) column, warm-up period dropped.
    """
    if lookback_window < 5:
        raise ValueError("lookback_window must be at least 5 trading days.")

    out = df.copy()
    out["momentum_return"] = out["Close"].pct_change(periods=lookback_window)

    out["signal"] = 0
    out.loc[out["momentum_return"] > 0, "signal"] = 1

    # Avoid lookahead bias: act the day after the momentum reading is known.
    out["signal"] = out["signal"].shift(1).fillna(0)

    # Keep column names consistent with the moving-average strategy so the
    # backtest engine and charts don't need to special-case this strategy.
    out["sma_short"] = out["Close"].rolling(max(lookback_window // 3, 2)).mean()
    out["sma_long"] = out["Close"].rolling(lookback_window).mean()

    return out.dropna(subset=["momentum_return"])
