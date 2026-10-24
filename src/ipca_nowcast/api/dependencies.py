"""FastAPI dependency wrappers around the DB session."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from ipca_nowcast.db.session import get_sessionmaker


def db_session() -> Iterator[Session]:
    maker = get_sessionmaker()
    session = maker()
    try:
        yield session
    finally:
        session.close()
