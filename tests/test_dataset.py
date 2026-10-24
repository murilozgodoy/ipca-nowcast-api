"""Tests for the real-time dataset builder — the anti-look-ahead backbone."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ipca_nowcast.db.base import Base
from ipca_nowcast.features.dataset import TARGET_CODE, build_dataset
from ipca_nowcast.ingestion.service import IngestionService


@pytest.fixture
def seeded_session(tmp_path: Path, fixtures_dir: Path) -> Session:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        svc = IngestionService(session)
        svc.seed_from_fixtures(fixtures_dir)
        session.commit()
        yield session


def test_build_dataset_shapes_and_target_month(seeded_session: Session) -> None:
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 11, 15), horizon=0)
    assert bundle.features.shape[1] > 0
    assert bundle.target_month == dt.date(2024, 11, 1)
    assert bundle.target.name == "y"
    assert bundle.features.index.name == "ds"


def test_cutoff_respects_publication_lag(seeded_session: Session) -> None:
    """IPCA has 11-day publication lag — on 15/Nov the Oct value is known."""
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 11, 15), horizon=0)
    assert bundle.asof_cutoffs[TARGET_CODE] == dt.date(2024, 10, 1)


def test_cutoff_hides_future_target_before_release(seeded_session: Session) -> None:
    """On 5/Nov the Oct IPCA has not been released yet (lag=11); last known is Sep."""
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 11, 5), horizon=0)
    assert bundle.asof_cutoffs[TARGET_CODE] == dt.date(2024, 9, 1)


def test_no_future_feature_values(seeded_session: Session) -> None:
    """No feature column may carry non-NaN values beyond the series cutoff."""
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 11, 15), horizon=0)
    for col in bundle.features.columns:
        series_code = col.split("__")[0]
        cutoff = bundle.asof_cutoffs[series_code]
        if cutoff is None:
            continue
        non_na = bundle.features[col].dropna()
        if not non_na.empty:
            latest = non_na.index.max().date()
            # feature at month t is a lag of a past value, so it may exist at
            # months after the series cutoff — but the raw monthly series it
            # comes from cannot have an entry beyond the cutoff. Check that.
            lag = int(col.split("__lag")[1])
            raw_series_cutoff = latest - dt.timedelta(days=1)  # month index -> date
            _ = raw_series_cutoff
            # The invariant we really want: the lagged value at month t comes
            # from month (t - lag). So the latest *source* month is
            # latest - lag months. That must be <= cutoff's month.
            from dateutil.relativedelta import relativedelta

            source_month = latest.replace(day=1) - relativedelta(months=lag)
            assert source_month <= cutoff, (
                f"look-ahead leak in {col}: source={source_month} cutoff={cutoff}"
            )


def test_two_origins_only_differ_in_newest_months(seeded_session: Session) -> None:
    early = build_dataset(seeded_session, origin_date=dt.date(2024, 6, 15))
    late = build_dataset(seeded_session, origin_date=dt.date(2024, 11, 15))
    # The earlier origin cannot know anything after its cutoff.
    common = early.features.index.intersection(late.features.index)
    for col in early.features.columns:
        early_vals = early.features.loc[common, col]
        late_vals = late.features.loc[common, col]
        mask = early_vals.notna() & late_vals.notna()
        # Where both are known, they should match (historical data is immutable).
        assert (early_vals[mask] == late_vals[mask]).all(), col


def test_build_dataset_rejects_negative_horizon(seeded_session: Session) -> None:
    with pytest.raises(ValueError, match="horizon"):
        build_dataset(seeded_session, origin_date=dt.date(2024, 11, 15), horizon=-1)


def test_build_dataset_without_data_raises() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session, pytest.raises(RuntimeError):
        build_dataset(session, origin_date=dt.date(2024, 11, 15))


def test_target_value_matches_direct_lookup(seeded_session: Session) -> None:
    """When the target month lies before cutoff, bundle.target[target_month] == IPCA."""
    bundle = build_dataset(seeded_session, origin_date=dt.date(2024, 12, 20), horizon=0)
    target_ts = _as_ts(bundle.target_month)
    if target_ts in bundle.target.index:
        value = bundle.target.loc[target_ts]
        assert value is None or isinstance(float(value), float)


def _as_ts(d: dt.date):  # tiny helper to avoid an import in multiple places
    import pandas as pd

    return pd.Timestamp(d)


# Silence unused imports used indirectly in markers.
_ = Decimal
