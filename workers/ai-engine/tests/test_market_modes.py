from __future__ import annotations

import os

from ai_engine.config import get_settings


def test_ci_forces_stub_modes(monkeypatch) -> None:
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lce")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    monkeypatch.setenv("LCE_DISCOVERY_MODE", "live")
    monkeypatch.setenv("LCE_QUALIFICATION_MODE", "live")
    monkeypatch.setenv("LCE_TREND_PROVIDER_MODE", "live")
    monkeypatch.setenv("LCE_SOCIAL_PROVIDER_MODE", "live")
    monkeypatch.setenv("LCE_SEO_PROVIDER_MODE", "live")

    settings = get_settings()

    assert settings.discovery_mode == "stub"
    assert settings.qualification_mode == "stub"
    assert settings.trend_provider_mode == "stub"
    assert settings.social_provider_mode == "stub"
    assert settings.seo_provider_mode == "stub"


def test_non_ci_respects_mixed_modes(monkeypatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lce")
    monkeypatch.setenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    monkeypatch.setenv("LCE_MARKET_MODE", "mixed")
    monkeypatch.setenv("LCE_DISCOVERY_MODE", "live")
    monkeypatch.setenv("LCE_QUALIFICATION_MODE", "mixed")
    monkeypatch.setenv("LCE_TREND_PROVIDER_MODE", "live")
    monkeypatch.setenv("LCE_SOCIAL_PROVIDER_MODE", "stub")
    monkeypatch.setenv("LCE_SEO_PROVIDER_MODE", "stub")

    settings = get_settings()

    assert settings.discovery_mode == "live"
    assert settings.qualification_mode == "mixed"
    assert settings.trend_provider_mode == "live"
    assert settings.social_provider_mode == "stub"
    assert settings.seo_provider_mode == "stub"
