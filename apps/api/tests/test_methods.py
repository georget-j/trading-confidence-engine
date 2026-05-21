"""Method catalog tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app
from src.core.schemas import CalcFamily
from src.kb import METHOD_CATALOG

client = TestClient(app)


def test_catalog_covers_every_calculator() -> None:
    """Every calculator referenced by the routes should have a catalog entry."""
    known_ids = {m.calculator_id for m in METHOD_CATALOG}
    expected = {
        "py_vollib_bsm_closed_form",
        "quantlib_binomial_lr",
        "historical_var",
        "parametric_var",
        "monte_carlo_var",
        "mean_variance_qp",
        "max_sharpe_qp",
    }
    missing = expected - known_ids
    assert not missing, f"Catalog missing: {missing}"


def test_methods_endpoint_returns_full_catalog() -> None:
    r = client.get("/api/methods")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == len(METHOD_CATALOG)
    # Spot-check fields are present.
    for entry in data:
        for k in (
            "calculator_id",
            "family",
            "method_name",
            "one_line",
            "long_description",
            "inputs_required",
            "domain_of_validity",
            "domain_limits",
            "invariants_checked",
            "cost",
            "independent_methods",
        ):
            assert k in entry, f"Missing field {k} on {entry.get('calculator_id')}"


def test_methods_endpoint_filters_by_family() -> None:
    r = client.get(
        "/api/methods", params={"family": CalcFamily.OPTIONS_PRICING.value}
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 2  # both BSM closed-form and binomial
    assert all(m["family"] == "options_pricing" for m in data)


def test_invalid_family_returns_422() -> None:
    r = client.get("/api/methods", params={"family": "nonsense"})
    assert r.status_code == 422


def test_independent_methods_cross_reference_correctly() -> None:
    """When method A lists B as 'independent', B should also list A."""
    ids = {m.calculator_id: m for m in METHOD_CATALOG}
    for m in METHOD_CATALOG:
        for other_id in m.independent_methods:
            assert other_id in ids, f"{m.calculator_id} refs unknown {other_id}"
            other = ids[other_id]
            assert m.calculator_id in other.independent_methods, (
                f"{other_id} doesn't reciprocate independence with {m.calculator_id}"
            )
