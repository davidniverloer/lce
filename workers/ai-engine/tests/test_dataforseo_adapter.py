from __future__ import annotations

import json
import pytest

from ai_engine.agents import SeoGapAgent, normalize_seo_query
from ai_engine.config import Settings
from ai_engine.dataforseo import DataForSEOClient, DataForSEOError


def make_settings(*, seo_provider_mode: str = "live") -> Settings:
    return Settings(
        database_url="postgresql://postgres:postgres@localhost:5432/lce",
        rabbitmq_url="amqp://guest:guest@localhost:5672/",
        rabbitmq_exchange="lce.events",
        generation_queue="content.generation-requests",
        consumer_name="ai-engine-generation-consumer",
        market_mode="mixed",
        discovery_mode="stub",
        qualification_mode="mixed",
        trend_provider_mode="stub",
        social_provider_mode="stub",
        seo_provider_mode=seo_provider_mode,
        market_trend_weight=0.35,
        market_social_weight=0.25,
        market_seo_weight=0.40,
        market_min_qualified_score=60.0,
        market_novelty_threshold=0.55,
        market_max_novelty_penalty=25.0,
        dataforseo_login="login",
        dataforseo_password="password",
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


def test_dataforseo_client_parses_keyword_overview() -> None:
    def transport(_url: str, _payload: bytes, _headers: dict[str, str]) -> dict:
        if "page_intersection" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "intersection_score": 0.82,
                                        "keyword_data": {
                                            "keyword": "ambient ai workflow",
                                            "keyword_info": {
                                                "search_volume": 1400,
                                                "competition": 0.41,
                                            },
                                        },
                                    },
                                    {
                                        "intersection_score": 0.71,
                                        "keyword_data": {
                                            "keyword": "clinical documentation automation",
                                            "keyword_info": {
                                                "search_volume": 1200,
                                                "competition": 0.38,
                                            },
                                        },
                                    },
                                ]
                            }
                        ],
                    }
                ],
            }
        if "organic/live/advanced" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "type": "organic",
                                        "domain": "example.com",
                                        "url": "https://example.com/ambient-ai-scribes",
                                        "title": "Ambient AI Scribes Guide",
                                        "rank_group": 1,
                                        "rank_absolute": 1,
                                        "position": "left",
                                        "is_featured_snippet": True,
                                    },
                                    {
                                        "type": "organic",
                                        "domain": "competitor.com",
                                        "url": "https://competitor.com/ambient-ai",
                                        "title": "Ambient AI in Healthcare",
                                        "rank_group": 2,
                                        "rank_absolute": 2,
                                        "position": "left",
                                        "is_featured_snippet": False,
                                    },
                                ]
                            }
                        ],
                    }
                ],
            }
        if "serp_competitors" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "domain": "example.com",
                                        "avg_position": 3,
                                        "median_position": 3,
                                        "rating": 97,
                                        "etv": 5200.0,
                                        "keywords_count": 1,
                                        "visibility": 0.8,
                                        "relevant_serp_items": 1,
                                    }
                                ]
                            }
                        ],
                    }
                ],
            }
        if "related_keywords" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "relevance": 0.81,
                                        "keyword_data": {
                                            "keyword": "clinical ai documentation",
                                            "keyword_info": {
                                                "search_volume": 1600,
                                                "competition": 0.47,
                                            },
                                        },
                                    }
                                ]
                            }
                        ],
                    }
                ],
            }
        if "keyword_ideas" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "keyword": "ambient ai scribe software",
                                        "keyword_info": {
                                            "search_volume": 1900,
                                            "competition": 0.33,
                                            "cpc": 6.1,
                                        },
                                    }
                                ]
                            }
                        ],
                    }
                ],
            }
        return {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [
                        {
                            "items": [
                                {
                                    "keyword": "ambient ai scribes in healthcare",
                                    "keyword_info": {
                                        "search_volume": 5400,
                                        "competition": 0.42,
                                        "cpc": 7.8,
                                        "low_top_of_page_bid": 3.4,
                                        "high_top_of_page_bid": 8.1,
                                        "monthly_searches": [
                                            {"year": 2026, "month": 3, "search_volume": 5400}
                                        ],
                                    },
                                }
                            ]
                        }
                    ],
                }
            ],
        }

    client = DataForSEOClient(
        base_url="https://api.dataforseo.com",
        login="login",
        password="password",
        location_code=2840,
        language_code="en",
        transport=transport,
    )

    overview = client.keyword_overview(keyword="ambient ai scribes in healthcare")

    assert overview.keyword == "ambient ai scribes in healthcare"
    assert overview.search_volume == 5400
    assert overview.competition == 0.42
    assert overview.cpc == 7.8
    ideas = client.keyword_ideas(keyword="ambient ai scribes in healthcare")
    assert len(ideas) == 1
    assert ideas[0].keyword == "ambient ai scribe software"
    assert ideas[0].search_volume == 1900
    related = client.related_keywords(keyword="ambient ai scribes in healthcare")
    assert len(related) == 1
    assert related[0].keyword == "clinical ai documentation"
    assert related[0].relevance == 0.81
    competitors = client.serp_competitors(keyword="ambient ai scribes in healthcare")
    assert len(competitors) == 1
    assert competitors[0].domain == "example.com"
    assert competitors[0].visibility == 0.8
    organic_results = client.serp_organic_results(keyword="ambient ai scribes in healthcare")
    assert len(organic_results) == 2
    assert organic_results[0].domain == "example.com"
    assert organic_results[0].is_featured_snippet is True
    intersection = client.page_intersection(
        page_urls=[
            "https://example.com/ambient-ai-scribes",
            "https://competitor.com/ambient-ai",
        ]
    )
    assert len(intersection) == 2
    assert intersection[0].keyword == "ambient ai workflow"
    assert intersection[0].intersection_score == 0.82


def test_dataforseo_client_uses_pages_payload_for_page_intersection() -> None:
    seen_payloads: list[dict] = []

    def transport(_url: str, payload: bytes, _headers: dict[str, str]) -> dict:
        seen_payloads.append(json.loads(payload.decode("utf-8")))
        return {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [{"items": []}],
                }
            ],
        }

    client = DataForSEOClient(
        base_url="https://api.dataforseo.com",
        login="login",
        password="password",
        location_code=2840,
        language_code="en",
        transport=transport,
    )

    with pytest.raises(DataForSEOError):
        client.page_intersection(
            page_urls=[
                "https://example.com/ambient-ai-scribes",
                "https://competitor.com/ambient-ai",
            ]
        )

    body = seen_payloads[0][0]
    assert body["pages"] == {
        "1": "https://example.com/ambient-ai-scribes",
        "2": "https://competitor.com/ambient-ai",
    }
    assert body["intersection_mode"] == "intersect"
    assert body["item_types"] == ["organic"]


def test_dataforseo_client_supports_union_page_intersection_mode() -> None:
    seen_payloads: list[dict] = []

    def transport(_url: str, payload: bytes, _headers: dict[str, str]) -> dict:
        seen_payloads.append(json.loads(payload.decode("utf-8")))
        return {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [{"items": []}],
                }
            ],
        }

    client = DataForSEOClient(
        base_url="https://api.dataforseo.com",
        login="login",
        password="password",
        location_code=2840,
        language_code="en",
        transport=transport,
    )

    with pytest.raises(DataForSEOError):
        client.page_intersection(
            page_urls=[
                "https://example.com/ambient-ai-scribes",
                "https://competitor.com/ambient-ai",
            ],
            intersection_mode="union",
        )

    body = seen_payloads[0][0]
    assert body["intersection_mode"] == "union"


def test_dataforseo_client_accepts_dict_result_layout() -> None:
    def transport(_url: str, _payload: bytes, _headers: dict[str, str]) -> dict:
        return {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": {
                        "items": [
                            {
                                "keyword": "ai in healthcare",
                                "keyword_info": {
                                    "search_volume": 18100,
                                    "competition": 0.34,
                                    "cpc": 8.7,
                                    "low_top_of_page_bid": 2.63,
                                    "high_top_of_page_bid": 8.07,
                                    "monthly_searches": [],
                                },
                            }
                        ]
                    },
                }
            ],
        }

    client = DataForSEOClient(
        base_url="https://api.dataforseo.com",
        login="login",
        password="password",
        location_code=2840,
        language_code="en",
        transport=transport,
    )

    overview = client.keyword_overview(keyword="ai in healthcare")
    assert overview.keyword == "ai in healthcare"
    assert overview.search_volume == 18100


def test_dataforseo_client_surfaces_empty_items_diagnostics() -> None:
    def transport(_url: str, _payload: bytes, _headers: dict[str, str]) -> dict:
        return {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "path": ["v3", "dataforseo_labs", "google", "keyword_overview", "live"],
                    "data": {"keywords": ["headline shaped topic"]},
                    "result": [
                        {
                            "items_count": 0,
                            "items": None,
                        }
                    ],
                }
            ],
        }

    client = DataForSEOClient(
        base_url="https://api.dataforseo.com",
        login="login",
        password="password",
        location_code=2840,
        language_code="en",
        transport=transport,
    )

    with pytest.raises(DataForSEOError) as exc_info:
        client.keyword_overview(keyword="headline shaped topic")

    assert "items_count=0" in str(exc_info.value)
    assert "headline shaped topic" in str(exc_info.value)


def test_normalize_seo_query_reduces_headline_style_topics() -> None:
    assert (
        normalize_seo_query("AI in health care: 26 leaders offer predictions for 2026")
        == "healthcare ai trends"
    )
    assert normalize_seo_query("ai in healthcare") == "ai healthcare"
    assert (
        normalize_seo_query("The future of healthcare providers: Empowering care, elevating outcomes")
        == "future healthcare providers care outcomes"
    )


def test_seo_gap_agent_uses_live_dataforseo_metadata() -> None:
    def transport(_url: str, _payload: bytes, _headers: dict[str, str]) -> dict:
        if "page_intersection" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "intersection_score": 0.82,
                                        "keyword_data": {
                                            "keyword": "ambient ai workflow",
                                            "keyword_info": {
                                                "search_volume": 1400,
                                                "competition": 0.41,
                                            },
                                        },
                                    },
                                    {
                                        "intersection_score": 0.71,
                                        "keyword_data": {
                                            "keyword": "clinical documentation automation",
                                            "keyword_info": {
                                                "search_volume": 1200,
                                                "competition": 0.38,
                                            },
                                        },
                                    },
                                ]
                            }
                        ],
                    }
                ],
            }
        if "organic/live/advanced" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "type": "organic",
                                        "domain": "example.com",
                                        "url": "https://example.com/ambient-ai-scribes",
                                        "title": "Ambient AI Scribes Guide",
                                        "rank_group": 1,
                                        "rank_absolute": 1,
                                        "position": "left",
                                        "is_featured_snippet": True,
                                    },
                                    {
                                        "type": "organic",
                                        "domain": "example.com",
                                        "url": "https://example.com/ambient-ai-ops",
                                        "title": "Ambient AI Operations",
                                        "rank_group": 2,
                                        "rank_absolute": 2,
                                        "position": "left",
                                        "is_featured_snippet": False,
                                    },
                                    {
                                        "type": "organic",
                                        "domain": "competitor.com",
                                        "url": "https://competitor.com/ambient-ai",
                                        "title": "Ambient AI in Healthcare",
                                        "rank_group": 3,
                                        "rank_absolute": 3,
                                        "position": "left",
                                        "is_featured_snippet": False,
                                    },
                                    {
                                        "type": "organic",
                                        "domain": "another-site.com",
                                        "url": "https://another-site.com/scribes",
                                        "title": "Healthcare AI Scribes",
                                        "rank_group": 4,
                                        "rank_absolute": 4,
                                        "position": "left",
                                        "is_featured_snippet": False,
                                    },
                                ]
                            }
                        ],
                    }
                ],
            }
        if "serp_competitors" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "domain": "example.com",
                                        "avg_position": 3,
                                        "median_position": 3,
                                        "rating": 97,
                                        "etv": 5200.0,
                                        "keywords_count": 1,
                                        "visibility": 0.8,
                                        "relevant_serp_items": 1,
                                    },
                                    {
                                        "domain": "competitor.com",
                                        "avg_position": 5,
                                        "median_position": 5,
                                        "rating": 91,
                                        "etv": 4100.0,
                                        "keywords_count": 1,
                                        "visibility": 0.6,
                                        "relevant_serp_items": 1,
                                    },
                                ]
                            }
                        ],
                    }
                ],
            }
        if "related_keywords" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "relevance": 0.81,
                                        "keyword_data": {
                                            "keyword": "clinical ai documentation",
                                            "keyword_info": {
                                                "search_volume": 1600,
                                                "competition": 0.47,
                                            },
                                        },
                                    },
                                    {
                                        "relevance": 0.73,
                                        "keyword_data": {
                                            "keyword": "medical ai scribe tools",
                                            "keyword_info": {
                                                "search_volume": 1200,
                                                "competition": 0.44,
                                            },
                                        },
                                    },
                                ]
                            }
                        ],
                    }
                ],
            }
        if "keyword_ideas" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "keyword": "ambient ai scribe software",
                                        "keyword_info": {
                                            "search_volume": 1900,
                                            "competition": 0.33,
                                            "cpc": 6.1,
                                        },
                                    },
                                    {
                                        "keyword": "clinical ai documentation tools",
                                        "keyword_info": {
                                            "search_volume": 1300,
                                            "competition": 0.29,
                                            "cpc": 5.7,
                                        },
                                    },
                                ]
                            }
                        ],
                    }
                ],
            }
        return {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [
                        {
                            "items": [
                                {
                                    "keyword": "ambient ai scribes in healthcare",
                                    "keyword_info": {
                                        "search_volume": 5400,
                                        "competition": 0.42,
                                        "cpc": 7.8,
                                        "low_top_of_page_bid": 3.4,
                                        "high_top_of_page_bid": 8.1,
                                        "monthly_searches": [
                                            {"year": 2026, "month": 3, "search_volume": 5400}
                                        ],
                                    },
                                }
                            ]
                        }
                    ],
                }
            ],
        }

    client = DataForSEOClient(
        base_url="https://api.dataforseo.com",
        login="login",
        password="password",
        location_code=2840,
        language_code="en",
        transport=transport,
    )
    score = SeoGapAgent(make_settings(), client=client).analyze(
        "healthcare",
        "ambient ai scribes in healthcare",
    )

    assert score.metadata["provider"] == "dataforseo_v3_composite"
    assert score.metadata["mode"] == "live"
    assert score.metadata["finalSeoScore"] == score.score
    assert score.metadata["seoQuery"] == "ambient ai scribes healthcare"
    assert score.metadata["componentModes"]["keywordOverview"] == "live"
    assert score.metadata["componentModes"]["pageIntersection"] == "live"
    assert score.metadata["rawComponents"]["searchVolume"] == 5400
    assert score.metadata["rawComponents"]["originalTopic"] == "ambient ai scribes in healthcare"
    assert score.metadata["rawComponents"]["normalizedSeoQuery"] == "ambient ai scribes healthcare"
    assert score.metadata["normalizedSubScores"]["volumeScore"] > 0
    assert score.metadata["normalizedSubScores"]["expansionScore"] > 0
    assert score.metadata["normalizedSubScores"]["competitiveOverlapScore"] > 0
    assert score.metadata["normalizedSubScores"]["serpCrowdingScore"] > 0
    assert score.metadata["normalizedSubScores"]["ownershipDiversityScore"] > 0
    assert score.metadata["normalizedSubScores"]["editorialGapScore"] > 0
    assert score.metadata["rawComponents"]["keywordIdeasCount"] == 2
    assert score.metadata["rawComponents"]["relatedKeywordsCount"] == 2
    assert score.metadata["rawComponents"]["serpCompetitorsCount"] == 2
    assert score.metadata["rawComponents"]["organicSerpResultCount"] == 4
    assert score.metadata["rawComponents"]["organicSerpUniqueDomainCount"] == 3
    assert score.metadata["rawComponents"]["organicSerpTopDomainShare"] == 0.5
    assert score.metadata["rawComponents"]["pageIntersectionCount"] == 2


def test_seo_gap_agent_supports_partial_live_components() -> None:
    def transport(_url: str, _payload: bytes, _headers: dict[str, str]) -> dict:
        if "serp_competitors" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "path": ["v3", "dataforseo_labs", "google", "serp_competitors", "live"],
                        "data": {"keywords": ["ambient ai scribes healthcare"]},
                        "result": [{"items_count": 0, "items": None}],
                    }
                ],
            }
        if "page_intersection" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "intersection_score": 0.82,
                                        "keyword_data": {
                                            "keyword": "ambient ai workflow",
                                            "keyword_info": {
                                                "search_volume": 1400,
                                                "competition": 0.41,
                                            },
                                        },
                                    }
                                ]
                            }
                        ],
                    }
                ],
            }
        if "organic/live/advanced" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "type": "organic",
                                        "domain": "example.com",
                                        "url": "https://example.com/ambient-ai-scribes",
                                        "title": "Ambient AI Scribes Guide",
                                        "rank_group": 1,
                                        "rank_absolute": 1,
                                        "position": "left",
                                        "is_featured_snippet": True,
                                    },
                                    {
                                        "type": "organic",
                                        "domain": "competitor.com",
                                        "url": "https://competitor.com/ambient-ai",
                                        "title": "Ambient AI in Healthcare",
                                        "rank_group": 2,
                                        "rank_absolute": 2,
                                        "position": "left",
                                        "is_featured_snippet": False,
                                    },
                                ]
                            }
                        ],
                    }
                ],
            }
        if "related_keywords" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "relevance": 0.81,
                                        "keyword_data": {
                                            "keyword": "clinical ai documentation",
                                            "keyword_info": {
                                                "search_volume": 1600,
                                                "competition": 0.47,
                                            },
                                        },
                                    }
                                ]
                            }
                        ],
                    }
                ],
            }
        if "keyword_ideas" in _url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "keyword": "ambient ai scribe software",
                                        "keyword_info": {
                                            "search_volume": 1900,
                                            "competition": 0.33,
                                            "cpc": 6.1,
                                        },
                                    }
                                ]
                            }
                        ],
                    }
                ],
            }
        return {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [
                        {
                            "items": [
                                {
                                    "keyword": "ambient ai scribes healthcare",
                                    "keyword_info": {
                                        "search_volume": 5400,
                                        "competition": 0.42,
                                        "cpc": 7.8,
                                        "low_top_of_page_bid": 3.4,
                                        "high_top_of_page_bid": 8.1,
                                        "monthly_searches": [],
                                    },
                                }
                            ]
                        }
                    ],
                }
            ],
        }

    client = DataForSEOClient(
        base_url="https://api.dataforseo.com",
        login="login",
        password="password",
        location_code=2840,
        language_code="en",
        transport=transport,
    )
    score = SeoGapAgent(make_settings(), client=client).analyze(
        "healthcare",
        "ambient ai scribes in healthcare",
    )

    assert score.metadata["mode"] == "mixed"
    assert score.metadata["componentModes"]["keywordOverview"] == "live"
    assert score.metadata["componentModes"]["serpCompetitors"] == "stub_fallback"
    assert "serp_competitors" in score.metadata["componentFallbackReasons"]["serpCompetitors"]
    assert score.metadata["normalizedSubScores"]["serpCrowdingScore"] > 0
    assert score.metadata["componentProviders"]["serpCompetitors"] == "dataforseo_v3_serp_competitors"


def test_seo_gap_agent_retries_page_intersection_with_union() -> None:
    page_intersection_modes: list[str] = []

    def transport(url: str, payload: bytes, _headers: dict[str, str]) -> dict:
        if "page_intersection" in url:
            body = json.loads(payload.decode("utf-8"))[0]
            page_intersection_modes.append(body["intersection_mode"])
            if body["intersection_mode"] == "intersect":
                return {
                    "status_code": 20000,
                    "tasks": [
                        {
                            "status_code": 20000,
                            "path": ["v3", "dataforseo_labs", "google", "page_intersection", "live"],
                            "data": body,
                            "result": [{"items_count": 0, "items": None}],
                        }
                    ],
                }
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "intersection_score": 0.82,
                                        "keyword_data": {
                                            "keyword": "ambient ai workflow",
                                            "keyword_info": {
                                                "search_volume": 1400,
                                                "competition": 0.41,
                                            },
                                        },
                                    }
                                ]
                            }
                        ],
                    }
                ],
            }
        if "organic/live/advanced" in url:
            return {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "result": [
                            {
                                "items": [
                                    {
                                        "type": "organic",
                                        "domain": "example.com",
                                        "url": "https://example.com/ambient-ai-scribes",
                                        "title": "Ambient AI Scribes Guide",
                                        "rank_group": 1,
                                        "rank_absolute": 1,
                                        "position": "left",
                                        "is_featured_snippet": False,
                                    },
                                    {
                                        "type": "organic",
                                        "domain": "competitor.com",
                                        "url": "https://competitor.com/ambient-ai",
                                        "title": "Ambient AI in Healthcare",
                                        "rank_group": 2,
                                        "rank_absolute": 2,
                                        "position": "left",
                                        "is_featured_snippet": False,
                                    },
                                ]
                            }
                        ],
                    }
                ],
            }
        if "keyword_ideas" in url or "related_keywords" in url or "serp_competitors" in url:
            return {"status_code": 20000, "tasks": [{"status_code": 20000, "result": [{"items": []}]}]}
        return {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [
                        {
                            "items": [
                                {
                                    "keyword": "ambient ai scribes healthcare",
                                    "keyword_info": {
                                        "search_volume": 5400,
                                        "competition": 0.42,
                                        "cpc": 7.8,
                                        "low_top_of_page_bid": 3.4,
                                        "high_top_of_page_bid": 8.1,
                                        "monthly_searches": [],
                                    },
                                }
                            ]
                        }
                    ],
                }
            ],
        }

    client = DataForSEOClient(
        base_url="https://api.dataforseo.com",
        login="login",
        password="password",
        location_code=2840,
        language_code="en",
        transport=transport,
    )
    score = SeoGapAgent(make_settings(), client=client).analyze(
        "healthcare",
        "ambient ai scribes in healthcare",
    )

    assert page_intersection_modes == ["intersect", "union"]
    assert score.metadata["componentModes"]["pageIntersection"] == "live"
    assert score.metadata["componentQueries"]["pageIntersection"].startswith("union::")


def test_seo_gap_agent_retries_with_component_specific_query() -> None:
    seen_queries: dict[str, list[str]] = {
        "keywordOverview": [],
        "keywordIdeas": [],
        "relatedKeywords": [],
        "serpCompetitors": [],
        "organicSerp": [],
    }

    def transport(url: str, payload: bytes, _headers: dict[str, str]) -> dict:
        body = json.loads(payload.decode("utf-8"))[0]
        if "keyword_overview" in url:
            query = body["keywords"][0]
            seen_queries["keywordOverview"].append(query)
            if query == "future healthcare providers care outcomes":
                return {
                    "status_code": 20000,
                    "tasks": [
                        {
                            "status_code": 20000,
                            "path": ["v3", "dataforseo_labs", "google", "keyword_overview", "live"],
                            "data": {"keywords": [query]},
                            "result": [{"items_count": 0, "items": None}],
                        }
                    ],
                }
        if "keyword_ideas" in url:
            seen_queries["keywordIdeas"].append(body["keywords"][0])
            return {
                "status_code": 20000,
                "tasks": [{"status_code": 20000, "result": [{"items": []}]}],
            }
        if "related_keywords" in url:
            seen_queries["relatedKeywords"].append(body["keyword"])
            return {
                "status_code": 20000,
                "tasks": [{"status_code": 20000, "result": [{"items": []}]}],
            }
        if "serp_competitors" in url:
            seen_queries["serpCompetitors"].append(body["keywords"][0])
            return {
                "status_code": 20000,
                "tasks": [{"status_code": 20000, "result": [{"items": []}]}],
            }
        if "organic/live/advanced" in url:
            seen_queries["organicSerp"].append(body["keyword"])
            return {
                "status_code": 20000,
                "tasks": [{"status_code": 20000, "result": [{"items": []}]}],
            }
        return {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [
                        {
                            "items": [
                                {
                                    "keyword": "healthcare providers",
                                    "keyword_info": {
                                        "search_volume": 5400,
                                        "competition": 0.42,
                                        "cpc": 7.8,
                                        "low_top_of_page_bid": 3.4,
                                        "high_top_of_page_bid": 8.1,
                                        "monthly_searches": [],
                                    },
                                }
                            ]
                        }
                    ],
                }
            ],
        }

    client = DataForSEOClient(
        base_url="https://api.dataforseo.com",
        login="login",
        password="password",
        location_code=2840,
        language_code="en",
        transport=transport,
    )
    score = SeoGapAgent(make_settings(), client=client).analyze(
        "healthcare",
        "The future of healthcare providers: Empowering care, elevating outcomes",
    )

    assert seen_queries["keywordOverview"] == [
        "future healthcare providers care outcomes",
        "future healthcare providers",
    ]
    assert score.metadata["mode"] == "mixed"
    assert score.metadata["componentModes"]["keywordOverview"] == "live"
    assert score.metadata["componentQueries"]["keywordOverview"] == "future healthcare providers"


def test_seo_gap_agent_falls_back_to_stub_when_live_fails() -> None:
    def transport(_url: str, _payload: bytes, _headers: dict[str, str]) -> dict:
        raise OSError("network down")

    client = DataForSEOClient(
        base_url="https://api.dataforseo.com",
        login="login",
        password="password",
        location_code=2840,
        language_code="en",
        transport=transport,
    )
    score = SeoGapAgent(make_settings(), client=client).analyze(
        "healthcare",
        "ambient ai scribes in healthcare",
    )

    assert score.metadata["provider"] == "dataforseo_stub"
    assert score.metadata["mode"] == "stub_fallback"
    assert "keywordOverview=network down" in score.metadata["fallbackReason"]
    assert score.metadata["seoQuery"] == "ambient ai scribes healthcare"
    assert score.metadata["componentModes"]["keywordOverview"] == "stub_fallback"
