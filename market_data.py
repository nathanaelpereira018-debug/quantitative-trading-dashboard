"""
data/market_data.py

Historical price data acquisition and cleaning.

This is a direct refactor of the notebook's data pipeline
(`download_price_data` / `_flatten_columns`) — the download, retry,
validation, and cleaning logic is unchanged. It's moved here so both the
Streamlit app and any future notebooks/scripts can import a single,
tested implementation instead of copy-pasting it.
"""

import time
import pandas as pd
import yfinance as yf


class DataFetchError(Exception):
    """Raised when historical price data cannot be retrieved or is unusable.

    The Streamlit app catches this specifically so it can show a clean
    message in the UI instead of a raw traceback.
    """
    pass


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance's column index to simple field names.

    Different yfinance versions return single-ticker downloads with either
    plain columns (Open, High, Low, Close, Volume) or MultiIndex columns —
    and the MultiIndex level order (field-then-ticker vs ticker-then-field)
    has also changed across versions. This checks which level actually
    contains recognizable field names instead of assuming a fixed order.
    """
    if not isinstance(df.columns, pd.MultiIndex):
        return df

    field_names = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
    level0 = set(df.columns.get_level_values(0))
    if field_names & level0:
        df.columns = df.columns.get_level_values(0)
    else:
        df.columns = df.columns.get_level_values(1)
    return df


def download_price_data(
    ticker: str,
    start,
    end,
    min_required_days: int = 60,
    max_retries: int = 3,
    retry_delay: int = 2,
) -> pd.DataFrame:
    """Download and clean historical price data for a single ticker.

    Retries transient failures (rate limiting, dropped connections) and
    raises a clear, actionable `DataFetchError` if data genuinely can't be
    retrieved, instead of letting a raw requests/pandas traceback bubble up
    and crash the caller (notebook cell or Streamlit app).

    Parameters
    ----------
    ticker : str
        Ticker symbol, e.g. "AAPL".
    start, end : str or datetime-like
        Date range to download.
    min_required_days : int
        Minimum number of clean trading days required for the result to be
        considered usable (protects downstream strategy/backtest code from
        being handed a too-short series).
    max_retries : int
        Number of download attempts before giving up.
    retry_delay : int
        Seconds to wait between retries.
    """
    if not ticker or not str(ticker).strip():
        raise DataFetchError("No ticker symbol provided.")

    last_error = None
    df = None

    for attempt in range(1, max_retries + 1):
        try:
            df = yf.download(
                ticker, start=start, end=end,
                auto_adjust=True, progress=False, threads=False,
            )
            if df is not None and not df.empty:
                break
            last_error = "Yahoo Finance returned an empty dataset."
        except Exception as e:  # noqa: BLE001 - intentionally broad: network/API errors vary
            last_error = e

        if attempt < max_retries:
            time.sleep(retry_delay)

    if df is None or df.empty:
        raise DataFetchError(
            f"Could not download data for '{ticker}' after {max_retries} attempts.\n"
            f"Last error: {last_error}\n\n"
            "Common causes: misspelled/delisted ticker, a date range with no "
            "trading days, or Yahoo Finance temporarily rate-limiting requests."
        )

    df = _flatten_columns(df)

    if "Close" not in df.columns:
        raise DataFetchError(
            f"Downloaded data for '{ticker}' is missing a 'Close' column "
            f"(columns found: {list(df.columns)}). Yahoo Finance's response "
            "format may have changed — try upgrading yfinance."
        )

    missing_before = int(df["Close"].isna().sum())
    df["Close"] = df["Close"].ffill()
    df = df.dropna(subset=["Close"])
    missing_after = int(df["Close"].isna().sum())

    df["daily_return"] = df["Close"].pct_change()
    df = df.dropna(subset=["daily_return"])

    if len(df) < min_required_days:
        raise DataFetchError(
            f"Only {len(df)} usable trading days for '{ticker}' after cleaning — "
            f"too few for a reliable backtest (need at least {min_required_days}). "
            "Widen the date range."
        )

    df.attrs["ticker"] = ticker
    df.attrs["missing_filled"] = missing_before
    df.attrs["missing_remaining"] = missing_after
    return df


def get_ticker_and_benchmark_data(ticker: str, benchmark: str, start, end):
    """Convenience wrapper: download both the traded ticker and benchmark.

    Returns (price_data, benchmark_data). Raises DataFetchError from
    whichever download fails first — the caller decides how to present that.
    """
    price_data = download_price_data(ticker, start, end)
    benchmark_data = download_price_data(benchmark, start, end)
    return price_data, benchmark_data
