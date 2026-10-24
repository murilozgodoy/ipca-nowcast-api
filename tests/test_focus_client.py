"""Offline tests for the Focus client."""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

import httpx
import respx

from ipca_nowcast.ingestion.base import HttpClient
from ipca_nowcast.ingestion.focus import FOCUS_BASE, FocusClient, parse_focus_payload


def test_parse_focus_payload(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "focus.json").read_text(encoding="utf-8"))
    rows = parse_focus_payload(payload)
    assert len(rows) == 6
    r = rows[0]
    assert r["indicator"] == "IPCA"
    assert r["reference_date"] == dt.date(2024, 11, 1)
    assert r["collected_at"] == dt.date(2024, 10, 1)
    assert r["median"] == Decimal("0.43")


@respx.mock
def test_focus_fetch_single_page(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "focus.json").read_text(encoding="utf-8"))
    respx.get(FOCUS_BASE).mock(return_value=httpx.Response(200, json=payload))
    client = FocusClient(http=HttpClient(max_retries=1))
    rows = client.fetch_ipca_monthly(start_date=dt.date(2024, 1, 1))
    assert len(rows) == 6


@respx.mock
def test_focus_pagination_stops_when_batch_small() -> None:
    pages = iter(
        [
            {
                "value": [{"Indicador": "IPCA", "Data": "2024-10-01", "DataReferencia": "11/2024"}]
                * 2
            },
            {"value": []},
        ]
    )
    respx.get(FOCUS_BASE).mock(side_effect=lambda req: httpx.Response(200, json=next(pages)))
    client = FocusClient(http=HttpClient(max_retries=1))
    rows = client.fetch_ipca_monthly(top=2)
    assert len(rows) == 2
