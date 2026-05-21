"""Market-data provider abstraction.

Defines a `MarketDataProvider` protocol with a single implementation today
(`YFinanceProvider`). Tests pass a fake provider so they never hit the network.

When a paid provider (Polygon, Databento) is added later it implements the
same protocol and the caller stays unchanged.
"""

from __future__ import annotations

import logging
from typing import Protocol

import numpy as np

LOG = logging.getLogger(__name__)


class MarketDataError(RuntimeError):
    """Raised when a market-data provider cannot satisfy a request."""


class MarketDataProvider(Protocol):
    def fetch_daily_returns(
        self, ticker: str, lookback_days: int
    ) -> list[float]:
        """Return at least `lookback_days // 2` valid daily simple returns
        for the requested ticker. Raises MarketDataError on failure."""
        ...

    def fetch_aligned_returns(
        self, tickers: list[str], lookback_days: int
    ) -> tuple[list[str], list[list[float]]]:
        """Return (tickers_in_column_order, aligned_returns) for a portfolio.

        Aligned = same number of observations per ticker (intersection of
        trading-day calendars). Used by the portfolio optimizer.
        """
        ...


class YFinanceProvider:
    """yfinance-backed provider. Free, no API key required."""

    def fetch_daily_returns(
        self, ticker: str, lookback_days: int
    ) -> list[float]:
        # Lazy import so a missing yfinance install doesn't break startup
        # for users who only ever use the structured /calc endpoints.
        try:
            import yfinance as yf
        except ImportError as exc:
            raise MarketDataError("yfinance is not installed") from exc

        # Pull a bit extra to account for weekends/holidays.
        period_days = int(lookback_days * 1.6) + 30
        try:
            data = yf.download(
                ticker,
                period=f"{period_days}d",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
        except Exception as exc:
            raise MarketDataError(
                f"yfinance fetch failed for {ticker}: {exc}"
            ) from exc

        if data is None or data.empty:
            raise MarketDataError(f"No data returned for ticker {ticker!r}")

        # yfinance returns a MultiIndex when threads=False sometimes; handle both.
        close = data["Close"]
        if hasattr(close, "iloc") and close.ndim > 1:
            close = close.iloc[:, 0]
        prices = np.asarray(close.dropna(), dtype=np.float64)
        if prices.size < 31:
            raise MarketDataError(
                f"Only {prices.size} prices returned for {ticker} — need >=31"
            )

        returns = np.diff(prices) / prices[:-1]
        returns = returns[np.isfinite(returns)]
        if returns.size < 30:
            raise MarketDataError(
                f"After cleaning, only {returns.size} valid returns for {ticker}"
            )
        # Trim to requested lookback if we pulled more.
        if returns.size > lookback_days:
            returns = returns[-lookback_days:]
        return [float(r) for r in returns]

    def fetch_aligned_returns(
        self, tickers: list[str], lookback_days: int
    ) -> tuple[list[str], list[list[float]]]:
        """Pull all tickers in one yfinance call and align on the date index."""
        try:
            import yfinance as yf
        except ImportError as exc:
            raise MarketDataError("yfinance is not installed") from exc

        period_days = int(lookback_days * 1.6) + 30
        try:
            data = yf.download(
                tickers,
                period=f"{period_days}d",
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
                group_by="ticker",
            )
        except Exception as exc:
            raise MarketDataError(
                f"yfinance multi-ticker fetch failed: {exc}"
            ) from exc

        if data is None or data.empty:
            raise MarketDataError(f"No data returned for tickers {tickers!r}")

        # Multi-ticker yfinance returns a MultiIndex DataFrame. Pull the Close
        # series for each ticker, then align by date index (inner join).
        import pandas as pd

        close_frame: pd.DataFrame
        if isinstance(data.columns, pd.MultiIndex):
            cols = {}
            for t in tickers:
                if (t, "Close") in data.columns:
                    cols[t] = data[(t, "Close")]
                elif t in data.columns.get_level_values(0):
                    sub = data[t]
                    if "Close" in sub.columns:
                        cols[t] = sub["Close"]
            close_frame = pd.DataFrame(cols)
        else:
            # Single-ticker fallback when len(tickers) == 1.
            close_frame = pd.DataFrame({tickers[0]: data["Close"]})

        close_frame = close_frame.dropna()
        if close_frame.shape[0] < 31:
            raise MarketDataError(
                f"After alignment only {close_frame.shape[0]} common days; need >=31"
            )

        # Ensure we have every requested ticker.
        missing = [t for t in tickers if t not in close_frame.columns]
        if missing:
            raise MarketDataError(f"No data for: {', '.join(missing)}")

        prices = close_frame[tickers].to_numpy(dtype=np.float64)
        returns = np.diff(prices, axis=0) / prices[:-1]
        # Drop any row with non-finite (rare — auto_adjust handles most cases).
        valid = np.all(np.isfinite(returns), axis=1)
        returns = returns[valid]
        if returns.shape[0] < 30:
            raise MarketDataError(
                f"After cleaning, only {returns.shape[0]} aligned valid returns"
            )
        if returns.shape[0] > lookback_days:
            returns = returns[-lookback_days:]
        # Shape (T, N) — rows are days, columns are tickers in `tickers` order.
        return list(tickers), returns.tolist()


_default = YFinanceProvider()


def default_provider() -> MarketDataProvider:
    """Process-wide default. Tests override via dependency injection."""
    return _default
