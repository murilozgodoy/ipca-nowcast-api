"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-23

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "series",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("frequency", sa.String(length=16), nullable=False),
        sa.Column("publication_lag_days", sa.Integer(), nullable=False),
        sa.Column("is_target", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_series"),
        sa.UniqueConstraint("code", name="uq_series_code"),
    )
    op.create_index("ix_series_code", "series", ["code"])

    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("series_id", sa.Integer(), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(20, 8), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["series_id"], ["series.id"], name="fk_observations_series_id_series", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_observations"),
        sa.UniqueConstraint("series_id", "reference_date", name="uq_observation_series_date"),
    )
    op.create_index("ix_observation_series_date", "observations", ["series_id", "reference_date"])

    op.create_table(
        "focus_expectations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("indicator", sa.String(length=32), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("collected_at", sa.Date(), nullable=False),
        sa.Column("base_calculo", sa.Integer(), nullable=False),
        sa.Column("median", sa.Numeric(20, 8), nullable=True),
        sa.Column("mean", sa.Numeric(20, 8), nullable=True),
        sa.Column("std_dev", sa.Numeric(20, 8), nullable=True),
        sa.Column("n_respondents", sa.Integer(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_focus_expectations"),
        sa.UniqueConstraint(
            "indicator",
            "reference_date",
            "collected_at",
            "base_calculo",
            name="uq_focus_point",
        ),
    )
    op.create_index(
        "ix_focus_ref_collected",
        "focus_expectations",
        ["indicator", "reference_date", "collected_at"],
    )

    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("origin_date", sa.Date(), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("prediction", sa.Numeric(20, 8), nullable=False),
        sa.Column("pi_lower", sa.Numeric(20, 8), nullable=True),
        sa.Column("pi_upper", sa.Numeric(20, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_forecasts"),
        sa.UniqueConstraint(
            "model", "origin_date", "reference_date", "horizon", name="uq_forecast_point"
        ),
    )
    op.create_index("ix_forecast_model_origin", "forecasts", ["model", "origin_date"])

    op.create_table(
        "backtest_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("subperiod", sa.String(length=32), nullable=False),
        sa.Column("n", sa.Integer(), nullable=False),
        sa.Column("rmse", sa.Numeric(20, 8), nullable=True),
        sa.Column("mae", sa.Numeric(20, 8), nullable=True),
        sa.Column("bias", sa.Numeric(20, 8), nullable=True),
        sa.Column("rmse_vs_focus", sa.Numeric(20, 8), nullable=True),
        sa.Column("dm_stat_vs_focus", sa.Numeric(20, 8), nullable=True),
        sa.Column("dm_pvalue_vs_focus", sa.Numeric(20, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backtest_results"),
        sa.UniqueConstraint("model", "horizon", "subperiod", name="uq_backtest_group"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_affected", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_runs"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_runs")
    op.drop_table("backtest_results")
    op.drop_index("ix_forecast_model_origin", table_name="forecasts")
    op.drop_table("forecasts")
    op.drop_index("ix_focus_ref_collected", table_name="focus_expectations")
    op.drop_table("focus_expectations")
    op.drop_index("ix_observation_series_date", table_name="observations")
    op.drop_table("observations")
    op.drop_index("ix_series_code", table_name="series")
    op.drop_table("series")
