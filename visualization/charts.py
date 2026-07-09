"""
visualization/charts.py

Plotly chart builders, refactored from the notebook's inline chart cells
into reusable functions. Each function returns a `go.Figure` so the same
chart code works in a notebook (`fig.show()`) or in Streamlit
(`st.plotly_chart(fig)`) without duplication.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def equity_curve_chart(backtest_df: pd.DataFrame, ticker: str, starting_capital: float,
                        benchmark_equity: pd.Series = None, benchmark_label: str = "Benchmark") -> go.Figure:
    """Strategy vs. Buy & Hold (and optionally a benchmark) portfolio value over time."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=backtest_df.index, y=backtest_df["equity_curve"],
        name=f"{ticker} Strategy", line=dict(color="#2E86AB", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=backtest_df.index, y=backtest_df["buy_hold_equity"],
        name=f"{ticker} Buy & Hold", line=dict(color="#A23B72", width=2, dash="dash")
    ))
    if benchmark_equity is not None:
        fig.add_trace(go.Scatter(
            x=benchmark_equity.index, y=benchmark_equity.values,
            name=benchmark_label, line=dict(color="#F18F01", width=2, dash="dot")
        ))
    fig.update_layout(
        title=f"Portfolio Equity Curve — {ticker} (Starting Capital ${starting_capital:,.0f})",
        xaxis_title="Date", yaxis_title="Portfolio Value ($)",
        template="plotly_white", hovermode="x unified",
    )
    return fig


def drawdown_chart(drawdown_series: pd.Series, ticker: str) -> go.Figure:
    """Peak-to-trough drawdown over time."""
    fig = go.Figure()
    if len(drawdown_series) > 0:
        fig.add_trace(go.Scatter(
            x=drawdown_series.index, y=drawdown_series.values * 100,
            fill="tozeroy", name="Drawdown", line=dict(color="#C73E1D"),
        ))
    fig.update_layout(
        title=f"Strategy Drawdown — {ticker}",
        xaxis_title="Date", yaxis_title="Drawdown (%)", template="plotly_white",
    )
    return fig


def monthly_returns_heatmap(strategy_returns: pd.Series, ticker: str) -> go.Figure:
    """Monthly return heatmap (year x month grid)."""
    monthly_returns = (1 + strategy_returns).resample("ME").prod() - 1
    heatmap_df = monthly_returns.to_frame("return")
    heatmap_df["year"] = heatmap_df.index.year
    heatmap_df["month"] = heatmap_df.index.strftime("%b")
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    pivot = heatmap_df.pivot(index="year", columns="month", values="return").reindex(columns=month_order)

    z = pivot.values * 100
    fig = go.Figure(data=go.Heatmap(
        z=z, x=pivot.columns, y=pivot.index.astype(str),
        colorscale="RdYlGn", zmid=0,
        text=[[f"{v:.1f}%" if not np.isnan(v) else "" for v in row] for row in z],
        texttemplate="%{text}", colorbar=dict(title="Return %"),
    ))
    fig.update_layout(
        title=f"Monthly Returns Heatmap — {ticker} Strategy",
        xaxis_title="Month", yaxis_title="Year", template="plotly_white",
    )
    return fig


def trade_signal_chart(backtest_df: pd.DataFrame, trade_log: pd.DataFrame, ticker: str,
                        short_label: str = "Short MA", long_label: str = "Long MA") -> go.Figure:
    """Price chart with moving-average style overlays and entry/exit trade markers."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=backtest_df.index, y=backtest_df["Close"],
        name=f"{ticker} Close", line=dict(color="#444444", width=1),
    ))
    if "sma_short" in backtest_df.columns:
        fig.add_trace(go.Scatter(
            x=backtest_df.index, y=backtest_df["sma_short"],
            name=short_label, line=dict(color="#2E86AB", width=1, dash="dot"),
        ))
    if "sma_long" in backtest_df.columns:
        fig.add_trace(go.Scatter(
            x=backtest_df.index, y=backtest_df["sma_long"],
            name=long_label, line=dict(color="#F18F01", width=1, dash="dot"),
        ))
    if trade_log is not None and not trade_log.empty:
        fig.add_trace(go.Scatter(
            x=trade_log["entry_date"], y=trade_log["entry_price"],
            mode="markers", name="Buy", marker=dict(symbol="triangle-up", size=11, color="green"),
        ))
        fig.add_trace(go.Scatter(
            x=trade_log["exit_date"], y=trade_log["exit_price"],
            mode="markers", name="Sell", marker=dict(symbol="triangle-down", size=11, color="red"),
        ))
    fig.update_layout(
        title=f"{ticker} Price with Trading Signals",
        xaxis_title="Date", yaxis_title="Price ($)", template="plotly_white", hovermode="x unified",
    )
    return fig


def risk_return_comparison_chart(comparison_df: pd.DataFrame) -> go.Figure:
    """Risk-return scatter: x=volatility, y=return, marker size ~ |Sharpe|.

    comparison_df must have columns: 'Strategy', 'Annualized Return',
    'Annualized Volatility', 'Sharpe Ratio'.
    """
    palette = ["#2E86AB", "#A23B72", "#F18F01", "#3B7A57", "#8E44AD"]
    colors = [palette[i % len(palette)] for i in range(len(comparison_df))]

    fig = go.Figure(data=go.Scatter(
        x=comparison_df["Annualized Volatility"] * 100,
        y=comparison_df["Annualized Return"] * 100,
        mode="markers+text", text=comparison_df["Strategy"], textposition="top center",
        marker=dict(
            size=comparison_df["Sharpe Ratio"].fillna(0).abs() * 15 + 10,
            color=colors,
        ),
    ))
    fig.update_layout(
        title="Risk-Return Comparison (marker size ~ |Sharpe Ratio|)",
        xaxis_title="Annualized Volatility (%)", yaxis_title="Annualized Return (%)",
        template="plotly_white",
    )
    return fig


def allocation_chart(backtest_df: pd.DataFrame, ticker: str) -> go.Figure:
    """Time-in-market (invested) vs. cash allocation, as a share of trading days."""
    days_long = int(backtest_df["signal"].sum())
    days_flat = int((backtest_df["signal"] == 0).sum())

    fig = go.Figure(data=go.Pie(
        labels=[f"Invested in {ticker}", "In Cash (flat)"],
        values=[days_long, days_flat],
        marker=dict(colors=["#2E86AB", "#CCCCCC"]), hole=0.4,
    ))
    fig.update_layout(title="Strategy Time Allocation: Invested vs. Cash", template="plotly_white")
    return fig


def volatility_chart(strategy_returns: pd.Series, window: int = 30, periods_per_year: int = 252) -> go.Figure:
    """Rolling annualized volatility over time."""
    rolling_vol = strategy_returns.rolling(window).std() * np.sqrt(periods_per_year) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rolling_vol.index, y=rolling_vol.values,
        name=f"{window}-Day Rolling Volatility", line=dict(color="#8E44AD", width=2),
    ))
    fig.update_layout(
        title=f"Rolling {window}-Day Annualized Volatility",
        xaxis_title="Date", yaxis_title="Volatility (%)", template="plotly_white",
    )
    return fig
