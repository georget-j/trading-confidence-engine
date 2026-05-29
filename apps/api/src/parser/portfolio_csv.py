"""Portfolio CSV parsers.

Two parsers share a common normalised output (``list[ParsedHolding]``):

- ``parse_trading212(csv_text)`` — Trading 212's CSV export. Columns vary
  across the App and Web exports, so this looks for the union of plausible
  header names (case-insensitive).
- ``parse_generic(csv_text)`` — any CSV that has a ticker column + a shares
  column (any common alias). Optional cost_basis column.

Pure-Python; no extra dependencies. Returns structured errors via
``CSVParseError`` instead of crashing — the route surfaces these as a 422.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass


class CSVParseError(ValueError):
    """Raised when a CSV cannot be parsed into a usable holding list."""


@dataclass(frozen=True)
class ParsedHolding:
    ticker: str
    shares: float
    cost_basis: float | None
    currency: str | None


# Header aliases — PRIORITY-ORDERED lists, not sets. The first alias found in
# the CSV's header row wins. The ordering matters because Trading 212 exports
# carry both an `Instrument` (company name) and a `Ticker` column — we want
# the ticker symbol, so `ticker` MUST come before `instrument`.
_TICKER_ALIASES: tuple[str, ...] = (
    "ticker",
    "tickersymbol",
    "symbol",
    "stock",
    "instrumentsymbol",
    "isin",
    "instrument",  # last resort — Trading 212 uses this for the company name
)
_SHARES_ALIASES: tuple[str, ...] = (
    "shares",
    "quantity",
    "noofshares",
    "numberofshares",
    "qty",
    "units",
)
_COST_ALIASES: tuple[str, ...] = (
    "costbasis",
    "averageprice",
    "avgprice",
    "averageopenprice",
    "totalcost",
    "price",
)
_CURRENCY_ALIASES: tuple[str, ...] = (
    "currency",
    "ccy",
    "currencyofinstrument",
)


def parse_trading212(csv_text: str) -> list[ParsedHolding]:
    """Parse a Trading 212 CSV export into normalised holdings.

    Trading 212's holdings export uses columns like
    ``Instrument, Ticker, Quantity, Average price, Currency``. This parser
    is tolerant of both the App-style and Web-style exports.
    """
    return _parse_with_aliases(csv_text, expected_origin="Trading 212")


def parse_generic(csv_text: str) -> list[ParsedHolding]:
    """Parse any CSV with ``ticker`` + ``shares`` columns (+ optional cost_basis).

    Header names are matched case-insensitively against a small alias set so
    the user can paste from a broker that doesn't conform to one specific
    schema.
    """
    return _parse_with_aliases(csv_text, expected_origin="generic")


def _parse_with_aliases(
    csv_text: str, *, expected_origin: str
) -> list[ParsedHolding]:
    text = csv_text.strip()
    if not text:
        raise CSVParseError("CSV is empty")

    # Sniff the dialect so commas / semicolons / tabs all work.
    # `csv.Sniffer.sniff()` returns a `_csv.Dialect` instance; `get_dialect`
    # returns a `type[Dialect]`. Both are accepted by `DictReader` at runtime
    # but typeshed types them differently — cast through `Any` to keep mypy
    # happy without an `Any`-import in callers.
    from typing import Any

    sample = text[:4096]
    try:
        dialect: Any = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.get_dialect("excel")

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if reader.fieldnames is None:
        raise CSVParseError("CSV has no header row")

    header_map = {h: _normalise_header(h) for h in reader.fieldnames}
    ticker_col = _pick_column(header_map, _TICKER_ALIASES)
    shares_col = _pick_column(header_map, _SHARES_ALIASES)
    cost_col = _pick_column(header_map, _COST_ALIASES)
    currency_col = _pick_column(header_map, _CURRENCY_ALIASES)
    if ticker_col is None or shares_col is None:
        raise CSVParseError(
            f"Could not find ticker + shares columns in {expected_origin} CSV. "
            f"Headers seen: {reader.fieldnames!r}"
        )

    holdings: dict[str, ParsedHolding] = {}
    for row_idx, row in enumerate(reader, start=2):  # row 1 = header
        raw_ticker = (row.get(ticker_col) or "").strip().upper()
        if not raw_ticker:
            continue  # tolerate blank lines / partial exports
        raw_shares = (row.get(shares_col) or "").strip()
        try:
            shares = float(raw_shares.replace(",", ""))
        except ValueError as exc:
            raise CSVParseError(
                f"Row {row_idx}: shares value {raw_shares!r} is not a number"
            ) from exc
        if shares <= 0:
            # Skip closed positions — the export often lists them with 0 shares.
            continue

        cost_basis: float | None = None
        if cost_col:
            raw_cost = (row.get(cost_col) or "").strip()
            if raw_cost:
                try:
                    cost_basis = float(raw_cost.replace(",", ""))
                except ValueError:
                    cost_basis = None  # tolerate junk in this optional column

        currency: str | None = None
        if currency_col:
            raw_ccy = (row.get(currency_col) or "").strip().upper()
            currency = raw_ccy or None

        symbol = _clean_ticker(raw_ticker)
        # Aggregate duplicates (e.g. multiple lots of the same ticker).
        if symbol in holdings:
            prev = holdings[symbol]
            new_shares = prev.shares + shares
            # Weighted-average cost basis when both rows have it; otherwise
            # whichever side has a value wins (or None).
            weighted: float | None
            if prev.cost_basis is not None and cost_basis is not None:
                weighted = (
                    prev.cost_basis * prev.shares + cost_basis * shares
                ) / new_shares
            else:
                weighted = prev.cost_basis if prev.cost_basis is not None else cost_basis
            holdings[symbol] = ParsedHolding(
                ticker=symbol,
                shares=new_shares,
                cost_basis=weighted,
                currency=prev.currency or currency,
            )
        else:
            holdings[symbol] = ParsedHolding(
                ticker=symbol,
                shares=shares,
                cost_basis=cost_basis,
                currency=currency,
            )

    if not holdings:
        raise CSVParseError(
            f"{expected_origin} CSV parsed but no usable holdings were found"
        )
    return list(holdings.values())


def _normalise_header(h: str) -> str:
    return "".join(c.lower() for c in h.strip() if c.isalnum())


def _pick_column(
    header_map: dict[str, str], aliases: tuple[str, ...]
) -> str | None:
    """Return the original header that matches the highest-priority alias.

    `aliases` is priority-ordered: when more than one CSV column matches
    something in the alias list, the alias that appears earliest wins.
    """
    for alias in aliases:
        for original, normalised in header_map.items():
            if normalised == alias:
                return original
    return None


def _clean_ticker(t: str) -> str:
    """Trading 212 sometimes appends an exchange suffix like ``AAPL_US_EQ``.
    Strip everything after the first underscore unless it looks like a
    legitimate exchange code (e.g. ``BRK.B``)."""
    if "_" in t:
        return t.split("_", 1)[0]
    return t
