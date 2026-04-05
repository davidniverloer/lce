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


def _read_optional(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def _read_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid float value for {name}: {value}") from exc


@dataclass(frozen=True)
class Settings:
    database_url: str
    rabbitmq_url: str
    rabbitmq_exchange: str
    generation_queue: str
    consumer_name: str
    llm_mode: str
    llm_model: str | None
    llm_api_key: str | None
    llm_api_base: str | None
    llm_temperature: float
    llm_timeout_seconds: float
    openai_api_key: str | None
    openai_base_url: str | None


def get_settings() -> Settings:
    return Settings(
        database_url=_read("DATABASE_URL"),
        rabbitmq_url=_read("RABBITMQ_URL"),
        rabbitmq_exchange=_read("RABBITMQ_EXCHANGE", "lce.events"),
        generation_queue=_read(
            "RABBITMQ_GENERATION_QUEUE",
            "content.generation-requests",
        ),
        consumer_name=_read(
            "INTEGRATION_CONSUMER_NAME",
            "ai-engine-generation-consumer",
        ),
        llm_mode=_read("AI_ENGINE_LLM_MODE", "stub"),
        llm_model=_read_optional("AI_ENGINE_LLM_MODEL"),
        llm_api_key=_read_optional("AI_ENGINE_LLM_API_KEY"),
        llm_api_base=_read_optional("AI_ENGINE_LLM_API_BASE"),
        llm_temperature=_read_float("AI_ENGINE_LLM_TEMPERATURE", 0.2),
        llm_timeout_seconds=_read_float("AI_ENGINE_LLM_TIMEOUT_SECONDS", 30.0),
        openai_api_key=_read_optional("OPENAI_API_KEY"),
        openai_base_url=_read_optional("OPENAI_BASE_URL"),
    )
