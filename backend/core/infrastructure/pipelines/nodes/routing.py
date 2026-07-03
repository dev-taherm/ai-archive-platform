from __future__ import annotations

import logging
from typing import Literal

from core.infrastructure.pipelines.document_state import DocumentPipelineState

logger = logging.getLogger(__name__)


def should_run_ocr(state: DocumentPipelineState) -> Literal["ocr", "classify"]:
    """Conditional edge: run OCR if parser yielded no meaningful text.

    Checks if the parse step extracted enough text. If not, routes to OCR.
    """
    markdown = state.get("markdown_content", "")
    ocr_text = state.get("ocr_text", "")

    # If we have enough text from parsing, skip OCR
    if markdown and len(markdown.strip()) > 50:
        logger.debug("ROUTING: parse extracted text, skipping OCR")
        return "classify"

    # If OCR already ran and produced text, go to classify
    if ocr_text and len(ocr_text.strip()) > 50:
        logger.debug("ROUTING: OCR produced text, going to classify")
        return "classify"

    # Parser failed to extract text — need OCR
    logger.debug("ROUTING: no text from parser, routing to OCR")
    return "ocr"


def check_status(state: DocumentPipelineState) -> Literal["completed", "failed"]:
    """Check if pipeline should terminate due to failure."""
    if state.get("status") == "failed":
        return "failed"
    return "completed"
