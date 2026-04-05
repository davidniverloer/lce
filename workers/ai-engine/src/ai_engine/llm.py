from __future__ import annotations

import json
import logging
import re
from typing import Any, Protocol, TypeVar

import litellm
from pydantic import BaseModel, ValidationError

from .config import Settings

LOGGER = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMProviderError(RuntimeError):
    pass


class LLMProvider(Protocol):
    def complete_json(
        self,
        *,
        operation_name: str,
        payload: dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T: ...


class StubLLMProvider:
    def complete_json(
        self,
        *,
        operation_name: str,
        payload: dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        del system_prompt
        del user_prompt

        if operation_name == "generate_draft":
            topic = str(payload["topic"])
            target_audience = payload.get("target_audience")
            revision_number = int(payload["revision_number"])
            qa_feedback = payload.get("qa_feedback")
            blueprint = payload.get("blueprint")

            audience = (
                str(target_audience).strip()
                if isinstance(target_audience, str) and target_audience.strip()
                else "General audience"
            )
            title = f"{topic}: Practical Guide"
            sections = (
                blueprint.get("sections")
                if isinstance(blueprint, dict) and isinstance(blueprint.get("sections"), list)
                else ["Overview", "Core Points", "Next Steps"]
            )
            style_guidance = (
                str(blueprint.get("style_guidance"))
                if isinstance(blueprint, dict) and blueprint.get("style_guidance")
                else "Use clear, neutral, reviewable language."
            )
            internal_links = (
                blueprint.get("internal_links")
                if isinstance(blueprint, dict) and isinstance(blueprint.get("internal_links"), list)
                else []
            )
            body_lines = [
                f"# {title}",
                "",
                f"Audience: {audience}",
                "",
                f"{topic} matters because teams need a reliable, easy-to-review starting point.",
                "This draft explains the main idea, the expected outcome, and a simple action plan.",
                "",
                f"Style Guidance: {style_guidance}",
            ]

            for section in sections:
                body_lines.extend(
                    [
                        "",
                        f"## {section}",
                        f"- Explain how {topic} supports this section.",
                        "- Keep the guidance specific and reviewable.",
                    ]
                )

            if internal_links:
                body_lines.extend(["", "## Internal Link Opportunities"])
                for item in internal_links:
                    if isinstance(item, dict):
                        body_lines.append(
                            f"- Reference [{item.get('anchor_text', 'related guidance')}]({item.get('url', '#')}) to connect this article to existing site knowledge."
                        )

            body_lines.extend(
                [
                    "",
                    "## Next Steps",
                    "- Confirm the proposed process with the operating team.",
                    "- Review the plan against the compliance checklist.",
                ]
            )

            if revision_number > 0:
                body_lines.extend(
                    [
                        "",
                        "## Compliance Checklist",
                        "- Contains an explicit audience section.",
                        "- Uses neutral, reviewable language.",
                        "- Includes a concrete next step.",
                        "",
                        f"Revision note: {qa_feedback or 'Updated to address QA feedback.'}",
                    ]
                )

            return response_model.model_validate(
                {
                    "title": title,
                    "body": "\n".join(body_lines),
                }
            )

        if operation_name == "build_article_blueprint":
            topic = str(payload["topic"])
            target_audience = payload.get("target_audience")

            audience = (
                str(target_audience).strip()
                if isinstance(target_audience, str) and target_audience.strip()
                else "General audience"
            )

            return response_model.model_validate(
                {
                    "angle": f"Show {audience.lower()} how to operationalize {topic} with clear internal references.",
                    "sections": [
                        "Context",
                        "Operational Workflow",
                        "Internal Alignment",
                        "Execution Checklist",
                    ],
                    "style_guidance": (
                        "Use concise, reviewable language with explicit operational recommendations "
                        "and natural internal-link callouts."
                    ),
                }
            )

        if operation_name == "review_draft":
            body = str(payload["body"])
            expected_sections = payload.get("expected_sections") or []

            if "## Compliance Checklist" not in body:
                return response_model.model_validate(
                    {
                        "passed": False,
                        "feedback": (
                            "Add a compliance checklist section and state how the draft satisfies it."
                        ),
                    }
                )

            if "Audience:" not in body:
                return response_model.model_validate(
                    {
                        "passed": False,
                        "feedback": "State the target audience explicitly in the article body.",
                    }
                )

            if isinstance(expected_sections, list):
                missing_section = next(
                    (
                        section
                        for section in expected_sections
                        if isinstance(section, str) and f"## {section}" not in body
                    ),
                    None,
                )
                if missing_section:
                    return response_model.model_validate(
                        {
                            "passed": False,
                            "feedback": (
                                f"Add the planned section '{missing_section}' so the draft follows the approved blueprint."
                            ),
                        }
                    )

            return response_model.model_validate(
                {
                    "passed": True,
                    "feedback": "Draft passes the minimum QA and compliance checks.",
                }
            )

        raise LLMProviderError(f"Unsupported stub operation: {operation_name}")


class LiteLLMProvider:
    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        api_base: str | None,
        temperature: float,
        timeout_seconds: float,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._api_base = api_base
        self._temperature = temperature
        self._timeout_seconds = timeout_seconds

    def complete_json(
        self,
        *,
        operation_name: str,
        payload: dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        del payload

        try:
            response = litellm.completion(
                model=self._model,
                api_key=self._api_key,
                api_base=self._api_base,
                temperature=self._temperature,
                timeout=self._timeout_seconds,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except litellm.AuthenticationError as exc:
            LOGGER.exception("LiteLLM authentication failed for %s", operation_name)
            raise LLMProviderError("LiteLLM authentication failed") from exc
        except litellm.APIError as exc:
            LOGGER.exception("LiteLLM API error during %s", operation_name)
            raise LLMProviderError(f"LiteLLM API error during {operation_name}") from exc
        except Exception as exc:
            LOGGER.exception("Unexpected LiteLLM failure during %s", operation_name)
            raise LLMProviderError(
                f"Unexpected LiteLLM failure during {operation_name}"
            ) from exc

        self._log_usage(operation_name, response)

        content = self._extract_content(response)
        if not content:
            raise LLMProviderError(
                f"LiteLLM returned an empty response for {operation_name}"
            )

        try:
            json_payload = self._extract_json_payload(content)
            return response_model.model_validate(json_payload)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            LOGGER.exception("Failed to parse LiteLLM response for %s", operation_name)
            raise LLMProviderError(
                f"Failed to parse LiteLLM response for {operation_name}"
            ) from exc

    def _extract_content(self, response: Any) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            return ""

        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", "")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
            return "\n".join(text_parts)

        return ""

    def _extract_json_payload(self, content: str) -> dict[str, Any]:
        stripped = content.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed

        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in LLM response")

        parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("LLM response JSON must be an object")
        return parsed

    def _log_usage(self, operation_name: str, response: Any) -> None:
        usage = getattr(response, "usage", None)
        hidden_params = getattr(response, "_hidden_params", None)
        response_cost = (
            hidden_params.get("response_cost")
            if isinstance(hidden_params, dict)
            else None
        )

        LOGGER.info(
            "LiteLLM call completed operation=%s model=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s response_cost=%s",
            operation_name,
            self._model,
            getattr(usage, "prompt_tokens", None),
            getattr(usage, "completion_tokens", None),
            getattr(usage, "total_tokens", None),
            response_cost,
        )


def create_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_mode == "stub":
        LOGGER.info("Using deterministic stub LLM provider")
        return StubLLMProvider()

    if settings.llm_mode == "openai":
        model = settings.llm_model or "openai/gpt-4.1-mini"
        api_key = settings.llm_api_key or settings.openai_api_key
        api_base = settings.llm_api_base or settings.openai_base_url

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY or AI_ENGINE_LLM_API_KEY is required when AI_ENGINE_LLM_MODE=openai"
            )

        LOGGER.info(
            "Using OpenAI via LiteLLM model=%s api_base=%s",
            model,
            api_base,
        )
        return LiteLLMProvider(
            model=model,
            api_key=api_key,
            api_base=api_base,
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    if settings.llm_mode == "litellm":
        model = settings.llm_model
        api_key = settings.llm_api_key
        api_base = settings.llm_api_base

        if not model:
            raise RuntimeError(
                "AI_ENGINE_LLM_MODEL is required when AI_ENGINE_LLM_MODE=litellm"
            )

        if model.startswith("openai/"):
            api_key = api_key or settings.openai_api_key
            api_base = api_base or settings.openai_base_url

        LOGGER.info(
            "Using LiteLLM provider model=%s api_base=%s",
            model,
            api_base,
        )
        return LiteLLMProvider(
            model=model,
            api_key=api_key,
            api_base=api_base,
            temperature=settings.llm_temperature,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    raise RuntimeError(f"Unsupported AI_ENGINE_LLM_MODE: {settings.llm_mode}")
