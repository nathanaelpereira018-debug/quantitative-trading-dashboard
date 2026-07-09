"""
app.py

Quantitative Trading Strategy Research Platform — Streamlit Dashboard

Run with:
    streamlit run app.py

This app wires together the data/strategies/backtesting/analytics/
visualization modules into an interactive research dashboard. It contains
no strategy, backtest, or risk-metric logic of its own — all of that lives
in the modules under data/, strategies/, backtesting/, analytics/, and
visualization/, so the same tested code path is used whether you're
running a notebook cell or clicking "Run Backtest" here.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from data.market_data import get_ticker_and_benchmark_data, DataFetchError
from strategies import STRATEGY_NAMES, get_strategy_module
from backtesting.engine import run_backtest, summarize_backtest
from analytics.risk_metrics import compute_risk_metrics
from visualization import charts


# ============================================================
# PAGE CONFIG & STYLE
# ============================================================
st.set_page_config(
    page_title="Quant Research Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .stApp { background-color: #0E1117; }
    section[data-testid="stSidebar"] { background-color: #161A25; }
    div[data-testid="stMetric"] {
        background-color: #161A25;
        border: 1px solid #2A2F3D;
        border-radius: 6px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricLabel"] { color: #8B93A7; font-size: 0.8rem; }
    h1, h2, h3 { font-family: "IBM Plex Mono", "Courier New", monospace; }
    .section-header {
        border-bottom: 2px solid #2E86AB;
        padding-bottom: 6px;
        margin-top: 28px;
        margin-bottom: 14px;
        font-size: 1.15rem;
        font-weight: 600;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        color: #D8DEE9;
    }
    .disclaimer {
        font-size: 0.78rem;
        color: #6B7280;
        border-left: 3px solid #2E86AB;
        padding-left: 10px;
        margin-top: 10px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def section_header(text: str):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


# ============================================================
# SIDEBAR — INPUTS
# ============================================================
st.sidebar.title("📊 Quant Research Terminal")
st.sidebar.caption("Strategy backtesting & risk analytics")

st.sidebar.markdown("### Configuration")

ticker_input = st.sidebar.text_input("Ticker Symbol", value="AAPL", help="e.g. AAPL, MSFT, TSLA").strip().upper()
benchmark_input = st.sidebar.text_input("Benchmark Symbol", value="SPY", help="Used for Beta/Alpha and comparison").strip().upper()

default_end = date.today() - timedelta(days=1)
default_start = default_end.replace(year=default_end.year - 5)

col_start, col_end = st.sidebar.columns(2)
start_date = col_start.date_input("Start Date", value=default_start, max_value=default_end)
end_date = col_end.date_input("End Date", value=default_end, max_value=date.today())

initial_investment = st.sidebar.number_input(
    "Initial Investment ($)", min_value=100.0, max_value=100_000_000.0,
    value=10_000.0, step=500.0, format="%.2f",
)

strategy_name = st.sidebar.selectbox("Strategy", STRATEGY_NAMES, index=0)

st.sidebar.markdown("### Strategy Parameters")
strategy_params = {}
if strategy_name == "Moving Average Crossover":
    strategy_params["short_window"] = st.sidebar.slider("Short MA Window (days)", 5, 60, 20)
    strategy_params["long_window"] = st.sidebar.slider("Long MA Window (days)", 20, 200, 50)
elif strategy_name == "Momentum Strategy":
    strategy_params["lookback_window"] = st.sidebar.slider("Momentum Lookback (days)", 10, 250, 90)
elif strategy_name == "Mean Reversion Strategy":
    strategy_params["lookback_window"] = st.sidebar.slider("Lookback Window (days)", 5, 100, 20)
    strategy_params["entry_zscore"] = st.sidebar.slider("Entry Z-Score Threshold", 0.5, 3.0, 1.0, step=0.1)

risk_free_rate = st.sidebar.slider("Risk-Free Rate (annualized, %)", 0.0, 8.0, 2.0, step=0.25) / 100.0

run_clicked = st.sidebar.button("▶ RUN BACKTEST", use_container_width=True, type="primary")

st.sidebar.markdown(
    '<div class="disclaimer">Research & educational tool only. Historical '
    "backtests are not indicative of future performance. Not investment "
    "advice.</div>",
    unsafe_allow_html=True,
)


# ============================================================
# MAIN AREA
# ============================================================
st.title("Quantitative Trading Strategy Research Platform")
st.caption(f"{strategy_name} · {ticker_input or '—'} vs. {benchmark_input or '—'} benchmark")

if not run_clicked and "last_result" not in st.session_state:
    st.info("Configure your backtest in the sidebar, then click **RUN BACKTEST**.")
    st.stop()

# ------------------------------------------------------------------
# INPUT VALIDATION — never let a bad input reach the data/strategy layer
# ------------------------------------------------------------------
def validate_inputs():
    errors = []
    if not ticker_input:
        errors.append("Ticker symbol is required.")
    if not benchmark_input:
        errors.append("Benchmark symbol is required.")
    if start_date >= end_date:
        errors.append("Start Date must be before End Date.")
    if (end_date - start_date).days < 90:
        errors.append("Date range must span at least ~90 days for a meaningful backtest.")
    if initial_investment <= 0:
        errors.append("Initial Investment must be greater than zero.")
    if strategy_name == "Moving Average Crossover" and strategy_params["short_window"] >= strategy_params["long_window"]:
        errors.append("Short MA Window must be less than Long MA Window.")
    return errors


if run_clicked:
    validation_errors = validate_inputs()
    if validation_errors:
        for err in validation_errors:
            st.error(err)
        st.stop()

    try:
        with st.spinner(f"Downloading historical data for {ticker_input} and {benchmark_input}..."):
            price_data, benchmark_data = get_ticker_and_benchmark_data(
                ticker_input, benchmark_input, start_date, end_date
            )

        with st.spinner(f"Running {strategy_name} backtest..."):
            strategy_module = get_strategy_module(strategy_name)
            strategy_df = strategy_module.generate_signals(price_data, **strategy_params)

            if strategy_df.empty:
                st.error(
                    "No usable data remains after applying the strategy's warm-up "
                    "period. Try a longer date range or shorter lookback window."
                )
                st.stop()

            backtest_df, trade_log = run_backtest(strategy_df, initial_investment)
            summary = summarize_backtest(backtest_df, trade_log, initial_investment)

            strategy_metrics, drawdown_series = compute_risk_metrics(
                backtest_df["strategy_return"], benchmark_data["daily_return"], risk_free_rate
            )
            buyhold_metrics, _ = compute_risk_metrics(
                backtest_df["daily_return"], benchmark_data["daily_return"], risk_free_rate
            )
            benchmark_metrics, _ = compute_risk_metrics(
                benchmark_data["daily_return"], benchmark_data["daily_return"], risk_free_rate
            )

        st.session_state["last_result"] = dict(
            ticker=ticker_input, benchmark=benchmark_input, strategy_name=strategy_name,
            price_data=price_data, benchmark_data=benchmark_data, strategy_df=strategy_df,
            backtest_df=backtest_df, trade_log=trade_log, summary=summary,
            strategy_metrics=strategy_metrics, buyhold_metrics=buyhold_metrics,
            benchmark_metrics=benchmark_metrics, drawdown_series=drawdown_series,
            initial_investment=initial_investment,
        )
        st.success(f"Backtest complete — {len(price_data)} trading days analyzed.")

    except DataFetchError as e:
        st.error(f"**Data error:** {e}")
        st.stop()
    except ValueError as e:
        st.error(f"**Invalid configuration:** {e}")
        st.stop()
    except Exception as e:  # noqa: BLE001 - last-resort guard so the app never hard-crashes
        st.error(
            "**Unexpected error while running the backtest.** "
            "This has been caught so the app can keep running — "
            f"technical detail: `{type(e).__name__}: {e}`"
        )
        st.stop()

# ------------------------------------------------------------------
# RENDER — use last successful result (persists across reruns/widget changes)
# ------------------------------------------------------------------
if "last_result" not in st.session_state:
    st.stop()

r = st.session_state["last_result"]
ticker = r["ticker"]
benchmark = r["benchmark"]
backtest_df = r["backtest_df"]
trade_log = r["trade_log"]
summary = r["summary"]
strategy_metrics = r["strategy_metrics"]
buyhold_metrics = r["buyhold_metrics"]
benchmark_metrics = r["benchmark_metrics"]
drawdown_series = r["drawdown_series"]
initial_investment = r["initial_investment"]


def fmt_pct(x):
    return "N/A" if pd.isna(x) else f"{x:.2%}"


def fmt_ratio(x):
    return "N/A" if pd.isna(x) else f"{x:.3f}"


# ============================================================
# SECTION 1 — PORTFOLIO PERFORMANCE SUMMARY
# ============================================================
section_header("1 · Portfolio Performance Summary")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Starting Capital", f"${summary['starting_capital']:,.2f}")
c2.metric("Ending Portfolio Value", f"${summary['final_strategy_value']:,.2f}",
          delta=f"{(summary['final_strategy_value']/summary['starting_capital']-1):.2%}")
c3.metric("Total Return", fmt_pct(strategy_metrics["Total Return"]))
c4.metric("Annualized Return", fmt_pct(strategy_metrics["Annualized Return"]))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Sharpe Ratio", fmt_ratio(strategy_metrics["Sharpe Ratio"]))
c6.metric("Sortino Ratio", fmt_ratio(strategy_metrics["Sortino Ratio"]))
c7.metric("Maximum Drawdown", fmt_pct(strategy_metrics["Maximum Drawdown"]))
c8.metric("Alpha / Beta", f"{fmt_pct(strategy_metrics['Alpha'])} / {fmt_ratio(strategy_metrics['Beta'])}")

st.caption(
    f"Total trades: {summary['total_trades']}  ·  "
    f"Winners: {summary['winning_trades']}  ·  "
    f"Losers: {summary['losing_trades']}  ·  "
    f"Win rate: {summary['win_rate']:.1%}"
)

# ============================================================
# SECTION 2 — PORTFOLIO PERFORMANCE CHART
# ============================================================
section_header("2 · Portfolio Performance")

benchmark_equity = initial_investment * (1 + r["benchmark_data"]["daily_return"]).cumprod()
fig_equity = charts.equity_curve_chart(
    backtest_df, ticker, initial_investment,
    benchmark_equity=benchmark_equity, benchmark_label=f"{benchmark} Benchmark",
)
st.plotly_chart(fig_equity, use_container_width=True)

# ============================================================
# SECTION 3 — TRADING SIGNAL ANALYSIS
# ============================================================
section_header("3 · Trading Signal Analysis")

short_label = "Short MA" if r["strategy_name"] == "Moving Average Crossover" else "Short Reference"
long_label = "Long MA" if r["strategy_name"] == "Moving Average Crossover" else "Long Reference"
fig_signals = charts.trade_signal_chart(backtest_df, trade_log, ticker, short_label, long_label)
st.plotly_chart(fig_signals, use_container_width=True)

# ============================================================
# SECTION 4 — RISK ANALYTICS
# ============================================================
section_header("4 · Risk Analytics")

rc1, rc2 = st.columns(2)
with rc1:
    st.plotly_chart(charts.drawdown_chart(drawdown_series, ticker), use_container_width=True)
with rc2:
    st.plotly_chart(charts.volatility_chart(backtest_df["strategy_return"]), use_container_width=True)

st.plotly_chart(charts.monthly_returns_heatmap(backtest_df["strategy_return"], ticker), use_container_width=True)

comparison_df = pd.DataFrame({
    "Strategy": [f"{ticker} Strategy", f"{ticker} Buy & Hold", f"{benchmark} Benchmark"],
    "Annualized Return": [strategy_metrics["Annualized Return"], buyhold_metrics["Annualized Return"], benchmark_metrics["Annualized Return"]],
    "Annualized Volatility": [strategy_metrics["Annualized Volatility"], buyhold_metrics["Annualized Volatility"], benchmark_metrics["Annualized Volatility"]],
    "Sharpe Ratio": [strategy_metrics["Sharpe Ratio"], buyhold_metrics["Sharpe Ratio"], benchmark_metrics["Sharpe Ratio"]],
})
rc3, rc4 = st.columns(2)
with rc3:
    st.plotly_chart(charts.risk_return_comparison_chart(comparison_df), use_container_width=True)
with rc4:
    st.plotly_chart(charts.allocation_chart(backtest_df, ticker), use_container_width=True)

with st.expander("Full metrics comparison table"):
    metrics_table = pd.DataFrame({
        f"{ticker} — Strategy": strategy_metrics,
        f"{ticker} — Buy & Hold": buyhold_metrics,
        f"{benchmark} — Benchmark": benchmark_metrics,
    })
    st.dataframe(metrics_table.style.format("{:.4f}"), use_container_width=True)

# ============================================================
# SECTION 5 — TRADE HISTORY
# ============================================================
section_header("5 · Trade History")

if trade_log.empty:
    st.info("No completed trades in this window — the strategy never generated a long entry/exit pair.")
else:
    display_log = trade_log.copy()
    display_log = display_log.rename(columns={
        "entry_date": "Entry Date", "exit_date": "Exit Date", "action": "Action",
        "entry_price": "Entry Price", "exit_price": "Exit Price",
        "portfolio_value": "Portfolio Value", "pnl_pct": "P/L %",
        "pnl_dollars": "P/L ($)", "holding_days": "Holding Days",
    })
    display_log["P/L %"] = display_log["P/L %"].map(lambda x: f"{x:.2%}")
    display_log["Entry Price"] = display_log["Entry Price"].map(lambda x: f"${x:,.2f}")
    display_log["Exit Price"] = display_log["Exit Price"].map(lambda x: f"${x:,.2f}")
    display_log["Portfolio Value"] = display_log["Portfolio Value"].map(lambda x: f"${x:,.2f}")
    display_log["P/L ($)"] = display_log["P/L ($)"].map(lambda x: f"${x:,.2f}")

    st.dataframe(
        display_log[["Entry Date", "Exit Date", "Action", "Entry Price", "Exit Price",
                      "Portfolio Value", "P/L %", "P/L ($)", "Holding Days"]],
        use_container_width=True, hide_index=True,
    )

    csv_bytes = trade_log.to_csv(index=False).encode("utf-8")
    st.download_button("Download Trade Log (CSV)", csv_bytes, file_name=f"{ticker}_trade_log.csv", mime="text/csv")

st.markdown("---")
st.caption(
    "This platform is a research and educational tool. Backtested results "
    "do not account for transaction costs, slippage, or taxes, and past "
    "performance is not indicative of future results. Not investment advice."
)
