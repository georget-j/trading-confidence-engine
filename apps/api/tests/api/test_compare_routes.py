"""Tests for /api/compare/{ticker}/peers."""

from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.compare import (
    _market_data_provider,
    _ticker_info_provider,
)
from src.data_providers.market_data import MarketDataError
from src.data_providers.ticker_info import OptionsChain, TickerSummary


class _FakeTickerInfo:
    def __init__(self) -> None:
        # NVDA is huge; AMD / AVGO / MU are progressively smaller "cheaper"
        # peers; JPM is a wildcard (different sector).
        self.summaries: dict[str, TickerSummary] = {
            "NVDA": _summary("NVDA", spot=900.0, sector="Technology", cap=2_000_000_000_000.0, industry="Semiconductors"),
            "AMD": _summary("AMD", spot=160.0, sector="Technology", cap=250_000_000_000.0, industry="Semiconductors"),
            "AVGO": _summary("AVGO", spot=1300.0, sector="Technology", cap=600_000_000_000.0, industry="Semiconductors"),
            "MU": _summary("MU", spot=120.0, sector="Technology", cap=130_000_000_000.0, industry="Semiconductors"),
            "TSM": _summary("TSM", spot=150.0, sector="Technology", cap=900_000_000_000.0, industry="Semiconductors"),
            "AAPL": _summary("AAPL", spot=180.0, sector="Technology", cap=3_000_000_000_000.0, industry="Hardware"),
            "MSFT": _summary("MSFT", spot=420.0, sector="Technology", cap=3_100_000_000_000.0, industry="Software"),
            "JPM": _summary("JPM", spot=200.0, sector="Financials", cap=550_000_000_000.0, industry="Banking"),
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
    """Same-sector tickers move together; cross-sector moves independently."""

    def fetch_daily_returns(self, ticker, lookback_days):  # pragma: no cover
        raise NotImplementedError

    def fetch_aligned_returns(self, tickers, lookback_days):
        rng = np.random.default_rng(7)
        tech_factor = rng.normal(0, 0.015, size=lookback_days)
        out: list[list[float]] = []
        for t in tickers:
            if t in {"NVDA", "AMD", "AVGO", "MU", "TSM", "AAPL", "MSFT"}:
                series = tech_factor + rng.normal(0, 0.004, size=lookback_days)
            else:
                series = rng.normal(0, 0.01, size=lookback_days)
            out.append(series.tolist())
        matrix = list(map(list, zip(*out, strict=True)))
        return list(tickers), matrix

    def fetch_price_history(self, ticker, lookback_days):  # pragma: no cover
        return []


def _summary(
    ticker: str, *, spot: float, sector: str, cap: float, industry: str
) -> TickerSummary:
    return TickerSummary(
        ticker=ticker,
        spot=spot,
        spot_currency="USD",
        realised_vol_annualised=0.30,
        sector=sector,
        industry=industry,
        market_cap=cap,
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


def test_peers_returns_same_sector_high_correlation_tickers() -> None:
    client = _client()
    try:
        r = client.get("/api/compare/NVDA/peers?top_k=10")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["reference_ticker"] == "NVDA"
        assert body["reference_sector"] == "Technology"
        peers = [p["ticker"] for p in body["peers"]]
        # All highly-correlated Tech tickers should show up; JPM should not.
        for expected in ["AMD", "AVGO", "MU", "TSM"]:
            assert expected in peers
        assert "JPM" not in peers
    finally:
        _teardown()


def test_peers_cheaper_filter_excludes_bigger_caps() -> None:
    client = _client()
    try:
        r = client.get("/api/compare/NVDA/peers?cheaper_than=true&top_k=5")
        assert r.status_code == 200
        body = r.json()
        for p in body["peers"]:
            assert p["is_cheaper"] is True
            # NVDA is 2T; cheaper-only must exclude AAPL/MSFT (3T+) and TSM (900B).
            assert p["ticker"] not in {"AAPL", "MSFT"}
    finally:
        _teardown()


def test_peers_502_when_reference_ticker_unknown() -> None:
    client = _client()
    try:
        r = client.get("/api/compare/ZZZZ/peers")
        assert r.status_code == 502
    finally:
        _teardown()
