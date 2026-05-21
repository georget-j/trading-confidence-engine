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


_default = YFinanceProvider()


def default_provider() -> MarketDataProvider:
    """Process-wide default. Tests override via dependency injection."""
    return _default
