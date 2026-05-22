"""End-to-end pipeline + API tests for multi-leg options strategies.

The unit tests in tests/calculators/test_strategy.py cover the strategy
calculator and verification primitives. These tests cover the full pipeline:
parse → calculate → verify → score → respond, plus the FastAPI route.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app
from src.core.schemas import (
    CalculationRequest,
    OptionsStrategyPayload,
    OptionsStrategyRequest,
    OptionType,
    StrategyLeg,
    VerificationStatus,
)
from src.orchestration.strategy_pipeline import run_strategy_pipeline

client = TestClient(app)


def _vertical(spot: float = 450.0) -> OptionsStrategyRequest:
    return OptionsStrategyRequest(
        spot=spot,
        risk_free_rate=0.05,
        dividend_yield=0.013,
        legs=[
            StrategyLeg(
                option_type=OptionType.CALL,
                strike=spot,
                quantity=1,
                time_to_expiry_years=30 / 365,
                volatility=0.20,
            ),
            StrategyLeg(
                option_type=OptionType.CALL,
                strike=spot * 1.05,
                quantity=-1,
                time_to_expiry_years=30 / 365,
                volatility=0.20,
            ),
        ],
    )


# ---- Pipeline ---------------------------------------------------------------


def test_pipeline_returns_verified_for_textbook_vertical() -> None:
    req = CalculationRequest(raw_input="")
    answer, log = run_strategy_pipeline(req, _vertical())

    assert answer.verification_status == VerificationStatus.VERIFIED
    payload = answer.primary_result
    assert isinstance(payload, OptionsStrategyPayload)
    assert len(payload.legs) == 2
    # Long call vertical is a debit spread — net premium should be positive
    # (the ATM call costs more than the OTM call sold against it).
    assert payload.net_premium > 0
    # Both methods present in the calculator_results.
    assert len(answer.calculator_results) == 2
    assert all(c.succeeded for c in answer.calculator_results)
    # Audit log captured every stage.
    stages = [e.stage for e in log.entries]
    assert stages == ["request", "parse", "calculate", "verify", "explain", "respond"]


def test_pipeline_records_per_leg_invariants() -> None:
    """All 2 legs of the vertical should have their full single-leg invariant
    suite applied (non_negative, lower_bound, upper_bound, delta, gamma)."""
    req = CalculationRequest(raw_input="")
    answer, _ = run_strategy_pipeline(req, _vertical())

    leg_names = {c.name.split("_")[0] for c in answer.verification.invariants}
    assert leg_names == {"leg0", "leg1"}
    assert all(c.passed for c in answer.verification.invariants)
    # Each leg should have 5 invariants (non_neg, lb, ub, delta, gamma).
    per_leg = {0: 0, 1: 0}
    for c in answer.verification.invariants:
        idx = int(c.name.split("_")[0].lstrip("leg"))
        per_leg[idx] += 1
    assert per_leg == {0: 5, 1: 5}


# ---- API route --------------------------------------------------------------


def test_strategy_endpoint_verified_response() -> None:
    payload = {
        "spot": 450.0,
        "risk_free_rate": 0.05,
        "dividend_yield": 0.013,
        "legs": [
            {
                "option_type": "call",
                "strike": 450.0,
                "quantity": 1,
                "time_to_expiry_years": 30 / 365,
                "volatility": 0.20,
            },
            {
                "option_type": "call",
                "strike": 472.5,
                "quantity": -1,
                "time_to_expiry_years": 30 / 365,
                "volatility": 0.20,
            },
        ],
    }
    r = client.post("/calc/options/strategy", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["verification_status"] == "verified"
    assert data["primary_result"]["kind"] == "options_strategy"
    assert len(data["primary_result"]["legs"]) == 2
    assert data["primary_result"]["net_premium"] > 0


def test_strategy_endpoint_rejects_single_leg() -> None:
    payload = {
        "spot": 100.0,
        "risk_free_rate": 0.05,
        "legs": [
            {
                "option_type": "call",
                "strike": 100.0,
                "quantity": 1,
                "time_to_expiry_years": 0.1,
                "volatility": 0.2,
            }
        ],
    }
    r = client.post("/calc/options/strategy", json=payload)
    assert r.status_code == 422


def test_strategy_endpoint_iron_condor_verifies() -> None:
    spot = 450.0
    payload = {
        "spot": spot,
        "risk_free_rate": 0.05,
        "dividend_yield": 0.013,
        "legs": [
            {
                "option_type": "put",
                "strike": spot * 0.95,
                "quantity": -1,
                "time_to_expiry_years": 30 / 365,
                "volatility": 0.22,
            },
            {
                "option_type": "put",
                "strike": spot * 0.90,
                "quantity": 1,
                "time_to_expiry_years": 30 / 365,
                "volatility": 0.22,
            },
            {
                "option_type": "call",
                "strike": spot * 1.05,
                "quantity": -1,
                "time_to_expiry_years": 30 / 365,
                "volatility": 0.22,
            },
            {
                "option_type": "call",
                "strike": spot * 1.10,
                "quantity": 1,
                "time_to_expiry_years": 30 / 365,
                "volatility": 0.22,
            },
        ],
    }
    r = client.post("/calc/options/strategy", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["verification_status"] == "verified"
    # Iron condor is a net-credit position (you collect premium from short legs).
    assert data["primary_result"]["net_premium"] < 0


def test_strategy_endpoint_does_not_accept_options_price_payload() -> None:
    """The single-leg payload shape should be rejected — legs[] is required."""
    payload = {
        "spot": 100.0,
        "strike": 100.0,
        "time_to_expiry_years": 0.5,
        "volatility": 0.20,
        "risk_free_rate": 0.05,
        "option_type": "call",
    }
    r = client.post("/calc/options/strategy", json=payload)
    assert r.status_code == 422
