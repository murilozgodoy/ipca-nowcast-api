"""Client for IBGE SIDRA — IPCA by groups (table 7060) and others.

Table 7060 — ``IPCA - Variação mensal, acumulada em 12 meses e peso mensal``
by Grupo/Subgrupo/Item/Subitem. We fetch the monthly variation for the
top-level groups and expose it as a flat time series per group.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ipca_nowcast.ingestion.base import HttpClient
from ipca_nowcast.logging import get_logger

_logger = get_logger(__name__)

SIDRA_BASE = "https://apisidra.ibge.gov.br/values"

# Top-level IPCA groups (c315 category codes in table 7060).
IPCA_GROUPS: dict[str, str] = {
    "7170": "Alimentação e bebidas",
    "7445": "Habitação",
    "7486": "Artigos de residência",
    "7558": "Vestuário",
    "7625": "Transportes",
    "7660": "Saúde e cuidados pessoais",
    "7712": "Despesas pessoais",
    "7766": "Educação",
    "7786": "Comunicação",
}


@dataclass(frozen=True)
class GroupPoint:
    group_code: str
    group_name: str
    reference_date: dt.date
    monthly_pct: Decimal | None


def _parse_period(period: str) -> dt.date | None:
    """SIDRA 'D2C' field is YYYYMM (e.g. '202410')."""
    if not period or len(period) < 6:
        return None
    try:
        return dt.date(int(period[:4]), int(period[4:6]), 1)
    except (ValueError, TypeError):
        return None


def _parse_br_decimal(value: str) -> Decimal | None:
    if value in (None, "", "-", "..."):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        return None


class SidraClient:
    """Thin wrapper around apisidra.ibge.gov.br."""

    def __init__(self, http: HttpClient | None = None, cache_dir: Path | None = None) -> None:
        self.http = http or HttpClient(cache_dir=cache_dir)

    def fetch(self, path: str, use_cache: bool = False) -> list[dict[str, Any]]:
        url = f"{SIDRA_BASE}{path}" if path.startswith("/") else f"{SIDRA_BASE}/{path}"
        payload = self.http.get_json(url, use_cache=use_cache) or []
        return list(payload) if isinstance(payload, list) else []

    def fetch_ipca_groups(
        self,
        start: dt.date | None = None,
        end: dt.date | None = None,
        use_cache: bool = False,
    ) -> list[GroupPoint]:
        """Fetch IPCA monthly variation by group (table 7060, variable 63)."""
        groups_csv = ",".join(IPCA_GROUPS.keys())
        period = "all"
        if start and end:
            period = f"{start.year}{start.month:02d}-{end.year}{end.month:02d}"
        path = f"/t/7060/n1/all/v/63/p/{period}/c315/{groups_csv}/d/v63%202"
        rows = self.fetch(path, use_cache=use_cache)
        return parse_ipca_groups_payload(rows)


def parse_ipca_groups_payload(rows: list[dict[str, Any]]) -> list[GroupPoint]:
    """Normalise a SIDRA table-7060 payload to typed ``GroupPoint`` rows."""
    out: list[GroupPoint] = []
    for row in rows:
        period = row.get("D2C") or row.get("d2c") or ""
        group_code = row.get("D3C") or row.get("d3c") or ""
        group_name = row.get("D3N") or row.get("d3n") or IPCA_GROUPS.get(group_code, group_code)
        raw_value = row.get("V") or row.get("v") or ""
        if not period or not group_code:
            continue
        if raw_value == "Valor":
            # Header row that SIDRA prepends — skip.
            continue
        ref = _parse_period(period)
        if ref is None:
            continue
        out.append(
            GroupPoint(
                group_code=str(group_code),
                group_name=str(group_name),
                reference_date=ref,
                monthly_pct=_parse_br_decimal(str(raw_value)),
            )
        )
    _logger.info("sidra_groups_parsed", n=len(out))
    return out
