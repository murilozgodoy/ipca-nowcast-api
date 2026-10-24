"""Tests for the series.yaml registry loader."""

from __future__ import annotations

from pathlib import Path

from ipca_nowcast.ingestion.registry import load_registry


def test_load_registry_from_config() -> None:
    specs = load_registry(Path("config/series.yaml"))
    assert specs, "registry should not be empty"
    target = next((s for s in specs if s.is_target), None)
    assert target is not None, "at least one series must be flagged as target"
    assert target.code == "sgs.433"
    assert all(s.publication_lag_days >= 0 for s in specs)
