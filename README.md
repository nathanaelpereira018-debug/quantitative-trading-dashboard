# Quantitative Trading Strategy Research Platform

An interactive Streamlit dashboard for backtesting systematic equity trading
strategies, evaluating them with institutional-grade risk metrics, and
comparing them against buy & hold and a market benchmark — built on top of
the moving-average crossover research originally developed and validated
in `notebooks/01_sma_crossover_backtest.ipynb`.

> Research and educational tool. Not investment advice. Backtested
> performance does not account for transaction costs, slippage, or taxes,
> and is not indicative of future results.

---

## Project Overview

This platform lets a user:

1. Enter any equity ticker and a benchmark (default: SPY)
2. Choose one of three systematic trading strategies
3. Run a backtest against a configurable starting capital
4. View institutional risk & performance metrics (Sharpe, Sortino, max
   drawdown, alpha, beta) side-by-side against Buy & Hold and the benchmark
5. Inspect the full trade history, equity curve, drawdown profile, monthly
   return heatmap, and risk-return positioning — all interactively, with
   zoom and hover detail

It started as a single notebook implementing one strategy (Moving Average
Crossover) and was refactored into a modular package so the same
strategy/backtest/risk logic can run from a notebook, a script, or this
dashboard without duplication.

---

## System Architecture

```
Quantitative-Trading-Platform/
│
├── app.py                        # Streamlit dashboard — UI only, no financial logic
│
├── data/
│   └── market_data.py            # yfinance download, MultiIndex handling, cleaning, retries
│
├── strategies/
│   ├── moving_average.py         # Moving Average Crossover (trend-following)
│   ├── momentum.py                # Time-series momentum
│   ├── mean_reversion.py          # Rolling z-score mean reversion
│   └── __init__.py                # Strategy name -> module registry
│
├── backtesting/
│   └── engine.py                  # Applies signals to returns; builds equity curve & trade log
│
├── analytics/
│   └── risk_metrics.py            # Sharpe, Sortino, drawdown, beta, alpha
│
├── visualization/
│   └── charts.py                  # All Plotly chart builders (reusable go.Figure functions)
│
├── notebooks/
│   └── 01_sma_crossover_backtest.ipynb   # Original research notebook (source of truth)
│
├── requirements.txt
└── README.md
```

**Design principle:** `app.py` contains zero pricing, strategy, or metric
logic — it only wires modules together and renders results. Every module
below it works standalone (importable from a notebook or a test script),
which is what makes the dashboard testable without a browser.

### What each file does

- **`data/market_data.py`** — Downloads OHLCV data via `yfinance`, handles
  the MultiIndex column inconsistency across yfinance versions, retries
  transient network/rate-limit failures, forward-fills isolated gaps, and
  raises a clear `DataFetchError` (not a raw traceback) when data genuinely
  can't be retrieved.

- **`strategies/moving_average.py`** — Go long when the short-term moving
  average crosses above the long-term moving average; flat otherwise.
  Classic trend-following.

- **`strategies/momentum.py`** — Go long when the asset's own trailing
  return over a lookback window is positive (time-series momentum); flat
  otherwise.

- **`strategies/mean_reversion.py`** — Go long when price falls a
  configurable number of standard deviations below its rolling average
  (a z-score); exit once price reverts back to the mean.

- **`backtesting/engine.py`** — Strategy-agnostic: takes any DataFrame with
  a `signal` (0/1) and `daily_return` column, and produces an equity curve,
  buy & hold comparison, and a trade-by-trade log (entry/exit price, P&L,
  holding period).

- **`analytics/risk_metrics.py`** — Total/annualized return, annualized
  volatility, Sharpe ratio, Sortino ratio, maximum drawdown, beta, and alpha
  vs. a benchmark.

- **`visualization/charts.py`** — Equity curve, drawdown, monthly return
  heatmap, trade signal markers, risk-return scatter, and allocation pie —
  each a function returning a `plotly.graph_objects.Figure`, usable in
  Streamlit (`st.plotly_chart`) or a notebook (`fig.show()`).

---

## Trading Strategies

| Strategy | Logic | Key Limitation |
|---|---|---|
| Moving Average Crossover | Long when short SMA > long SMA | Lags price; whipsaws in choppy markets |
| Momentum | Long when trailing-window return > 0 | Sharp reversals ("momentum crashes") |
| Mean Reversion | Long when price z-score ≤ −threshold, exit at z ≥ 0 | Fails in sustained downtrends ("catching a falling knife") |

All three strategies shift their signal forward one trading day before
applying it to returns, to avoid lookahead bias — a decision confirmed at
today's close can only be acted on starting tomorrow.

---

## Backtesting Methodology

- Starting capital is configurable (default $10,000)
- Each strategy outputs a binary long/flat signal per day
- Portfolio return each day = signal × that day's asset return (no
  leverage, no shorting)
- A trade is logged each time the signal transitions 0→1 (entry) and back
  to 0 (exit), with entry/exit price, P&L %, P&L $, and holding period
- Buy & Hold and the benchmark (e.g. SPY) are computed the same way with an
  always-on signal, for a fair comparison

**Not modeled:** transaction costs, bid-ask spread, slippage, taxes,
margin/leverage, or partial position sizing. Real-world returns would be
lower than what's shown.

---

## Risk Metrics Explained

- **Total Return** — cumulative % gain/loss over the full backtest window
- **Annualized Return** — total return rescaled to a 1-year equivalent
- **Sharpe Ratio** — (annualized return − risk-free rate) / annualized
  volatility — return earned per unit of total risk taken
- **Sortino Ratio** — same idea as Sharpe, but only penalizes downside
  volatility, since investors don't mind upside swings
- **Maximum Drawdown** — the worst peak-to-trough decline in portfolio
  value over the window
- **Beta** — sensitivity to the benchmark's moves (market risk exposure)
- **Alpha** — CAPM-style excess return after adjusting for beta exposure —
  the return the strategy added beyond what market exposure alone predicts

---

## Installation

```bash
git clone https://github.com/<your-username>/Quantitative-Trading-Platform.git
cd Quantitative-Trading-Platform
pip install -r requirements.txt
```

## Running the Dashboard

```bash
streamlit run app.py
```

Open the local URL Streamlit prints (typically `http://localhost:8501`),
configure a ticker/date range/strategy in the sidebar, and click
**RUN BACKTEST**.

## Running the Original Research Notebook

`notebooks/01_sma_crossover_backtest.ipynb` is the original single-strategy
research notebook this project was refactored from. Open it in Google
Colab or Jupyter and run top to bottom.

---

## Error Handling

The dashboard is built to never hard-crash on:

- Invalid or misspelled ticker symbols
- Empty date ranges / date ranges with too few trading days
- Yahoo Finance rate-limiting or transient network failures (auto-retried,
  then surfaced as a clear message)
- A strategy configuration with no valid parameter combination (e.g. short
  MA window ≥ long MA window)
- A backtest window with zero completed trades

All of these paths were tested with simulated failure conditions in
addition to the normal success path.

---

## Limitations

- Single-asset, long-only strategies — no shorting, no diversification
  across multiple tickers
- No transaction costs, slippage, or taxes modeled
- One historical window on one ticker is not statistically sufficient to
  conclude a strategy "works" — proper validation requires out-of-sample
  testing across multiple tickers and market regimes
- Momentum and Mean Reversion here are single-asset (time-series) signals,
  not cross-sectional rankings across a universe of stocks

## Future Improvements

- Multi-asset portfolio backtesting with position sizing across a universe
- Transaction cost and slippage modeling
- Walk-forward / out-of-sample parameter validation to guard against
  overfitting
- Additional strategies (pairs trading, factor-based models)
- Persisted backtest history so multiple runs can be compared side-by-side
