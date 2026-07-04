from __future__ import annotations

import logging
from typing import Any

from core.domain.documents.value_objects import Confidence, Language
from core.infrastructure.agents.base_agent import BaseAgent
from core.infrastructure.services.ocr_engine import PaddleOCREngine

logger = logging.getLogger(__name__)


class OCRAgent(BaseAgent):
    """Agent responsible for OCR text extraction with confidence scoring.

    Supported actions:
        - extract_text: Extract text from image/PDF bytes.
        - detect_language: Detect the primary language of text.
    """

    def __init__(
        self,
        ocr_engine: PaddleOCREngine | None = None,
        *,
        lang: str = "en",
        use_gpu: bool = False,
    ) -> None:
        super().__init__(name="OCRAgent")
        self._engine = ocr_engine or PaddleOCREngine(lang=lang, use_gpu=use_gpu)

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        if not action:
            return self._error("Missing required field: action")

        try:
            if action == "extract_text":
                return await self._extract_text(task)
            if action == "detect_language":
                return await self._detect_language(task)
            return self._error(f"Unknown action: {action}")
        except Exception as exc:
            logger.exception("OCRAgent action=%s failed", action)
            return self._error(str(exc))

    async def _extract_text(self, task: dict[str, Any]) -> dict[str, Any]:
        content = task.get("content")
        content_type = task.get("content_type", "image/png")

        if content is None:
            return self._error("content (bytes) is required for extract_text")

        if isinstance(content, str):
            content = content.encode("utf-8")

        lang_hint_raw = task.get("language_hint")
        lang_hint: Language | None = None
        if lang_hint_raw:
            try:
                lang_hint = Language(lang_hint_raw)
            except ValueError:
                lang_hint = None

        text = await self._engine.extract_text(
            content,
            content_type=content_type,
            language_hint=lang_hint,
        )

        confidence: Confidence = await self._engine.get_confidence(text)

        logger.info(
            "OCR extracted %d chars (confidence=%.2f)",
            len(text),
            confidence.value,
        )
        return self._ok(
            data={
                "text": text,
                "char_count": len(text),
                "confidence": confidence.value,
                "confidence_percentage": confidence.percentage,
                "is_high_confidence": confidence.is_high,
            },
            message=f"Extracted {len(text)} characters",
        )

    async def _detect_language(self, task: dict[str, Any]) -> dict[str, Any]:
        text = task.get("text")
        if not text:
            return self._error("text is required for detect_language")

        lang: Language = await self._engine.detect_language(text)

        return self._ok(
            data={
                "language": lang.value,
                "language_name": lang.name,
            },
            message=f"Detected language: {lang.value}",
        )
