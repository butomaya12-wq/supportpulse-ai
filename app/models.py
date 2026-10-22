from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    watermark: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    health: Mapped[str] = mapped_column(String(24), default="UNKNOWN")


class SourceEvent(Base):
    __tablename__ = "source_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (UniqueConstraint("tenant_id", "source_id", "external_id", name="unique_provider_event"),)


class Commitment(Base):
    __tablename__ = "commitments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), default="send_quote")
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    basis_event_id: Mapped[int] = mapped_column(ForeignKey("source_events.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(20), default="APPROVED")
    __table_args__ = (UniqueConstraint("tenant_id", "basis_event_id", "action_type", name="unique_approved_promise"),)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    commitment_id: Mapped[int] = mapped_column(ForeignKey("commitments.id"), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_event_id: Mapped[int | None] = mapped_column(ForeignKey("source_events.id"), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class CorrectiveAction(Base):
    __tablename__ = "corrective_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), nullable=False, unique=True)
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(40), default="OPEN")
    proof_event_id: Mapped[int | None] = mapped_column(ForeignKey("source_events.id"), nullable=True)


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(70), nullable=False)
    old_state: Mapped[str | None] = mapped_column(String(40))
    new_state: Mapped[str | None] = mapped_column(String(40))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    note: Mapped[str | None] = mapped_column(Text)
