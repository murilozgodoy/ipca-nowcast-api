"""SQLAlchemy models for the macro nowcasting toolkit."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ipca_nowcast.db.base import Base


class Series(Base):
    """A macroeconomic time series registered in `config/series.yaml`."""

    __tablename__ = "series"
    __table_args__ = (UniqueConstraint("code", name="uq_series_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    frequency: Mapped[str] = mapped_column(String(16), nullable=False)
    publication_lag_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_target: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    observations: Mapped[list[Observation]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )


class Observation(Base):
    """A single data point for a series."""

    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("series_id", "reference_date", name="uq_observation_series_date"),
        Index("ix_observation_series_date", "series_id", "reference_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(
        ForeignKey("series.id", ondelete="CASCADE"), nullable=False
    )
    reference_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    ingested_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    series: Mapped[Series] = relationship(back_populates="observations")


class FocusExpectation(Base):
    """BCB Olinda Focus survey — monthly IPCA expectations (median consensus)."""

    __tablename__ = "focus_expectations"
    __table_args__ = (
        UniqueConstraint(
            "indicator",
            "reference_date",
            "collected_at",
            "base_calculo",
            name="uq_focus_point",
        ),
        Index(
            "ix_focus_ref_collected",
            "indicator",
            "reference_date",
            "collected_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicator: Mapped[str] = mapped_column(String(32), nullable=False, default="IPCA")
    reference_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    collected_at: Mapped[dt.date] = mapped_column(Date, nullable=False)
    base_calculo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    median: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    mean: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    std_dev: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    n_respondents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ingested_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Forecast(Base):
    """A single model forecast for a reference month."""

    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint(
            "model",
            "origin_date",
            "reference_date",
            "horizon",
            name="uq_forecast_point",
        ),
        Index("ix_forecast_model_origin", "model", "origin_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    origin_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    reference_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    prediction: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    pi_lower: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    pi_upper: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BacktestResult(Base):
    """Aggregated backtest metrics for a (model, horizon, subperiod) triple."""

    __tablename__ = "backtest_results"
    __table_args__ = (
        UniqueConstraint(
            "model",
            "horizon",
            "subperiod",
            name="uq_backtest_group",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)
    subperiod: Mapped[str] = mapped_column(String(32), nullable=False, default="full")
    n: Mapped[int] = mapped_column(Integer, nullable=False)
    rmse: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    mae: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    bias: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    rmse_vs_focus: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    dm_stat_vs_focus: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    dm_pvalue_vs_focus: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IngestionRun(Base):
    """Audit log of ingestion / pipeline runs."""

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rows_affected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
