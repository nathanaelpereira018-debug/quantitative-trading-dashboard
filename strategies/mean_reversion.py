"""
strategies/mean_reversion.py

Mean Reversion strategy (rolling z-score).

Logic: compute how many standard deviations the current price is away from
its own trailing rolling average (a z-score). When price has fallen
significantly below its recent average (z-score below -entry_threshold),
treat that as oversold and go long, on the assumption it will revert back
toward the mean. Exit (go flat) once price has reverted back above the
mean (z-score >= 0).
"""

import pandas as pd


STRATEGY_NAME = "Mean Reversion Strategy"

STRATEGY_LIMITATIONS = (
    "Mean reversion assumes price will revert to its recent average — this "
    "fails badly during genuine regime changes or sustained downtrends, "
    "where 'buying the dip' repeatedly buys into a falling knife. The "
    "z-score threshold and lookback window are both parameters that can be "
    "overfit to a specific historical window if tuned too aggressively."
)


def generate_signals(
    df: pd.DataFrame,
    lookback_window: int = 20,
    entry_zscore: float = 1.0,
    **_ignored,
) -> pd.DataFrame:
    """Generate long/flat signals from a rolling price z-score.

    Parameters
    ----------
    df : DataFrame with at least a 'Close' column.
    lookback_window : rolling window (days) for the mean/std reference.
    entry_zscore : how many standard deviations below the mean triggers
        a long entry (e.g. 1.0 = enter when 1 std dev below average).

    Returns
    -------
    DataFrame with added 'rolling_mean', 'rolling_std', 'zscore', and
    'signal' (0/1) columns, warm-up period dropped.
    """
    if lookback_window < 5:
        raise ValueError("lookback_window must be at least 5 trading days.")
    if entry_zscore <= 0:
        raise ValueError("entry_zscore must be positive.")

    out = df.copy()
    out["rolling_mean"] = out["Close"].rolling(lookback_window).mean()
    out["rolling_std"] = out["Close"].rolling(lookback_window).std()
    out["zscore"] = (out["Close"] - out["rolling_mean"]) / out["rolling_std"]

    out["signal"] = 0
    is_long = False
    signals = []
    for z in out["zscore"]:
        if pd.isna(z):
            signals.append(0)
            continue
        if not is_long and z <= -entry_zscore:
            is_long = True
        elif is_long and z >= 0:
            is_long = False
        signals.append(1 if is_long else 0)
    out["signal"] = signals

    # Avoid lookahead bias: act the day after the z-score is known.
    out["signal"] = pd.Series(out["signal"], index=out.index).shift(1).fillna(0)

    # Keep column names consistent with the other strategies so the
    # backtest engine and charts don't need to special-case this strategy.
    out["sma_short"] = out["rolling_mean"]
    out["sma_long"] = out["Close"].rolling(lookback_window * 2).mean()

    return out.dropna(subset=["rolling_mean", "rolling_std"])
