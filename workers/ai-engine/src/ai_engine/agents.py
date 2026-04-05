from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from pydantic import BaseModel

from .config import Settings
from .dataforseo import (
    DataForSEOClient,
    DataForSEOError,
    DataForSEOKeywordIdea,
    DataForSEOKeywordOverview,
    DataForSEOPageIntersectionKeyword,
    DataForSEORelatedKeyword,
    DataForSEOSerpCompetitor,
    DataForSEOSerpOrganicResult,
)
from .llm import LLMProvider


@dataclass(frozen=True)
class SignalScore:
    score: float
    note: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class QualifiedTopicCandidate:
    topic: str
    trend_score: float
    social_score: float
    seo_score: float
    total_score: float
    qualification_note: str
    source_metadata: dict[str, object]


@dataclass(frozen=True)
class DiscoveredTopicCandidate:
    topic: str
    discovery_note: str
    source_metadata: dict[str, object]


@dataclass(frozen=True)
class InternalLinkSuggestion:
    url: str
    title: str
    anchor_text: str
    rationale: str


@dataclass(frozen=True)
class BlueprintOutput:
    topic: str
    target_audience: str | None
    content_language: str | None
    geo_context: str | None
    angle: str
    sections: list[str]
    style_guidance: str
    internal_links: list[InternalLinkSuggestion]


@dataclass(frozen=True)
class DraftOutput:
    title: str
    body: str


@dataclass(frozen=True)
class QaResult:
    passed: bool
    feedback: str


class DraftResponse(BaseModel):
    title: str
    body: str


class QaResponse(BaseModel):
    passed: bool
    feedback: str


class BlueprintResponse(BaseModel):
    angle: str
    sections: list[str]
    style_guidance: str


def _bounded_score(key: str, minimum: int = 55, maximum: int = 95) -> float:
    span = maximum - minimum
    hashed = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return float(minimum + (int(hashed[:8], 16) % (span + 1)))


def _fetch_text(url: str, *, accept: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "LCE-Market-Intelligence/0.1",
        },
    )
    with urlopen(request, timeout=10) as response:
        return response.read().decode("utf-8", errors="ignore")


def _live_fallback_score(prefix: str, seed_topic: str, candidate_topic: str) -> float:
    return _bounded_score(f"{prefix}:fallback:{seed_topic}:{candidate_topic}")


def _normalized_market_weights(settings: Settings) -> dict[str, float]:
    raw_weights = {
        "trend": max(0.0, settings.market_trend_weight),
        "social": max(0.0, settings.market_social_weight),
        "seo": max(0.0, settings.market_seo_weight),
    }
    total = sum(raw_weights.values())
    if total <= 0:
        return {"trend": 0.35, "social": 0.25, "seo": 0.40}
    return {
        name: round(weight / total, 4)
        for name, weight in raw_weights.items()
    }


def _news_rss_titles(query: str, *, limit: int = 8) -> list[str]:
    rss_url = f"https://news.google.com/rss/search?q={quote(query)}"
    xml = _fetch_text(rss_url, accept="application/rss+xml")
    root = ElementTree.fromstring(xml)
    titles: list[str] = []
    for item in root.findall(".//item/title"):
        if item.text and item.text.strip():
            titles.append(item.text.strip())
        if len(titles) >= limit:
            break
    return titles


def _slugify_topic(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_seo_query(topic: str) -> str:
    normalized = _slugify_topic(topic)
    if not normalized:
        return topic.strip()

    normalized = normalized.replace("health care", "healthcare")
    tokens = [token for token in normalized.split() if token]
    if not tokens:
        return topic.strip()

    trend_tokens = {"trend", "trends", "prediction", "predictions", "future", "outlook"}
    if "ai" in tokens and "healthcare" in tokens and any(token in tokens for token in trend_tokens):
        return "healthcare ai trends"

    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "by",
        "for",
        "from",
        "get",
        "how",
        "in",
        "into",
        "is",
        "it",
        "many",
        "of",
        "offer",
        "offers",
        "on",
        "real",
        "state",
        "the",
        "to",
        "what",
        "with",
    }
    editorial_filler = {
        "best",
        "checklist",
        "ease",
        "elevating",
        "empowering",
        "guide",
        "hurdles",
        "know",
        "leaders",
        "leaning",
        "playbook",
        "practices",
    }

    filtered = [
        token
        for token in tokens
        if token not in stopwords
        and token not in editorial_filler
        and not re.fullmatch(r"\d{4}", token)
        and not token.isdigit()
    ]
    if not filtered:
        return normalized

    deduped: list[str] = []
    for token in filtered:
        if token not in deduped:
            deduped.append(token)

    query = " ".join(deduped[:5]).strip()
    return query or normalized


def _endpoint_seo_queries(component_name: str, seo_query: str) -> list[str]:
    base = seo_query.strip()
    if not base:
        return []

    tokens = [token for token in base.split() if token]
    variants: list[str] = [base]

    compact_token_limits = {
        "keywordOverview": 3,
        "keywordIdeas": 4,
        "relatedKeywords": 3,
        "serpCompetitors": 3,
        "organicSerp": 4,
    }
    compact_limit = compact_token_limits.get(component_name)
    if compact_limit and len(tokens) > compact_limit:
        variants.append(" ".join(tokens[:compact_limit]))

    if component_name in {"keywordOverview", "relatedKeywords", "serpCompetitors"}:
        shorter_tokens = [
            token
            for token in tokens
            if token
            not in {
                "future",
                "providers",
                "outcomes",
                "care",
                "leaders",
                "operations",
            }
        ]
        if shorter_tokens:
            variants.append(" ".join(shorter_tokens[:3]))

    deduped: list[str] = []
    for variant in variants:
        candidate = variant.strip()
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _topic_variants_from_titles(titles: list[str], *, industry: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for title in titles:
        cleaned = re.split(r"\s[-|:]\s", title)[0].strip()
        cleaned = re.sub(r"^(breaking|analysis|opinion)\s*:\s*", "", cleaned, flags=re.I)
        if not cleaned:
            continue
        lower = _slugify_topic(cleaned)
        if len(lower.split()) < 3:
            continue
        if industry.lower() not in lower and "health" in industry.lower():
            if "health" not in lower and "medical" not in lower and "clinic" not in lower:
                continue
        if lower in seen:
            continue
        seen.add(lower)
        candidates.append(cleaned)
    return candidates[:5]


class TrendAnalysisAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def analyze(self, seed_topic: str, candidate_topic: str) -> SignalScore:
        if self._settings.trend_provider_mode != "live":
            score = _bounded_score(f"trend:{seed_topic}:{candidate_topic}")
            return SignalScore(
                score=score,
                note="Trend interest is stable enough to support evergreen planning.",
                metadata={
                    "provider": "pytrends_stub",
                    "mode": "stub",
                    "seedTopic": seed_topic,
                    "candidateTopic": candidate_topic,
                },
            )

        try:
            titles = _news_rss_titles(f"{candidate_topic} trend")
            score = float(min(95, 55 + (len(titles) * 5)))
            return SignalScore(
                score=score,
                note="Live news coverage suggests current trend visibility.",
                metadata={
                    "provider": "google_news_rss",
                    "mode": "live",
                    "seedTopic": seed_topic,
                    "candidateTopic": candidate_topic,
                    "headlineCount": len(titles),
                    "sampleHeadlines": titles[:3],
                },
            )
        except Exception as exc:
            score = _live_fallback_score("trend", seed_topic, candidate_topic)
            return SignalScore(
                score=score,
                note="Live trend provider failed; falling back to deterministic score.",
                metadata={
                    "provider": "pytrends_stub",
                    "mode": "stub_fallback",
                    "seedTopic": seed_topic,
                    "candidateTopic": candidate_topic,
                    "fallbackReason": str(exc),
                },
            )


class SocialListeningAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def analyze(self, seed_topic: str, candidate_topic: str) -> SignalScore:
        if self._settings.social_provider_mode != "live":
            score = _bounded_score(f"social:{seed_topic}:{candidate_topic}")
            return SignalScore(
                score=score,
                note="Community discussion suggests the topic has practical operator interest.",
                metadata={
                    "provider": "reddit_stub",
                    "mode": "stub",
                    "seedTopic": seed_topic,
                    "candidateTopic": candidate_topic,
                },
            )

        try:
            url = (
                "https://www.reddit.com/search.json?q="
                f"{quote(candidate_topic)}&sort=top&t=month&limit=5"
            )
            payload = json.loads(_fetch_text(url, accept="application/json"))
            posts = payload.get("data", {}).get("children", [])
            score = float(min(95, 55 + (len(posts) * 6)))
            return SignalScore(
                score=score,
                note="Live Reddit discussion indicates practical social interest.",
                metadata={
                    "provider": "reddit_json",
                    "mode": "live",
                    "seedTopic": seed_topic,
                    "candidateTopic": candidate_topic,
                    "postCount": len(posts),
                    "sampleTitles": [
                        item.get("data", {}).get("title")
                        for item in posts[:3]
                        if item.get("data", {}).get("title")
                    ],
                },
            )
        except Exception as exc:
            score = _live_fallback_score("social", seed_topic, candidate_topic)
            return SignalScore(
                score=score,
                note="Live social provider failed; falling back to deterministic score.",
                metadata={
                    "provider": "reddit_stub",
                    "mode": "stub_fallback",
                    "seedTopic": seed_topic,
                    "candidateTopic": candidate_topic,
                    "fallbackReason": str(exc),
                },
            )


class SeoGapAgent:
    def __init__(
        self,
        settings: Settings,
        *,
        client: DataForSEOClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client if client is not None else DataForSEOClient.from_settings(settings)

    def analyze(self, seed_topic: str, candidate_topic: str) -> SignalScore:
        seo_query = normalize_seo_query(candidate_topic)
        if self._settings.seo_provider_mode == "live":
            if self._client is None:
                return self._stub_fallback(
                    seed_topic=seed_topic,
                    candidate_topic=candidate_topic,
                    seo_query=seo_query,
                    reason="DataForSEO credentials are missing.",
                )
            return self._partial_live_score(
                seed_topic=seed_topic,
                candidate_topic=candidate_topic,
                seo_query=seo_query,
            )

        score = _bounded_score(f"seo:{seed_topic}:{candidate_topic}")
        return SignalScore(
            score=score,
            note="SERP opportunity remains open enough for a differentiated article.",
            metadata={
                "provider": "dataforseo_stub",
                "mode": (
                    "stub_fallback"
                    if self._settings.seo_provider_mode == "live"
                    else "stub"
                ),
                "seedTopic": seed_topic,
                "candidateTopic": candidate_topic,
                "seoQuery": seo_query,
                "componentModes": {
                    "keywordOverview": "stub",
                    "keywordIdeas": "stub",
                    "relatedKeywords": "stub",
                    "serpCompetitors": "stub",
                    "organicSerp": "stub",
                    "pageIntersection": "stub",
                },
            },
        )

    def _partial_live_score(
        self,
        *,
        seed_topic: str,
        candidate_topic: str,
        seo_query: str,
    ) -> SignalScore:
        assert self._client is not None

        component_modes: dict[str, str] = {}
        component_fallback_reasons: dict[str, str] = {}
        component_providers = {
            "keywordOverview": "dataforseo_v3_keyword_overview",
            "keywordIdeas": "dataforseo_v3_keyword_ideas",
            "relatedKeywords": "dataforseo_v3_related_keywords",
            "serpCompetitors": "dataforseo_v3_serp_competitors",
            "organicSerp": "dataforseo_v3_organic_serp",
            "pageIntersection": "dataforseo_v3_page_intersection",
        }
        component_queries: dict[str, str] = {}

        overview = self._fetch_component(
            component_name="keywordOverview",
            component_modes=component_modes,
            fallback_reasons=component_fallback_reasons,
            component_queries=component_queries,
            queries=_endpoint_seo_queries("keywordOverview", seo_query),
            fetcher=lambda query: self._client.keyword_overview(keyword=query),
        )
        ideas = self._fetch_component(
            component_name="keywordIdeas",
            component_modes=component_modes,
            fallback_reasons=component_fallback_reasons,
            component_queries=component_queries,
            queries=_endpoint_seo_queries("keywordIdeas", seo_query),
            fetcher=lambda query: self._client.keyword_ideas(keyword=query, limit=5),
            fallback_value=[],
        )
        related_keywords = self._fetch_component(
            component_name="relatedKeywords",
            component_modes=component_modes,
            fallback_reasons=component_fallback_reasons,
            component_queries=component_queries,
            queries=_endpoint_seo_queries("relatedKeywords", seo_query),
            fetcher=lambda query: self._client.related_keywords(keyword=query, limit=5),
            fallback_value=[],
        )
        serp_competitors = self._fetch_component(
            component_name="serpCompetitors",
            component_modes=component_modes,
            fallback_reasons=component_fallback_reasons,
            component_queries=component_queries,
            queries=_endpoint_seo_queries("serpCompetitors", seo_query),
            fetcher=lambda query: self._client.serp_competitors(keyword=query, limit=5),
            fallback_value=[],
        )
        organic_results = self._fetch_component(
            component_name="organicSerp",
            component_modes=component_modes,
            fallback_reasons=component_fallback_reasons,
            component_queries=component_queries,
            queries=_endpoint_seo_queries("organicSerp", seo_query),
            fetcher=lambda query: self._client.serp_organic_results(keyword=query, limit=10),
            fallback_value=[],
        )
        page_intersection = self._fetch_component(
            component_name="pageIntersection",
            component_modes=component_modes,
            fallback_reasons=component_fallback_reasons,
            component_queries=component_queries,
            queries=self._page_intersection_query_variants(organic_results),
            fetcher=lambda query: self._fetch_page_intersection(query),
            fallback_value=[],
            skip_reason="Need at least 2 organic SERP URLs for page intersection.",
            should_skip=len(self._page_intersection_urls(organic_results)) < 2,
        )

        live_component_count = sum(1 for mode in component_modes.values() if mode == "live")
        if overview is None and live_component_count == 0:
            reason = "; ".join(
                f"{name}={message}" for name, message in component_fallback_reasons.items()
            ) or "No live SEO components succeeded."
            return self._stub_fallback(
                seed_topic=seed_topic,
                candidate_topic=candidate_topic,
                seo_query=seo_query,
                reason=reason,
                component_modes=component_modes,
                component_fallback_reasons=component_fallback_reasons,
                component_providers=component_providers,
                component_queries=component_queries,
            )

        return self._live_score(
            seed_topic=seed_topic,
            candidate_topic=candidate_topic,
            seo_query=seo_query,
            overview=overview,
            ideas=ideas or [],
            related_keywords=related_keywords or [],
            serp_competitors=serp_competitors or [],
            organic_results=organic_results or [],
            page_intersection=page_intersection or [],
            component_modes=component_modes,
            component_fallback_reasons=component_fallback_reasons,
            component_providers=component_providers,
            component_queries=component_queries,
        )

    def _fetch_component(
        self,
        *,
        component_name: str,
        component_modes: dict[str, str],
        fallback_reasons: dict[str, str],
        component_queries: dict[str, str],
        queries: list[str],
        fetcher,
        fallback_value=None,
        skip_reason: str | None = None,
        should_skip: bool = False,
    ):
        if should_skip:
            component_modes[component_name] = "stub_fallback"
            if queries:
                component_queries[component_name] = queries[0]
            if skip_reason:
                fallback_reasons[component_name] = skip_reason
            return fallback_value
        last_error: str | None = None
        attempted_queries = queries or [""]
        for query in attempted_queries:
            if query:
                component_queries[component_name] = query
            try:
                value = fetcher(query) if query else fetcher()
                component_modes[component_name] = "live"
                return value
            except (DataForSEOError, OSError, ValueError) as exc:
                last_error = str(exc)
        component_modes[component_name] = "stub_fallback"
        if last_error:
            fallback_reasons[component_name] = last_error
        return fallback_value

    def _page_intersection_urls(
        self,
        organic_results: list[DataForSEOSerpOrganicResult],
    ) -> list[str]:
        urls: list[str] = []
        for item in organic_results:
            if item.url and item.url not in urls:
                urls.append(item.url)
            if len(urls) >= 2:
                break
        return urls

    def _page_intersection_query_variants(
        self,
        organic_results: list[DataForSEOSerpOrganicResult],
    ) -> list[str]:
        urls = self._page_intersection_urls(organic_results)
        if len(urls) < 2:
            return []
        joined = ", ".join(urls)
        return [f"intersect::{joined}", f"union::{joined}"]

    def _fetch_page_intersection(self, query: str) -> list[DataForSEOPageIntersectionKeyword]:
        mode, _, joined_urls = query.partition("::")
        page_urls = [url.strip() for url in joined_urls.split(",") if url.strip()]
        if len(page_urls) < 2:
            return []
        return self._client.page_intersection(
            page_urls=page_urls,
            limit=5,
            intersection_mode=mode or "intersect",
        )

    def _live_score(
        self,
        *,
        seed_topic: str,
        candidate_topic: str,
        seo_query: str,
        overview: DataForSEOKeywordOverview | None,
        ideas: list[DataForSEOKeywordIdea],
        related_keywords: list[DataForSEORelatedKeyword],
        serp_competitors: list[DataForSEOSerpCompetitor],
        organic_results: list[DataForSEOSerpOrganicResult],
        page_intersection: list[DataForSEOPageIntersectionKeyword],
        component_modes: dict[str, str],
        component_fallback_reasons: dict[str, str],
        component_providers: dict[str, str],
        component_queries: dict[str, str],
    ) -> SignalScore:
        search_volume = overview.search_volume if overview and overview.search_volume is not None else None
        competition = overview.competition if overview and overview.competition is not None else None
        cpc = overview.cpc if overview and overview.cpc is not None else None
        idea_count = len(ideas)
        idea_avg_volume = (
            sum(idea.search_volume or 0 for idea in ideas) / idea_count
            if idea_count > 0
            else 0.0
        )
        idea_avg_competition = (
            sum(idea.competition if idea.competition is not None else 0.5 for idea in ideas)
            / idea_count
            if idea_count > 0
            else 0.5
        )
        related_count = len(related_keywords)
        related_avg_competition = (
            sum(
                item.competition if item.competition is not None else 0.5
                for item in related_keywords
            )
            / related_count
            if related_count > 0
            else 0.5
        )
        related_avg_relevance = (
            sum(item.relevance or 0.0 for item in related_keywords) / related_count
            if related_count > 0
            else 0.0
        )
        competitor_count = len(serp_competitors)
        competitor_avg_visibility = (
            sum(item.visibility or 0.0 for item in serp_competitors) / competitor_count
            if competitor_count > 0
            else 0.0
        )
        competitor_avg_position = (
            sum(item.avg_position or 20.0 for item in serp_competitors) / competitor_count
            if competitor_count > 0
            else 20.0
        )
        competitor_avg_rating = (
            sum(item.rating or 0.0 for item in serp_competitors) / competitor_count
            if competitor_count > 0
            else 0.0
        )
        organic_result_count = len(organic_results)
        organic_domains = [item.domain for item in organic_results if item.domain]
        unique_domain_count = len(set(organic_domains))
        top_domain_share = 0.0
        if organic_domains:
            domain_counts: dict[str, int] = {}
            for domain in organic_domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            top_domain_share = max(domain_counts.values()) / len(organic_domains)
        featured_snippet_count = sum(
            1 for item in organic_results if item.is_featured_snippet
        )
        unique_domain_ratio = (
            unique_domain_count / organic_result_count if organic_result_count > 0 else 0.0
        )
        page_overlap_count = len(page_intersection)
        page_overlap_avg_volume = (
            sum(item.search_volume or 0 for item in page_intersection) / page_overlap_count
            if page_overlap_count > 0
            else 0.0
        )
        page_overlap_avg_competition = (
            sum(item.competition if item.competition is not None else 0.5 for item in page_intersection)
            / page_overlap_count
            if page_overlap_count > 0
            else 0.5
        )
        page_overlap_avg_intersection = (
            sum(item.intersection_score or 0.0 for item in page_intersection) / page_overlap_count
            if page_overlap_count > 0
            else 0.0
        )

        volume_score = self._component_score(
            component_name="keywordOverview",
            component_modes=component_modes,
            candidate_topic=candidate_topic,
            fallback_suffix="volume",
            live_score=round(min(100.0, math.log10((search_volume or 0) + 1) * 16.5), 2)
            if search_volume is not None
            else None,
        )
        opportunity_score = self._component_score(
            component_name="keywordOverview",
            component_modes=component_modes,
            candidate_topic=candidate_topic,
            fallback_suffix="opportunity",
            live_score=round(max(0.0, min(100.0, (1.0 - competition) * 100.0)), 2)
            if competition is not None
            else None,
        )
        commercial_score = self._component_score(
            component_name="keywordOverview",
            component_modes=component_modes,
            candidate_topic=candidate_topic,
            fallback_suffix="commercial",
            live_score=round(min(100.0, cpc * 10.0), 2)
            if cpc is not None
            else None,
        )
        expansion_score = self._component_score(
            component_name="keywordIdeas",
            component_modes=component_modes,
            candidate_topic=candidate_topic,
            fallback_suffix="expansion",
            live_score=round(
                min(
                    100.0,
                    (min(idea_count, 5) / 5.0) * 60.0
                    + min(40.0, math.log10(idea_avg_volume + 1) * 10.0)
                    + max(0.0, (0.6 - idea_avg_competition) * 25.0),
                ),
                2,
            )
            if idea_count > 0
            else None,
        )
        competitive_overlap_score = self._component_score(
            component_name="relatedKeywords",
            component_modes=component_modes,
            candidate_topic=candidate_topic,
            fallback_suffix="overlap",
            live_score=round(
                max(
                    0.0,
                    min(
                        100.0,
                        100.0
                        - (min(related_count, 5) / 5.0) * 45.0
                        - min(35.0, related_avg_competition * 35.0)
                        - min(20.0, related_avg_relevance * 20.0),
                    ),
                ),
                2,
            )
            if related_count > 0
            else None,
        )
        serp_crowding_score = self._component_score(
            component_name="serpCompetitors",
            component_modes=component_modes,
            candidate_topic=candidate_topic,
            fallback_suffix="crowding",
            live_score=round(
                max(
                    0.0,
                    min(
                        100.0,
                        100.0
                        - min(40.0, competitor_avg_visibility * 50.0)
                        - min(35.0, max(0.0, (12.0 - competitor_avg_position) * 3.5))
                        - min(25.0, competitor_avg_rating * 0.2),
                    ),
                ),
                2,
            )
            if competitor_count > 0
            else None,
        )
        ownership_diversity_score = self._component_score(
            component_name="organicSerp",
            component_modes=component_modes,
            candidate_topic=candidate_topic,
            fallback_suffix="ownership",
            live_score=round(
                max(
                    0.0,
                    min(
                        100.0,
                        (unique_domain_ratio * 70.0)
                        + ((1.0 - top_domain_share) * 25.0)
                        + max(0.0, 5.0 - (featured_snippet_count * 2.5)),
                    ),
                ),
                2,
            )
            if organic_result_count > 0
            else None,
        )
        editorial_gap_score = self._component_score(
            component_name="pageIntersection",
            component_modes=component_modes,
            candidate_topic=candidate_topic,
            fallback_suffix="editorial_gap",
            live_score=round(
                max(
                    0.0,
                    min(
                        100.0,
                        100.0
                        - (min(page_overlap_count, 5) / 5.0) * 35.0
                        - min(30.0, math.log10(page_overlap_avg_volume + 1) * 9.0)
                        - min(20.0, page_overlap_avg_competition * 25.0)
                        - min(15.0, page_overlap_avg_intersection * 15.0),
                    ),
                ),
                2,
            )
            if page_overlap_count > 0
            else None,
        )
        final_score = round(
            (volume_score * 0.28)
            + (opportunity_score * 0.18)
            + (commercial_score * 0.10)
            + (expansion_score * 0.14)
            + (competitive_overlap_score * 0.12)
            + (serp_crowding_score * 0.07)
            + (ownership_diversity_score * 0.05)
            + (editorial_gap_score * 0.06),
            2,
        )
        live_count = sum(1 for mode in component_modes.values() if mode == "live")
        fallback_count = sum(1 for mode in component_modes.values() if mode == "stub_fallback")
        overall_mode = (
            "live"
            if fallback_count == 0
            else "mixed"
        )

        return SignalScore(
            score=final_score,
            note=(
                "Live DataForSEO keyword data indicates measurable SEO opportunity."
                if overall_mode == "live"
                else "Mixed live and fallback SEO signals indicate measurable opportunity."
            ),
            metadata={
                "provider": "dataforseo_v3_composite",
                "mode": overall_mode,
                "seedTopic": seed_topic,
                "candidateTopic": candidate_topic,
                "seoQuery": seo_query,
                "componentModes": component_modes,
                "componentFallbackReasons": component_fallback_reasons,
                "componentProviders": component_providers,
                "componentQueries": component_queries,
                "rawComponents": {
                    "keyword": overview.keyword if overview is not None else None,
                    "originalTopic": candidate_topic,
                    "normalizedSeoQuery": seo_query,
                    "searchVolume": overview.search_volume if overview is not None else None,
                    "competition": overview.competition if overview is not None else None,
                    "cpc": overview.cpc if overview is not None else None,
                    "lowTopOfPageBid": overview.low_top_of_page_bid if overview is not None else None,
                    "highTopOfPageBid": overview.high_top_of_page_bid if overview is not None else None,
                    "monthlySearchesSample": overview.monthly_searches[:3] if overview is not None else [],
                    "keywordIdeasSample": [
                        {
                            "keyword": idea.keyword,
                            "searchVolume": idea.search_volume,
                            "competition": idea.competition,
                            "cpc": idea.cpc,
                        }
                        for idea in ideas[:3]
                    ],
                    "keywordIdeasCount": idea_count,
                    "keywordIdeasAverageVolume": round(idea_avg_volume, 2),
                    "keywordIdeasAverageCompetition": round(idea_avg_competition, 4),
                    "relatedKeywordsSample": [
                        {
                            "keyword": item.keyword,
                            "searchVolume": item.search_volume,
                            "competition": item.competition,
                            "relevance": item.relevance,
                        }
                        for item in related_keywords[:3]
                    ],
                    "relatedKeywordsCount": related_count,
                    "relatedKeywordsAverageCompetition": round(related_avg_competition, 4),
                    "relatedKeywordsAverageRelevance": round(related_avg_relevance, 4),
                    "serpCompetitorsSample": [
                        {
                            "domain": item.domain,
                            "avgPosition": item.avg_position,
                            "visibility": item.visibility,
                            "rating": item.rating,
                            "etv": item.etv,
                        }
                        for item in serp_competitors[:3]
                    ],
                    "serpCompetitorsCount": competitor_count,
                    "serpCompetitorsAverageVisibility": round(competitor_avg_visibility, 4),
                    "serpCompetitorsAveragePosition": round(competitor_avg_position, 2),
                    "serpCompetitorsAverageRating": round(competitor_avg_rating, 2),
                    "organicSerpSample": [
                        {
                            "domain": item.domain,
                            "url": item.url,
                            "rankGroup": item.rank_group,
                            "rankAbsolute": item.rank_absolute,
                            "featuredSnippet": item.is_featured_snippet,
                        }
                        for item in organic_results[:5]
                    ],
                    "organicSerpResultCount": organic_result_count,
                    "organicSerpUniqueDomainCount": unique_domain_count,
                    "organicSerpUniqueDomainRatio": round(unique_domain_ratio, 4),
                    "organicSerpTopDomainShare": round(top_domain_share, 4),
                    "organicSerpFeaturedSnippetCount": featured_snippet_count,
                    "pageIntersectionSample": [
                        {
                            "keyword": item.keyword,
                            "searchVolume": item.search_volume,
                            "competition": item.competition,
                            "intersectionScore": item.intersection_score,
                        }
                        for item in page_intersection[:3]
                    ],
                    "pageIntersectionCount": page_overlap_count,
                    "pageIntersectionAverageVolume": round(page_overlap_avg_volume, 2),
                    "pageIntersectionAverageCompetition": round(
                        page_overlap_avg_competition, 4
                    ),
                    "pageIntersectionAverageScore": round(page_overlap_avg_intersection, 4),
                },
                "normalizedSubScores": {
                    "volumeScore": volume_score,
                    "opportunityScore": opportunity_score,
                    "commercialScore": commercial_score,
                    "expansionScore": expansion_score,
                    "competitiveOverlapScore": competitive_overlap_score,
                    "serpCrowdingScore": serp_crowding_score,
                    "ownershipDiversityScore": ownership_diversity_score,
                    "editorialGapScore": editorial_gap_score,
                },
                "finalSeoScore": final_score,
            },
        )

    def _component_score(
        self,
        *,
        component_name: str,
        component_modes: dict[str, str],
        candidate_topic: str,
        fallback_suffix: str,
        live_score: float | None,
    ) -> float:
        if component_modes.get(component_name) == "live" and live_score is not None:
            return live_score
        return _bounded_score(f"seo:{fallback_suffix}:{candidate_topic}")

    def _stub_fallback(
        self,
        *,
        seed_topic: str,
        candidate_topic: str,
        seo_query: str,
        reason: str,
        component_modes: dict[str, str] | None = None,
        component_fallback_reasons: dict[str, str] | None = None,
        component_providers: dict[str, str] | None = None,
        component_queries: dict[str, str] | None = None,
    ) -> SignalScore:
        score = _bounded_score(f"seo:{seed_topic}:{candidate_topic}")
        return SignalScore(
            score=score,
            note="Live SEO provider failed; falling back to deterministic score.",
            metadata={
                "provider": "dataforseo_stub",
                "mode": "stub_fallback",
                "seedTopic": seed_topic,
                "candidateTopic": candidate_topic,
                "seoQuery": seo_query,
                "componentModes": component_modes or {
                    "keywordOverview": "stub_fallback",
                    "keywordIdeas": "stub_fallback",
                    "relatedKeywords": "stub_fallback",
                    "serpCompetitors": "stub_fallback",
                    "organicSerp": "stub_fallback",
                    "pageIntersection": "stub_fallback",
                },
                "componentFallbackReasons": component_fallback_reasons or {
                    "seo": reason,
                },
                "componentProviders": component_providers or {
                    "keywordOverview": "dataforseo_v3_keyword_overview",
                    "keywordIdeas": "dataforseo_v3_keyword_ideas",
                    "relatedKeywords": "dataforseo_v3_related_keywords",
                    "serpCompetitors": "dataforseo_v3_serp_competitors",
                    "organicSerp": "dataforseo_v3_organic_serp",
                    "pageIntersection": "dataforseo_v3_page_intersection",
                },
                "componentQueries": component_queries or {
                    "keywordOverview": seo_query,
                    "keywordIdeas": seo_query,
                    "relatedKeywords": seo_query,
                    "serpCompetitors": seo_query,
                    "organicSerp": seo_query,
                    "pageIntersection": "",
                },
                "rawComponents": {},
                "normalizedSubScores": {},
                "finalSeoScore": score,
                "fallbackReason": reason,
            },
        )


class TopicDiscoveryAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def discover(
        self,
        *,
        industry: str,
        target_audience: str | None,
    ) -> list[DiscoveredTopicCandidate]:
        if self._settings.discovery_mode == "live":
            try:
                return self._discover_live(
                    industry=industry,
                    target_audience=target_audience,
                )
            except Exception as exc:
                fallback = self._discover_stub(
                    industry=industry,
                    target_audience=target_audience,
                )
                return [
                    DiscoveredTopicCandidate(
                        topic=item.topic,
                        discovery_note=f"{item.discovery_note} Live discovery failed; stub fallback was used.",
                        source_metadata={
                            **item.source_metadata,
                            "mode": "stub_fallback",
                            "fallbackReason": str(exc),
                        },
                    )
                    for item in fallback
                ]

        return self._discover_stub(
            industry=industry,
            target_audience=target_audience,
        )

    def _discover_stub(
        self,
        *,
        industry: str,
        target_audience: str | None,
    ) -> list[DiscoveredTopicCandidate]:
        normalized = industry.strip().lower()
        audience = target_audience or "general operators"

        if "health" in normalized or "medical" in normalized or "clinic" in normalized:
            topics = [
                "ambient AI scribes in healthcare",
                "remote patient monitoring reimbursement",
                "GLP-1 care coordination workflows",
                "prior authorization automation in healthcare",
                "nurse staffing analytics",
            ]
        else:
            topics = [
                f"{industry} workflow automation",
                f"{industry} AI operations",
                f"{industry} compliance checklist",
                f"{industry} process optimization",
                f"{industry} team enablement playbook",
            ]

        return [
            DiscoveredTopicCandidate(
                topic=topic,
                discovery_note=(
                    f"Discovered as a candidate trend for {audience} operating in {industry}."
                ),
                source_metadata={
                    "provider": "topic_discovery_stub",
                    "mode": "stub",
                    "industry": industry,
                    "targetAudience": target_audience,
                },
            )
            for topic in topics
        ]

    def _discover_live(
        self,
        *,
        industry: str,
        target_audience: str | None,
    ) -> list[DiscoveredTopicCandidate]:
        audience = target_audience or "general operators"
        query = f"{industry} {audience} trends"
        titles = _news_rss_titles(query, limit=10)
        topics = _topic_variants_from_titles(titles, industry=industry)
        if not topics:
            raise RuntimeError("No live discovery topics were extracted from provider results.")

        return [
            DiscoveredTopicCandidate(
                topic=topic,
                discovery_note=(
                    f"Discovered from live news signals for {audience} operating in {industry}."
                ),
                source_metadata={
                    "provider": "google_news_rss",
                    "mode": "live",
                    "industry": industry,
                    "targetAudience": target_audience,
                    "headlineSamples": titles[:3],
                },
            )
            for topic in topics
        ]


class MarketAwarenessCrew:
    def __init__(
        self,
        *,
        discovery_agent: TopicDiscoveryAgent,
        trend_agent: TrendAnalysisAgent,
        social_agent: SocialListeningAgent,
        seo_agent: SeoGapAgent,
    ) -> None:
        self._discovery_agent = discovery_agent
        self._trend_agent = trend_agent
        self._social_agent = social_agent
        self._seo_agent = seo_agent

    def discover(
        self,
        *,
        industry: str,
        target_audience: str | None,
    ) -> list[DiscoveredTopicCandidate]:
        return self._discovery_agent.discover(
            industry=industry,
            target_audience=target_audience,
        )

    def qualify(
        self,
        *,
        seed_topic: str,
        target_audience: str | None,
    ) -> list[QualifiedTopicCandidate]:
        variants = [
            seed_topic,
            f"{seed_topic} best practices",
            f"{seed_topic} checklist",
        ]
        return self.qualify_topics(
            seed_topic_context=seed_topic,
            candidate_topics=variants,
            target_audience=target_audience,
        )

    def qualify_topics(
        self,
        *,
        seed_topic_context: str,
        candidate_topics: list[str],
        target_audience: str | None,
        discovery_metadata: dict[str, DiscoveredTopicCandidate] | None = None,
    ) -> list[QualifiedTopicCandidate]:
        qualified_topics: list[QualifiedTopicCandidate] = []
        settings = self._trend_agent._settings
        weights = _normalized_market_weights(settings)

        for candidate_topic in candidate_topics:
            trend = self._trend_agent.analyze(seed_topic_context, candidate_topic)
            social = self._social_agent.analyze(seed_topic_context, candidate_topic)
            seo = self._seo_agent.analyze(seed_topic_context, candidate_topic)
            weighted_components = {
                "trend": round(trend.score * weights["trend"], 2),
                "social": round(social.score * weights["social"], 2),
                "seo": round(seo.score * weights["seo"], 2),
            }
            total = round(
                weighted_components["trend"]
                + weighted_components["social"]
                + weighted_components["seo"],
                2,
            )
            audience_note = target_audience or "general operators"
            provider_modes = {
                "trend": str(trend.metadata.get("mode") or "unknown"),
                "social": str(social.metadata.get("mode") or "unknown"),
                "seo": str(seo.metadata.get("mode") or "unknown"),
            }
            live_signal_count = sum(
                1 for mode in provider_modes.values() if mode == "live"
            )
            fallback_signal_count = sum(
                1 for mode in provider_modes.values() if mode == "stub_fallback"
            )
            stub_signal_count = sum(
                1 for mode in provider_modes.values() if mode == "stub"
            )
            qualification_status = (
                "qualified"
                if total >= settings.market_min_qualified_score
                else "watchlist"
            )
            source_metadata: dict[str, object] = {
                "trend": trend.metadata,
                "social": social.metadata,
                "seo": seo.metadata,
                "qualificationMode": settings.qualification_mode,
                "rawScores": {
                    "trend": trend.score,
                    "social": social.score,
                    "seo": seo.score,
                },
                "weightedScore": total,
                "calibration": {
                    "weights": weights,
                    "weightedComponents": weighted_components,
                    "minimumQualifiedScore": settings.market_min_qualified_score,
                    "qualificationStatus": qualification_status,
                    "providerModes": provider_modes,
                    "liveSignalCount": live_signal_count,
                    "stubSignalCount": stub_signal_count,
                    "stubFallbackSignalCount": fallback_signal_count,
                },
            }
            discovered = discovery_metadata.get(candidate_topic) if discovery_metadata else None
            if discovered is not None:
                source_metadata["discovery"] = discovered.source_metadata
                source_metadata["discoveryNote"] = discovered.discovery_note

            qualified_topics.append(
                QualifiedTopicCandidate(
                    topic=candidate_topic,
                    trend_score=trend.score,
                    social_score=social.score,
                    seo_score=seo.score,
                    total_score=total,
                    qualification_note=(
                        f"Qualified for {audience_note} with a {qualification_status} scorecard across trend, social, and SEO signals."
                    ),
                    source_metadata=source_metadata,
                )
            )

        return sorted(
            qualified_topics,
            key=lambda candidate: candidate.total_score,
            reverse=True,
        )


class SitemapIngestorAgent:
    def derive_internal_links(
        self,
        *,
        topic: str,
        indexed_pages: list[dict[str, str]],
    ) -> list[InternalLinkSuggestion]:
        suggestions: list[InternalLinkSuggestion] = []

        for page in indexed_pages[:3]:
            title = page["title"]
            suggestions.append(
                InternalLinkSuggestion(
                    url=page["url"],
                    title=title,
                    anchor_text=title,
                    rationale=f"Use this page to reinforce {topic} with an internal reference to {title}.",
                )
            )

        return suggestions


class StructureStyleAgent:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm_provider = llm_provider

    def build_blueprint(
        self,
        *,
        topic: str,
        target_audience: str | None,
        content_language: str | None,
        geo_context: str | None,
        internal_links: list[InternalLinkSuggestion],
    ) -> BlueprintOutput:
        response = self._llm_provider.complete_json(
            operation_name="build_article_blueprint",
            payload={
                "topic": topic,
                "target_audience": target_audience,
                "content_language": content_language,
                "geo_context": geo_context,
                "internal_links": [
                    {
                        "url": link.url,
                        "title": link.title,
                        "anchor_text": link.anchor_text,
                        "rationale": link.rationale,
                    }
                    for link in internal_links
                ],
            },
            system_prompt=(
                "You are the Structure & Style Agent. Return valid JSON with exactly three fields: "
                "angle, sections, style_guidance."
            ),
            user_prompt=(
                "Build an explicit article blueprint for the qualified topic.\n"
                f"topic: {topic}\n"
                f"target_audience: {target_audience or 'General audience'}\n"
                f"content_language: {content_language or 'English'}\n"
                f"geo_context: {geo_context or 'No specific geographic context'}\n"
                f"internal_links: {[link.title for link in internal_links]}\n"
                "Requirements:\n"
                "- sections must be an ordered list of section names.\n"
                "- style_guidance must describe tone and structure expectations.\n"
                "- Keep the plan deterministic and easy to follow.\n"
                "- Return JSON only."
            ),
            response_model=BlueprintResponse,
        )

        return BlueprintOutput(
            topic=topic,
            target_audience=target_audience,
            content_language=content_language,
            geo_context=geo_context,
            angle=response.angle,
            sections=response.sections,
            style_guidance=response.style_guidance,
            internal_links=internal_links,
        )


class ContentGenerationAgent:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm_provider = llm_provider
        self.role = "Content Generation Agent"
        self.goal = "Create a structured article draft from the approved topic and blueprint."
        self.backstory = (
            "A deterministic draft writer used for the LCE generation loop."
        )

    def generate(
        self,
        *,
        topic: str,
        target_audience: str | None,
        content_language: str | None,
        geo_context: str | None,
        revision_number: int,
        qa_feedback: str | None,
        blueprint: BlueprintOutput | None,
    ) -> DraftOutput:
        response = self._llm_provider.complete_json(
            operation_name="generate_draft",
            payload={
                "topic": topic,
                "target_audience": target_audience,
                "content_language": content_language,
                "geo_context": geo_context,
                "revision_number": revision_number,
                "qa_feedback": qa_feedback,
                "blueprint": None
                if blueprint is None
                else {
                    "angle": blueprint.angle,
                    "sections": blueprint.sections,
                    "style_guidance": blueprint.style_guidance,
                    "internal_links": [
                        {
                            "title": link.title,
                            "url": link.url,
                            "anchor_text": link.anchor_text,
                        }
                        for link in blueprint.internal_links
                    ],
                },
            },
            system_prompt=(
                f"You are the {self.role}. {self.goal} {self.backstory} "
                "Return valid JSON with exactly two fields: title and body."
            ),
            user_prompt=(
                "Create a markdown article draft.\n"
                f"topic: {topic}\n"
                f"target_audience: {target_audience or 'General audience'}\n"
                f"content_language: {content_language or 'English'}\n"
                f"geo_context: {geo_context or 'No specific geographic context'}\n"
                f"revision_number: {revision_number}\n"
                f"qa_feedback: {qa_feedback or 'None'}\n"
                f"blueprint_angle: {blueprint.angle if blueprint else 'Use a practical guide angle.'}\n"
                f"blueprint_sections: {blueprint.sections if blueprint else ['Overview', 'Core Points', 'Next Steps']}\n"
                f"blueprint_style_guidance: {blueprint.style_guidance if blueprint else 'Use clear, neutral, reviewable language.'}\n"
                f"internal_links: {[link.anchor_text for link in blueprint.internal_links] if blueprint else []}\n"
                "Requirements:\n"
                "- The body must be markdown.\n"
                "- Include an explicit Audience line.\n"
                "- Write in the requested content language.\n"
                "- Reflect the requested geographic context when one is provided.\n"
                "- Include a section that references the internal link guidance when provided.\n"
                "- For revision_number > 0, address the QA feedback directly.\n"
                "- Return JSON only."
            ),
            response_model=DraftResponse,
        )

        return DraftOutput(title=response.title, body=response.body)


class QaComplianceAgent:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm_provider = llm_provider
        self.role = "QA & Compliance Agent"
        self.goal = "Check that a draft meets the minimum review and compliance rules."
        self.backstory = (
            "A deterministic QA reviewer for the LCE execution loop."
        )

    def review(
        self,
        draft: DraftOutput,
        blueprint: BlueprintOutput | None,
        *,
        content_language: str | None,
        geo_context: str | None,
    ) -> QaResult:
        response = self._llm_provider.complete_json(
            operation_name="review_draft",
            payload={
                "title": draft.title,
                "body": draft.body,
                "content_language": content_language,
                "geo_context": geo_context,
                "expected_sections": blueprint.sections if blueprint else [],
                "expected_links": [
                    link.anchor_text for link in blueprint.internal_links
                ]
                if blueprint
                else [],
            },
            system_prompt=(
                f"You are the {self.role}. {self.goal} {self.backstory} "
                "Return valid JSON with exactly two fields: passed and feedback."
            ),
            user_prompt=(
                "Review the markdown article draft against the Phase 2 and Phase 3 rules.\n"
                "Required checks:\n"
                "- The article states the target audience explicitly.\n"
                "- The article includes a compliance checklist section.\n"
                "- The article uses neutral, reviewable language.\n"
                "- The article honors the requested language.\n"
                "- The article honors the requested geographic context when one is provided.\n"
                "- When blueprint sections are provided, the article should reflect them.\n"
                "- The feedback must tell the generation agent what to fix if the draft fails.\n"
                "Return JSON only.\n"
                f"title: {draft.title}\n"
                f"content_language: {content_language or 'English'}\n"
                f"geo_context: {geo_context or 'No specific geographic context'}\n"
                f"expected_sections: {blueprint.sections if blueprint else []}\n"
                f"expected_links: {[link.anchor_text for link in blueprint.internal_links] if blueprint else []}\n"
                f"body:\n{draft.body}"
            ),
            response_model=QaResponse,
        )

        return QaResult(passed=response.passed, feedback=response.feedback)
