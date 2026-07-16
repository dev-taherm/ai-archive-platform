"""Shared OCR fallback logic — used by both the worker and the API routes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Extensions eligible for OCR fallback
_OCR_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif", ".webp", ".pdf",
})

# Minimum text length before triggering OCR
_MIN_TEXT_LENGTH = 50

# Map file extension → MIME type so Tesseract writes valid temp files
_EXT_MIME: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def _is_garbled(text: str) -> bool:
    """Return True if text looks like binary garbage rather than readable content."""
    if not text:
        return False
    sample = text[:1000]
    printable = sum(1 for c in sample if c.isprintable() or c in '\n\r\t')
    return printable / max(len(sample), 1) < 0.5


def ocr_fallback(text: str, file_path: Path, ocr_engine: Any, language_hint: str | None = None) -> tuple[str, bool]:
    """Attempt OCR if extracted text is too short.

    Returns (final_text, ocr_used).
    """
    if text and len(text.strip()) >= _MIN_TEXT_LENGTH and not _is_garbled(text):
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
        content_type = _EXT_MIME.get(suffix, "application/octet-stream")
        ocr_text = ocr_engine.extract_text(content, content_type=content_type, language_hint=hint)
        if ocr_text and ocr_text.strip():
            return ocr_text.strip(), True
    except Exception:
        logger.exception("OCR fallback failed for %s", file_path)

    return text, False
