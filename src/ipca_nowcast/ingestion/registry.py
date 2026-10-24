"""Load the `config/series.yaml` registry."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SeriesSpec:
    code: str
    external_id: str
    source: str
    name: str
    unit: str
    frequency: str
    publication_lag_days: int
    is_target: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SeriesSpec:
        return cls(
            code=str(data["code"]),
            external_id=str(data["external_id"]),
            source=str(data["source"]),
            name=str(data["name"]),
            unit=str(data["unit"]),
            frequency=str(data["frequency"]),
            publication_lag_days=int(data.get("publication_lag_days", 0)),
            is_target=bool(data.get("is_target", False)),
        )

    def as_row(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "external_id": self.external_id,
            "source": self.source,
            "name": self.name,
            "unit": self.unit,
            "frequency": self.frequency,
            "publication_lag_days": self.publication_lag_days,
            "is_target": self.is_target,
        }


def load_registry(path: Path | str = Path("config/series.yaml")) -> list[SeriesSpec]:
    file_path = Path(path)
    data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    items = data.get("series", []) if isinstance(data, dict) else []
    return [SeriesSpec.from_dict(item) for item in items]
