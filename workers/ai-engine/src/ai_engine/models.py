from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GenerationTask(Base):
    __tablename__ = "generation_tasks"
    __table_args__ = {"schema": "content"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    campaign_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_formats: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class GenerationRun(Base):
    __tablename__ = "generation_runs"
    __table_args__ = {"schema": "content"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    campaign_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DraftRevision(Base):
    __tablename__ = "draft_revisions"
    __table_args__ = {"schema": "content"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )


class QaFeedback(Base):
    __tablename__ = "qa_feedback"
    __table_args__ = {"schema": "content"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )


class RepositoryArticle(Base):
    __tablename__ = "articles"
    __table_args__ = {"schema": "repository"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    campaign_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    task_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ProcessedEventLog(Base):
    __tablename__ = "processed_event_log"
    __table_args__ = {"schema": "audit"}

    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    event_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    consumer_name: Mapped[str] = mapped_column(String, primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )


class EventReceipt(Base):
    __tablename__ = "event_receipts"
    __table_args__ = {"schema": "audit"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    organization_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    event_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    consumer_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
