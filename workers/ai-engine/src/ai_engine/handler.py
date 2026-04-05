from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .agents import (
    ContentGenerationAgent,
    DiscoveredTopicCandidate,
    MarketAwarenessCrew,
    QaComplianceAgent,
    QualifiedTopicCandidate,
    SeoGapAgent,
    SitemapIngestorAgent,
    StructureStyleAgent,
    SocialListeningAgent,
    TopicDiscoveryAgent,
    TrendAnalysisAgent,
)
from .config import Settings
from .flow import ArticleGenerationFlow, GenerationRequest
from .llm import LLMProvider
from .models import (
    ArticleBlueprint,
    EventReceipt,
    GenerationTask,
    IndexedPage,
    InternalLink,
    MarketAnalysisRequest,
    OutboxEvent,
    ProcessedEventLog,
    QualifiedTopic,
    SitemapIngestion,
    RepositoryArticle,
)

GENERATION_REQUESTED = "GenerationRequested"
TOPIC_GENERATION_REQUESTED = "TopicGenerationRequested"
TOPIC_QUALIFIED = "TopicQualified"
SITEMAP_UPDATED = "SitemapUpdated"
BLUEPRINT_VALIDATED = "BlueprintValidated"


@dataclass(frozen=True)
class BaseEvent:
    event_id: str
    event_type: str
    version: str
    timestamp: datetime


@dataclass(frozen=True)
class TopicGenerationRequestedEvent(BaseEvent):
    organization_id: str
    campaign_id: str
    analysis_request_id: str
    seed_topic: str | None
    industry: str | None
    auto_discover: bool
    target_audience: str | None
    content_language: str | None
    geo_context: str | None


@dataclass(frozen=True)
class TopicQualifiedEvent(BaseEvent):
    organization_id: str
    campaign_id: str
    analysis_request_id: str
    qualified_topic_id: str
    topic: str
    score: float
    target_audience: str | None


@dataclass(frozen=True)
class SitemapUpdatedEvent(BaseEvent):
    organization_id: str
    campaign_id: str
    sitemap_ingestion_id: str
    sitemap_url: str
    indexed_page_count: int


@dataclass(frozen=True)
class BlueprintValidatedEvent(BaseEvent):
    organization_id: str
    campaign_id: str
    qualified_topic_id: str
    sitemap_ingestion_id: str | None
    blueprint_id: str


@dataclass(frozen=True)
class GenerationRequestedEvent(BaseEvent):
    request: GenerationRequest


def parse_event(raw: dict) -> BaseEvent | GenerationRequestedEvent:
    if not isinstance(raw, dict):
        raise ValueError("Event body must be an object")

    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Event payload must be an object")

    required_top_level_fields = ("eventId", "eventType", "version", "timestamp")
    for field in required_top_level_fields:
        if not isinstance(raw.get(field), str) or not str(raw[field]).strip():
            raise ValueError(f"Missing required field: {field}")

    event_type = str(raw["eventType"])
    timestamp = datetime.fromisoformat(str(raw["timestamp"]).replace("Z", "+00:00"))
    common_kwargs = {
        "event_id": str(raw["eventId"]),
        "event_type": event_type,
        "version": str(raw["version"]),
        "timestamp": timestamp,
    }

    if event_type == TOPIC_GENERATION_REQUESTED:
        required = ("organizationId", "campaignId", "analysisRequestId")
        for field in required:
            if not isinstance(payload.get(field), str) or not str(payload[field]).strip():
                raise ValueError(f"Missing required payload field: {field}")

        seed_topic = payload.get("seedTopic")
        if seed_topic is not None and not isinstance(seed_topic, str):
            raise ValueError("seedTopic must be a string or null")

        industry = payload.get("industry")
        if industry is not None and not isinstance(industry, str):
            raise ValueError("industry must be a string or null")

        auto_discover = bool(payload.get("autoDiscover", False))
        if not seed_topic and not industry:
            raise ValueError("seedTopic or industry is required")

        target_audience = payload.get("targetAudience")
        if target_audience is not None and not isinstance(target_audience, str):
            raise ValueError("targetAudience must be a string or null")

        content_language = payload.get("contentLanguage")
        if content_language is not None and not isinstance(content_language, str):
            raise ValueError("contentLanguage must be a string or null")

        geo_context = payload.get("geoContext")
        if geo_context is not None and not isinstance(geo_context, str):
            raise ValueError("geoContext must be a string or null")

        return TopicGenerationRequestedEvent(
            organization_id=str(payload["organizationId"]),
            campaign_id=str(payload["campaignId"]),
            analysis_request_id=str(payload["analysisRequestId"]),
            seed_topic=seed_topic,
            industry=industry,
            auto_discover=auto_discover,
            target_audience=target_audience,
            content_language=content_language,
            geo_context=geo_context,
            **common_kwargs,
        )

    if event_type == TOPIC_QUALIFIED:
        required = (
            "organizationId",
            "campaignId",
            "analysisRequestId",
            "qualifiedTopicId",
            "topic",
            "score",
        )
        for field in required:
            if payload.get(field) is None:
                raise ValueError(f"Missing required payload field: {field}")

        target_audience = payload.get("targetAudience")
        if target_audience is not None and not isinstance(target_audience, str):
            raise ValueError("targetAudience must be a string or null")

        return TopicQualifiedEvent(
            organization_id=str(payload["organizationId"]),
            campaign_id=str(payload["campaignId"]),
            analysis_request_id=str(payload["analysisRequestId"]),
            qualified_topic_id=str(payload["qualifiedTopicId"]),
            topic=str(payload["topic"]),
            score=float(payload["score"]),
            target_audience=target_audience,
            **common_kwargs,
        )

    if event_type == SITEMAP_UPDATED:
        required = (
            "organizationId",
            "campaignId",
            "sitemapIngestionId",
            "sitemapUrl",
            "indexedPageCount",
        )
        for field in required:
            if payload.get(field) is None:
                raise ValueError(f"Missing required payload field: {field}")

        return SitemapUpdatedEvent(
            organization_id=str(payload["organizationId"]),
            campaign_id=str(payload["campaignId"]),
            sitemap_ingestion_id=str(payload["sitemapIngestionId"]),
            sitemap_url=str(payload["sitemapUrl"]),
            indexed_page_count=int(payload["indexedPageCount"]),
            **common_kwargs,
        )

    if event_type == BLUEPRINT_VALIDATED:
        required = ("organizationId", "campaignId", "qualifiedTopicId", "blueprintId")
        for field in required:
            if not isinstance(payload.get(field), str) or not str(payload[field]).strip():
                raise ValueError(f"Missing required payload field: {field}")

        sitemap_ingestion_id = payload.get("sitemapIngestionId")
        if sitemap_ingestion_id is not None and not isinstance(sitemap_ingestion_id, str):
            raise ValueError("sitemapIngestionId must be a string or null")

        return BlueprintValidatedEvent(
            organization_id=str(payload["organizationId"]),
            campaign_id=str(payload["campaignId"]),
            qualified_topic_id=str(payload["qualifiedTopicId"]),
            sitemap_ingestion_id=sitemap_ingestion_id,
            blueprint_id=str(payload["blueprintId"]),
            **common_kwargs,
        )

    if event_type == GENERATION_REQUESTED:
        required = ("organizationId", "campaignId", "taskId", "topic")
        for field in required:
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

        content_language = payload.get("contentLanguage")
        if content_language is not None and not isinstance(content_language, str):
            raise ValueError("contentLanguage must be a string or null")

        geo_context = payload.get("geoContext")
        if geo_context is not None and not isinstance(geo_context, str):
            raise ValueError("geoContext must be a string or null")

        blueprint_id = payload.get("blueprintId")
        if blueprint_id is not None and not isinstance(blueprint_id, str):
            raise ValueError("blueprintId must be a string or null")

        blueprint = payload.get("blueprint")
        if blueprint is not None and not isinstance(blueprint, dict):
            raise ValueError("blueprint must be an object or null")

        return GenerationRequestedEvent(
            request=GenerationRequest(
                organization_id=str(payload["organizationId"]),
                campaign_id=str(payload["campaignId"]),
                task_id=str(payload["taskId"]),
                topic=str(payload["topic"]),
                target_audience=target_audience,
                content_language=content_language,
                geo_context=geo_context,
                output_formats=list(output_formats),
                blueprint_id=blueprint_id,
                blueprint=blueprint,
            ),
            **common_kwargs,
        )

    raise ValueError(f"Unsupported event type: {event_type}")


def process_event(
    *,
    session_factory: sessionmaker,
    consumer_name: str,
    settings: Settings,
    event: BaseEvent | GenerationRequestedEvent,
    llm_provider: LLMProvider,
) -> bool:
    with session_factory() as session:
        session: Session

        try:
            organization_id = _organization_id(event)
            session.add(
                ProcessedEventLog(
                    organization_id=organization_id,
                    event_id=event.event_id,
                    consumer_name=consumer_name,
                )
            )
            session.flush()

            if isinstance(event, TopicGenerationRequestedEvent):
                _process_topic_generation_requested(
                    session=session,
                    event=event,
                    settings=settings,
                )
            elif isinstance(event, TopicQualifiedEvent):
                _process_topic_qualified(
                    session=session,
                    event=event,
                    llm_provider=llm_provider,
                )
            elif isinstance(event, SitemapUpdatedEvent):
                _process_sitemap_updated(
                    session=session,
                    event=event,
                    llm_provider=llm_provider,
                )
            elif isinstance(event, BlueprintValidatedEvent):
                _process_blueprint_validated(session=session, event=event)
            elif isinstance(event, GenerationRequestedEvent):
                _process_generation_requested(
                    session=session,
                    event=event,
                    llm_provider=llm_provider,
                )
            else:
                raise ValueError(f"Unhandled event type: {event.event_type}")

            _record_receipt(
                session=session,
                organization_id=organization_id,
                event_id=event.event_id,
                event_type=event.event_type,
                consumer_name=consumer_name,
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            return False

        return True


def _organization_id(event: BaseEvent | GenerationRequestedEvent) -> str:
    if isinstance(event, GenerationRequestedEvent):
        return event.request.organization_id
    return event.organization_id


def _record_receipt(
    *,
    session: Session,
    organization_id: str,
    event_id: str,
    event_type: str,
    consumer_name: str,
) -> None:
    session.add(
        EventReceipt(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            event_id=event_id,
            event_type=event_type,
            consumer_name=consumer_name,
        )
    )


def _enqueue_event(
    *,
    session: Session,
    organization_id: str,
    event_type: str,
    payload: dict,
) -> None:
    event_id = str(uuid.uuid4())
    session.add(
        OutboxEvent(
            id=event_id,
            organization_id=organization_id,
            event_type=event_type,
            payload={
                "eventId": event_id,
                "eventType": event_type,
                "version": "1.0",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": payload,
            },
            processed=False,
        )
    )


def _normalize_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _tokenize(value: str) -> set[str]:
    return {token for token in _normalize_text(value).split(" ") if token}


def _semantic_similarity(left: str, right: str) -> float:
    normalized_left = _normalize_text(left)
    normalized_right = _normalize_text(right)
    if not normalized_left or not normalized_right:
        return 0.0

    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    intersection = left_tokens.intersection(right_tokens)
    union = left_tokens.union(right_tokens)
    jaccard = (len(intersection) / len(union)) if union else 0.0
    sequence_ratio = SequenceMatcher(None, normalized_left, normalized_right).ratio()
    containment = 1.0 if normalized_left in normalized_right or normalized_right in normalized_left else 0.0
    return round(max(jaccard, sequence_ratio, containment), 4)


def _prior_topic_and_article_texts(
    *,
    session: Session,
    organization_id: str,
) -> list[str]:
    prior_topics = (
        session.query(QualifiedTopic.topic)
        .filter(QualifiedTopic.organization_id == organization_id)
        .all()
    )
    prior_articles = (
        session.query(RepositoryArticle.title, RepositoryArticle.body)
        .filter(RepositoryArticle.organization_id == organization_id)
        .all()
    )

    texts = [topic for (topic,) in prior_topics if isinstance(topic, str) and topic.strip()]
    for title, body in prior_articles:
        if isinstance(title, str) and title.strip():
            texts.append(title)
        if isinstance(body, str) and body.strip():
            texts.append(body[:1200])
    return texts


def _apply_novelty_rules(
    *,
    session: Session,
    settings: Settings,
    organization_id: str,
    candidates: list[QualifiedTopicCandidate],
) -> list[QualifiedTopicCandidate]:
    prior_texts = _prior_topic_and_article_texts(
        session=session,
        organization_id=organization_id,
    )
    exact_duplicates = {_normalize_text(text) for text in prior_texts}

    unique_candidates: list[QualifiedTopicCandidate] = []
    seen_candidate_topics: set[str] = set()
    for candidate in candidates:
        normalized_topic = _normalize_text(candidate.topic)
        if not normalized_topic or normalized_topic in exact_duplicates:
            continue
        if normalized_topic in seen_candidate_topics:
            continue
        seen_candidate_topics.add(normalized_topic)
        unique_candidates.append(candidate)

    reranked_candidates: list[QualifiedTopicCandidate] = []
    for candidate in unique_candidates:
        similarity = 0.0
        closest_match: str | None = None
        for prior_text in prior_texts:
            current_similarity = _semantic_similarity(candidate.topic, prior_text)
            if current_similarity > similarity:
                similarity = current_similarity
                closest_match = prior_text[:160]

        novelty_penalty = 0.0
        if similarity >= settings.market_novelty_threshold:
            normalized_similarity = (
                (similarity - settings.market_novelty_threshold)
                / (1.0 - settings.market_novelty_threshold)
            )
            novelty_penalty = round(
                min(
                    settings.market_max_novelty_penalty,
                    normalized_similarity * settings.market_max_novelty_penalty,
                ),
                2,
            )

        adjusted_score = round(max(0.0, candidate.total_score - novelty_penalty), 2)
        reranked_candidates.append(
            QualifiedTopicCandidate(
                topic=candidate.topic,
                trend_score=candidate.trend_score,
                social_score=candidate.social_score,
                seo_score=candidate.seo_score,
                total_score=adjusted_score,
                qualification_note=(
                    f"{candidate.qualification_note} Novelty penalty applied: {novelty_penalty}."
                    if novelty_penalty > 0
                    else f"{candidate.qualification_note} Topic cleared the novelty check."
                ),
                source_metadata={
                    **candidate.source_metadata,
                    "novelty": {
                        "semanticSimilarity": similarity,
                        "noveltyPenalty": novelty_penalty,
                        "closestPriorMatch": closest_match,
                        "threshold": settings.market_novelty_threshold,
                        "maxPenalty": settings.market_max_novelty_penalty,
                    },
                    "rawWeightedScore": candidate.total_score,
                    "adjustedScore": adjusted_score,
                    "fallbackInfluence": {
                        "fallbackWeightShare": (
                            candidate.source_metadata.get("calibration", {}).get("fallbackWeightShare")
                            if isinstance(candidate.source_metadata.get("calibration"), dict)
                            else None
                        ),
                        "providerModes": (
                            candidate.source_metadata.get("calibration", {}).get("providerModes")
                            if isinstance(candidate.source_metadata.get("calibration"), dict)
                            else {}
                        ),
                    },
                },
            )
        )

    sorted_candidates = sorted(
        reranked_candidates,
        key=lambda candidate: candidate.total_score,
        reverse=True,
    )
    annotated: list[QualifiedTopicCandidate] = []
    for index, candidate in enumerate(sorted_candidates, start=1):
        next_score = (
            sorted_candidates[index].total_score
            if index < len(sorted_candidates)
            else None
        )
        annotated.append(
            QualifiedTopicCandidate(
                topic=candidate.topic,
                trend_score=candidate.trend_score,
                social_score=candidate.social_score,
                seo_score=candidate.seo_score,
                total_score=candidate.total_score,
                qualification_note=candidate.qualification_note,
                source_metadata={
                    **candidate.source_metadata,
                    "selectionRank": index,
                    "selectedForBlueprint": index == 1,
                    "scoreGapToNext": (
                        round(candidate.total_score - next_score, 2)
                        if next_score is not None
                        else None
                    ),
                    "selectionValidation": {
                        "rawWeightedScore": candidate.source_metadata.get("rawWeightedScore")
                        or candidate.source_metadata.get("weightedScore"),
                        "adjustedScore": candidate.source_metadata.get("adjustedScore")
                        or candidate.total_score,
                        "scoreGapToNext": (
                            round(candidate.total_score - next_score, 2)
                            if next_score is not None
                            else None
                        ),
                        "selected": index == 1,
                        "confidenceScore": (
                            candidate.source_metadata.get("calibration", {}).get("confidenceScore")
                            if isinstance(candidate.source_metadata.get("calibration"), dict)
                            else None
                        ),
                        "confidenceBand": (
                            candidate.source_metadata.get("calibration", {}).get("confidenceBand")
                            if isinstance(candidate.source_metadata.get("calibration"), dict)
                            else None
                        ),
                    },
                    "providerSources": [
                        metadata.get("provider")
                        for metadata in (
                            candidate.source_metadata.get("discovery"),
                            candidate.source_metadata.get("trend"),
                            candidate.source_metadata.get("social"),
                            candidate.source_metadata.get("seo"),
                        )
                        if isinstance(metadata, dict) and metadata.get("provider")
                    ],
                    "discoveryMode": (
                        candidate.source_metadata.get("discovery", {}).get("mode")
                        if isinstance(candidate.source_metadata.get("discovery"), dict)
                        else None
                    ),
                    "status": {
                        **(
                            candidate.source_metadata.get("status")
                            if isinstance(candidate.source_metadata.get("status"), dict)
                            else {}
                        ),
                        "selection": {
                            "rank": index,
                            "selectedForBlueprint": index == 1,
                            "scoreGapToNext": (
                                round(candidate.total_score - next_score, 2)
                                if next_score is not None
                                else None
                            ),
                        },
                    },
                },
            )
        )

    return annotated


def _process_topic_generation_requested(
    *,
    session: Session,
    event: TopicGenerationRequestedEvent,
    settings: Settings,
) -> None:
    request = session.get(MarketAnalysisRequest, event.analysis_request_id)
    if request is None:
        raise ValueError(f"Market analysis request not found: {event.analysis_request_id}")

    request.status = "processing"

    crew = MarketAwarenessCrew(
        discovery_agent=TopicDiscoveryAgent(settings),
        trend_agent=TrendAnalysisAgent(settings),
        social_agent=SocialListeningAgent(settings),
        seo_agent=SeoGapAgent(settings),
    )
    candidates: list[QualifiedTopicCandidate]
    if event.auto_discover:
        if not event.industry:
            raise ValueError("industry is required when auto discovery is enabled")

        discovered_topics = crew.discover(
            industry=event.industry,
            target_audience=event.target_audience,
        )
        request.discovered_topics = [
            {
                "topic": candidate.topic,
                "discoveryNote": candidate.discovery_note,
                "sourceMetadata": candidate.source_metadata,
            }
            for candidate in discovered_topics
        ]
        candidates = crew.qualify_topics(
            seed_topic_context=event.industry,
            candidate_topics=[candidate.topic for candidate in discovered_topics],
            target_audience=event.target_audience,
            discovery_metadata={
                candidate.topic: candidate for candidate in discovered_topics
            },
        )
    else:
        if not event.seed_topic:
            raise ValueError("seedTopic is required when auto discovery is disabled")
        candidates = crew.qualify(
            seed_topic=event.seed_topic,
            target_audience=event.target_audience,
        )

    candidates = _apply_novelty_rules(
        session=session,
        settings=settings,
        organization_id=event.organization_id,
        candidates=candidates,
    )

    top_candidate_id: str | None = None
    top_candidate_score = -1.0

    for candidate in candidates:
        topic_id = str(uuid.uuid4())
        if candidate.total_score > top_candidate_score:
            top_candidate_id = topic_id
            top_candidate_score = candidate.total_score

        session.add(
            QualifiedTopic(
                id=topic_id,
                organization_id=event.organization_id,
                campaign_id=event.campaign_id,
                analysis_request_id=event.analysis_request_id,
                topic=candidate.topic,
                score=candidate.total_score,
                trend_score=candidate.trend_score,
                social_score=candidate.social_score,
                seo_score=candidate.seo_score,
                qualification_note=candidate.qualification_note,
                source_metadata=candidate.source_metadata,
            )
        )

    request.status = "completed"

    if top_candidate_id is None:
        raise ValueError(
            "Market analysis did not produce any unique qualified topics after novelty filtering"
        )

    top_candidate = candidates[0]
    _enqueue_event(
        session=session,
        organization_id=event.organization_id,
        event_type=TOPIC_QUALIFIED,
        payload={
            "organizationId": event.organization_id,
            "campaignId": event.campaign_id,
            "analysisRequestId": event.analysis_request_id,
            "qualifiedTopicId": top_candidate_id,
            "topic": top_candidate.topic,
            "score": top_candidate.total_score,
            "targetAudience": event.target_audience,
        },
    )


def _process_topic_qualified(
    *,
    session: Session,
    event: TopicQualifiedEvent,
    llm_provider: LLMProvider,
) -> None:
    qualified_topic = session.get(QualifiedTopic, event.qualified_topic_id)
    if qualified_topic is None:
        raise ValueError(f"Qualified topic not found: {event.qualified_topic_id}")

    sitemap = (
        session.query(SitemapIngestion)
        .filter(
            SitemapIngestion.organization_id == event.organization_id,
            SitemapIngestion.campaign_id == event.campaign_id,
            SitemapIngestion.status == "ready",
        )
        .order_by(SitemapIngestion.updated_at.desc())
        .first()
    )

    request = session.get(MarketAnalysisRequest, event.analysis_request_id)
    content_language = request.content_language if request else None
    geo_context = request.geo_context if request else None

    _ensure_blueprint(
        session=session,
        organization_id=event.organization_id,
        campaign_id=event.campaign_id,
        qualified_topic=qualified_topic,
        sitemap=sitemap,
        target_audience=event.target_audience,
        content_language=content_language,
        geo_context=geo_context,
        llm_provider=llm_provider,
    )


def _process_sitemap_updated(
    *,
    session: Session,
    event: SitemapUpdatedEvent,
    llm_provider: LLMProvider,
) -> None:
    sitemap = session.get(SitemapIngestion, event.sitemap_ingestion_id)
    if sitemap is None:
        raise ValueError(f"Sitemap ingestion not found: {event.sitemap_ingestion_id}")

    qualified_topic = (
        session.query(QualifiedTopic)
        .filter(
            QualifiedTopic.organization_id == event.organization_id,
            QualifiedTopic.campaign_id == event.campaign_id,
        )
        .order_by(QualifiedTopic.score.desc(), QualifiedTopic.created_at.asc())
        .first()
    )

    if qualified_topic is None:
        return

    request = session.get(MarketAnalysisRequest, qualified_topic.analysis_request_id)
    target_audience = request.target_audience if request else None
    content_language = request.content_language if request else None
    geo_context = request.geo_context if request else None

    _ensure_blueprint(
        session=session,
        organization_id=event.organization_id,
        campaign_id=event.campaign_id,
        qualified_topic=qualified_topic,
        sitemap=sitemap,
        target_audience=target_audience,
        content_language=content_language,
        geo_context=geo_context,
        llm_provider=llm_provider,
    )


def _ensure_blueprint(
    *,
    session: Session,
    organization_id: str,
    campaign_id: str,
    qualified_topic: QualifiedTopic,
    sitemap: SitemapIngestion | None,
    target_audience: str | None,
    content_language: str | None,
    geo_context: str | None,
    llm_provider: LLMProvider,
) -> None:
    existing_blueprint = (
        session.query(ArticleBlueprint)
        .filter(ArticleBlueprint.qualified_topic_id == qualified_topic.id)
        .first()
    )
    if existing_blueprint is not None:
        return

    indexed_pages: list[IndexedPage] = []
    if sitemap is not None:
        indexed_pages = (
            session.query(IndexedPage)
            .filter(
                IndexedPage.organization_id == organization_id,
                IndexedPage.sitemap_ingestion_id == sitemap.id,
            )
            .order_by(IndexedPage.created_at.asc())
            .all()
        )

    internal_links = []
    site_context: dict[str, object] = {
        "sitemapUsed": False,
        "indexedPageCount": 0,
        "coverageTopics": [],
        "coverageGaps": [],
        "pages": [],
        "linkingGuidance": "No sitemap was provided, so internal linking guidance is intentionally minimal.",
    }
    if indexed_pages:
        sitemap_agent = SitemapIngestorAgent()
        site_context = sitemap_agent.build_site_context(
            topic=qualified_topic.topic,
            indexed_pages=[
                {
                    "url": page.url,
                    "title": page.title,
                }
                for page in indexed_pages
            ],
        )
        internal_links = sitemap_agent.derive_internal_links(
            topic=qualified_topic.topic,
            indexed_pages=[
                {
                    "url": page.url,
                    "title": page.title,
                }
                for page in indexed_pages
            ],
        )
    structure_agent = StructureStyleAgent(llm_provider)
    blueprint = structure_agent.build_blueprint(
        topic=qualified_topic.topic,
        target_audience=target_audience,
        content_language=content_language,
        geo_context=geo_context,
        internal_links=internal_links,
        qualification_metadata=qualified_topic.source_metadata,
        site_context=site_context,
    )

    blueprint_id = str(uuid.uuid4())
    blueprint_json = {
        "topic": blueprint.topic,
        "targetAudience": blueprint.target_audience,
        "contentLanguage": blueprint.content_language,
        "geoContext": blueprint.geo_context,
        "angle": blueprint.angle,
        "sections": blueprint.sections,
        "styleGuidance": blueprint.style_guidance,
        "differentiationAngle": blueprint.differentiation_angle,
        "differentiationRationale": blueprint.differentiation_rationale,
        "targetDelta": blueprint.target_delta,
        "audienceShift": blueprint.audience_shift,
        "siteContext": blueprint.site_context,
        "status": {
            "blueprintReady": True,
            "differentiationReady": bool(
                blueprint.differentiation_angle
                and blueprint.differentiation_rationale
                and blueprint.target_delta
            ),
            "sitemapUsed": bool(indexed_pages),
            "internalLinkCount": len(blueprint.internal_links),
            "siteAware": bool(blueprint.site_context.get("pages")),
        },
        "internalLinks": [
            {
                "url": link.url,
                "title": link.title,
                "anchorText": link.anchor_text,
                "rationale": link.rationale,
                "pageSummary": link.page_summary,
                "pageRole": link.page_role,
                "topicCluster": link.topic_cluster,
                "relevanceScore": link.relevance_score,
                "placementHint": link.placement_hint,
            }
            for link in blueprint.internal_links
        ],
    }

    session.add(
        ArticleBlueprint(
            id=blueprint_id,
            organization_id=organization_id,
            campaign_id=campaign_id,
            qualified_topic_id=qualified_topic.id,
            sitemap_ingestion_id=sitemap.id if sitemap is not None else None,
            topic=qualified_topic.topic,
            status="validated",
            blueprint_json=blueprint_json,
        )
    )
    for link in blueprint.internal_links:
        session.add(
            InternalLink(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                campaign_id=campaign_id,
                blueprint_id=blueprint_id,
                url=link.url,
                title=link.title,
                anchor_text=link.anchor_text,
                rationale=link.rationale,
            )
        )

    _enqueue_event(
        session=session,
        organization_id=organization_id,
        event_type=BLUEPRINT_VALIDATED,
        payload={
            "organizationId": organization_id,
            "campaignId": campaign_id,
            "qualifiedTopicId": qualified_topic.id,
            "sitemapIngestionId": sitemap.id if sitemap is not None else None,
            "blueprintId": blueprint_id,
        },
    )


def _process_blueprint_validated(
    *,
    session: Session,
    event: BlueprintValidatedEvent,
) -> None:
    existing_task = (
        session.query(GenerationTask)
        .filter(
            GenerationTask.organization_id == event.organization_id,
            GenerationTask.blueprint_id == event.blueprint_id,
        )
        .first()
    )
    if existing_task is not None:
        return

    blueprint = session.get(ArticleBlueprint, event.blueprint_id)
    if blueprint is None:
        raise ValueError(f"Blueprint not found: {event.blueprint_id}")

    blueprint_json = blueprint.blueprint_json
    task_id = str(uuid.uuid4())
    session.add(
        GenerationTask(
            id=task_id,
            organization_id=event.organization_id,
            campaign_id=event.campaign_id,
            topic=blueprint.topic,
            target_audience=blueprint_json.get("targetAudience"),
            content_language=blueprint_json.get("contentLanguage"),
            geo_context=blueprint_json.get("geoContext"),
            output_formats=["markdown_article"],
            status="queued",
            qualified_topic_id=event.qualified_topic_id,
            blueprint_id=event.blueprint_id,
            blueprint_json=blueprint_json,
        )
    )
    _enqueue_event(
        session=session,
        organization_id=event.organization_id,
        event_type=GENERATION_REQUESTED,
        payload={
            "organizationId": event.organization_id,
            "campaignId": event.campaign_id,
            "taskId": task_id,
            "topic": blueprint.topic,
            "targetAudience": blueprint_json.get("targetAudience"),
            "contentLanguage": blueprint_json.get("contentLanguage"),
            "geoContext": blueprint_json.get("geoContext"),
            "outputFormats": ["markdown_article"],
            "blueprintId": event.blueprint_id,
            "blueprint": blueprint_json,
        },
    )


def _process_generation_requested(
    *,
    session: Session,
    event: GenerationRequestedEvent,
    llm_provider: LLMProvider,
) -> None:
    flow = ArticleGenerationFlow(
        request=event.request,
        session=session,
        content_agent=ContentGenerationAgent(llm_provider),
        qa_agent=QaComplianceAgent(llm_provider),
    )
    flow.kickoff()
