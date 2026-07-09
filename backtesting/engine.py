"""
backtesting/engine.py

Backtesting engine.

This is the notebook's `run_backtest` function, unchanged in logic:
applies a strategy's 0/1 signal to daily returns to build an equity curve
against a given starting capital, and reconstructs a trade log from every
long-entry/long-exit pair for trade-level statistics (win rate, holding
period, P&L per trade).

Works with any strategy module that outputs a 'signal' (0/1) column and a
'daily_return' column — the engine itself has no strategy-specific logic,
which is what lets Moving Average, Momentum, and Mean Reversion all share
this same code path.
"""

import pandas as pd


def run_backtest(df: pd.DataFrame, starting_capital: float):
    """Simulate portfolio value under a strategy's signal vs. buy & hold.

    Parameters
    ----------
    df : DataFrame with 'signal', 'Close', and 'daily_return' columns
        (as produced by any strategies/*.py `generate_signals` function).
    starting_capital : starting portfolio value in dollars.

    Returns
    -------
    (backtest_df, trade_log) : (DataFrame, DataFrame)
        backtest_df adds 'strategy_return', 'equity_curve', and
        'buy_hold_equity' columns.
        trade_log has one row per completed long trade: entry/exit date,
        entry/exit price, pnl_pct, holding_days.
    """
    bt = df.copy()
    bt["strategy_return"] = bt["signal"] * bt["daily_return"]

    bt["equity_curve"] = starting_capital * (1 + bt["strategy_return"]).cumprod()
    bt["buy_hold_equity"] = starting_capital * (1 + bt["daily_return"]).cumprod()

    # --- trade log: pair each entry (0->1) with its exit (1->0) ---
    signal_change = bt["signal"].diff().fillna(0)
    entries = bt.index[signal_change == 1]
    exits = bt.index[signal_change == -1]

    trade_records = []
    for entry_date in entries:
        later_exits = exits[exits > entry_date]
        exit_date = later_exits[0] if len(later_exits) > 0 else bt.index[-1]
        entry_price = bt.loc[entry_date, "Close"]
        exit_price = bt.loc[exit_date, "Close"]

        entry_equity = bt.loc[entry_date, "equity_curve"]
        exit_equity = bt.loc[exit_date, "equity_curve"]

        trade_records.append({
            "entry_date": entry_date,
            "exit_date": exit_date,
            "action": "LONG",
            "entry_price": round(float(entry_price), 2),
            "exit_price": round(float(exit_price), 2),
            "portfolio_value": round(float(exit_equity), 2),
            "pnl_pct": float(exit_price / entry_price - 1),
            "pnl_dollars": round(float(exit_equity - entry_equity), 2),
            "holding_days": (exit_date - entry_date).days,
        })

    trade_log = pd.DataFrame(trade_records)
    return bt, trade_log


def summarize_backtest(backtest_df: pd.DataFrame, trade_log: pd.DataFrame, starting_capital: float) -> dict:
    """Compute the headline backtest summary numbers used in the UI/reports."""
    n_trades = len(trade_log)
    winners = int((trade_log["pnl_pct"] > 0).sum()) if n_trades else 0
    losers = int((trade_log["pnl_pct"] <= 0).sum()) if n_trades else 0
    win_rate = winners / n_trades if n_trades else 0.0

    final_strategy_value = float(backtest_df["equity_curve"].iloc[-1])
    final_buyhold_value = float(backtest_df["buy_hold_equity"].iloc[-1])

    return {
        "starting_capital": starting_capital,
        "final_strategy_value": final_strategy_value,
        "final_buyhold_value": final_buyhold_value,
        "total_trades": n_trades,
        "winning_trades": winners,
        "losing_trades": losers,
        "win_rate": win_rate,
    }
