from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from .llm import LLMProvider


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


class ContentGenerationAgent:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self._llm_provider = llm_provider
        self.role = "Content Generation Agent"
        self.goal = "Create a structured article draft from a manual topic."
        self.backstory = (
            "A deterministic draft writer used for the first LCE execution loop."
        )

    def generate(
        self,
        *,
        topic: str,
        target_audience: str | None,
        revision_number: int,
        qa_feedback: str | None,
    ) -> DraftOutput:
        response = self._llm_provider.complete_json(
            operation_name="generate_draft",
            payload={
                "topic": topic,
                "target_audience": target_audience,
                "revision_number": revision_number,
                "qa_feedback": qa_feedback,
            },
            system_prompt=(
                f"You are the {self.role}. {self.goal} {self.backstory} "
                "Return valid JSON with exactly two fields: title and body."
            ),
            user_prompt=(
                "Create a markdown article draft for the provided manual topic.\n"
                f"topic: {topic}\n"
                f"target_audience: {target_audience or 'General audience'}\n"
                f"revision_number: {revision_number}\n"
                f"qa_feedback: {qa_feedback or 'None'}\n"
                "Requirements:\n"
                "- The body must be markdown.\n"
                "- Include an explicit Audience line.\n"
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
            "A deterministic QA reviewer for the first LCE execution loop."
        )

    def review(self, draft: DraftOutput) -> QaResult:
        response = self._llm_provider.complete_json(
            operation_name="review_draft",
            payload={
                "title": draft.title,
                "body": draft.body,
            },
            system_prompt=(
                f"You are the {self.role}. {self.goal} {self.backstory} "
                "Return valid JSON with exactly two fields: passed and feedback."
            ),
            user_prompt=(
                "Review the markdown article draft against the Phase 2 rules.\n"
                "Required checks:\n"
                "- The article states the target audience explicitly.\n"
                "- The article includes a compliance checklist section.\n"
                "- The article uses neutral, reviewable language.\n"
                "- The feedback must tell the generation agent what to fix if the draft fails.\n"
                "Return JSON only.\n"
                f"title: {draft.title}\n"
                f"body:\n{draft.body}"
            ),
            response_model=QaResponse,
        )

        return QaResult(passed=response.passed, feedback=response.feedback)
