from __future__ import annotations

from dataclasses import dataclass

from ai_engine.agents import (
    DiscoveredTopicCandidate,
    MarketAwarenessCrew,
    QualifiedTopicCandidate,
    SignalScore,
    TopicDiscoveryAgent,
)
from ai_engine.config import Settings
from ai_engine.handler import _apply_novelty_rules


def make_settings() -> Settings:
    return Settings(
        database_url="postgresql://postgres:postgres@localhost:5432/lce",
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
        rabbitmq_exchange="lce.events",
        generation_queue="content.generation-requests",
        consumer_name="ai-engine-generation-consumer",
        market_mode="mixed",
        discovery_mode="live",
        qualification_mode="mixed",
        trend_provider_mode="live",
        social_provider_mode="stub",
        seo_provider_mode="live",
        market_trend_weight=0.30,
        market_social_weight=0.20,
        market_seo_weight=0.50,
        market_min_qualified_score=60.0,
        market_novelty_threshold=0.55,
        market_max_novelty_penalty=25.0,
        dataforseo_login=None,
        dataforseo_password=None,
        dataforseo_base_url="https://api.dataforseo.com",
        dataforseo_location_code=2840,
        dataforseo_language_code="en",
        llm_mode="stub",
        llm_model=None,
        llm_api_key=None,
        llm_api_base=None,
        llm_temperature=0.2,
        llm_timeout_seconds=30.0,
        openai_api_key=None,
        openai_base_url=None,
    )


@dataclass
class FakeSignalAgent:
    _settings: Settings
    score: float
    provider: str
    mode: str

    def analyze(self, seed_topic: str, candidate_topic: str) -> SignalScore:
        return SignalScore(
            score=self.score,
            note=f"{self.provider} score generated for {candidate_topic}",
            metadata={
                "provider": self.provider,
                "mode": self.mode,
                "seedTopic": seed_topic,
                "candidateTopic": candidate_topic,
            },
        )


def test_market_scoring_calibration_metadata_is_explainable() -> None:
    settings = make_settings()
    crew = MarketAwarenessCrew(
        discovery_agent=TopicDiscoveryAgent(settings),
        trend_agent=FakeSignalAgent(settings, 80.0, "trend_live", "live"),
        social_agent=FakeSignalAgent(settings, 60.0, "social_stub", "stub"),
        seo_agent=FakeSignalAgent(settings, 90.0, "seo_live", "live"),
    )

    discovered = DiscoveredTopicCandidate(
        topic="ambient ai scribes in healthcare",
        discovery_note="Live discovery produced the topic.",
        source_metadata={"provider": "google_news_rss", "mode": "live"},
    )
    qualified = crew.qualify_topics(
        seed_topic_context="healthcare",
        candidate_topics=[discovered.topic],
        target_audience="operators",
        discovery_metadata={discovered.topic: discovered},
    )

    assert len(qualified) == 1
    candidate = qualified[0]
    assert candidate.total_score == 81.0
    calibration = candidate.source_metadata["calibration"]
    assert calibration["weights"] == {"trend": 0.3, "social": 0.2, "seo": 0.5}
    assert calibration["weightedComponents"] == {"trend": 24.0, "social": 12.0, "seo": 45.0}
    assert calibration["qualificationStatus"] == "qualified"
    assert calibration["liveSignalCount"] == 2
    assert calibration["stubSignalCount"] == 1
    assert calibration["confidenceBand"] == "high"
    assert calibration["confidenceScore"] == 0.94
    assert calibration["fallbackWeightShare"] == 0.0
    assert candidate.source_metadata["weightedScore"] == 81.0
    assert candidate.source_metadata["status"]["qualification"]["confidenceBand"] == "high"
    assert candidate.source_metadata["status"]["qualification"]["fallbackCount"] == 0


def test_novelty_reranking_uses_configured_thresholds(monkeypatch) -> None:
    settings = make_settings()
    candidates = [
        QualifiedTopicCandidate(
            topic="ambient ai scribes in healthcare operations",
            trend_score=82.0,
            social_score=60.0,
            seo_score=90.0,
            total_score=81.0,
            qualification_note="Qualified candidate.",
                source_metadata={
                    "weightedScore": 81.0,
                    "calibration": {
                        "weights": {"trend": 0.3, "social": 0.2, "seo": 0.5},
                        "confidenceScore": 0.82,
                        "confidenceBand": "medium",
                    },
                },
            ),
        QualifiedTopicCandidate(
            topic="remote patient monitoring reimbursement",
            trend_score=70.0,
            social_score=58.0,
            seo_score=76.0,
            total_score=70.4,
            qualification_note="Qualified candidate.",
                source_metadata={
                    "weightedScore": 70.4,
                    "calibration": {
                        "weights": {"trend": 0.3, "social": 0.2, "seo": 0.5},
                        "confidenceScore": 0.82,
                        "confidenceBand": "medium",
                    },
                },
            ),
    ]

    monkeypatch.setattr(
        "ai_engine.handler._prior_topic_and_article_texts",
        lambda session, organization_id: [
            "ambient ai scribes in healthcare checklist",
            "prior authorization automation",
        ],
    )

    reranked = _apply_novelty_rules(
        session=object(),
        settings=settings,
        organization_id="org-demo",
        candidates=candidates,
    )

    assert len(reranked) == 2
    assert reranked[0].source_metadata["selectionRank"] == 1
    assert reranked[0].source_metadata["selectedForBlueprint"] is True
    assert reranked[0].source_metadata["selectionValidation"]["selected"] is True
    assert reranked[0].source_metadata["novelty"]["threshold"] == 0.55
    assert reranked[0].source_metadata["novelty"]["maxPenalty"] == 25.0
    assert reranked[0].source_metadata["adjustedScore"] <= reranked[0].source_metadata["rawWeightedScore"]
    assert reranked[0].source_metadata["selectionValidation"]["adjustedScore"] == reranked[0].total_score
    assert reranked[0].source_metadata["selectionValidation"]["confidenceBand"] is not None
