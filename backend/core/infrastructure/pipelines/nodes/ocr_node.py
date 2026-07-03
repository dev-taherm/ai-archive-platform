from __future__ import annotations

import logging
import time
from typing import Any

from core.infrastructure.pipelines.document_state import DocumentPipelineState

logger = logging.getLogger(__name__)


def ocr_node(state: DocumentPipelineState) -> dict[str, Any]:
    """Node: Run OCR if parsed content has no extractable text.

    Checks if the parse step yielded meaningful text. If not, reads the
    raw file bytes and runs PaddleOCR (via OCRProvider) to get text.
    Sets ocr_text, ocr_confidence, detected_language.
    """
    t0 = time.time()
    markdown = state.get("markdown_content", "")
    file_path = state.get("file_path", "")
    logger.info("OCR: checking if needed for %s", file_path)

    # Skip OCR if we already have meaningful text from parsing
    if markdown and len(markdown.strip()) > 50:
        elapsed_ms = (time.time() - t0) * 1000
        logger.info("OCR: skipped (parser already extracted %d chars)", len(markdown))
        return {
            "ocr_text": "",
            "ocr_confidence": 0.0,
            "detected_language": "unknown",
            "processing_log": [f"OCR: skipped — parser extracted text ({elapsed_ms:.0f}ms)"],
        }

    # OCR is needed — read file bytes and run OCR
    try:
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_bytes()
        mime_type = state.get("mime_type", "application/octet-stream")

        # Lazy-load OCR provider from Django app config
        from django.apps import apps
        docs_config = apps.get_app_config("documents")
        ocr_provider = docs_config.ocr_provider

        text = ocr_provider.extract_text(
            content,
            content_type=mime_type,
        )

        lang = ocr_provider.detect_language(text)
        conf = ocr_provider.get_confidence(text)

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(
            "OCR done: %d chars, lang=%s, conf=%.2f (%.0fms)",
            len(text), lang.value, conf.value, elapsed_ms,
        )

        return {
            "ocr_text": text,
            "ocr_confidence": conf.value,
            "detected_language": lang.value,
            "processing_log": [f"OCR: extracted {len(text)} chars, lang={lang.value}, conf={conf.value:.2f} ({elapsed_ms:.0f}ms)"],
        }
    except Exception as e:
        logger.exception("OCR failed: %s", e)
        return {
            "ocr_text": "",
            "ocr_confidence": 0.0,
            "detected_language": "unknown",
            "processing_log": [f"OCR FAILED: {e}"],
        }
