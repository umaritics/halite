"""Record Integrity tables; imported by the model registry so create_all makes them."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .identity import Base, _uuid, utc_now


class ReviewDecision(Base):
    """One human accept or reject of a proposed supersession, kept with the model's view at the time.

    The graph holds the current state; this table keeps every decision so the model can be
    calibrated against reviewers later, even after a record is decided again.
    """

    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    record_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    prior_record_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)  # "accepted" | "rejected"
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    reviewer_role: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    model_p: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
