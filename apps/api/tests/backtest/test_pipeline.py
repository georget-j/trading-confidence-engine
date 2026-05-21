"""Backtest pipeline + endpoint tests."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.schemas import (
    BacktestPayload,
    BacktestRequest,
    BacktestStrategy,
    CalculationRequest,
    VerificationStatus,
)
from src.data_providers.market_data import MarketDataError
from src.orchestration.backtest_pipeline import run_backtest_pipeline

client = TestClient(app)


class FakeProvider:
    def __init__(self, seed: int = 42, drift: float = 0.0005, n: int = 504) -> None:
        rng = np.random.default_rng(seed)
        self._returns = rng.normal(drift, 0.012, n).tolist()

    def fetch_daily_returns(self, ticker: str, lookback_days: int) -> list[float]:
        return list(self._returns)

    def fetch_aligned_returns(
        self, tickers: list[str], lookback_days: int
    ) -> tuple[list[str], list[list[float]]]:
        return tickers, [[self._returns[i]] * len(tickers) for i in range(len(self._returns))]


def test_pipeline_runs_end_to_end() -> None:
    req = BacktestRequest(
        ticker="SPY", strategy=BacktestStrategy.MA_CROSSOVER, ma_fast=20, ma_slow=50
    )
    answer, log = run_backtest_pipeline(
        CalculationRequest(raw_input=""), req, provider=FakeProvider()
    )
    assert isinstance(answer.primary_result, BacktestPayload)
    assert [e.stage for e in log.entries] == [
        "request", "parse", "calculate", "verify", "explain", "respond",
    ]
    # Walk-forward and look-ahead flags both filled.
    assert answer.primary_result.walk_forward_reproducible is True
    assert answer.primary_result.lookahead_clean is True


def test_pipeline_verified_on_clean_strategy() -> None:
    req = BacktestRequest(ticker="SPY", strategy=BacktestStrategy.BUY_AND_HOLD)
    answer, _ = run_backtest_pipeline(
        CalculationRequest(raw_input=""), req, provider=FakeProvider()
    )
    # Buy-and-hold with default slippage on a positive-drift series should
    # easily land at verified or partially_verified (never not_verified).
    assert answer.verification_status != VerificationStatus.NOT_VERIFIED


def test_api_run_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.orchestration.backtest_pipeline.default_provider",
        lambda: FakeProvider(),
    )
    payload = {
        "ticker": "SPY",
        "strategy": "ma_crossover",
        "lookback_days": 504,
        "ma_fast": 20,
        "ma_slow": 50,
    }
    r = client.post("/calc/backtest/run", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["primary_result"]["kind"] == "backtest"
    assert "metrics" in data["primary_result"]
    assert len(data["primary_result"]["equity_curve"]) > 0
    assert "slippage_sensitivity" in data["primary_result"]


def test_api_run_502_on_data_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class Broken:
        def fetch_daily_returns(self, ticker: str, lookback: int) -> list[float]:
            raise MarketDataError("nope")
        def fetch_aligned_returns(self, *a, **kw):
            raise MarketDataError("nope")

    monkeypatch.setattr(
        "src.orchestration.backtest_pipeline.default_provider", lambda: Broken()
    )
    r = client.post(
        "/calc/backtest/run",
        json={"ticker": "DOES_NOT_EXIST", "strategy": "buy_and_hold"},
    )
    assert r.status_code == 502
