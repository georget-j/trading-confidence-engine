"""Method catalog routes (V4)."""

from __future__ import annotations

from fastapi import APIRouter

from src.core.schemas import CalcFamily
from src.kb import METHOD_CATALOG, MethodEntry

router = APIRouter()


@router.get("", response_model=list[MethodEntry])
def list_methods(family: CalcFamily | None = None) -> list[MethodEntry]:
    """Return the catalog of verified calculators.

    Filter by family with `?family=options_pricing` etc.
    """
    if family is None:
        return METHOD_CATALOG
    return [m for m in METHOD_CATALOG if m.family == family]
