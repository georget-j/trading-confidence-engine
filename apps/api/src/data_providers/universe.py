"""Bundled hedging universe — large-caps, sector ETFs, asset-class ETFs.

Loaded once at process start from ``data/universe.json``. The hedge finder
scans this universe for anti-correlations against a user's concentrated
sectors. Phase 7d is the only consumer today; Phase 7e (peer comparison)
reuses the same loader.

Refreshing the universe is a manual operation (run a script that pulls
yfinance metadata for each ticker, dumps the JSON). We don't auto-refresh
at runtime because the data is stable on a weekly cadence and we don't
want a startup network dependency.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from importlib import resources

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class UniverseEntry:
    ticker: str
    name: str
    sector: str
    kind: str  # "etf" | "stock"


def load_universe() -> list[UniverseEntry]:
    """Read the bundled universe JSON from disk (cached at import time)."""
    return _UNIVERSE


def universe_by_ticker() -> dict[str, UniverseEntry]:
    """Indexed lookup by ticker symbol."""
    return _BY_TICKER


def _load() -> list[UniverseEntry]:
    try:
        with (
            resources.files("src.data_providers.data")
            .joinpath("universe.json")
            .open("r", encoding="utf-8") as fh
        ):
            blob = json.load(fh)
    except FileNotFoundError as exc:  # pragma: no cover
        raise RuntimeError(
            "universe.json missing — run `make refresh-universe`"
        ) from exc

    raw_tickers = blob.get("tickers", [])
    entries: list[UniverseEntry] = []
    for row in raw_tickers:
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker:
            continue
        entries.append(
            UniverseEntry(
                ticker=ticker,
                name=str(row.get("name", ticker)),
                sector=str(row.get("sector", "Unknown")),
                kind=str(row.get("kind", "stock")),
            )
        )
    if not entries:
        raise RuntimeError("universe.json contains no tickers")
    LOG.info("Loaded universe of %d tickers", len(entries))
    return entries


_UNIVERSE: list[UniverseEntry] = _load()
_BY_TICKER: dict[str, UniverseEntry] = {e.ticker: e for e in _UNIVERSE}
