"""Smoke tests for the FastAPI endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_price_endpoint_verified_response() -> None:
    payload = {
        "spot": 100.0,
        "strike": 100.0,
        "time_to_expiry_years": 0.5,
        "volatility": 0.20,
        "risk_free_rate": 0.05,
        "dividend_yield": 0.0,
        "option_type": "call",
        "style": "european",
    }
    r = client.post("/calc/options/price", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["verification_status"] == "verified"
    assert data["primary_result"]["price"] > 0
    assert len(data["calculator_results"]) == 2
    assert all(c["succeeded"] for c in data["calculator_results"])


def test_price_endpoint_validation_error() -> None:
    payload = {
        "spot": -100.0,
        "strike": 100.0,
        "time_to_expiry_years": 0.5,
        "volatility": 0.2,
        "risk_free_rate": 0.05,
        "option_type": "call",
    }
    r = client.post("/calc/options/price", json=payload)
    assert r.status_code == 422
