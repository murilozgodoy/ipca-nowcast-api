"""Offline tests for the SIDRA IPCA groups parser."""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

import httpx
import respx

from ipca_nowcast.ingestion.base import HttpClient
from ipca_nowcast.ingestion.sidra import SIDRA_BASE, SidraClient, parse_ipca_groups_payload


def test_parse_ipca_groups_skips_header_row(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "sidra_ipca_groups.json").read_text(encoding="utf-8"))
    points = parse_ipca_groups_payload(payload)
    # Three months x 9 groups = 27 rows; the header row is skipped.
    assert len(points) == 27
    first = points[0]
    assert first.reference_date == dt.date(2024, 8, 1)
    assert first.group_code == "7170"
    assert first.monthly_pct == Decimal("0.76")


def test_parse_handles_sentinel_values() -> None:
    rows = [
        {"D2C": "202410", "D3C": "7766", "D3N": "Educação", "V": "..."},
        {"D2C": "202410", "D3C": "7170", "D3N": "Alimentação", "V": "0,46"},
    ]
    points = parse_ipca_groups_payload(rows)
    assert len(points) == 2
    assert points[0].monthly_pct is None
    assert points[1].monthly_pct == Decimal("0.46")


@respx.mock
def test_sidra_client_fetches_ipca_groups(fixtures_dir: Path) -> None:
    payload = json.loads((fixtures_dir / "sidra_ipca_groups.json").read_text(encoding="utf-8"))
    respx.get(url__startswith=SIDRA_BASE).mock(return_value=httpx.Response(200, json=payload))
    client = SidraClient(http=HttpClient(max_retries=1))
    points = client.fetch_ipca_groups()
    assert len(points) == 27
    assert all(p.monthly_pct is None or isinstance(p.monthly_pct, Decimal) for p in points)
