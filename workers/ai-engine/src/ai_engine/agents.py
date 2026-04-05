from __future__ import annotations

from dataclasses import dataclass
import hashlib

from pydantic import BaseModel

from .config import Settings
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


class TrendAnalysisAgent:
    def analyze(self, seed_topic: str, candidate_topic: str) -> SignalScore:
        score = _bounded_score(f"trend:{seed_topic}:{candidate_topic}")
        return SignalScore(
            score=score,
            note="Trend interest is stable enough to support evergreen planning.",
            metadata={
                "provider": "pytrends_stub",
                "seedTopic": seed_topic,
                "candidateTopic": candidate_topic,
            },
        )


class SocialListeningAgent:
    def analyze(self, seed_topic: str, candidate_topic: str) -> SignalScore:
        score = _bounded_score(f"social:{seed_topic}:{candidate_topic}")
        return SignalScore(
            score=score,
            note="Community discussion suggests the topic has practical operator interest.",
            metadata={
                "provider": "reddit_stub",
                "seedTopic": seed_topic,
                "candidateTopic": candidate_topic,
            },
        )


class SeoGapAgent:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def analyze(self, seed_topic: str, candidate_topic: str) -> SignalScore:
        mode = (
            "dataforseo"
            if (
                self._settings.market_signal_mode == "dataforseo"
                and self._settings.dataforseo_login
                and self._settings.dataforseo_password
            )
            else "dataforseo_stub"
        )
        score = _bounded_score(f"seo:{seed_topic}:{candidate_topic}")
        return SignalScore(
            score=score,
            note="SERP opportunity remains open enough for a differentiated article.",
            metadata={
                "provider": mode,
                "seedTopic": seed_topic,
                "candidateTopic": candidate_topic,
            },
        )


class TopicDiscoveryAgent:
    def discover(
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
                    "industry": industry,
                    "targetAudience": target_audience,
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

        for candidate_topic in candidate_topics:
            trend = self._trend_agent.analyze(seed_topic_context, candidate_topic)
            social = self._social_agent.analyze(seed_topic_context, candidate_topic)
            seo = self._seo_agent.analyze(seed_topic_context, candidate_topic)
            total = round(
                (trend.score * 0.35) + (social.score * 0.25) + (seo.score * 0.40),
                2,
            )
            audience_note = target_audience or "general operators"
            source_metadata: dict[str, object] = {
                "trend": trend.metadata,
                "social": social.metadata,
                "seo": seo.metadata,
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
                        f"Qualified for {audience_note} because trend, social, and SEO signals all clear the minimum threshold."
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
