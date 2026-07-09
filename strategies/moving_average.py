"""
strategies/moving_average.py

Moving Average Crossover strategy.

Logic (unchanged from the original notebook): go long when the short-term
moving average is above the long-term moving average (a trend-following
signal), stay flat otherwise.

The signal is shifted forward one trading day before being applied to
returns — a crossover confirmed at today's close can only be acted on
starting the next trading day. Skipping this shift is the most common
lookahead-bias bug in beginner backtests, so it's kept explicit here.
"""

import pandas as pd


STRATEGY_NAME = "Moving Average Crossover"

STRATEGY_LIMITATIONS = (
    "Moving average crossovers lag price (they confirm a trend only after it "
    "has partly happened), tend to whipsaw in sideways/choppy markets "
    "generating repeated small losses, and use no volatility or volume "
    "filter. This implementation also ignores transaction costs, bid-ask "
    "spread, and slippage."
)


def generate_signals(df: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> pd.DataFrame:
    """Generate long/flat signals from a moving average crossover.

    Parameters
    ----------
    df : DataFrame with at least a 'Close' column.
    short_window, long_window : rolling window lengths in trading days.

    Returns
    -------
    DataFrame with added 'sma_short', 'sma_long', and 'signal' (0/1) columns,
    with the initial warm-up period (where the long SMA isn't defined yet)
    dropped.
    """
    if short_window >= long_window:
        raise ValueError(
            f"short_window ({short_window}) must be less than "
            f"long_window ({long_window})."
        )

    out = df.copy()
    out["sma_short"] = out["Close"].rolling(short_window).mean()
    out["sma_long"] = out["Close"].rolling(long_window).mean()

    out["signal"] = 0
    out.loc[out["sma_short"] > out["sma_long"], "signal"] = 1

    # Avoid lookahead bias: trade on the day after the crossover is confirmed.
    out["signal"] = out["signal"].shift(1).fillna(0)

    return out.dropna(subset=["sma_long"])
