"""Ticker info + options-chain provider.

Separate from `MarketDataProvider` (which serves historical returns) because
the consumer set is different — only Phase 7's trader-pivot routes use these
methods, and existing tests already structurally implement
`MarketDataProvider`. A separate protocol keeps those tests untouched.

Both implementations here are yfinance-backed. Realised volatility is
computed from the trailing 30 trading-day return series since yfinance's
options chain IV is sparse and noisy for illiquid strikes.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Protocol

import numpy as np

from src.data_providers.market_data import MarketDataError

LOG = logging.getLogger(__name__)


class TickerSummary:
    """Lightweight DTO; the FastAPI route serialises this via TickerSummaryModel."""

    def __init__(
        self,
        *,
        ticker: str,
        spot: float,
        spot_currency: str,
        realised_vol_annualised: float,
        sector: str | None,
        industry: str | None,
        market_cap: float | None,
        short_name: str | None,
        long_name: str | None,
    ) -> None:
        self.ticker = ticker
        self.spot = spot
        self.spot_currency = spot_currency
        self.realised_vol_annualised = realised_vol_annualised
        self.sector = sector
        self.industry = industry
        self.market_cap = market_cap
        self.short_name = short_name
        self.long_name = long_name


class OptionChainEntry:
    def __init__(
        self,
        *,
        contract_symbol: str,
        option_type: str,  # "call" | "put"
        strike: float,
        last_price: float | None,
        bid: float | None,
        ask: float | None,
        volume: int | None,
        open_interest: int | None,
        implied_volatility: float | None,
        in_the_money: bool,
    ) -> None:
        self.contract_symbol = contract_symbol
        self.option_type = option_type
        self.strike = strike
        self.last_price = last_price
        self.bid = bid
        self.ask = ask
        self.volume = volume
        self.open_interest = open_interest
        self.implied_volatility = implied_volatility
        self.in_the_money = in_the_money


class OptionsChain:
    def __init__(
        self,
        *,
        ticker: str,
        expiry: str,
        spot: float,
        entries: list[OptionChainEntry],
    ) -> None:
        self.ticker = ticker
        self.expiry = expiry
        self.spot = spot
        self.entries = entries


class TickerInfoProvider(Protocol):
    def fetch_ticker_summary(self, ticker: str) -> TickerSummary: ...

    def list_expiries(self, ticker: str) -> list[str]:
        """Available option expiries as ISO date strings, ascending."""
        ...

    def fetch_options_chain(self, ticker: str, expiry: str) -> OptionsChain: ...


class YFinanceTickerInfoProvider:
    def fetch_ticker_summary(self, ticker: str) -> TickerSummary:
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover — covered by static test
            raise MarketDataError("yfinance is not installed") from exc

        symbol = ticker.upper().strip()
        if not symbol:
            raise MarketDataError("ticker must not be empty")

        try:
            t = yf.Ticker(symbol)
            # `.info` triggers a network call; some tickers raise here.
            info = t.info or {}
            history = t.history(period="60d", interval="1d", auto_adjust=True)
        except Exception as exc:
            raise MarketDataError(
                f"yfinance summary fetch failed for {symbol}: {exc}"
            ) from exc

        if history is None or history.empty:
            raise MarketDataError(f"No price history returned for {symbol!r}")

        close = history["Close"].dropna()
        if close.size < 2:
            raise MarketDataError(
                f"Only {close.size} closes returned for {symbol}; need >=2"
            )

        spot = float(close.iloc[-1])
        if not math.isfinite(spot) or spot <= 0:
            raise MarketDataError(f"Invalid spot price {spot!r} for {symbol}")

        # Realised vol from the trailing window. Use up to 30 returns; daily-to-
        # annualised conversion = std * sqrt(252).
        prices = np.asarray(close, dtype=np.float64)
        returns = np.diff(prices) / prices[:-1]
        returns = returns[np.isfinite(returns)]
        window = returns[-30:] if returns.size >= 5 else returns
        realised_vol = (
            float(np.std(window, ddof=1) * math.sqrt(252)) if window.size >= 2 else 0.0
        )

        return TickerSummary(
            ticker=symbol,
            spot=spot,
            spot_currency=str(info.get("currency") or "USD"),
            realised_vol_annualised=realised_vol,
            sector=_str_or_none(info.get("sector")),
            industry=_str_or_none(info.get("industry")),
            market_cap=_float_or_none(info.get("marketCap")),
            short_name=_str_or_none(info.get("shortName")),
            long_name=_str_or_none(info.get("longName")),
        )

    def list_expiries(self, ticker: str) -> list[str]:
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover
            raise MarketDataError("yfinance is not installed") from exc

        symbol = ticker.upper().strip()
        try:
            expiries = list(yf.Ticker(symbol).options or [])
        except Exception as exc:
            raise MarketDataError(
                f"yfinance options-expiry fetch failed for {symbol}: {exc}"
            ) from exc

        # yfinance returns ISO YYYY-MM-DD strings already; filter to future
        # dates and sort ascending.
        today = datetime.utcnow().date()
        out: list[str] = []
        for e in expiries:
            try:
                d = datetime.strptime(e, "%Y-%m-%d").date()
                if d >= today:
                    out.append(e)
            except ValueError:
                continue
        return out

    def fetch_options_chain(self, ticker: str, expiry: str) -> OptionsChain:
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover
            raise MarketDataError("yfinance is not installed") from exc

        symbol = ticker.upper().strip()
        # Validate expiry shape eagerly so the network call doesn't waste time.
        try:
            datetime.strptime(expiry, "%Y-%m-%d")
        except ValueError as exc:
            raise MarketDataError(
                f"expiry must be ISO YYYY-MM-DD, got {expiry!r}"
            ) from exc

        try:
            t = yf.Ticker(symbol)
            chain = t.option_chain(expiry)
            history = t.history(period="5d", interval="1d", auto_adjust=True)
        except Exception as exc:
            raise MarketDataError(
                f"yfinance option_chain fetch failed for {symbol} @ {expiry}: {exc}"
            ) from exc

        if history is None or history.empty:
            raise MarketDataError(f"No spot price available for {symbol!r}")
        spot = float(history["Close"].dropna().iloc[-1])

        entries: list[OptionChainEntry] = []
        for row in chain.calls.itertuples(index=False):
            entries.append(_row_to_entry(row, option_type="call"))
        for row in chain.puts.itertuples(index=False):
            entries.append(_row_to_entry(row, option_type="put"))

        # Sort by strike then by type so the UI can render a tidy stacked view.
        entries.sort(key=lambda e: (e.strike, e.option_type))

        return OptionsChain(
            ticker=symbol,
            expiry=expiry,
            spot=spot,
            entries=entries,
        )


def _row_to_entry(row: object, *, option_type: str) -> OptionChainEntry:
    """Map a pandas itertuples row from a yfinance option_chain DataFrame.

    yfinance's frame is a fixed schema (contractSymbol, strike, lastPrice,
    bid, ask, volume, openInterest, impliedVolatility, inTheMoney) and
    every row carries those columns — `getattr` with a default tolerates
    unexpected upstream changes.
    """
    strike_raw = getattr(row, "strike", 0.0)
    strike = float(strike_raw) if isinstance(strike_raw, (int, float)) else 0.0
    return OptionChainEntry(
        contract_symbol=str(getattr(row, "contractSymbol", "")),
        option_type=option_type,
        strike=strike,
        last_price=_float_or_none(getattr(row, "lastPrice", None)),
        bid=_float_or_none(getattr(row, "bid", None)),
        ask=_float_or_none(getattr(row, "ask", None)),
        volume=_int_or_none(getattr(row, "volume", None)),
        open_interest=_int_or_none(getattr(row, "openInterest", None)),
        implied_volatility=_float_or_none(
            getattr(row, "impliedVolatility", None)
        ),
        in_the_money=bool(getattr(row, "inTheMoney", False)),
    )


def _str_or_none(v: object) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _float_or_none(v: object) -> float | None:
    if v is None:
        return None
    if not isinstance(v, (int, float, str)):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def _int_or_none(v: object) -> int | None:
    f = _float_or_none(v)
    if f is None:
        return None
    return int(f)


_default = YFinanceTickerInfoProvider()


def default_ticker_info_provider() -> TickerInfoProvider:
    return _default
