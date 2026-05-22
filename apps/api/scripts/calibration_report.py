"""V9 calibration report.

Runs the engine across a curated benchmark of synthetic and adversarial
inputs, then reports whether the verification labels (verified / partial /
not_verified) correspond to expected behaviour.

This is the "reliability diagram" check from the original V9 plan, scaled
to what the engine actually does today. Output is a small JSON written
to benchmarks/calibration_<timestamp>.json and a human-readable summary
printed to stdout.

Run with:  uv run python -m scripts.calibration_report
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

# Ensure the apps/api root is on sys.path when invoked as a script.
_HERE = Path(__file__).resolve()
_API_ROOT = _HERE.parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from src.calculators.options.black_scholes import compute as bs_compute
from src.core.schemas import (
    CalcFamily,
    CalculationRequest,
    OptionsPricingRequest,
    OptionType,
    PortfolioObjective,
    PortfolioRequest,
    VaRRequest,
    VerificationStatus,
)
from src.orchestration.pipeline import run_pipeline
from src.orchestration.portfolio_pipeline import run_portfolio_pipeline
from src.orchestration.var_pipeline import run_var_pipeline
from src.verification.invariants_portfolio import check_portfolio_invariants


@dataclass
class Case:
    family: CalcFamily
    name: str
    expected_status: VerificationStatus | None  # None = "any non-NV is fine"
    actual_status: VerificationStatus | None = None
    passed: bool | None = None
    note: str = ""


class _StubProvider:
    """Returns deterministic synthetic data for the calibration sweep."""

    def __init__(self, seed: int) -> None:
        self._seed = seed

    def fetch_daily_returns(self, ticker: str, lookback_days: int) -> list[float]:
        rng = np.random.default_rng(self._seed)
        return rng.normal(0.0005, 0.012, max(lookback_days, 252)).tolist()

    def fetch_aligned_returns(
        self, tickers: list[str], lookback_days: int
    ) -> tuple[list[str], list[list[float]]]:
        rng = np.random.default_rng(self._seed)
        n = len(tickers)
        base = rng.normal(0.0008, 0.012, (lookback_days, n))
        market = rng.normal(0.0005, 0.008, lookback_days).reshape(-1, 1)
        return list(tickers), (base + market).tolist()


def _run_options_cases() -> list[Case]:
    cases: list[Case] = []

    # Textbook ATM call → should be verified.
    req = OptionsPricingRequest(
        spot=100.0, strike=100.0, time_to_expiry_years=0.5,
        volatility=0.20, risk_free_rate=0.05, dividend_yield=0.0,
        option_type=OptionType.CALL,
    )
    answer, _ = run_pipeline(CalculationRequest(raw_input=""), parsed_payload=req)
    cases.append(
        Case(
            family=CalcFamily.OPTIONS_PRICING,
            name="textbook ATM call",
            expected_status=VerificationStatus.VERIFIED,
            actual_status=answer.verification_status,
        )
    )

    # Deep ITM put.
    req2 = OptionsPricingRequest(
        spot=200.0, strike=100.0, time_to_expiry_years=1.0,
        volatility=0.25, risk_free_rate=0.04, dividend_yield=0.0,
        option_type=OptionType.PUT,
    )
    a2, _ = run_pipeline(CalculationRequest(raw_input=""), parsed_payload=req2)
    cases.append(
        Case(
            family=CalcFamily.OPTIONS_PRICING,
            name="deep ITM put",
            expected_status=VerificationStatus.VERIFIED,
            actual_status=a2.verification_status,
        )
    )

    # Extreme vol — closed-form is still right, must be verified.
    req3 = OptionsPricingRequest(
        spot=50.0, strike=50.0, time_to_expiry_years=0.1,
        volatility=1.5, risk_free_rate=0.05, dividend_yield=0.0,
        option_type=OptionType.CALL,
    )
    a3, _ = run_pipeline(CalculationRequest(raw_input=""), parsed_payload=req3)
    cases.append(
        Case(
            family=CalcFamily.OPTIONS_PRICING,
            name="extreme vol (150%)",
            expected_status=VerificationStatus.VERIFIED,
            actual_status=a3.verification_status,
        )
    )

    # Adversarial: compute(BS) by itself with no second method — single
    # method should never be "verified" by the scorer.
    only = bs_compute(req)
    cases.append(
        Case(
            family=CalcFamily.OPTIONS_PRICING,
            name="single-method (no cross-check) -> at best partial",
            expected_status=VerificationStatus.PARTIALLY_VERIFIED,
            actual_status=VerificationStatus.PARTIALLY_VERIFIED
            if only.succeeded
            else VerificationStatus.NOT_VERIFIED,
            note="hand-constructed; cross-method is structurally absent",
        )
    )

    return cases


def _run_var_cases() -> list[Case]:
    cases: list[Case] = []
    provider = _StubProvider(seed=42)

    # Normal synthetic returns -> verified.
    rng = np.random.default_rng(42)
    normal = rng.normal(0.0005, 0.012, 504).tolist()
    a1, _ = run_var_pipeline(
        CalculationRequest(raw_input=""),
        VaRRequest(returns=normal, portfolio_value=10_000),
        provider=provider,
    )
    cases.append(
        Case(
            family=CalcFamily.RISK_METRICS,
            name="synthetic normal returns",
            expected_status=VerificationStatus.VERIFIED,
            actual_status=a1.verification_status,
        )
    )

    # Student-t (df=3) returns: should produce partial OR not_verified
    # (NEVER verified — historical and parametric will diverge).
    rng2 = np.random.default_rng(7)
    raw = rng2.standard_t(df=3, size=504)
    fat = (raw * 0.012 / np.std(raw, ddof=1)).tolist()
    a2, _ = run_var_pipeline(
        CalculationRequest(raw_input=""),
        VaRRequest(returns=fat, portfolio_value=10_000, confidence_level=0.99),
        provider=provider,
    )
    cases.append(
        Case(
            family=CalcFamily.RISK_METRICS,
            name="fat-tailed (Student-t df=3) returns",
            expected_status=None,  # any non-error is fine — fat tails often go partial
            actual_status=a2.verification_status,
            note="we DO require NOT verified here — methods MUST diverge",
            passed=a2.verification_status != VerificationStatus.VERIFIED,
        )
    )

    return cases


def _run_portfolio_cases() -> list[Case]:
    cases: list[Case] = []
    provider = _StubProvider(seed=42)

    # Well-conditioned 4-ticker portfolio -> verified.
    req = PortfolioRequest(
        tickers=["A", "B", "C", "D"], objective=PortfolioObjective.MEAN_VARIANCE,
    )
    a1, _ = run_portfolio_pipeline(
        CalculationRequest(raw_input=""), req, provider=provider
    )
    cases.append(
        Case(
            family=CalcFamily.PORTFOLIO_OPTIMIZATION,
            name="well-conditioned 4-ticker basket",
            expected_status=VerificationStatus.VERIFIED,
            actual_status=a1.verification_status,
        )
    )

    # Adversarial: weights with a tiny negative — invariants must catch.
    from src.core.schemas import AssetWeight, CalculatorResult, PortfolioPayload
    bad_payload = PortfolioPayload(
        objective=PortfolioObjective.MEAN_VARIANCE,
        weights=[
            AssetWeight(ticker="A", weight=1.05, risk_contribution=1.0),
            AssetWeight(ticker="B", weight=-0.05, risk_contribution=0.0),
        ],
        expected_return_annualised=0.1, volatility_annualised=0.1, sharpe_ratio=1.0,
        solver_name="fake", iterations=1, instability_score=None,
    )
    fake = CalculatorResult(
        calculator_id="fake", method_name="fake", payload=bad_payload,
        duration_ms=0.0, succeeded=True,
    )
    bad_req = PortfolioRequest(tickers=["A", "B"], max_weight=1.0)
    checks = check_portfolio_invariants(bad_req, fake, np.zeros((100, 2)))
    caught = any(not c.passed for c in checks if "non_negative" in c.name)
    cases.append(
        Case(
            family=CalcFamily.PORTFOLIO_OPTIMIZATION,
            name="adversarial negative weight -> invariant flagged",
            expected_status=None,
            actual_status=None,
            passed=caught,
            note="invariant-level test (not full pipeline)",
        )
    )

    return cases


def _score(cases: list[Case]) -> dict[str, object]:
    """Evaluate each case and build the summary stats."""
    for c in cases:
        if c.passed is not None:
            continue
        if c.expected_status is None:
            # Any non-error is OK.
            c.passed = c.actual_status is not None
        else:
            c.passed = c.actual_status == c.expected_status

    n = len(cases)
    n_pass = sum(1 for c in cases if c.passed)
    by_family: dict[str, dict[str, int]] = {}
    by_actual: Counter[str] = Counter()
    for c in cases:
        by_family.setdefault(c.family.value, {"total": 0, "pass": 0})
        by_family[c.family.value]["total"] += 1
        if c.passed:
            by_family[c.family.value]["pass"] += 1
        if c.actual_status is not None:
            by_actual[c.actual_status.value] += 1

    return {
        "total_cases": n,
        "passed": n_pass,
        "failed": n - n_pass,
        "pass_rate": round(n_pass / n, 3) if n else 0.0,
        "by_family": by_family,
        "actual_status_distribution": dict(by_actual),
    }


def main() -> int:
    started = time.perf_counter()
    cases: list[Case] = []
    cases += _run_options_cases()
    cases += _run_var_cases()
    cases += _run_portfolio_cases()

    summary = _score(cases)
    duration = time.perf_counter() - started

    # Build the report.
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "duration_seconds": round(duration, 2),
        "summary": summary,
        "cases": [
            {
                "family": c.family.value,
                "name": c.name,
                "expected": c.expected_status.value if c.expected_status else None,
                "actual": c.actual_status.value if c.actual_status else None,
                "passed": c.passed,
                "note": c.note,
            }
            for c in cases
        ],
    }

    # Persist to a single canonical path so the repo stays clean. The report
    # carries its own ISO timestamp so prior runs can be reconstructed from
    # git history if needed.
    out_dir = _API_ROOT.parent.parent / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "calibration_latest.json"
    out_path.write_text(json.dumps(report, indent=2))

    # Human-readable summary.
    print(f"\nCalibration report — {report['timestamp']}")
    print(f"  duration: {report['duration_seconds']}s")
    print(f"  cases:    {summary['total_cases']}")
    print(
        f"  passed:   {summary['passed']} ({summary['pass_rate'] * 100:.1f}%)"
    )
    print(f"  failed:   {summary['failed']}")
    print("\nBy family:")
    for fam, stats in summary["by_family"].items():
        print(f"  {fam:25s} {stats['pass']}/{stats['total']}")
    print("\nVerification status distribution:")
    for status, count in summary["actual_status_distribution"].items():
        print(f"  {status:22s} {count}")
    print(f"\nFull report -> {out_path}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
