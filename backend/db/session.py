"""
Database engine and session factory for Halite relational store.

Supports:
  - PostgreSQL (`postgresql://...`, `postgres://...`, `postgresql+psycopg2://...`)
    for Docker Compose, dev1 VM, or Supabase PostgreSQL URI.
  - Isolated in-memory SQLite (`sqlite+pysqlite:///:memory:`) when `DEMO_MODE=true`
    and `DATABASE_URL` is unset, keeping unit tests fast and offline.
  - Honest fail-closed behavior (`mode="unconfigured"`) when `DEMO_MODE=false`
    and `DATABASE_URL` is missing.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from db.models import Base

logger = logging.getLogger(__name__)


def normalize_database_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


class RelationalStore:
    """Lifecycle wrapper holding SQLAlchemy engine, session factory, and runtime mode."""

    def __init__(self, engine: Engine | None, mode: str):
        self.engine = engine
        self.mode = mode  # "postgresql" | "sqlite" | "unconfigured"
        self._session_factory = (
            sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
            if engine is not None
            else None
        )

    @property
    def is_available(self) -> bool:
        return self._session_factory is not None

    def init_schema(self) -> None:
        if self.engine is not None:
            Base.metadata.create_all(bind=self.engine)

    def ping(self) -> bool:
        if self.engine is None:
            return False
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        if self._session_factory is None:
            raise RuntimeError(
                "Relational identity database is not configured on this server (set DATABASE_URL)."
            )
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        if self.engine is not None:
            self.engine.dispose()


def build_relational_store(settings) -> RelationalStore:
    raw_url = (getattr(settings, "DATABASE_URL", "") or "").strip()
    demo_mode = bool(getattr(settings, "DEMO_MODE", True))

    if raw_url:
        normalized = normalize_database_url(raw_url)
        if normalized.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            kwargs = (
                {"connect_args": connect_args, "poolclass": StaticPool}
                if ":memory:" in normalized
                else {"connect_args": connect_args}
            )
            engine = create_engine(normalized, future=True, **kwargs)
            store = RelationalStore(engine, mode="sqlite")
        else:
            engine = create_engine(
                normalized,
                future=True,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_recycle=1800,
            )
            store = RelationalStore(engine, mode="postgresql")
        store.init_schema()
        return store

    if demo_mode:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        store = RelationalStore(engine, mode="sqlite")
        store.init_schema()
        return store

    logger.error("DEMO_MODE=false without DATABASE_URL; user authentication DB is unconfigured")
    return RelationalStore(None, mode="unconfigured")
