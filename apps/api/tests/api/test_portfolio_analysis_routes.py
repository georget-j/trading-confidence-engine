"""Tests for /api/portfolio/import and /api/portfolio/analyse."""

from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.portfolio_analysis import (
    _market_data_provider,
    _ticker_info_provider,
)
from src.data_providers.ticker_info import (
    OptionsChain,
    TickerSummary,
)


class _FakeTickerInfo:
    """Deterministic TickerInfoProvider for the analyse endpoint."""

    def __init__(self) -> None:
        self.summaries: dict[str, TickerSummary] = {
            "AAPL": _summary("AAPL", spot=175.0, sector="Technology"),
            "MSFT": _summary("MSFT", spot=420.0, sector="Technology"),
            "JPM": _summary("JPM", spot=200.0, sector="Financials"),
            "XOM": _summary("XOM", spot=110.0, sector="Energy"),
        }

    def fetch_ticker_summary(self, ticker: str) -> TickerSummary:
        key = ticker.upper().strip()
        if key not in self.summaries:
            from src.data_providers.market_data import MarketDataError

            raise MarketDataError(f"no fake summary for {key}")
        return self.summaries[key]

    def list_expiries(self, ticker: str) -> list[str]:  # pragma: no cover
        return []

    def fetch_options_chain(self, ticker: str, expiry: str) -> OptionsChain:  # pragma: no cover
        raise NotImplementedError


class _FakeMarketData:
    """Returns a fixed (T, N) matrix where columns correspond to tickers
    in the requested order. Synthetic correlated returns so corr matrix
    has non-trivial off-diagonal entries."""

    def fetch_daily_returns(self, ticker, lookback_days):  # pragma: no cover
        raise NotImplementedError

    def fetch_aligned_returns(self, tickers, lookback_days):
        rng = np.random.default_rng(42)
        # Common factor + idiosyncratic noise per ticker → realistic corr.
        common = rng.normal(0, 0.01, size=lookback_days)
        out = []
        for _ in tickers:
            idio = rng.normal(0, 0.005, size=lookback_days)
            out.append((common + idio).tolist())
        # fetch_aligned_returns returns (T, N) shape — transpose.
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


# --- /import ----------------------------------------------------------------


def test_import_from_paste_round_trips_holdings() -> None:
    client = _client()
    try:
        r = client.post(
            "/api/portfolio/import",
            json={
                "source": "paste",
                "holdings": [
                    {"ticker": "AAPL", "shares": 10, "cost_basis": 175.0, "currency": "USD"},
                    {"ticker": "MSFT", "shares": 5, "cost_basis": 420.0, "currency": "USD"},
                ],
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source"] == "paste"
        assert len(body["holdings"]) == 2
        assert body["rows_seen"] == 2
    finally:
        _teardown()


def test_import_from_trading212_csv() -> None:
    client = _client()
    try:
        csv_text = (
            "Instrument,Ticker,Quantity,Average price,Currency\n"
            "Apple,AAPL,10,175.32,USD\n"
            "Tesla,TSLA,5,250.10,USD\n"
        )
        r = client.post(
            "/api/portfolio/import",
            json={"source": "trading_212", "csv_text": csv_text},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        tickers = sorted(h["ticker"] for h in body["holdings"])
        assert tickers == ["AAPL", "TSLA"]
    finally:
        _teardown()


def test_import_422_on_invalid_csv() -> None:
    client = _client()
    try:
        r = client.post(
            "/api/portfolio/import",
            json={"source": "trading_212", "csv_text": ""},
        )
        assert r.status_code == 422
    finally:
        _teardown()


def test_import_rejects_both_csv_and_holdings() -> None:
    client = _client()
    try:
        r = client.post(
            "/api/portfolio/import",
            json={
                "csv_text": "a,b\n1,2\n",
                "holdings": [{"ticker": "AAPL", "shares": 1}],
            },
        )
        assert r.status_code == 422
    finally:
        _teardown()


# --- /analyse ---------------------------------------------------------------


def test_analyse_computes_weights_and_sectors() -> None:
    client = _client()
    try:
        r = client.post(
            "/api/portfolio/analyse",
            json={
                "lookback_days": 252,
                "holdings": [
                    {"ticker": "AAPL", "shares": 10},  # 1750
                    {"ticker": "MSFT", "shares": 5},   # 2100
                    {"ticker": "JPM", "shares": 20},   # 4000
                    {"ticker": "XOM", "shares": 10},   # 1100
                ],
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_value_usd"] == 1750 + 2100 + 4000 + 1100
        # Sector exposure must include all three sectors.
        sectors = {s["sector"] for s in body["sector_exposure"]}
        assert sectors == {"Technology", "Financials", "Energy"}
        # Sum of weights ≈ 1.
        total_w = sum(h["weight"] for h in body["holdings"])
        assert abs(total_w - 1.0) < 1e-9
        # Correlation matrix present with the right shape.
        corr = body["correlation_matrix"]
        assert corr is not None
        assert len(corr["matrix"]) == 4
        assert all(len(row) == 4 for row in corr["matrix"])
        # Portfolio volatility present + positive (synthetic data has it).
        assert body["portfolio_volatility_annualised"] is not None
        assert body["portfolio_volatility_annualised"] > 0
    finally:
        _teardown()


def test_analyse_surfaces_concentration_alerts() -> None:
    client = _client()
    try:
        r = client.post(
            "/api/portfolio/analyse",
            json={
                "lookback_days": 252,
                "holdings": [
                    {"ticker": "AAPL", "shares": 100},  # 17,500 — dominates
                    {"ticker": "JPM", "shares": 1},     # 200
                ],
            },
        )
        assert r.status_code == 200
        body = r.json()
        alert_kinds = {a["kind"] for a in body["concentration_alerts"]}
        # AAPL is >25% AND the Technology sector is >45% → both alerts fire.
        assert "single_position" in alert_kinds
        assert "single_sector" in alert_kinds
    finally:
        _teardown()


def test_analyse_handles_unknown_ticker_gracefully() -> None:
    client = _client()
    try:
        r = client.post(
            "/api/portfolio/analyse",
            json={
                "lookback_days": 252,
                "holdings": [
                    {"ticker": "AAPL", "shares": 10},
                    {"ticker": "ZZZZ", "shares": 5},  # not in fake provider
                ],
            },
        )
        # AAPL still prices → not a 502. The ZZZZ failure surfaces as a
        # limitation string.
        assert r.status_code == 200
        body = r.json()
        assert any("ZZZZ" in lim for lim in body["limitations"])
    finally:
        _teardown()
