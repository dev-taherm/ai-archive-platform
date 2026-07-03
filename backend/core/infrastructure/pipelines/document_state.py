from __future__ import annotations

import operator
from typing import Any, Optional, TypedDict

from typing_extensions import Annotated


class DocumentPipelineState(TypedDict):
    """Shared state for the document processing pipeline."""

    # Input
    file_id: str
    file_path: str
    mime_type: str

    # Parser output
    markdown_content: str
    structured_blocks: list[dict[str, Any]]
    tables: list[dict[str, Any]]
    images: list[dict[str, Any]]
    parse_method: str  # "mineru", "reader-fallback"
    page_count: int

    # OCR output
    ocr_text: str
    ocr_confidence: float
    detected_language: str

    # AI output
    classification: str
    classification_confidence: float
    entities: list[dict[str, Any]]
    summary: str
    enriched_metadata: dict[str, Any]

    # Chunking output
    chunks: list[dict[str, Any]]
    chunk_count: int

    # Indexing output
    document_id: str
    embedding_ids: list[str]

    # Control flow
    status: str  # "pending", "parsing", "ocr", "ai_processing", "chunking", "indexing", "completed", "failed"
    error: Optional[str]
    retry_count: int

    # Audit trail
    processing_log: Annotated[list[str], operator.add]
