from __future__ import annotations

import logging
from typing import Any

from core.domain.ai.value_objects import AIProvider, ModelConfig
from core.infrastructure.agents.base_agent import BaseAgent
from core.infrastructure.services.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a document summarisation assistant. "
    "Produce a clear, concise summary of the provided text. "
    "Focus on key facts, decisions, and actionable items."
)


class SummaryAgent(BaseAgent):
    """Agent responsible for generating document summaries via an LLM.

    Supported actions:
        - summarize: Generate a summary of the provided text.
        - extract_fields: Extract structured fields from text.
    """

    def __init__(
        self,
        llm_provider_name: str = "openai",
        model_config: ModelConfig | None = None,
        **llm_kwargs: Any,
    ) -> None:
        super().__init__(name="SummaryAgent")
        config = model_config or ModelConfig(
            provider=AIProvider.OPENAI,
            model_name="gpt-4o-mini",
        )
        self._llm = LLMFactory.create(llm_provider_name, config, **llm_kwargs)

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        if not action:
            return self._error("Missing required field: action")

        try:
            if action == "summarize":
                return await self._summarize(task)
            if action == "extract_fields":
                return await self._extract_fields(task)
            return self._error(f"Unknown action: {action}")
        except Exception as exc:
            logger.exception("SummaryAgent action=%s failed", action)
            return self._error(str(exc))

    async def _summarize(self, task: dict[str, Any]) -> dict[str, Any]:
        text = task.get("text")
        if not text:
            return self._error("text is required for summarize")

        max_tokens = task.get("max_tokens", 500)
        system_prompt = task.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

        summary = await self._llm.summarize(
            text,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )

        logger.info("Summary generated: %d chars", len(summary))
        return self._ok(
            data={
                "summary": summary,
                "original_length": len(text),
                "summary_length": len(summary),
            },
            message=f"Summary generated ({len(summary)} chars)",
        )

    async def _extract_fields(self, task: dict[str, Any]) -> dict[str, Any]:
        text = task.get("text")
        fields = task.get("fields")

        if not text:
            return self._error("text is required for extract_fields")
        if not fields or not isinstance(fields, list):
            return self._error("fields (list) is required for extract_fields")

        system_prompt = task.get(
            "system_prompt",
            "Extract the following fields from the text as a JSON object.",
        )

        extracted = await self._llm.extract(
            text,
            fields=fields,
            system_prompt=system_prompt,
        )

        logger.info("Extracted %d fields", len(extracted))
        return self._ok(
            data={"extracted": extracted, "fields": fields},
            message=f"Extracted {len(extracted)} fields",
        )
