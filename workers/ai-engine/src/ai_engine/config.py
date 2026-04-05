from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.getenv("DOTENV_CONFIG_PATH"))


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


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer value for {name}: {value}") from exc


def _read_generation_queue() -> str:
    return (
        _read_optional("RABBITMQ_GENERATION_QUEUE")
        or _read_optional("RABBITMQ_TOPIC_GENERATION_QUEUE")
        or "content.generation-requests"
    )


def _read_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalized_mode(value: str | None, default: str) -> str:
    if value is None:
        return default
    stripped = value.strip().lower()
    return stripped or default


def _resolve_market_modes() -> tuple[str, str, str, str, str]:
    ci_enabled = _read_bool("CI", False)
    if ci_enabled:
        return ("stub", "stub", "stub", "stub", "stub")

    market_mode = _normalized_mode(os.getenv("LCE_MARKET_MODE"), "stub")
    discovery_mode = _normalized_mode(
        os.getenv("LCE_DISCOVERY_MODE"),
        "live" if market_mode in {"mixed", "live"} else "stub",
    )
    qualification_mode = _normalized_mode(
        os.getenv("LCE_QUALIFICATION_MODE"),
        market_mode if market_mode in {"stub", "mixed", "live"} else "stub",
    )

    if qualification_mode == "live":
        default_provider_mode = "live"
    else:
        default_provider_mode = "stub"

    trend_provider_mode = _normalized_mode(
        os.getenv("LCE_TREND_PROVIDER_MODE"),
        default_provider_mode,
    )
    social_provider_mode = _normalized_mode(
        os.getenv("LCE_SOCIAL_PROVIDER_MODE"),
        default_provider_mode,
    )
    seo_provider_mode = _normalized_mode(
        os.getenv("LCE_SEO_PROVIDER_MODE"),
        "live" if qualification_mode == "live" else "stub",
    )

    if qualification_mode == "mixed":
        trend_provider_mode = _normalized_mode(
            os.getenv("LCE_TREND_PROVIDER_MODE"),
            "stub",
        )
        social_provider_mode = _normalized_mode(
            os.getenv("LCE_SOCIAL_PROVIDER_MODE"),
            "stub",
        )
        seo_provider_mode = _normalized_mode(
            os.getenv("LCE_SEO_PROVIDER_MODE"),
            "stub",
        )

    return (
        discovery_mode,
        qualification_mode,
        trend_provider_mode,
        social_provider_mode,
        seo_provider_mode,
    )


@dataclass(frozen=True)
class Settings:
    database_url: str
    rabbitmq_url: str
    rabbitmq_exchange: str
    generation_queue: str
    consumer_name: str
    market_mode: str
    discovery_mode: str
    qualification_mode: str
    trend_provider_mode: str
    social_provider_mode: str
    seo_provider_mode: str
    market_trend_weight: float
    market_social_weight: float
    market_seo_weight: float
    market_min_qualified_score: float
    market_novelty_threshold: float
    market_max_novelty_penalty: float
    dataforseo_login: str | None
    dataforseo_password: str | None
    dataforseo_base_url: str
    dataforseo_location_code: int
    dataforseo_language_code: str
    llm_mode: str
    llm_model: str | None
    llm_api_key: str | None
    llm_api_base: str | None
    llm_temperature: float
    llm_timeout_seconds: float
    openai_api_key: str | None
    openai_base_url: str | None


def get_settings() -> Settings:
    (
        discovery_mode,
        qualification_mode,
        trend_provider_mode,
        social_provider_mode,
        seo_provider_mode,
    ) = _resolve_market_modes()
    return Settings(
        database_url=_read("DATABASE_URL"),
        rabbitmq_url=_read("RABBITMQ_URL"),
        rabbitmq_exchange=_read("RABBITMQ_EXCHANGE", "lce.events"),
        generation_queue=_read_generation_queue(),
        consumer_name=_read(
            "INTEGRATION_CONSUMER_NAME",
            "ai-engine-generation-consumer",
        ),
        market_mode=_normalized_mode(os.getenv("LCE_MARKET_MODE"), "stub"),
        discovery_mode=discovery_mode,
        qualification_mode=qualification_mode,
        trend_provider_mode=trend_provider_mode,
        social_provider_mode=social_provider_mode,
        seo_provider_mode=seo_provider_mode,
        market_trend_weight=_read_float("LCE_MARKET_TREND_WEIGHT", 0.35),
        market_social_weight=_read_float("LCE_MARKET_SOCIAL_WEIGHT", 0.25),
        market_seo_weight=_read_float("LCE_MARKET_SEO_WEIGHT", 0.40),
        market_min_qualified_score=_read_float("LCE_MARKET_MIN_QUALIFIED_SCORE", 60.0),
        market_novelty_threshold=_read_float("LCE_MARKET_NOVELTY_THRESHOLD", 0.55),
        market_max_novelty_penalty=_read_float("LCE_MARKET_MAX_NOVELTY_PENALTY", 25.0),
        dataforseo_login=_read_optional("DATAFORSEO_LOGIN"),
        dataforseo_password=_read_optional("DATAFORSEO_PASSWORD"),
        dataforseo_base_url=_read("DATAFORSEO_BASE_URL", "https://api.dataforseo.com"),
        dataforseo_location_code=_read_int("DATAFORSEO_LOCATION_CODE", 2840),
        dataforseo_language_code=_read("DATAFORSEO_LANGUAGE_CODE", "en"),
        llm_mode=_read("AI_ENGINE_LLM_MODE", "stub"),
        llm_model=_read_optional("AI_ENGINE_LLM_MODEL"),
        llm_api_key=_read_optional("AI_ENGINE_LLM_API_KEY"),
        llm_api_base=_read_optional("AI_ENGINE_LLM_API_BASE"),
        llm_temperature=_read_float("AI_ENGINE_LLM_TEMPERATURE", 0.2),
        llm_timeout_seconds=_read_float("AI_ENGINE_LLM_TIMEOUT_SECONDS", 30.0),
        openai_api_key=_read_optional("OPENAI_API_KEY"),
        openai_base_url=_read_optional("OPENAI_BASE_URL"),
    )
