"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from src.core.schemas import OptionsPricingRequest, OptionType


@pytest.fixture
def atm_call_30d() -> OptionsPricingRequest:
    """Classic at-the-money 30-day call (SPY-like)."""
    return OptionsPricingRequest(
        spot=450.0,
        strike=450.0,
        time_to_expiry_years=30 / 365,
        volatility=0.18,
        risk_free_rate=0.05,
        dividend_yield=0.013,
        option_type=OptionType.CALL,
    )


@pytest.fixture
def atm_put_30d() -> OptionsPricingRequest:
    """Same parameters as atm_call_30d but a put — used for parity tests."""
    return OptionsPricingRequest(
        spot=450.0,
        strike=450.0,
        time_to_expiry_years=30 / 365,
        volatility=0.18,
        risk_free_rate=0.05,
        dividend_yield=0.013,
        option_type=OptionType.PUT,
    )
