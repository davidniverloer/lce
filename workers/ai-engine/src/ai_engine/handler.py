from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .agents import ContentGenerationAgent, QaComplianceAgent
from .flow import ArticleGenerationFlow, GenerationRequest
from .llm import LLMProvider
from .models import EventReceipt, ProcessedEventLog


@dataclass(frozen=True)
class GenerationRequestedEvent:
    event_id: str
    event_type: str
    version: str
    timestamp: datetime
    request: GenerationRequest


def parse_generation_requested_event(raw: dict) -> GenerationRequestedEvent:
    if not isinstance(raw, dict):
        raise ValueError("Event body must be an object")

    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Event payload must be an object")

    required_top_level_fields = ("eventId", "eventType", "version", "timestamp")
    for field in required_top_level_fields:
        if not isinstance(raw.get(field), str) or not str(raw[field]).strip():
            raise ValueError(f"Missing required field: {field}")

    if raw["eventType"] != "GenerationRequested":
        raise ValueError("Unsupported event type")

    required_payload_fields = ("organizationId", "campaignId", "taskId", "topic")
    for field in required_payload_fields:
        if not isinstance(payload.get(field), str) or not str(payload[field]).strip():
            raise ValueError(f"Missing required payload field: {field}")

    output_formats = payload.get("outputFormats") or []
    if not isinstance(output_formats, list) or not all(
        isinstance(item, str) for item in output_formats
    ):
        raise ValueError("outputFormats must be a list of strings")

    target_audience = payload.get("targetAudience")
    if target_audience is not None and not isinstance(target_audience, str):
        raise ValueError("targetAudience must be a string or null")

    return GenerationRequestedEvent(
        event_id=str(raw["eventId"]),
        event_type=str(raw["eventType"]),
        version=str(raw["version"]),
        timestamp=datetime.fromisoformat(str(raw["timestamp"]).replace("Z", "+00:00")),
        request=GenerationRequest(
            organization_id=str(payload["organizationId"]),
            campaign_id=str(payload["campaignId"]),
            task_id=str(payload["taskId"]),
            topic=str(payload["topic"]),
            target_audience=target_audience,
            output_formats=list(output_formats),
        ),
    )


def process_generation_requested_event(
    session_factory: sessionmaker,
    consumer_name: str,
    event: GenerationRequestedEvent,
    llm_provider: LLMProvider,
) -> bool:
    with session_factory() as session:
        session: Session

        try:
            session.add(
                ProcessedEventLog(
                    organization_id=event.request.organization_id,
                    event_id=event.event_id,
                    consumer_name=consumer_name,
                )
            )
            session.flush()

            flow = ArticleGenerationFlow(
                request=event.request,
                session=session,
                content_agent=ContentGenerationAgent(llm_provider),
                qa_agent=QaComplianceAgent(llm_provider),
            )
            flow.kickoff()

            session.add(
                EventReceipt(
                    id=str(uuid.uuid4()),
                    organization_id=event.request.organization_id,
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
