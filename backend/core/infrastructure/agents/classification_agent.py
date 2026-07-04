from __future__ import annotations

import logging
from typing import Any

from core.domain.ai.value_objects import AIProvider, ModelConfig
from core.domain.documents.value_objects import DocumentType
from core.infrastructure.agents.base_agent import BaseAgent
from core.infrastructure.services.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES: list[str] = [dt.value for dt in DocumentType]

DEFAULT_SYSTEM_PROMPT = (
    "You are a document classification assistant. "
    "Classify the given text into exactly one category from the provided list. "
    "Respond with ONLY: category_name (confidence_score between 0 and 1)"
)


class ClassificationAgent(BaseAgent):
    """Agent responsible for classifying documents by type using an LLM.

    Supported actions:
        - classify:      Classify text into one of the predefined document types.
        - classify_custom: Classify text into user-provided categories.
    """

    def __init__(
        self,
        llm_provider_name: str = "openai",
        model_config: ModelConfig | None = None,
        **llm_kwargs: Any,
    ) -> None:
        super().__init__(name="ClassificationAgent")
        config = model_config or ModelConfig(
            provider=AIProvider.OPENAI,
            model_name="gpt-4o-mini",
        )
        self._llm = LLMFactory.create(llm_provider_name, config, **llm_kwargs)
        self._categories = list(DEFAULT_CATEGORIES)

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        if not action:
            return self._error("Missing required field: action")

        try:
            if action == "classify":
                return await self._classify(task)
            if action == "classify_custom":
                return await self._classify_custom(task)
            return self._error(f"Unknown action: {action}")
        except Exception as exc:
            logger.exception("ClassificationAgent action=%s failed", action)
            return self._error(str(exc))

    async def _classify(self, task: dict[str, Any]) -> dict[str, Any]:
        text = task.get("text")
        if not text:
            return self._error("text is required for classify")

        categories = task.get("categories", self._categories)
        system_prompt = task.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

        category, confidence = await self._llm.classify(
            text,
            categories=categories,
            system_prompt=system_prompt,
        )

        logger.info("Classified as %s (confidence=%.2f)", category, confidence)
        return self._ok(
            data={
                "category": category,
                "confidence": confidence,
                "categories_checked": categories,
            },
            message=f"Classified as {category} ({confidence:.0%})",
        )

    async def _classify_custom(self, task: dict[str, Any]) -> dict[str, Any]:
        text = task.get("text")
        categories = task.get("categories")

        if not text:
            return self._error("text is required for classify_custom")
        if not categories or not isinstance(categories, list):
            return self._error("categories (list) is required for classify_custom")

        system_prompt = task.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

        category, confidence = await self._llm.classify(
            text,
            categories=categories,
            system_prompt=system_prompt,
        )

        logger.info("Custom classification: %s (confidence=%.2f)", category, confidence)
        return self._ok(
            data={
                "category": category,
                "confidence": confidence,
                "categories_checked": categories,
            },
            message=f"Classified as {category} ({confidence:.0%})",
        )
