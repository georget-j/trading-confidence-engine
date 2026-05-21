"""Tests for /api/prices/history (cached price-history endpoint)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.data_providers.market_data import MarketDataError

client = TestClient(app)


def _fake_prices(days: int) -> list[tuple[str, float]]:
    return [(f"2024-01-{i + 1:02d}", 100.0 + i * 0.5) for i in range(days)]


def test_history_returns_points(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.api.routes.prices._cache", {}, raising=False
    )
    monkeypatch.setattr(
        "src.api.routes.prices.default_provider",
        lambda: type(
            "P",
            (),
            {"fetch_price_history": lambda self, t, d: _fake_prices(min(d, 30))},
        )(),
    )
    r = client.get("/api/prices/history", params={"ticker": "SPY", "days": 30})
    assert r.status_code == 200
    data = r.json()
    assert data["ticker"] == "SPY"
    assert len(data["points"]) == 30
    assert data["cached"] is False
    # First and last prices are sensible.
    assert data["points"][0]["close"] == 100.0
    assert data["points"][-1]["close"] == pytest.approx(100.0 + 29 * 0.5)


def test_history_cache_hit_on_second_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """First call populates the cache; second within TTL returns cached=True
    without invoking the provider again."""
    monkeypatch.setattr("src.api.routes.prices._cache", {}, raising=False)

    call_count = {"n": 0}

    class CountingProvider:
        def fetch_price_history(self, ticker: str, days: int):
            call_count["n"] += 1
            return _fake_prices(days)

    monkeypatch.setattr(
        "src.api.routes.prices.default_provider", lambda: CountingProvider()
    )
    r1 = client.get("/api/prices/history", params={"ticker": "SPY", "days": 30})
    r2 = client.get("/api/prices/history", params={"ticker": "SPY", "days": 30})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["cached"] is False
    assert r2.json()["cached"] is True
    assert call_count["n"] == 1


def test_history_502_on_data_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.api.routes.prices._cache", {}, raising=False)

    class Broken:
        def fetch_price_history(self, ticker: str, days: int):
            raise MarketDataError("nope")

    monkeypatch.setattr(
        "src.api.routes.prices.default_provider", lambda: Broken()
    )
    r = client.get(
        "/api/prices/history", params={"ticker": "NOPE", "days": 30}
    )
    assert r.status_code == 502
