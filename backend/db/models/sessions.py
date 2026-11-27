"""Replayable investigation records. Identity tables remain unchanged."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .identity import Base, utc_now


def _id() -> str:
    return str(uuid.uuid4())


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'closed')", name="session_valid_status"),
        Index("ix_diagnostic_sessions_org_created", "organization_id", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    asset_id: Mapped[str | None] = mapped_column(String(36))
    asset_tail: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(160), default="Investigation")
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    outcome_part: Mapped[str | None] = mapped_column(String(200))
    outcome_jasc: Mapped[str | None] = mapped_column(String(20))
    outcome_note: Mapped[str | None] = mapped_column(Text)
    outcome_record_id: Mapped[str | None] = mapped_column(String(120))
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessionTurn(Base):
    __tablename__ = "session_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "idx", name="uq_session_turn_index"),
        CheckConstraint("idx > 0", name="session_turn_positive_index"),
        CheckConstraint("decision IN ('answer','ask','abstain','report')", name="session_turn_decision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    session_id: Mapped[str] = mapped_column(ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    user_text: Mapped[str] = mapped_column(Text)
    case_state_json: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(16))
    question_json: Mapped[str | None] = mapped_column(Text)
    answer_json: Mapped[str | None] = mapped_column(Text)
    reply_text: Mapped[str | None] = mapped_column(Text)
    llm_status: Mapped[str] = mapped_column(String(24))
    grounding_json: Mapped[str | None] = mapped_column(Text)
    ranker_mode: Mapped[str] = mapped_column(String(40))
    ranker_version: Mapped[str] = mapped_column(String(80))
    latency_ms: Mapped[int] = mapped_column(Integer)
    # Exact response and evidence text preserve replay if graph records change later.
    response_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SessionSnapshot(Base):
    __tablename__ = "session_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    turn_id: Mapped[str] = mapped_column(ForeignKey("session_turns.id", ondelete="CASCADE"), unique=True)
    hypotheses_json: Mapped[str] = mapped_column(Text)
    evidence_ids_json: Mapped[str] = mapped_column(Text)
    belief_entropy: Mapped[float | None] = mapped_column(Float)
