"""Per-method status aggregator tests.

Covers the family-agnostic ``build_per_method_status`` helper plus the
end-to-end shape of ``VerificationResult.per_method_status`` for each
pipeline (options, VaR, portfolio, backtest).
"""

from __future__ import annotations

import numpy as np

from src.calculators.options.black_scholes import compute as bs_compute
from src.calculators.options.crank_nicolson import compute as cn_compute
from src.core.schemas import (
    AgreementStatus,
    BacktestRequest,
    BacktestStrategy,
    CalcFamily,
    CalculationRequest,
    CalculatorResult,
    CrossMethodCheck,
    OptionsPriceResult,
    OptionsPricingRequest,
    OptionType,
    PortfolioObjective,
    PortfolioRequest,
    VaRRequest,
)
from src.data_providers.market_data import MarketDataProvider
from src.orchestration.backtest_pipeline import run_backtest_pipeline
from src.orchestration.pipeline import run_pipeline
from src.orchestration.portfolio_pipeline import run_portfolio_pipeline
from src.orchestration.var_pipeline import run_var_pipeline
from src.verification.invariants import check_options_invariants
from src.verification.per_method import build_per_method_status

# --- Direct aggregator unit tests -------------------------------------------


def _opt_result(method_id: str, price: float, succeeded: bool = True) -> CalculatorResult:
    return CalculatorResult(
        calculator_id=method_id,
        method_name=method_id.replace("_", " ").title(),
        payload=OptionsPriceResult(price=price),
        duration_ms=1.0,
        succeeded=succeeded,
        error=None if succeeded else "boom",
    )


def _opt_req() -> OptionsPricingRequest:
    return OptionsPricingRequest(
        spot=450.0,
        strike=450.0,
        time_to_expiry_years=30 / 365,
        volatility=0.18,
        risk_free_rate=0.05,
        dividend_yield=0.0,
        option_type=OptionType.CALL,
    )


def test_per_method_marks_agreeing_methods_when_within_tolerance() -> None:
    req = _opt_req()
    a = _opt_result("a", 9.94)
    b = _opt_result("b", 9.9401)
    cross = CrossMethodCheck(
        methods_compared=["a", "b"],
        max_absolute_delta=0.0001,
        max_relative_delta=1e-5,
        tolerance=1e-3,
        passed=True,
    )

    rows = build_per_method_status(
        results=[a, b],
        cross_check=cross,
        value_extractor=lambda r: r.payload.price if r.succeeded else None,
        invariant_runner=lambda r: check_options_invariants(req, [r]),
        abs_tol=1e-3,
        rel_tol=1e-3,
    )

    assert {r.method_id for r in rows} == {"a", "b"}
    for r in rows:
        assert r.ran is True
        assert r.agreement_status == AgreementStatus.AGREES
        assert r.divergent_against == []
        assert r.value is not None and r.value > 0
        # All standard options invariants pass for an ATM call.
        assert r.invariants_failed == []
        assert "non_negative_price" in r.invariants_passed


def test_per_method_marks_divergent_when_outside_tolerance() -> None:
    req = _opt_req()
    a = _opt_result("a", 9.94)
    b = _opt_result("b", 15.0)  # clearly divergent
    cross = CrossMethodCheck(
        methods_compared=["a", "b"],
        max_absolute_delta=5.06,
        max_relative_delta=0.4,
        tolerance=1e-3,
        passed=False,
    )

    rows = build_per_method_status(
        results=[a, b],
        cross_check=cross,
        value_extractor=lambda r: r.payload.price if r.succeeded else None,
        invariant_runner=lambda r: check_options_invariants(req, [r]),
        abs_tol=1e-3,
        rel_tol=1e-3,
    )
    by_id = {r.method_id: r for r in rows}
    assert by_id["a"].agreement_status == AgreementStatus.DIVERGES
    assert by_id["a"].divergent_against == ["b"]
    assert by_id["b"].agreement_status == AgreementStatus.DIVERGES
    assert by_id["b"].divergent_against == ["a"]


def test_per_method_marks_non_headline_method_as_n_slash_a() -> None:
    """A method that ran but wasn't in cross_check.methods_compared is n/a."""
    req = _opt_req()
    a = _opt_result("a", 9.94)
    b = _opt_result("b", 9.94)
    c_extra = _opt_result("c_loose", 9.95)  # not in headline pair
    cross = CrossMethodCheck(
        methods_compared=["a", "b"],
        max_absolute_delta=0.0,
        max_relative_delta=0.0,
        tolerance=1e-3,
        passed=True,
    )

    rows = build_per_method_status(
        results=[a, b, c_extra],
        cross_check=cross,
        value_extractor=lambda r: r.payload.price if r.succeeded else None,
        invariant_runner=lambda r: check_options_invariants(req, [r]),
        abs_tol=1e-3,
        rel_tol=1e-3,
    )
    by_id = {r.method_id: r for r in rows}
    assert by_id["c_loose"].agreement_status == AgreementStatus.NOT_APPLICABLE
    assert by_id["c_loose"].ran is True
    assert by_id["c_loose"].value == 9.95


def test_per_method_handles_failed_method() -> None:
    req = _opt_req()
    a = _opt_result("a", 9.94)
    b_bad = _opt_result("b", 0.0, succeeded=False)
    cross = CrossMethodCheck(
        methods_compared=["a"],  # b excluded because it failed
        max_absolute_delta=0.0,
        max_relative_delta=0.0,
        tolerance=1e-3,
        passed=True,
    )

    rows = build_per_method_status(
        results=[a, b_bad],
        cross_check=cross,
        value_extractor=lambda r: r.payload.price if r.succeeded else None,
        invariant_runner=lambda r: check_options_invariants(req, [r]),
    )
    by_id = {r.method_id: r for r in rows}
    assert by_id["b"].ran is False
    assert by_id["b"].value is None
    assert by_id["b"].error == "boom"
    assert by_id["b"].invariants_passed == []
    assert by_id["b"].invariants_failed == []
    assert by_id["b"].agreement_status == AgreementStatus.NOT_APPLICABLE


def test_per_method_invariants_run_against_each_method_payload() -> None:
    """One method has a sane price; another has a negative price.

    The bad method's per-method invariants_failed must include
    non_negative_price even though the primary's didn't.
    """
    req = _opt_req()
    good = _opt_result("good", bs_compute(req).payload.price)
    bad = _opt_result("bad", -5.0)
    cross = CrossMethodCheck(
        methods_compared=["good", "bad"],
        max_absolute_delta=20.0,
        max_relative_delta=2.0,
        tolerance=1e-3,
        passed=False,
    )

    rows = build_per_method_status(
        results=[good, bad],
        cross_check=cross,
        value_extractor=lambda r: r.payload.price if r.succeeded else None,
        invariant_runner=lambda r: check_options_invariants(req, [r]),
    )
    by_id = {r.method_id: r for r in rows}
    assert "non_negative_price" in by_id["bad"].invariants_failed
    assert "non_negative_price" in by_id["good"].invariants_passed


# --- End-to-end pipeline shape tests ----------------------------------------


def test_options_pipeline_emits_per_method_status() -> None:
    """Full options pipeline yields one per_method row per calculator."""
    req = _opt_req()
    answer, _ = run_pipeline(
        CalculationRequest(raw_input="x", family_hint=CalcFamily.OPTIONS_PRICING),
        parsed_payload=req,
    )
    rows = answer.verification.per_method_status
    # The runner registers 4 calculators (BSM, LR binomial, MC, CN PDE).
    assert len(rows) == 4
    method_ids = {r.method_id for r in rows}
    assert "py_vollib_bsm_closed_form" in method_ids
    assert "quantlib_binomial_lr" in method_ids
    # The headline pair must be marked AGREES; the loose pair is n/a.
    by_id = {r.method_id: r for r in rows}
    assert by_id["py_vollib_bsm_closed_form"].agreement_status == AgreementStatus.AGREES
    assert by_id["quantlib_binomial_lr"].agreement_status == AgreementStatus.AGREES
    # Crank-Nicolson is not in the headline pair → n/a.
    assert by_id["crank_nicolson_pde"].agreement_status == AgreementStatus.NOT_APPLICABLE
    # Every successful row carries a price + invariant counts.
    for r in rows:
        if r.ran:
            assert r.value is not None
            assert r.duration_ms is not None


def test_options_per_method_failing_method_path() -> None:
    """The per-method row for a successfully cross-checked method also reports
    its own invariants — directly exercise the in-pipeline runner."""
    req = _opt_req()
    a = bs_compute(req)
    b = cn_compute(req)
    cross = CrossMethodCheck(
        methods_compared=[a.calculator_id, b.calculator_id],
        max_absolute_delta=0.01,
        max_relative_delta=0.001,
        tolerance=1e-3,
        passed=True,
    )
    rows = build_per_method_status(
        results=[a, b],
        cross_check=cross,
        value_extractor=lambda r: r.payload.price if r.succeeded else None,
        invariant_runner=lambda r: check_options_invariants(req, [r]),
        abs_tol=1e-3,
        rel_tol=1e-3,
    )
    for r in rows:
        if r.ran:
            assert "non_negative_price" in r.invariants_passed


# --- VaR pipeline ------------------------------------------------------------


class _StaticReturnsProvider:
    """In-memory MarketDataProvider that returns a fixed daily-return series."""

    def __init__(self, returns: list[float]) -> None:
        self._returns = returns

    def fetch_daily_returns(self, ticker: str, lookback_days: int) -> list[float]:
        return list(self._returns[-lookback_days:])

    def fetch_aligned_returns(self, tickers, lookback_days):  # pragma: no cover
        raise NotImplementedError


def test_var_pipeline_emits_per_method_status_for_each_calculator() -> None:
    rng = np.random.default_rng(7)
    returns = rng.normal(loc=0.0, scale=0.01, size=600).tolist()
    var_req = VaRRequest(
        returns=returns,
        confidence_level=0.99,
        horizon_days=1,
        portfolio_value=50_000.0,
        lookback_days=504,
    )
    answer, _ = run_var_pipeline(
        CalculationRequest(raw_input="x", family_hint=CalcFamily.RISK_METRICS),
        var_req,
        provider=None,  # returns supplied directly
    )
    rows = answer.verification.per_method_status
    # The runner registers 5 calculators (historical, parametric, MC,
    # cornish-fisher, bootstrap).
    assert len(rows) >= 3
    for r in rows:
        if r.ran:
            assert r.value is not None and r.value >= 0
            assert r.agreement_status in (
                AgreementStatus.AGREES,
                AgreementStatus.DIVERGES,
                AgreementStatus.NOT_APPLICABLE,
            )


# --- Portfolio pipeline ------------------------------------------------------


class _StaticAlignedProvider(MarketDataProvider):
    def __init__(self, returns_matrix: np.ndarray, tickers: list[str]) -> None:
        self._mat = returns_matrix
        self._tickers = tickers

    def fetch_daily_returns(self, ticker: str, lookback_days: int) -> list[float]:
        idx = self._tickers.index(ticker)
        return self._mat[-lookback_days:, idx].tolist()

    def fetch_aligned_returns(self, tickers, lookback_days):
        idx = [self._tickers.index(t) for t in tickers]
        sub = self._mat[-lookback_days:, idx]
        return list(tickers), sub.tolist()


def test_portfolio_pipeline_emits_per_method_with_solver_row() -> None:
    rng = np.random.default_rng(11)
    tickers = ["A", "B", "C", "D"]
    returns = rng.normal(loc=0.0005, scale=0.01, size=(300, 4))
    provider = _StaticAlignedProvider(returns, tickers)
    req = PortfolioRequest(
        tickers=tickers,
        lookback_days=252,
        objective=PortfolioObjective.MAX_SHARPE,
        risk_aversion=2.0,
        max_weight=0.6,
    )
    answer, _ = run_portfolio_pipeline(
        CalculationRequest(
            raw_input="x", family_hint=CalcFamily.PORTFOLIO_OPTIMIZATION
        ),
        req,
        provider=provider,
    )
    rows = answer.verification.per_method_status
    # Primary CLARABEL row + (when cross-check ran) an SCS pseudo-row.
    assert len(rows) >= 1
    primary = rows[0]
    assert primary.ran is True
    assert primary.sensitivity_passed in (True, False)
    if len(rows) == 2:
        scs = rows[1]
        assert scs.method_id == "scs"
        # SCS pseudo-row never carries invariants — they're attributed to the
        # primary solver.
        assert scs.invariants_passed == []
        assert scs.invariants_failed == []


# --- Backtest pipeline -------------------------------------------------------


def test_backtest_pipeline_emits_single_per_method_row() -> None:
    rng = np.random.default_rng(23)
    returns = rng.normal(0.0005, 0.01, size=400).tolist()
    provider = _StaticReturnsProvider(returns)
    bt_req = BacktestRequest(
        ticker="SPY",
        strategy=BacktestStrategy.BUY_AND_HOLD,
        lookback_days=252,
        initial_capital=100_000.0,
    )
    answer, _ = run_backtest_pipeline(
        CalculationRequest(raw_input="x", family_hint=CalcFamily.BACKTEST),
        bt_req,
        provider=provider,
    )
    rows = answer.verification.per_method_status
    assert len(rows) == 1
    r = rows[0]
    assert r.ran is True
    assert r.agreement_status == AgreementStatus.NOT_APPLICABLE
    # Reproducibility + look-ahead show up as synthesised invariant flags.
    assert "walk_forward_reproducible" in r.invariants_passed
    assert "lookahead_clean" in r.invariants_passed
    assert r.sensitivity_passed is not None


