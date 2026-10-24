"""Offline tests for the SGS client (uses respx to intercept HTTP)."""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

from ipca_nowcast.ingestion.base import HttpClient
from ipca_nowcast.ingestion.sgs import SGS_URL, SgsClient, parse_sgs_payload


def test_parse_sgs_payload(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "sgs_433.json").read_text(encoding="utf-8"))
    points = parse_sgs_payload(payload)
    assert len(points) == len(payload)
    assert points[0] == (dt.date(2020, 1, 1), Decimal("0.21"))


@respx.mock
def test_sgs_fetch_single_window(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "sgs_433.json").read_text(encoding="utf-8"))
    url = SGS_URL.format(code="433")
    route = respx.get(url).mock(return_value=httpx.Response(200, json=payload))
    client = SgsClient(http=HttpClient(max_retries=1))
    points = client.fetch("433", dt.date(2020, 1, 1), dt.date(2024, 10, 31), window_years=10)
    assert route.called
    assert len(points) == len(payload)
    assert points[0][0] < points[-1][0]


@respx.mock
def test_sgs_fetch_windows_multiple_calls() -> None:
    url = SGS_URL.format(code="1")
    first_payload = [{"data": "02/01/2015", "valor": "3.14"}]
    second_payload = [{"data": "02/01/2024", "valor": "4.92"}]
    responses = iter([first_payload, second_payload])
    respx.get(url).mock(side_effect=lambda req: httpx.Response(200, json=next(responses)))
    client = SgsClient(http=HttpClient(max_retries=1))
    points = client.fetch("1", dt.date(2015, 1, 1), dt.date(2024, 12, 31), window_years=5)
    assert len(points) == 2
    assert points[0][0] == dt.date(2015, 1, 2)


@respx.mock
def test_sgs_404_returns_empty() -> None:
    url = SGS_URL.format(code="999999")
    respx.get(url).mock(return_value=httpx.Response(404))
    client = SgsClient(http=HttpClient(max_retries=1))
    points = client.fetch("999999", dt.date(2024, 1, 1), dt.date(2024, 2, 1))
    assert points == []


@respx.mock
def test_sgs_retries_on_transient_error() -> None:
    url = SGS_URL.format(code="433")
    responses = iter([httpx.Response(503), httpx.Response(200, json=[])])
    respx.get(url).mock(side_effect=lambda req: next(responses))
    client = SgsClient(http=HttpClient(max_retries=3))
    out = client.fetch("433", dt.date(2024, 1, 1), dt.date(2024, 2, 1))
    assert out == []


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ([{"data": "01/01/2020", "valor": "0,21"}], Decimal("0.21")),
        ([{"data": "01/01/2020", "valor": 0.21}], Decimal("0.21")),
        ([{"data": "01/01/2020", "valor": "n/a"}], None),
    ],
)
def test_parse_sgs_value_variants(
    payload: list[dict[str, str | float]], expected: Decimal | None
) -> None:
    points = parse_sgs_payload(payload)
    assert points[0][1] == expected
