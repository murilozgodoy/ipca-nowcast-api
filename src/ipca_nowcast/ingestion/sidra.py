"""Minimal client for IBGE SIDRA (used optionally in F11 for IPCA by groups)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ipca_nowcast.ingestion.base import HttpClient

SIDRA_BASE = "https://apisidra.ibge.gov.br/values"


class SidraClient:
    def __init__(
        self,
        http: HttpClient | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        self.http = http or HttpClient(cache_dir=cache_dir)

    def fetch(self, path: str, use_cache: bool = False) -> list[dict[str, Any]]:
        url = f"{SIDRA_BASE}{path}" if path.startswith("/") else f"{SIDRA_BASE}/{path}"
        payload = self.http.get_json(url, use_cache=use_cache) or []
        return list(payload) if isinstance(payload, list) else []
