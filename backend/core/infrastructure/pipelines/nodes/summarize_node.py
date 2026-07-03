from __future__ import annotations

import logging
import time
from typing import Any

from core.infrastructure.pipelines.document_state import DocumentPipelineState

logger = logging.getLogger(__name__)


def summarize_node(state: DocumentPipelineState) -> dict[str, Any]:
    """Node: Generate summary using LLM.

    Creates a concise summary of the document content.
    """
    t0 = time.time()
    text = state.get("markdown_content") or state.get("ocr_text", "")
    file_path = state.get("file_path", "")
    classification = state.get("classification", "other")
    logger.info("SUMMARIZE: %s", file_path)

    if not text or not text.strip():
        elapsed_ms = (time.time() - t0) * 1000
        return {
            "summary": "",
            "enriched_metadata": {},
            "processing_log": [f"SUMMARIZE: skipped — no text ({elapsed_ms:.0f}ms)"],
        }

    try:
        from django.apps import apps
        ai_config = apps.get_app_config("ai")
        llm_provider = ai_config.llm_provider

        # Truncate for summarization (use more context for better summaries)
        summary_text = text[:6000]

        summary = llm_provider.summarize(
            summary_text,
            max_tokens=500,
            system_prompt=(
                "Provide a concise summary of this document in 2-4 sentences. "
                "Focus on the key information, purpose, and main points."
            ),
        )

        # Build enriched metadata from entities + classification
        entities = state.get("entities", [])
        enriched = {
            "document_type": classification,
            "language": state.get("detected_language", "unknown"),
            "page_count": state.get("page_count", 0),
            "word_count": len(text.split()),
            "char_count": len(text),
            "entity_count": len(entities),
            "parse_method": state.get("parse_method", ""),
        }

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(
            "SUMMARIZE done: %d chars (%.0fms)",
            len(summary), elapsed_ms,
        )

        return {
            "summary": summary,
            "enriched_metadata": enriched,
            "processing_log": [f"SUMMARIZE: {len(summary)} chars ({elapsed_ms:.0f}ms)"],
        }
    except Exception as e:
        logger.exception("SUMMARIZE failed: %s", e)
        return {
            "summary": f"[Summarization failed: {e}]",
            "enriched_metadata": {},
            "processing_log": [f"SUMMARIZE FAILED: {e}"],
        }
