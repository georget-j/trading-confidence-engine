"""Tests for /api/hedge/suggest."""

from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.hedge import _market_data_provider, _ticker_info_provider
from src.data_providers.market_data import MarketDataError
from src.data_providers.ticker_info import OptionsChain, TickerSummary


class _FakeTickerInfo:
    """Heavy Tech holdings; everything else is an unknown sector by default."""

    def __init__(self) -> None:
        self.summaries: dict[str, TickerSummary] = {
            "AAPL": _summary("AAPL", spot=170.0, sector="Technology"),
            "MSFT": _summary("MSFT", spot=420.0, sector="Technology"),
            "NVDA": _summary("NVDA", spot=900.0, sector="Technology"),
            "JPM": _summary("JPM", spot=180.0, sector="Financials"),
        }

    def fetch_ticker_summary(self, ticker: str) -> TickerSummary:
        key = ticker.upper().strip()
        if key not in self.summaries:
            raise MarketDataError(f"no fake summary for {key}")
        return self.summaries[key]

    def list_expiries(self, ticker: str) -> list[str]:  # pragma: no cover
        return []

    def fetch_options_chain(self, ticker: str, expiry: str) -> OptionsChain:  # pragma: no cover
        raise NotImplementedError


class _FakeMarketData:
    """Builds synthetic returns whose sign vs the Tech basket is hard-coded
    so we can assert specific tickers rank highest in the negative direction.

    - AAPL / MSFT / NVDA: ``base`` (the Tech basket signal)
    - SQQQ / SH / TLT: ``-base`` (strongly negatively correlated)
    - DBC / GLD: independent noise (~0 correlation)
    """

    def __init__(self) -> None:
        self.negative_set = {"SQQQ", "SH", "TLT"}
        self.tech_set = {"AAPL", "MSFT", "NVDA"}

    def fetch_daily_returns(self, ticker, lookback_days):  # pragma: no cover
        raise NotImplementedError

    def fetch_aligned_returns(self, tickers, lookback_days):
        rng = np.random.default_rng(99)
        n = lookback_days
        base = rng.normal(0, 0.012, size=n)
        out: list[list[float]] = []
        for t in tickers:
            if t in self.tech_set:
                series = base + rng.normal(0, 0.003, size=n)
            elif t in self.negative_set:
                series = -base + rng.normal(0, 0.003, size=n)
            else:
                series = rng.normal(0, 0.012, size=n)
            out.append(series.tolist())
        # transpose to (T, N)
        matrix = list(map(list, zip(*out, strict=True)))
        return list(tickers), matrix

    def fetch_price_history(self, ticker, lookback_days):  # pragma: no cover
        return []


def _summary(ticker: str, *, spot: float, sector: str) -> TickerSummary:
    return TickerSummary(
        ticker=ticker,
        spot=spot,
        spot_currency="USD",
        realised_vol_annualised=0.20,
        sector=sector,
        industry=None,
        market_cap=None,
        short_name=ticker,
        long_name=ticker,
    )


def _client() -> TestClient:
    app.dependency_overrides[_ticker_info_provider] = lambda: _FakeTickerInfo()
    app.dependency_overrides[_market_data_provider] = lambda: _FakeMarketData()
    return TestClient(app)


def _teardown() -> None:
    app.dependency_overrides.pop(_ticker_info_provider, None)
    app.dependency_overrides.pop(_market_data_provider, None)


def test_hedge_suggest_ranks_negatively_correlated_tickers_first() -> None:
    client = _client()
    try:
        r = client.post(
            "/api/hedge/suggest",
            json={
                "holdings": [
                    {"ticker": "AAPL", "shares": 10},
                    {"ticker": "MSFT", "shares": 10},
                    {"ticker": "NVDA", "shares": 10},
                    {"ticker": "JPM", "shares": 1},
                ],
                "lookback_days": 300,
                "top_k": 5,
                "min_sector_weight": 0.25,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["universe_size"] > 0
        tech = next(
            (s for s in body["suggestions"] if s["sector"] == "Technology"),
            None,
        )
        assert tech is not None, "Technology sector should clear threshold"
        top_tickers = [c["ticker"] for c in tech["candidates"]]
        # SQQQ / SH / TLT must be in the top 5 by construction.
        assert "SQQQ" in top_tickers
        assert "SH" in top_tickers
        assert "TLT" in top_tickers
        # Correlations on those rows must be strongly negative.
        for c in tech["candidates"]:
            if c["ticker"] in {"SQQQ", "SH", "TLT"}:
                assert c["correlation"] < -0.5
    finally:
        _teardown()


def test_hedge_suggest_returns_no_suggestions_when_diversified() -> None:
    """Equal weights across sectors → no single sector clears the threshold."""
    client = _client()
    try:
        r = client.post(
            "/api/hedge/suggest",
            json={
                "holdings": [
                    {"ticker": "AAPL", "shares": 1},
                    {"ticker": "JPM", "shares": 1},
                ],
                "lookback_days": 252,
                "min_sector_weight": 0.6,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["suggestions"] == []
        assert any("threshold" in lim for lim in body["limitations"])
    finally:
        _teardown()


def test_hedge_suggest_includes_disclaimer() -> None:
    client = _client()
    try:
        r = client.post(
            "/api/hedge/suggest",
            json={
                "holdings": [
                    {"ticker": "AAPL", "shares": 10},
                    {"ticker": "MSFT", "shares": 10},
                ],
                "lookback_days": 252,
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "not investment advice" in body["disclaimer"].lower()
    finally:
        _teardown()
