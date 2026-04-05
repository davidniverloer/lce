from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _read(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    rabbitmq_url: str
    rabbitmq_exchange: str
    audit_queue: str
    consumer_name: str


def get_settings() -> Settings:
    return Settings(
        database_url=_read("DATABASE_URL"),
        rabbitmq_url=_read("RABBITMQ_URL"),
        rabbitmq_exchange=_read("RABBITMQ_EXCHANGE", "lce.events"),
        audit_queue=_read(
            "RABBITMQ_AUDIT_QUEUE",
            "audit.integration-events",
        ),
        consumer_name=_read(
            "INTEGRATION_CONSUMER_NAME",
            "ai-engine-audit-consumer",
        ),
    )
