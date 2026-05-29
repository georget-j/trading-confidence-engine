"""Tests for /api/ticker/* endpoints.

Uses an in-memory fake provider so the suite never touches yfinance. The
real yfinance integration is exercised manually in dev — testing it would
make the suite flaky and slow.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.ticker import _provider
from src.data_providers.market_data import MarketDataError
from src.data_providers.ticker_info import (
    OptionChainEntry,
    OptionsChain,
    TickerSummary,
)


class _FakeProvider:
    """In-memory TickerInfoProvider for deterministic tests."""

    def __init__(self) -> None:
        self.summary_calls: list[str] = []
        self.expiries_calls: list[str] = []
        self.chain_calls: list[tuple[str, str]] = []
        self.raise_on_summary = False

    def fetch_ticker_summary(self, ticker: str) -> TickerSummary:
        self.summary_calls.append(ticker)
        if self.raise_on_summary:
            raise MarketDataError("fake provider error")
        return TickerSummary(
            ticker=ticker.upper(),
            spot=450.12,
            spot_currency="USD",
            realised_vol_annualised=0.18,
            sector="Technology",
            industry="Semiconductors",
            market_cap=1_000_000_000.0,
            short_name="Tesla, Inc.",
            long_name="Tesla, Inc.",
        )

    def list_expiries(self, ticker: str) -> list[str]:
        self.expiries_calls.append(ticker)
        return ["2026-06-19", "2026-07-17", "2026-12-18"]

    def fetch_options_chain(self, ticker: str, expiry: str) -> OptionsChain:
        self.chain_calls.append((ticker, expiry))
        entries = [
            OptionChainEntry(
                contract_symbol=f"{ticker}{expiry}C00440000",
                option_type="call",
                strike=440.0,
                last_price=14.10,
                bid=14.00,
                ask=14.20,
                volume=1200,
                open_interest=8500,
                implied_volatility=0.21,
                in_the_money=True,
            ),
            OptionChainEntry(
                contract_symbol=f"{ticker}{expiry}P00440000",
                option_type="put",
                strike=440.0,
                last_price=3.85,
                bid=3.80,
                ask=3.90,
                volume=900,
                open_interest=4200,
                implied_volatility=0.22,
                in_the_money=False,
            ),
        ]
        return OptionsChain(
            ticker=ticker.upper(),
            expiry=expiry,
            spot=450.12,
            entries=entries,
        )


def _client_with(fake: _FakeProvider) -> TestClient:
    app.dependency_overrides[_provider] = lambda: fake
    return TestClient(app)


def _teardown() -> None:
    app.dependency_overrides.pop(_provider, None)


def test_summary_returns_normalised_payload() -> None:
    fake = _FakeProvider()
    client = _client_with(fake)
    try:
        r = client.get("/api/ticker/tsla/summary")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ticker"] == "TSLA"
        assert body["spot"] == 450.12
        assert body["sector"] == "Technology"
        assert 0.0 <= body["realised_vol_annualised"] <= 5.0
        assert fake.summary_calls == ["tsla"]
    finally:
        _teardown()


def test_summary_502_on_provider_error() -> None:
    fake = _FakeProvider()
    fake.raise_on_summary = True
    client = _client_with(fake)
    try:
        r = client.get("/api/ticker/badx/summary")
        assert r.status_code == 502
        assert "fake provider error" in r.json()["detail"]
    finally:
        _teardown()


def test_expiries_returns_list() -> None:
    fake = _FakeProvider()
    client = _client_with(fake)
    try:
        r = client.get("/api/ticker/tsla/expiries")
        assert r.status_code == 200
        body = r.json()
        assert body["ticker"] == "TSLA"
        assert body["expiries"] == ["2026-06-19", "2026-07-17", "2026-12-18"]
    finally:
        _teardown()


def test_chain_returns_call_and_put_rows() -> None:
    fake = _FakeProvider()
    client = _client_with(fake)
    try:
        r = client.get("/api/ticker/tsla/chain?expiry=2026-06-19")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ticker"] == "TSLA"
        assert body["expiry"] == "2026-06-19"
        assert len(body["entries"]) == 2
        types = {e["option_type"] for e in body["entries"]}
        assert types == {"call", "put"}
        assert fake.chain_calls == [("tsla", "2026-06-19")]
    finally:
        _teardown()


def test_chain_requires_expiry_query_param() -> None:
    fake = _FakeProvider()
    client = _client_with(fake)
    try:
        r = client.get("/api/ticker/tsla/chain")
        assert r.status_code == 422
    finally:
        _teardown()


def test_empty_ticker_rejected() -> None:
    fake = _FakeProvider()
    client = _client_with(fake)
    try:
        # Use "%20" so the path segment isn't dropped by FastAPI's router.
        r = client.get("/api/ticker/%20/summary")
        assert r.status_code == 422
    finally:
        _teardown()
