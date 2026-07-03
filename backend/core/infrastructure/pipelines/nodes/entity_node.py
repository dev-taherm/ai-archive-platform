from __future__ import annotations

import logging
import time
from typing import Any

from core.infrastructure.pipelines.document_state import DocumentPipelineState

logger = logging.getLogger(__name__)

DEFAULT_ENTITY_TYPES = [
    "person",
    "organization",
    "date",
    "amount",
    "location",
    "email",
    "phone",
    "reference_number",
    "project_name",
]


def extract_entities_node(state: DocumentPipelineState) -> dict[str, Any]:
    """Node: Extract named entities from document text using LLM.

    Extracts structured entities (people, orgs, dates, amounts, etc.)
    from the document text.
    """
    t0 = time.time()
    text = state.get("markdown_content") or state.get("ocr_text", "")
    file_path = state.get("file_path", "")
    logger.info("ENTITIES: %s", file_path)

    if not text or not text.strip():
        elapsed_ms = (time.time() - t0) * 1000
        return {
            "entities": [],
            "processing_log": [f"ENTITIES: skipped — no text ({elapsed_ms:.0f}ms)"],
        }

    try:
        from django.apps import apps
        ai_config = apps.get_app_config("ai")
        llm_provider = ai_config.llm_provider

        # Truncate text for entity extraction
        extraction_text = text[:4000]

        entities = llm_provider.extract_entities(
            extraction_text,
            entity_types=DEFAULT_ENTITY_TYPES,
        )

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(
            "ENTITIES done: %d entities (%.0fms)",
            len(entities), elapsed_ms,
        )

        return {
            "entities": entities,
            "processing_log": [f"ENTITIES: extracted {len(entities)} entities ({elapsed_ms:.0f}ms)"],
        }
    except Exception as e:
        logger.exception("ENTITIES failed: %s", e)
        return {
            "entities": [],
            "processing_log": [f"ENTITIES FAILED: {e}"],
        }
