"""Offline tests for the ANP fuel-price parser."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from ipca_nowcast.ingestion.anp import AnpClient, parse_anp_csv


def test_parse_anp_csv_aggregates_to_monthly(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "anp_gasolina.csv").read_text(encoding="utf-8")
    monthly = parse_anp_csv(text, product="GASOLINA COMUM")
    assert len(monthly) >= 9
    # Jan 2024 has 3 weekly rows at 4.891, 4.923, 5.012 → mean ~4.942
    jan = next(m for m in monthly if m[0] == dt.date(2024, 1, 1))
    assert jan[1] is not None
    assert abs(float(jan[1]) - 4.9420) < 1e-3
    # Prices should be sorted
    dates = [m[0] for m in monthly]
    assert dates == sorted(dates)


def test_parse_anp_csv_filters_by_product(fixtures_dir: Path) -> None:
    text = (fixtures_dir / "anp_gasolina.csv").read_text(encoding="utf-8")
    none_matching = parse_anp_csv(text, product="DIESEL S10")
    assert none_matching == []


def test_anp_client_reads_file_url(fixtures_dir: Path) -> None:
    client = AnpClient()
    url = f"file://{(fixtures_dir / 'anp_gasolina.csv').as_posix()}"
    monthly = client.fetch_monthly(product="GASOLINA COMUM", url=url)
    assert len(monthly) >= 9
    assert isinstance(monthly[0][1], (Decimal, type(None)))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("06/01/2024", dt.date(2024, 1, 6)),
        ("2024-01-06", dt.date(2024, 1, 6)),
        ("garbage", None),
    ],
)
def test_internal_date_parser(raw: str, expected: dt.date | None) -> None:
    from ipca_nowcast.ingestion.anp import _parse_br_date

    assert _parse_br_date(raw) == expected
