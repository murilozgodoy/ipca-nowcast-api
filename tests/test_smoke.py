"""Smoke tests. Keep these green at all times."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ipca_nowcast import __version__
from ipca_nowcast.api.main import app
from ipca_nowcast.cli.main import app as cli_app


def test_package_has_version() -> None:
    assert __version__


def test_health_endpoint_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__


def test_cli_registered() -> None:
    assert cli_app.info.name == "macro"
