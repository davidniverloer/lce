from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
import uuid

from crewai.flow.flow import Flow, FlowState, listen, start
from pydantic import Field
from sqlalchemy.orm import Session

from .agents import (
    BlueprintOutput,
    ContentGenerationAgent,
    DraftOutput,
    InternalLinkSuggestion,
    QaComplianceAgent,
)
from .models import (
    DraftRevision,
    GenerationRun,
    GenerationTask,
    QaFeedback,
    RepositoryArticle,
)


class ArticleGenerationState(FlowState):
    organization_id: str
    campaign_id: str
    task_id: str
    topic: str
    target_audience: str | None = None
    content_language: str | None = None
    geo_context: str | None = None
    output_formats: list[str] = Field(default_factory=list)
    qualified_topic_id: str | None = None
    blueprint_id: str | None = None
    blueprint: dict | None = None
    run_id: str
    status: str = "processing"
    revision_number: int = 0
    max_revision_attempts: int = 1
    current_title: str | None = None
    current_body: str | None = None
    qa_passed: bool = False
    qa_feedback: str | None = None
    completed_article_id: str | None = None


@dataclass(frozen=True)
class GenerationRequest:
    organization_id: str
    campaign_id: str
    task_id: str
    topic: str
    target_audience: str | None
    content_language: str | None
    geo_context: str | None
    output_formats: list[str]
    qualified_topic_id: str | None = None
    blueprint_id: str | None = None
    blueprint: dict | None = None


def _hydrate_blueprint(raw_blueprint: dict | None) -> BlueprintOutput | None:
    if not raw_blueprint:
        return None

    internal_links = [
        InternalLinkSuggestion(
            url=str(item["url"]),
            title=str(item["title"]),
            anchor_text=str(item["anchorText"]),
            rationale=str(item["rationale"]),
        )
        for item in raw_blueprint.get("internalLinks", [])
        if isinstance(item, dict)
    ]

    return BlueprintOutput(
        topic=str(raw_blueprint["topic"]),
        target_audience=(
            str(raw_blueprint["targetAudience"])
            if raw_blueprint.get("targetAudience") is not None
            else None
        ),
        content_language=(
            str(raw_blueprint["contentLanguage"])
            if raw_blueprint.get("contentLanguage") is not None
            else None
        ),
        geo_context=(
            str(raw_blueprint["geoContext"])
            if raw_blueprint.get("geoContext") is not None
            else None
        ),
        angle=str(raw_blueprint["angle"]),
        sections=[str(item) for item in raw_blueprint.get("sections", [])],
        style_guidance=str(raw_blueprint["styleGuidance"]),
        internal_links=internal_links,
    )


class ArticleGenerationFlow(Flow[ArticleGenerationState]):
    def __init__(
        self,
        *,
        request: GenerationRequest,
        session: Session,
        content_agent: ContentGenerationAgent,
        qa_agent: QaComplianceAgent,
    ) -> None:
        initial_state = ArticleGenerationState(
            organization_id=request.organization_id,
            campaign_id=request.campaign_id,
            task_id=request.task_id,
            topic=request.topic,
            target_audience=request.target_audience,
            content_language=request.content_language,
            geo_context=request.geo_context,
            output_formats=request.output_formats,
            qualified_topic_id=request.qualified_topic_id,
            blueprint_id=request.blueprint_id,
            blueprint=request.blueprint,
            run_id=str(uuid.uuid4()),
        )
        super().__init__(initial_state=initial_state)
        self._session = session
        self._content_agent = content_agent
        self._qa_agent = qa_agent
        self._run: GenerationRun | None = None

    @start()
    def initialize_run(self) -> str:
        task = self._get_task()
        task.status = "processing"

        self._run = GenerationRun(
            id=self.state.run_id,
            organization_id=self.state.organization_id,
            task_id=self.state.task_id,
            campaign_id=self.state.campaign_id,
            status="processing",
            state_json=self._state_payload(),
        )
        self._session.add(self._run)
        self._session.flush()
        self._persist_run_state("processing")
        return "initialized"

    @listen(initialize_run)
    def generate_initial_draft(self) -> str:
        draft = self._content_agent.generate(
            topic=self.state.topic,
            target_audience=self.state.target_audience,
            content_language=self.state.content_language,
            geo_context=self.state.geo_context,
            revision_number=0,
            qa_feedback=None,
            blueprint=self._blueprint(),
        )
        self._store_draft(draft, revision_number=0)
        return "draft_generated"

    @listen(generate_initial_draft)
    def qa_initial_draft(self) -> str:
        self._review_current_draft(revision_number=0)
        return "initial_review_complete"

    @listen(qa_initial_draft)
    def revise_once_if_needed(self) -> str:
        if self.state.qa_passed:
            self._persist_run_state("approved")
            return "approved_without_revision"

        draft = self._content_agent.generate(
            topic=self.state.topic,
            target_audience=self.state.target_audience,
            content_language=self.state.content_language,
            geo_context=self.state.geo_context,
            revision_number=1,
            qa_feedback=self.state.qa_feedback,
            blueprint=self._blueprint(),
        )
        self.state.revision_number = 1
        self._store_draft(draft, revision_number=1)
        return "revision_generated"

    @listen(revise_once_if_needed)
    def qa_revision(self) -> str:
        if self.state.qa_passed:
            return "revision_skipped"

        self._review_current_draft(revision_number=1)
        return "revision_review_complete"

    @listen(qa_revision)
    def finalize_article(self) -> str:
        if not self.state.qa_passed:
            raise ValueError("Draft did not pass QA after one bounded revision")

        article_id = str(uuid.uuid4())
        self._session.add(
            RepositoryArticle(
                id=article_id,
                organization_id=self.state.organization_id,
                campaign_id=self.state.campaign_id,
                task_id=self.state.task_id,
                title=self.state.current_title or "Untitled Article",
                body=self.state.current_body or "",
                status="completed",
            )
        )

        task = self._get_task()
        task.status = "completed"
        task.completed_at = datetime.utcnow()

        self.state.completed_article_id = article_id
        self._persist_run_state("completed")
        return "article_stored"

    def _blueprint(self) -> BlueprintOutput | None:
        return _hydrate_blueprint(self.state.blueprint)

    def _get_task(self) -> GenerationTask:
        task = self._session.get(GenerationTask, self.state.task_id)
        if task is None:
            raise ValueError(f"Generation task not found: {self.state.task_id}")
        return task

    def _store_draft(self, draft: DraftOutput, *, revision_number: int) -> None:
        self.state.current_title = draft.title
        self.state.current_body = draft.body
        self.state.revision_number = revision_number

        self._session.add(
            DraftRevision(
                id=str(uuid.uuid4()),
                organization_id=self.state.organization_id,
                task_id=self.state.task_id,
                run_id=self.state.run_id,
                revision_number=revision_number,
                title=draft.title,
                body=draft.body,
            )
        )
        self._persist_run_state("draft_ready")

    def _review_current_draft(self, *, revision_number: int) -> None:
        draft = DraftOutput(
            title=self.state.current_title or "Untitled Draft",
            body=self.state.current_body or "",
        )
        review = self._qa_agent.review(
            draft,
            self._blueprint(),
            content_language=self.state.content_language,
            geo_context=self.state.geo_context,
        )
        self.state.qa_passed = review.passed
        self.state.qa_feedback = review.feedback
        self.state.status = "approved" if review.passed else "revision_requested"

        self._session.add(
            QaFeedback(
                id=str(uuid.uuid4()),
                organization_id=self.state.organization_id,
                task_id=self.state.task_id,
                run_id=self.state.run_id,
                revision_number=revision_number,
                passed=review.passed,
                feedback=review.feedback,
            )
        )
        self._persist_run_state(self.state.status)

    def _persist_run_state(self, status: str) -> None:
        self.state.status = status
        run = self._run or self._session.get(GenerationRun, self.state.run_id)
        if run is None:
            raise ValueError(f"Generation run not found: {self.state.run_id}")

        self._run = run
        run.status = status
        run.state_json = self._state_payload()

    def _state_payload(self) -> dict:
        return json.loads(self.state.model_dump_json())
