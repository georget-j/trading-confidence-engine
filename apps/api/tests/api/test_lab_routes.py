"""Tests for the /lab/* Methods Lab endpoints."""

from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


# ---- /lab/methods -----------------------------------------------------------


def test_list_methods_returns_catalog() -> None:
    r = client.get("/lab/methods")
    assert r.status_code == 200
    methods = r.json()
    assert isinstance(methods, list)
    # 19 expected: 4 options + 5 VaR + 5 portfolio + 5 backtest.
    assert len(methods) == 19
    families = {m["family"] for m in methods}
    assert families == {"options", "var", "portfolio", "backtest"}


def test_list_methods_includes_independent_from() -> None:
    """Each entry advertises which other methods it independently cross-checks against."""
    r = client.get("/lab/methods")
    methods = r.json()
    bsm = next(m for m in methods if m["method_id"] == "py_vollib_bsm_closed_form")
    assert "quantlib_binomial_lr" in bsm["independent_from"]
    assert "monte_carlo_gbm" in bsm["independent_from"]
    assert "crank_nicolson_pde" in bsm["independent_from"]


# ---- /lab/run (options) -----------------------------------------------------


def test_run_options_method() -> None:
    r = client.post(
        "/lab/run",
        json={
            "method_id": "py_vollib_bsm_closed_form",
            "inputs": {
                "spot": 100, "strike": 100,
                "time_to_expiry_years": 0.5,
                "volatility": 0.20, "risk_free_rate": 0.05, "dividend_yield": 0.0,
                "option_type": "call", "style": "european",
            },
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["method_id"] == "py_vollib_bsm_closed_form"
    assert data["family"] == "options"
    assert data["result"]["succeeded"] is True
    assert data["result"]["payload"]["price"] > 0
    # Greeks present for closed-form.
    assert data["result"]["payload"]["greeks"] is not None


def test_run_monte_carlo_options() -> None:
    r = client.post(
        "/lab/run",
        json={
            "method_id": "monte_carlo_gbm",
            "inputs": {
                "spot": 100, "strike": 100,
                "time_to_expiry_years": 0.5,
                "volatility": 0.20, "risk_free_rate": 0.05, "dividend_yield": 0.0,
                "option_type": "call", "style": "european",
            },
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["result"]["payload"]["price"] > 0
    # MC deliberately doesn't supply greeks.
    assert data["result"]["payload"]["greeks"] is None


# ---- /lab/run (VaR with explicit returns) -----------------------------------


def test_run_var_method_with_explicit_returns() -> None:
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0005, 0.01, size=504).tolist()
    r = client.post(
        "/lab/run",
        json={
            "method_id": "cornish_fisher_var",
            "inputs": {
                "lookback_days": 504, "portfolio_value": 50_000.0,
                "confidence_level": 0.99, "horizon_days": 1,
            },
            "returns": returns,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["family"] == "var"
    assert data["result"]["succeeded"] is True
    assert data["result"]["payload"]["var_loss"] > 0


# ---- /lab/run (portfolio with explicit returns_matrix) ----------------------


def test_run_portfolio_method_with_explicit_matrix() -> None:
    rng = np.random.default_rng(42)
    ret_matrix = rng.normal(0.0005, 0.01, size=(252, 3)).tolist()
    r = client.post(
        "/lab/run",
        json={
            "method_id": "min_variance_qp",
            "inputs": {
                "tickers": ["A", "B", "C"],
                "lookback_days": 252, "risk_free_rate": 0.05,
                "objective": "min_variance", "max_weight": 0.6,
                "shrink_covariance": True,
            },
            "returns_matrix": ret_matrix,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["family"] == "portfolio"
    assert data["result"]["succeeded"] is True
    weights = data["result"]["payload"]["weights"]
    assert abs(sum(w["weight"] for w in weights) - 1.0) < 1e-4


# ---- /lab/run (backtest with explicit returns) ------------------------------


def test_run_backtest_method_with_explicit_returns() -> None:
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0003, 0.012, size=504).tolist()
    r = client.post(
        "/lab/run",
        json={
            "method_id": "backtest_engine:mean_reversion",
            "inputs": {
                "ticker": "TEST", "lookback_days": 504,
                "initial_capital": 10_000.0,
            },
            "returns": returns,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["family"] == "backtest"
    assert data["result"]["succeeded"] is True
    assert data["result"]["payload"]["strategy"] == "mean_reversion"


# ---- Error handling ---------------------------------------------------------


def test_unknown_method_returns_404() -> None:
    r = client.post(
        "/lab/run", json={"method_id": "bogus_method", "inputs": {}}
    )
    assert r.status_code == 404
    assert "bogus_method" in r.json()["detail"]


def test_invalid_inputs_returns_422() -> None:
    """Invalid input fields → 422 (Pydantic validation reformatted to HTTP)."""
    r = client.post(
        "/lab/run",
        json={
            "method_id": "py_vollib_bsm_closed_form",
            "inputs": {
                "spot": -100,  # invalid
                "strike": 100, "time_to_expiry_years": 0.5,
                "volatility": 0.20, "risk_free_rate": 0.05, "dividend_yield": 0.0,
                "option_type": "call", "style": "european",
            },
        },
    )
    assert r.status_code == 422
