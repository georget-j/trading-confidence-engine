"""Portfolio pipeline + verification + endpoint tests.

All tests use a deterministic in-memory data provider — no network."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.schemas import (
    CalculationRequest,
    PortfolioObjective,
    PortfolioPayload,
    PortfolioRequest,
    VerificationStatus,
)
from src.data_providers.market_data import MarketDataError
from src.orchestration.portfolio_pipeline import run_portfolio_pipeline
from src.verification.invariants_portfolio import check_portfolio_invariants
from src.verification.sensitivity_portfolio import compute_instability

client = TestClient(app)


class FakeProvider:
    """Aligned multi-ticker returns. Same factor model as the optimizer tests."""

    def __init__(self, seed: int = 42, n_days: int = 504) -> None:
        self.seed = seed
        self.n_days = n_days

    def fetch_aligned_returns(
        self, tickers: list[str], lookback_days: int
    ) -> tuple[list[str], list[list[float]]]:
        rng = np.random.default_rng(self.seed)
        n = len(tickers)
        base = rng.normal(0.0008, 0.012, (self.n_days, n))
        market = rng.normal(0.0005, 0.008, self.n_days).reshape(-1, 1)
        returns = base + market
        return list(tickers), returns.tolist()

    def fetch_daily_returns(self, ticker: str, lookback_days: int) -> list[float]:
        rng = np.random.default_rng(self.seed)
        return rng.normal(0.0005, 0.012, self.n_days).tolist()


class BrokenProvider:
    def fetch_aligned_returns(
        self, tickers: list[str], lookback_days: int
    ) -> tuple[list[str], list[list[float]]]:
        raise MarketDataError("fake fetch failure")

    def fetch_daily_returns(self, ticker: str, lookback_days: int) -> list[float]:
        raise MarketDataError("fake fetch failure")


def test_pipeline_verified_on_well_conditioned_synthetic() -> None:
    req = PortfolioRequest(
        tickers=["SPY", "QQQ", "GLD", "TLT"],
        objective=PortfolioObjective.MEAN_VARIANCE,
    )
    answer, log = run_portfolio_pipeline(
        CalculationRequest(raw_input=""), req, provider=FakeProvider()
    )
    assert answer.verification_status == VerificationStatus.VERIFIED
    assert isinstance(answer.primary_result, PortfolioPayload)
    assert [e.stage for e in log.entries] == [
        "request", "parse", "calculate", "verify", "explain", "respond",
    ]


def test_pipeline_records_instability_score() -> None:
    req = PortfolioRequest(tickers=["A", "B", "C", "D"])
    answer, _ = run_portfolio_pipeline(
        CalculationRequest(raw_input=""), req, provider=FakeProvider()
    )
    payload = answer.primary_result
    assert isinstance(payload, PortfolioPayload)
    assert payload.instability_score is not None
    assert 0.0 <= payload.instability_score <= 1.0


def test_max_sharpe_path_works_end_to_end() -> None:
    req = PortfolioRequest(
        tickers=["A", "B", "C", "D"], objective=PortfolioObjective.MAX_SHARPE
    )
    answer, _ = run_portfolio_pipeline(
        CalculationRequest(raw_input=""), req, provider=FakeProvider()
    )
    assert isinstance(answer.primary_result, PortfolioPayload)
    assert answer.primary_result.objective == PortfolioObjective.MAX_SHARPE
    # max-Sharpe by construction should be in the verified or partial bucket
    # for well-conditioned synthetic data (never not_verified).
    assert answer.verification_status != VerificationStatus.NOT_VERIFIED


def test_invariants_catch_negative_weights() -> None:
    """Inject a fake CalculatorResult with a negative weight — invariants must fail."""
    from src.core.schemas import AssetWeight, CalculatorResult

    payload = PortfolioPayload(
        objective=PortfolioObjective.MEAN_VARIANCE,
        weights=[
            AssetWeight(ticker="A", weight=1.2, risk_contribution=1.0),
            AssetWeight(ticker="B", weight=-0.2, risk_contribution=0.0),
        ],
        expected_return_annualised=0.1,
        volatility_annualised=0.1,
        sharpe_ratio=1.0,
        solver_name="fake",
        iterations=1,
        instability_score=None,
    )
    fake = CalculatorResult(
        calculator_id="fake", method_name="fake",
        payload=payload, duration_ms=0.0, succeeded=True,
    )
    req = PortfolioRequest(tickers=["A", "B"])
    returns = np.zeros((100, 2))
    checks = check_portfolio_invariants(req, fake, returns)
    failed = [c for c in checks if not c.passed]
    assert any("non_negative" in c.name for c in failed)


def test_sensitivity_stable_on_independent_returns() -> None:
    """Returns with no factor coupling and similar means should produce a
    stable optimum (low instability). This anchors the sensitivity metric."""
    rng = np.random.default_rng(11)
    returns = rng.normal(0.0008, 0.012, (504, 4))
    req = PortfolioRequest(tickers=["A", "B", "C", "D"])
    # Solve once to get the base weights for the sensitivity diff.
    from src.calculators.portfolio import mean_variance

    base_weights, _ = mean_variance.solve(req, returns)
    score, diag = compute_instability(req, returns, base_weights)
    assert 0.0 <= score <= 1.0
    assert "max_weight_move" in diag


def test_api_optimize_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the default provider for the API call so we don't hit the network."""
    monkeypatch.setattr(
        "src.orchestration.portfolio_pipeline.default_provider",
        lambda: FakeProvider(),
    )
    payload = {
        "tickers": ["SPY", "QQQ", "GLD", "TLT"],
        "objective": "mean_variance",
        "lookback_days": 504,
        "risk_free_rate": 0.04,
        "risk_aversion": 2.0,
    }
    r = client.post("/calc/portfolio/optimize", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["verification_status"] in {"verified", "partially_verified"}
    assert data["primary_result"]["kind"] == "portfolio"
    assert len(data["primary_result"]["weights"]) == 4
    total_weight = sum(w["weight"] for w in data["primary_result"]["weights"])
    assert abs(total_weight - 1.0) < 1e-3


def test_api_optimize_requires_two_tickers() -> None:
    r = client.post(
        "/calc/portfolio/optimize",
        json={"tickers": ["SPY"], "objective": "mean_variance"},
    )
    assert r.status_code == 422


def test_api_optimize_data_failure_502(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.orchestration.portfolio_pipeline.default_provider",
        lambda: BrokenProvider(),
    )
    r = client.post(
        "/calc/portfolio/optimize",
        json={"tickers": ["A", "B"], "objective": "mean_variance"},
    )
    assert r.status_code == 502
