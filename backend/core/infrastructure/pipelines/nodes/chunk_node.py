from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from core.infrastructure.pipelines.document_state import DocumentPipelineState

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """Split text into overlapping chunks.

    Returns list of dicts with keys: text, index, start, end, hash.
    """
    if not text or not text.strip():
        return []

    chunks = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Try to break at sentence/paragraph boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind("\n\n", start + chunk_size // 2, end)
            if para_break > start:
                end = para_break + 2
            else:
                # Look for sentence break
                for sep in (". ", ".\n", "! ", "? ", "\n"):
                    sent_break = text.rfind(sep, start + chunk_size // 2, end)
                    if sent_break > start:
                        end = sent_break + len(sep)
                        break

        chunk_text_str = text[start:end].strip()
        if chunk_text_str:
            chunk_hash = hashlib.sha256(chunk_text_str.encode("utf-8")).hexdigest()[:16]
            chunks.append({
                "text": chunk_text_str,
                "index": idx,
                "start": start,
                "end": end,
                "hash": chunk_hash,
            })
            idx += 1

        # Move start forward, accounting for overlap
        start = end - overlap
        if start <= (chunks[-1]["start"] if chunks else 0):
            start = end

    return chunks


def chunk_node(state: DocumentPipelineState) -> dict[str, Any]:
    """Node: Split document text into overlapping chunks.

    Creates semantically meaningful chunks for embedding and indexing.
    """
    t0 = time.time()
    text = state.get("markdown_content") or state.get("ocr_text", "")
    file_path = state.get("file_path", "")
    logger.info("CHUNK: %s", file_path)

    if not text or not text.strip():
        elapsed_ms = (time.time() - t0) * 1000
        return {
            "chunks": [],
            "chunk_count": 0,
            "processing_log": [f"CHUNK: skipped — no text ({elapsed_ms:.0f}ms)"],
        }

    try:
        chunks = chunk_text(text)

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(
            "CHUNK done: %d chunks from %d chars (%.0fms)",
            len(chunks), len(text), elapsed_ms,
        )

        return {
            "chunks": chunks,
            "chunk_count": len(chunks),
            "processing_log": [f"CHUNK: {len(chunks)} chunks from {len(text)} chars ({elapsed_ms:.0f}ms)"],
        }
    except Exception as e:
        logger.exception("CHUNK failed: %s", e)
        return {
            "chunks": [],
            "chunk_count": 0,
            "processing_log": [f"CHUNK FAILED: {e}"],
        }
