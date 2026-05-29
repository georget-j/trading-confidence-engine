"""Tests for the Trading 212 / generic portfolio CSV parsers."""

from __future__ import annotations

import pytest

from src.parser.portfolio_csv import (
    CSVParseError,
    parse_generic,
    parse_trading212,
)


def test_trading212_parses_standard_export() -> None:
    csv_text = (
        "Instrument,Ticker,Quantity,Average price,Currency\n"
        "Apple,AAPL,10,175.32,USD\n"
        "Tesla,TSLA,5,250.10,USD\n"
        "Microsoft,MSFT,2.5,330.00,USD\n"
    )
    holdings = parse_trading212(csv_text)
    by_t = {h.ticker: h for h in holdings}
    assert set(by_t.keys()) == {"AAPL", "TSLA", "MSFT"}
    assert by_t["AAPL"].shares == 10
    assert by_t["AAPL"].cost_basis == 175.32
    assert by_t["AAPL"].currency == "USD"
    assert by_t["MSFT"].shares == 2.5


def test_trading212_aggregates_duplicate_tickers_with_weighted_cost() -> None:
    csv_text = (
        "Ticker,Quantity,Average price\n"
        "AAPL,10,100\n"
        "AAPL,30,200\n"  # weighted avg should be 175 = (10*100 + 30*200)/40
    )
    holdings = parse_trading212(csv_text)
    assert len(holdings) == 1
    h = holdings[0]
    assert h.ticker == "AAPL"
    assert h.shares == 40
    assert h.cost_basis == pytest.approx(175.0)


def test_trading212_skips_zero_share_rows() -> None:
    csv_text = (
        "Ticker,Quantity,Average price\n"
        "AAPL,10,100\n"
        "MSFT,0,330\n"  # closed position — should be ignored
    )
    holdings = parse_trading212(csv_text)
    assert [h.ticker for h in holdings] == ["AAPL"]


def test_trading212_strips_underscore_suffix() -> None:
    csv_text = (
        "Ticker,Quantity\n"
        "AAPL_US_EQ,10\n"
        "TSLA_US_EQ,5\n"
    )
    holdings = parse_trading212(csv_text)
    tickers = sorted(h.ticker for h in holdings)
    assert tickers == ["AAPL", "TSLA"]


def test_generic_parses_semicolon_delimited() -> None:
    csv_text = "symbol;qty;price\nAAPL;10;175\nTSLA;5;250\n"
    holdings = parse_generic(csv_text)
    assert {h.ticker for h in holdings} == {"AAPL", "TSLA"}


def test_empty_csv_raises() -> None:
    with pytest.raises(CSVParseError):
        parse_trading212("")


def test_csv_without_required_columns_raises() -> None:
    with pytest.raises(CSVParseError):
        parse_generic("name,age\nfoo,20\n")


def test_non_numeric_shares_raises_with_row_context() -> None:
    csv_text = "Ticker,Quantity\nAAPL,banana\n"
    with pytest.raises(CSVParseError) as exc:
        parse_trading212(csv_text)
    assert "row 2" in str(exc.value).lower()
