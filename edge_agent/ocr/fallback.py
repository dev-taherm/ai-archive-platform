"""Shared OCR fallback logic — used by both the worker and the API routes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Extensions eligible for OCR fallback
_OCR_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp", ".pdf",
})

# Minimum text length before triggering OCR
_MIN_TEXT_LENGTH = 50


def ocr_fallback(text: str, file_path: Path, ocr_engine: Any, language_hint: str | None = None) -> tuple[str, bool]:
    """Attempt OCR if extracted text is too short.

    Returns (final_text, ocr_used).
    """
    if text and len(text.strip()) >= _MIN_TEXT_LENGTH:
        return text, False

    suffix = file_path.suffix.lower()
    if suffix not in _OCR_EXTENSIONS:
        return text, False

    try:
        content = file_path.read_bytes()
        from edge_agent.core.models import Language
        hint = None
        if language_hint:
            try:
                hint = Language(language_hint)
            except ValueError:
                hint = None
        ocr_text = ocr_engine.extract_text(content, content_type="application/octet-stream", language_hint=hint)
        if ocr_text and len(ocr_text) > len(text):
            return ocr_text, True
    except Exception:
        logger.exception("OCR fallback failed for %s", file_path)

    return text, False
