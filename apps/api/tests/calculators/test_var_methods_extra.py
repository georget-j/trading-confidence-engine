"""Tests for the Cornish-Fisher + Bootstrap VaR methods."""

from __future__ import annotations

import numpy as np

from src.calculators.risk import bootstrap, cornish_fisher
from src.calculators.risk.runner import run_var_calculators
from src.core.schemas import VaRRequest


def _normal_returns(n: int = 504, mu: float = 0.0005, sigma: float = 0.01) -> list[float]:
    rng = np.random.default_rng(42)
    return rng.normal(mu, sigma, size=n).tolist()


def _fat_tailed_returns(n: int = 504) -> list[float]:
    """5% draws from a heavy left tail mixed into a near-normal core."""
    rng = np.random.default_rng(42)
    core = rng.normal(0.0005, 0.01, size=int(n * 0.95))
    tail = rng.normal(-0.03, 0.02, size=n - core.size)
    arr = np.concatenate([core, tail])
    rng.shuffle(arr)
    return arr.tolist()


def _req(confidence: float = 0.99) -> VaRRequest:
    return VaRRequest(
        ticker="TEST",
        lookback_days=504,
        portfolio_value=50_000.0,
        confidence_level=confidence,
        horizon_days=1,
    )


# ---- Cornish-Fisher ---------------------------------------------------------


def test_cornish_fisher_matches_parametric_on_normal_sample() -> None:
    """On a clean Gaussian sample CF should reduce to plain parametric."""
    from src.calculators.risk import parametric

    returns = _normal_returns()
    req = _req()
    cf = cornish_fisher.compute(req, returns)
    pm = parametric.compute(req, returns)
    assert cf.succeeded and pm.succeeded
    # Skew + excess kurtosis are ~0 → CF correction is ~0 → CF VaR ≈ parametric.
    rel = abs(cf.payload.var_loss - pm.payload.var_loss) / pm.payload.var_loss
    assert rel < 0.05, f"CF diverged from parametric on Gaussian: {rel:.4f}"


def test_cornish_fisher_exceeds_parametric_on_fat_tails() -> None:
    """On a fat-tailed sample CF should report MORE loss than plain parametric."""
    from src.calculators.risk import parametric

    returns = _fat_tailed_returns()
    req = _req()
    cf = cornish_fisher.compute(req, returns)
    pm = parametric.compute(req, returns)
    assert cf.succeeded and pm.succeeded
    assert cf.payload.var_loss > pm.payload.var_loss, (
        f"CF should exceed parametric on fat tails: cf={cf.payload.var_loss} pm={pm.payload.var_loss}"
    )


def test_cornish_fisher_cvar_at_least_var() -> None:
    """CVaR is by definition ≥ VaR (it's the mean of the tail beyond VaR)."""
    returns = _fat_tailed_returns()
    cf = cornish_fisher.compute(_req(), returns)
    assert cf.succeeded
    assert cf.payload.cvar_loss >= cf.payload.var_loss


# ---- Bootstrap --------------------------------------------------------------


def test_bootstrap_is_deterministic() -> None:
    """Fixed-seed bootstrap must produce identical results across calls."""
    returns = _fat_tailed_returns()
    req = _req()
    r1 = bootstrap.compute(req, returns)
    r2 = bootstrap.compute(req, returns)
    assert r1.succeeded and r2.succeeded
    assert r1.payload.var_loss == r2.payload.var_loss
    assert r1.payload.cvar_loss == r2.payload.cvar_loss


def test_bootstrap_close_to_historical_median() -> None:
    """Bootstrap median quantile should be close to historical empirical quantile."""
    from src.calculators.risk import historical

    returns = _fat_tailed_returns()
    req = _req()
    bs = bootstrap.compute(req, returns)
    hist = historical.compute(req, returns)
    assert bs.succeeded and hist.succeeded
    # Resampled median ≈ point estimate within 15% on n=504 sample.
    rel = abs(bs.payload.var_loss - hist.payload.var_loss) / hist.payload.var_loss
    assert rel < 0.15, f"Bootstrap diverged from historical: {rel:.4f}"


def test_bootstrap_cvar_at_least_var() -> None:
    returns = _fat_tailed_returns()
    bs = bootstrap.compute(_req(), returns)
    assert bs.succeeded
    assert bs.payload.cvar_loss >= bs.payload.var_loss


# ---- Runner -----------------------------------------------------------------


def test_runner_returns_five_methods() -> None:
    """The VaR runner now returns 5 methods in a documented order."""
    returns = _normal_returns()
    results = run_var_calculators(_req(), returns)
    ids = [r.calculator_id for r in results]
    assert ids == [
        "historical_var",
        "parametric_var",
        "monte_carlo_var",
        "cornish_fisher_var",
        "bootstrap_var",
    ]
    assert all(r.succeeded for r in results), [r.error for r in results if not r.succeeded]
