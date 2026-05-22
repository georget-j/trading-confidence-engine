"""Tests for the per-family chat parsers (VaR, portfolio, backtest).

All LLM calls mocked — no real API hits. Mirrors the structure of test_chat.py
for the options family but covers the new endpoints added in M3.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def _fake_litellm_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "choices": [
            {"message": {"role": "assistant", "content": json.dumps(payload)}}
        ]
    }


@pytest.fixture(autouse=True)
def _force_api_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    yield


# ============================================================================
# VaR parser
# ============================================================================


def test_chat_parse_var_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(**_kw: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "ticker": "SPY",
                "lookback_days": 504,
                "portfolio_value": 50_000,
                "confidence_level": 0.99,
                "horizon_days": 1,
                "parse_confidence": 0.95,
                "parser_notes": [],
            }
        )

    monkeypatch.setattr("litellm.completion", lambda **kw: fake(**kw), raising=False)

    r = client.post(
        "/chat/parse/var",
        json={"text": "99% 1-day VaR on $50k SPY using 2 years of history"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ready_to_compute"] is True
    s = data["structured"]
    assert s["ticker"] == "SPY"
    assert s["portfolio_value"] == 50_000
    assert s["confidence_level"] == 0.99


def test_chat_parse_var_missing_ticker_returns_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake(**_kw: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "ticker": None,
                "lookback_days": None,
                "portfolio_value": None,
                "confidence_level": None,
                "horizon_days": None,
                "parse_confidence": 0.3,
                "parser_notes": ["user said 'tech stocks' — no single ticker"],
            }
        )

    monkeypatch.setattr("litellm.completion", lambda **kw: fake(**kw), raising=False)

    r = client.post("/chat/parse/var", json={"text": "VaR on tech stocks"})
    assert r.status_code == 200
    data = r.json()
    assert data["ready_to_compute"] is False
    assert data["structured"] is None


def test_chat_parse_var_503_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client.post("/chat/parse/var", json={"text": "VaR on SPY"})
    assert r.status_code == 503


# ============================================================================
# Portfolio parser
# ============================================================================


def test_chat_parse_portfolio_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(**_kw: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "tickers": ["SPY", "QQQ", "GLD", "TLT"],
                "lookback_days": 504,
                "objective": "max_sharpe",
                "risk_aversion": None,
                "max_weight": 0.35,
                "parse_confidence": 0.92,
                "parser_notes": [],
            }
        )

    monkeypatch.setattr("litellm.completion", lambda **kw: fake(**kw), raising=False)

    r = client.post(
        "/chat/parse/portfolio",
        json={
            "text": "Max-Sharpe portfolio of SPY, QQQ, GLD, TLT with 35% max per asset"
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ready_to_optimise"] is True
    s = data["structured"]
    assert s["tickers"] == ["SPY", "QQQ", "GLD", "TLT"]
    assert s["objective"] == "max_sharpe"
    assert s["max_weight"] == 0.35


def test_chat_parse_portfolio_one_ticker_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Portfolio needs >= 2 tickers — a one-ticker parse should not produce
    a structured request."""

    def fake(**_kw: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "tickers": ["SPY"],
                "lookback_days": None,
                "objective": None,
                "risk_aversion": None,
                "max_weight": None,
                "parse_confidence": 0.9,
                "parser_notes": ["only one ticker supplied"],
            }
        )

    monkeypatch.setattr("litellm.completion", lambda **kw: fake(**kw), raising=False)

    r = client.post("/chat/parse/portfolio", json={"text": "Portfolio with just SPY"})
    assert r.status_code == 200
    data = r.json()
    assert data["ready_to_optimise"] is False
    assert data["structured"] is None


# ============================================================================
# Backtest parser
# ============================================================================


def test_chat_parse_backtest_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(**_kw: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "ticker": "AAPL",
                "lookback_days": 504,
                "strategy": "momentum",
                "initial_capital": 25_000,
                "slippage_bps": 10,
                "parse_confidence": 0.93,
                "parser_notes": [],
            }
        )

    monkeypatch.setattr("litellm.completion", lambda **kw: fake(**kw), raising=False)

    r = client.post(
        "/chat/parse/backtest",
        json={
            "text": "Backtest momentum on AAPL over 2 years with $25k and 10bps slippage"
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ready_to_run"] is True
    s = data["structured"]
    assert s["ticker"] == "AAPL"
    assert s["strategy"] == "momentum"
    assert s["initial_capital"] == 25_000
    assert s["slippage_bps"] == 10


def test_chat_parse_backtest_no_ticker(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(**_kw: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "ticker": None,
                "lookback_days": None,
                "strategy": None,
                "initial_capital": None,
                "slippage_bps": None,
                "parse_confidence": 0.3,
                "parser_notes": ["no specific ticker given"],
            }
        )

    monkeypatch.setattr("litellm.completion", lambda **kw: fake(**kw), raising=False)

    r = client.post("/chat/parse/backtest", json={"text": "backtest something"})
    assert r.status_code == 200
    data = r.json()
    assert data["ready_to_run"] is False
    assert data["structured"] is None


# ============================================================================
# LLM safety — no numerical outputs accepted from the model
# ============================================================================


def test_var_schema_rejects_unknown_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """The LLM is forbidden from claiming a numerical answer; extra keys
    should fail validation, which manifests as a 503."""

    def fake(**_kw: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "ticker": "SPY",
                "lookback_days": None,
                "portfolio_value": None,
                "confidence_level": None,
                "horizon_days": None,
                "parse_confidence": 0.9,
                "parser_notes": [],
                "var_loss": 42.0,  # forbidden!
            }
        )

    monkeypatch.setattr("litellm.completion", lambda **kw: fake(**kw), raising=False)

    r = client.post("/chat/parse/var", json={"text": "VaR on SPY"})
    assert r.status_code == 503
