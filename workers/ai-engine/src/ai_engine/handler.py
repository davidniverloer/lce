from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .models import EventReceipt, ProcessedEventLog


@dataclass(frozen=True)
class IntegrationEvent:
    event_id: str
    event_type: str
    version: str
    timestamp: datetime
    organization_id: str


def parse_integration_event(raw: dict) -> IntegrationEvent:
    if not isinstance(raw, dict):
        raise ValueError("Event body must be an object")

    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Event payload must be an object")

    required_top_level_fields = ("eventId", "eventType", "version", "timestamp")
    for field in required_top_level_fields:
        if not isinstance(raw.get(field), str) or not str(raw[field]).strip():
            raise ValueError(f"Missing required field: {field}")

    organization_id = payload.get("organizationId")
    if not isinstance(organization_id, str) or not organization_id.strip():
        raise ValueError("Missing required payload field: organizationId")

    return IntegrationEvent(
        event_id=str(raw["eventId"]),
        event_type=str(raw["eventType"]),
        version=str(raw["version"]),
        timestamp=datetime.fromisoformat(str(raw["timestamp"]).replace("Z", "+00:00")),
        organization_id=organization_id,
    )


def process_integration_event(
    session_factory: sessionmaker,
    consumer_name: str,
    event: IntegrationEvent,
) -> bool:
    with session_factory() as session:
        session: Session

        try:
            session.add(
                ProcessedEventLog(
                    organization_id=event.organization_id,
                    event_id=event.event_id,
                    consumer_name=consumer_name,
                )
            )
            session.flush()

            session.add(
                EventReceipt(
                    id=str(uuid.uuid4()),
                    organization_id=event.organization_id,
                    event_id=event.event_id,
                    event_type=event.event_type,
                    consumer_name=consumer_name,
                )
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            return False

        return True
