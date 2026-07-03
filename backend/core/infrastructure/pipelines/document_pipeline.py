from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from core.infrastructure.pipelines.document_state import DocumentPipelineState
from core.infrastructure.pipelines.nodes import (
    check_status,
    chunk_node,
    classify_node,
    embed_index_node,
    extract_entities_node,
    ocr_node,
    parse_node,
    should_run_ocr,
    summarize_node,
)

logger = logging.getLogger(__name__)


def build_document_pipeline() -> StateGraph:
    """Build the LangGraph document processing pipeline.

    Graph structure:
        START
          │
          ▼
        parse ──────────────────────────┐
          │                             │
          ├─ status=failed → END        │
          │                             │
          ▼                             │
        should_run_ocr? ──► ocr ────────┤
          │                             │
          ├─ "classify" (has text)      │
          │                             │
          ▼                             │
        classify                        │
          │                             │
          ├─ status=failed → END        │
          │                             │
          ▼                             │
        extract_entities                │
          │                             │
          ▼                             │
        summarize                       │
          │                             │
          ├─ status=failed → END        │
          │                             │
          ▼                             │
        chunk                           │
          │                             │
          ├─ status=failed → END        │
          │                             │
          ▼                             │
        embed_index                     │
          │                             │
          ├─ status=failed → END        │
          │                             │
          ▼                             │
        END
    """
    graph = StateGraph(DocumentPipelineState)

    # Add nodes
    graph.add_node("parse", parse_node)
    graph.add_node("ocr", ocr_node)
    graph.add_node("classify", classify_node)
    graph.add_node("extract_entities", extract_entities_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("chunk", chunk_node)
    graph.add_node("embed_index", embed_index_node)

    # Entry point
    graph.set_entry_point("parse")

    # Edges
    graph.add_conditional_edges(
        "parse",
        should_run_ocr,
        {
            "ocr": "ocr",
            "classify": "classify",
        },
    )

    graph.add_edge("ocr", "classify")
    graph.add_edge("classify", "extract_entities")
    graph.add_edge("extract_entities", "summarize")
    graph.add_edge("summarize", "chunk")
    graph.add_edge("chunk", "embed_index")
    graph.add_edge("embed_index", END)

    # Error handling: any node can set status="failed"
    for node_name in ["parse", "classify", "summarize", "chunk", "embed_index"]:
        graph.add_conditional_edges(
            node_name,
            check_status,
            {
                "failed": END,
                "completed": END,  # placeholder, actual next edge already set
            },
        )

    return graph.compile()


# Singleton compiled graph
_compiled_graph = None


def get_document_pipeline():
    """Get the compiled document processing pipeline (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_document_pipeline()
    return _compiled_graph


def run_document_pipeline(
    file_id: str,
    file_path: str,
    mime_type: str,
) -> dict[str, Any]:
    """Run the full document processing pipeline.

    Args:
        file_id: UUID of the source file record.
        file_path: Absolute path to the file on disk.
        mime_type: MIME type of the file.

    Returns:
        Final pipeline state with all results.
    """
    pipeline = get_document_pipeline()

    initial_state: DocumentPipelineState = {
        "file_id": file_id,
        "file_path": file_path,
        "mime_type": mime_type,
        "markdown_content": "",
        "structured_blocks": [],
        "tables": [],
        "images": [],
        "parse_method": "",
        "page_count": 0,
        "ocr_text": "",
        "ocr_confidence": 0.0,
        "detected_language": "unknown",
        "classification": "other",
        "classification_confidence": 0.0,
        "entities": [],
        "summary": "",
        "enriched_metadata": {},
        "chunks": [],
        "chunk_count": 0,
        "document_id": "",
        "embedding_ids": [],
        "status": "pending",
        "error": None,
        "retry_count": 0,
        "processing_log": [],
    }

    logger.info("Starting document pipeline: file=%s, path=%s", file_id, file_path)

    final_state = pipeline.invoke(initial_state)

    logger.info(
        "Pipeline complete: status=%s, doc=%s, chunks=%d, log=%d entries",
        final_state.get("status"),
        final_state.get("document_id"),
        final_state.get("chunk_count", 0),
        len(final_state.get("processing_log", [])),
    )

    return final_state
