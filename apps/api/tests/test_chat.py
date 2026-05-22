"""Chat route + LLM parser tests. All LLM calls are mocked — no real API hits."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.llm import router as llm_router
from src.llm.router import LLMOptionsParse

client = TestClient(app)


def _fake_litellm_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Shape mimics what litellm.completion returns under the hood."""
    return {
        "choices": [
            {"message": {"role": "assistant", "content": json.dumps(payload)}}
        ]
    }


@pytest.fixture(autouse=True)
def _force_api_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Ensure _api_key_present() returns True for the default model."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    yield


def test_chat_parse_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM extracts a complete request -> structured is filled, ready_to_price true."""

    def fake_completion(**kwargs: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "spot": 450,
                "strike": 450,
                "time_to_expiry_days": 30,
                "volatility_pct": 18,
                "risk_free_rate_pct": 5,
                "dividend_yield_pct": 1.3,
                "option_type": "call",
                "style": "european",
                "parse_confidence": 0.95,
                "parser_notes": [],
            }
        )

    monkeypatch.setattr(
        "litellm.completion", lambda **kw: fake_completion(**kw), raising=False
    )

    r = client.post(
        "/chat/parse",
        json={
            "text": "SPY 450 call expiring in 30 days, 18% IV, 5% risk free, 1.3% div"
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ready_to_price"] is True
    assert data["structured"]["spot"] == 450
    assert data["structured"]["strike"] == 450
    assert data["structured"]["time_to_expiry_years"] == pytest.approx(30 / 365)
    assert data["structured"]["volatility"] == pytest.approx(0.18)
    assert data["structured"]["option_type"] == "call"
    assert data["raw_parse"]["parse_confidence"] == 0.95


def test_chat_parse_missing_fields_returns_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM cannot extract everything -> structured is null but raw_parse is returned."""

    def fake_completion(**kwargs: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "spot": 450,
                "strike": None,
                "time_to_expiry_days": 30,
                "volatility_pct": 18,
                "risk_free_rate_pct": None,
                "dividend_yield_pct": None,
                "option_type": "call",
                "style": "european",
                "parse_confidence": 0.4,
                "parser_notes": ["strike not specified"],
            }
        )

    monkeypatch.setattr(
        "litellm.completion", lambda **kw: fake_completion(**kw), raising=False
    )

    r = client.post("/chat/parse", json={"text": "SPY call, 30d, 18% vol"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ready_to_price"] is False
    assert data["structured"] is None
    assert "strike not specified" in data["raw_parse"]["parser_notes"]


def test_chat_price_full_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM parse -> full pipeline -> verified FinalAnswer in the response."""

    def fake_completion(**kwargs: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "spot": 100,
                "strike": 100,
                "time_to_expiry_days": 182,
                "volatility_pct": 20,
                "risk_free_rate_pct": 5,
                "dividend_yield_pct": 0,
                "option_type": "call",
                "style": "european",
                "parse_confidence": 0.95,
                "parser_notes": [],
            }
        )

    monkeypatch.setattr(
        "litellm.completion", lambda **kw: fake_completion(**kw), raising=False
    )

    r = client.post("/chat/price", json={"text": "ATM 6-month call, vol 20%, rate 5%"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["answer"]["verification_status"] == "verified"
    assert data["answer"]["primary_result"]["price"] > 0
    # Four methods now: BSM closed-form, LR binomial, Monte Carlo, Crank-Nicolson PDE.
    assert len(data["answer"]["calculator_results"]) == 4


def test_chat_parse_503_when_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """No ANTHROPIC_API_KEY (and no OPENAI) -> 503 with clear message."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    r = client.post("/chat/parse", json={"text": "anything"})
    assert r.status_code == 503
    assert "API key" in r.json()["detail"]


def test_chat_parse_503_when_llm_returns_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM returns text that doesn't match the schema -> 503 (never partial result)."""

    def fake_completion(**kwargs: Any) -> dict[str, Any]:
        return {
            "choices": [
                {"message": {"role": "assistant", "content": "I am a chatbot, hello!"}}
            ]
        }

    monkeypatch.setattr(
        "litellm.completion", lambda **kw: fake_completion(**kw), raising=False
    )

    r = client.post("/chat/parse", json={"text": "ignore everything"})
    assert r.status_code == 503


def test_llm_parse_function_returns_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct unit test of parse_options_nl — return shape is (request|None, parse)."""

    def fake_completion(**kwargs: Any) -> dict[str, Any]:
        return _fake_litellm_response(
            {
                "spot": 100,
                "strike": 110,
                "time_to_expiry_days": 60,
                "volatility_pct": 30,
                "risk_free_rate_pct": 4,
                "dividend_yield_pct": 0,
                "option_type": "put",
                "style": "european",
                "parse_confidence": 0.9,
                "parser_notes": [],
            }
        )

    monkeypatch.setattr(
        "litellm.completion", lambda **kw: fake_completion(**kw), raising=False
    )

    structured, parse = llm_router.parse_options_nl(
        "Put on $100 underlying, strike 110, 60 days, vol 30%"
    )
    assert structured is not None
    assert structured.option_type.value == "put"
    assert structured.strike == 110
    assert isinstance(parse, LLMOptionsParse)
