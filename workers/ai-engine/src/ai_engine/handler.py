from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .models import ProcessedEventLog, Topic


@dataclass(frozen=True)
class TopicGenerationRequestedPayload:
    organization_id: str
    campaign_id: str
    niche: str


@dataclass(frozen=True)
class TopicGenerationRequestedEvent:
    event_id: str
    event_type: str
    version: str
    timestamp: datetime
    payload: TopicGenerationRequestedPayload


def parse_topic_generation_requested(raw: dict) -> TopicGenerationRequestedEvent:
    payload = raw.get("payload")

    if not isinstance(raw, dict):
        raise ValueError("Event body must be an object")

    if raw.get("eventType") != "TopicGenerationRequested":
        raise ValueError("Unsupported event type")

    if not isinstance(payload, dict):
        raise ValueError("Event payload must be an object")

    required_top_level_fields = ("eventId", "eventType", "version", "timestamp")
    required_payload_fields = ("organizationId", "campaignId", "niche")

    for field in required_top_level_fields:
        if not isinstance(raw.get(field), str) or not str(raw[field]).strip():
            raise ValueError(f"Missing required field: {field}")

    for field in required_payload_fields:
        if not isinstance(payload.get(field), str) or not str(payload[field]).strip():
            raise ValueError(f"Missing required payload field: {field}")

    return TopicGenerationRequestedEvent(
        event_id=str(raw["eventId"]),
        event_type=str(raw["eventType"]),
        version=str(raw["version"]),
        timestamp=datetime.fromisoformat(str(raw["timestamp"]).replace("Z", "+00:00")),
        payload=TopicGenerationRequestedPayload(
            organization_id=str(payload["organizationId"]),
            campaign_id=str(payload["campaignId"]),
            niche=str(payload["niche"]),
        ),
    )


def process_topic_generation_requested(
    session_factory: sessionmaker,
    consumer_name: str,
    event: TopicGenerationRequestedEvent,
) -> bool:
    with session_factory() as session:
        session: Session

        existing = session.execute(
            select(ProcessedEventLog).where(
                ProcessedEventLog.organization_id == event.payload.organization_id,
                ProcessedEventLog.event_id == event.event_id,
                ProcessedEventLog.consumer_name == consumer_name,
            )
        ).scalar_one_or_none()

        if existing is not None:
            return False

        session.add(
            Topic(
                id=str(uuid.uuid4()),
                organization_id=event.payload.organization_id,
                campaign_id=event.payload.campaign_id,
                title=f"Starter topic for {event.payload.niche}",
            )
        )
        session.add(
            ProcessedEventLog(
                organization_id=event.payload.organization_id,
                event_id=event.event_id,
                consumer_name=consumer_name,
            )
        )

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return False

        return True
