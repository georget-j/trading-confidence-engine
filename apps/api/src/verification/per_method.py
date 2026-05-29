"""Per-method status aggregator.

Builds one ``PerMethodStatus`` row per calculator in a result list. This is
the data the frontend's MethodScorecard renders — one line per method showing
whether it ran, what value it produced, whether it agreed with peers, and
which invariants its payload satisfied.

The aggregator is family-agnostic: callers supply a value-extractor, an
invariant runner that operates on a single result, the cross-check (so we
know which methods participated in the headline comparison and what
tolerance applied), and an optional sensitivity map for portfolio.

The pairwise divergence logic mirrors ``cross_method`` / ``cross_method_var``:
two methods agree iff their absolute or relative delta is within tolerance.
"""

from __future__ import annotations

from collections.abc import Callable

from src.core.schemas import (
    AgreementStatus,
    CalculatorResult,
    CrossMethodCheck,
    InvariantCheck,
    PerMethodStatus,
)

# Re-export the union types under shorter aliases for readability below.
ValueExtractor = Callable[[CalculatorResult], float | None]
InvariantRunner = Callable[[CalculatorResult], list[InvariantCheck]]


def build_per_method_status(
    *,
    results: list[CalculatorResult],
    cross_check: CrossMethodCheck | None,
    value_extractor: ValueExtractor,
    invariant_runner: InvariantRunner | None = None,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
    sensitivity_passed: dict[str, bool] | None = None,
) -> list[PerMethodStatus]:
    """Build one row per calculator result.

    - Methods NOT in ``cross_check.methods_compared`` get ``agreement_status =
      n/a`` (they ran but didn't gate the headline verdict).
    - Methods that failed (``ran=False``) get ``agreement_status = n/a``,
      no value, the error string, and an empty invariants list.
    - When ``cross_check`` is ``None`` (only one method, or none), every
      successful method is marked ``n/a``.

    The pairwise-divergence calculation uses the same tolerance semantics as
    the family's ``cross_check_*`` function: a pair AGREES iff its absolute
    or relative delta is within tolerance.
    """
    headline_ids: set[str] = (
        set(cross_check.methods_compared) if cross_check is not None else set()
    )

    # Pre-compute the per-method value once so the pairwise loop is cheap.
    values: dict[str, float | None] = {
        r.calculator_id: value_extractor(r) if r.succeeded else None for r in results
    }

    rows: list[PerMethodStatus] = []
    for r in results:
        method_id = r.calculator_id
        ran = r.succeeded
        v = values.get(method_id)

        # Per-method invariants: re-run the invariant suite against this
        # single result so we get per-payload pass/fail (not just the
        # primary's). Catches the case where one method's price satisfies
        # the no-arb bound and another's doesn't.
        passed_names: list[str] = []
        failed_names: list[str] = []
        if ran and invariant_runner is not None:
            try:
                inv = invariant_runner(r)
            except Exception:
                inv = []
            for c in inv:
                (passed_names if c.passed else failed_names).append(c.name)

        # Agreement: only meaningful for methods that participated in the
        # headline cross-check.
        if not ran or cross_check is None or method_id not in headline_ids:
            agreement = AgreementStatus.NOT_APPLICABLE
            divergent_against: list[str] = []
        else:
            divergent_against = _pairwise_divergent(
                method_id=method_id,
                values=values,
                headline_ids=headline_ids,
                abs_tol=abs_tol,
                rel_tol=rel_tol,
            )
            agreement = (
                AgreementStatus.AGREES
                if not divergent_against
                else AgreementStatus.DIVERGES
            )

        rows.append(
            PerMethodStatus(
                method_id=method_id,
                method_name=r.method_name,
                ran=ran,
                value=v,
                agreement_status=agreement,
                divergent_against=divergent_against,
                invariants_passed=passed_names,
                invariants_failed=failed_names,
                sensitivity_passed=(
                    None
                    if sensitivity_passed is None
                    else sensitivity_passed.get(method_id)
                ),
                duration_ms=r.duration_ms,
                error=r.error,
            )
        )
    return rows


def _pairwise_divergent(
    *,
    method_id: str,
    values: dict[str, float | None],
    headline_ids: set[str],
    abs_tol: float,
    rel_tol: float,
) -> list[str]:
    """Return the list of headline method ids that disagree with ``method_id``."""
    a = values.get(method_id)
    if a is None:
        return []
    out: list[str] = []
    for other in sorted(headline_ids):
        if other == method_id:
            continue
        b = values.get(other)
        if b is None:
            continue
        if not _within_tol(a, b, abs_tol=abs_tol, rel_tol=rel_tol):
            out.append(other)
    return out


def _within_tol(a: float, b: float, *, abs_tol: float, rel_tol: float) -> bool:
    diff = abs(a - b)
    if diff <= abs_tol:
        return True
    denom = (abs(a) + abs(b)) / 2.0
    if denom > 0 and diff / denom <= rel_tol:
        return True
    return False
