from __future__ import annotations

from ai_engine.agents import (
    ContentGenerationAgent,
    QaComplianceAgent,
    SitemapIngestorAgent,
    StructureStyleAgent,
    TopicDiscoveryAgent,
)
from ai_engine.config import Settings
from ai_engine.dataforseo import DataForSEOKeywordIdea
from ai_engine.llm import StubLLMProvider


def make_settings() -> Settings:
    return Settings(
        database_url="postgresql://postgres:postgres@localhost:5432/lce",
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
        rabbitmq_exchange="lce.events",
        generation_queue="content.generation-requests",
        consumer_name="ai-engine-generation-consumer",
        market_mode="live",
        discovery_mode="live",
        qualification_mode="mixed",
        trend_provider_mode="live",
        social_provider_mode="live",
        seo_provider_mode="live",
        market_trend_weight=0.35,
        market_social_weight=0.25,
        market_seo_weight=0.40,
        market_min_qualified_score=60.0,
        market_novelty_threshold=0.55,
        market_max_novelty_penalty=25.0,
        dataforseo_login="demo",
        dataforseo_password="demo",
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


class FakeDiscoverySeoClient:
    def keyword_ideas(self, *, keyword: str, limit: int = 5) -> list[DataForSEOKeywordIdea]:
        del keyword
        del limit
        return [
            DataForSEOKeywordIdea(
                keyword="healthcare workflow automation",
                search_volume=1200,
                competition=0.42,
                cpc=4.5,
            ),
            DataForSEOKeywordIdea(
                keyword="healthcare ai operations",
                search_volume=900,
                competition=0.38,
                cpc=4.2,
            ),
        ]


def test_live_discovery_enrichment_includes_source_attribution(monkeypatch) -> None:
    monkeypatch.setattr(
        "ai_engine.agents._news_rss_titles",
        lambda query, limit=10: [
            "Healthcare workflow automation trends in 2026",
            "Healthcare AI operations playbook for providers",
        ],
    )
    monkeypatch.setattr(
        "ai_engine.agents._reddit_titles",
        lambda query, limit=8: [
            "Healthcare AI operations wins for clinic operators",
            "Workflow automation in healthcare teams",
        ],
    )
    monkeypatch.setattr(
        "ai_engine.agents.DataForSEOClient.from_settings",
        lambda settings: FakeDiscoverySeoClient(),
    )

    agent = TopicDiscoveryAgent(make_settings())
    discovered = agent.discover(industry="healthcare", target_audience="operators")

    assert discovered
    assert all(item.source_metadata["mode"] == "live" for item in discovered)
    assert any("news" in item.source_metadata["discoverySources"] for item in discovered)
    assert any("social" in item.source_metadata["discoverySources"] for item in discovered)
    assert any(item.source_metadata["sourceConfidence"] >= 0.65 for item in discovered)


def test_blueprint_contains_differentiation_and_site_context() -> None:
    llm = StubLLMProvider()
    sitemap_agent = SitemapIngestorAgent()
    indexed_pages = [
        {
            "url": "https://example.com/healthcare/ai-operations-guide",
            "title": "Healthcare AI Operations Guide",
        },
        {
            "url": "https://example.com/healthcare/workflow-checklist",
            "title": "Healthcare Workflow Checklist",
        },
    ]
    site_context = sitemap_agent.build_site_context(
        topic="healthcare ai operations",
        indexed_pages=indexed_pages,
    )
    links = sitemap_agent.derive_internal_links(
        topic="healthcare ai operations",
        indexed_pages=indexed_pages,
    )

    blueprint = StructureStyleAgent(llm).build_blueprint(
        topic="healthcare ai operations",
        target_audience="operators",
        content_language="English",
        geo_context="United States",
        internal_links=links,
        qualification_metadata={"novelty": {"closestPriorMatch": "generic healthcare AI overview"}},
        site_context=site_context,
    )

    assert blueprint.differentiation_angle
    assert blueprint.differentiation_rationale
    assert blueprint.target_delta
    assert blueprint.site_context["sitemapUsed"] is True
    assert blueprint.internal_links[0].page_summary is not None
    assert blueprint.internal_links[0].placement_hint is not None


def test_qa_feedback_is_structured_and_actionable() -> None:
    llm = StubLLMProvider()
    sitemap_agent = SitemapIngestorAgent()
    indexed_pages = [
        {
            "url": "https://example.com/healthcare/ai-operations-guide",
            "title": "Healthcare AI Operations Guide",
        }
    ]
    blueprint = StructureStyleAgent(llm).build_blueprint(
        topic="healthcare ai operations",
        target_audience="operators",
        content_language="English",
        geo_context="United States",
        internal_links=sitemap_agent.derive_internal_links(
            topic="healthcare ai operations",
            indexed_pages=indexed_pages,
        ),
        qualification_metadata={},
        site_context=sitemap_agent.build_site_context(
            topic="healthcare ai operations",
            indexed_pages=indexed_pages,
        ),
    )

    content_agent = ContentGenerationAgent(llm)
    qa_agent = QaComplianceAgent(llm)

    initial_draft = content_agent.generate(
        topic="healthcare ai operations",
        target_audience="operators",
        content_language="English",
        geo_context="United States",
        revision_number=0,
        qa_feedback=None,
        blueprint=blueprint,
    )
    initial_review = qa_agent.review(
        initial_draft,
        blueprint,
        content_language="English",
        geo_context="United States",
    )
    assert initial_review.passed is False
    assert initial_review.issues
    assert initial_review.revision_instructions
    assert initial_review.rubric["structureCompleteness"] == "fail"

    revised_draft = content_agent.generate(
        topic="healthcare ai operations",
        target_audience="operators",
        content_language="English",
        geo_context="United States",
        revision_number=1,
        qa_feedback=initial_review.feedback,
        blueprint=blueprint,
    )
    revised_review = qa_agent.review(
        revised_draft,
        blueprint,
        content_language="English",
        geo_context="United States",
    )
    assert revised_review.passed is True
    assert revised_review.issues == []
