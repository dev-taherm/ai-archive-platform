from __future__ import annotations

import logging
import time
from typing import Any

from core.infrastructure.pipelines.document_pipeline import DOCUMENT_CATEGORIES
from core.infrastructure.pipelines.document_state import DocumentPipelineState

logger = logging.getLogger(__name__)


def classify_node(state: DocumentPipelineState) -> dict[str, Any]:
    """Node: Classify document using LLM.

    Uses the LLMProvider to classify the document into one of the
    predefined categories. Falls back to heuristic if LLM is unavailable.
    """
    t0 = time.time()
    text = state.get("markdown_content") or state.get("ocr_text", "")
    file_path = state.get("file_path", "")
    logger.info("CLASSIFY: %s", file_path)

    if not text or not text.strip():
        elapsed_ms = (time.time() - t0) * 1000
        return {
            "classification": "other",
            "classification_confidence": 0.0,
            "processing_log": [f"CLASSIFY: skipped — no text ({elapsed_ms:.0f}ms)"],
        }

    try:
        from django.apps import apps
        ai_config = apps.get_app_config("ai")
        llm_provider = ai_config.llm_provider

        # Truncate text for classification (LLM context limits)
        classification_text = text[:3000]

        category, confidence = llm_provider.classify(
            classification_text,
            categories=DOCUMENT_CATEGORIES,
            system_prompt=(
                "Classify this document into one of the given categories. "
                "Return only the category name."
            ),
        )

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(
            "CLASSIFY done: category=%s, conf=%.2f (%.0fms)",
            category, confidence, elapsed_ms,
        )

        return {
            "classification": category,
            "classification_confidence": confidence,
            "processing_log": [f"CLASSIFY: {category} ({confidence:.2f}) ({elapsed_ms:.0f}ms)"],
        }
    except Exception as e:
        logger.exception("CLASSIFY failed: %s", e)
        return {
            "classification": "other",
            "classification_confidence": 0.0,
            "processing_log": [f"CLASSIFY FAILED: {e}"],
        }
