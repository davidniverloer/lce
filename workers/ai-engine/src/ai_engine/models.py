from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, PrimaryKeyConstraint, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    campaign_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )


class ProcessedEventLog(Base):
    __tablename__ = "processed_event_log"
    __table_args__ = (
        PrimaryKeyConstraint(
            "organization_id",
            "event_id",
            "consumer_name",
            name="processed_event_log_pkey",
        ),
    )

    organization_id: Mapped[str] = mapped_column(String, nullable=False)
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    consumer_name: Mapped[str] = mapped_column(String, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
