"""Shared helpers for options calculators.

The most important thing this module does: normalize time-to-expiry to an
integer number of days. QuantLib is date-based and can only represent expiry
in whole days, so we round at the boundary and feed BOTH calculators the same
canonical T. This way the cross-method check measures real numerical agreement
between methods, not date-rounding artefacts.
"""

from __future__ import annotations

DAYS_PER_YEAR = 365.0


def canonical_days(time_to_expiry_years: float) -> int:
    """Round a year-fraction T to the nearest whole number of days.

    Clamped to >=1 so we never produce a same-day expiry.
    """
    return max(1, int(round(time_to_expiry_years * DAYS_PER_YEAR)))


def canonical_time(time_to_expiry_years: float) -> float:
    """Year-fraction corresponding to `canonical_days(T)`. Both calculators
    should price against this, not the raw input T."""
    return canonical_days(time_to_expiry_years) / DAYS_PER_YEAR
