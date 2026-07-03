from __future__ import annotations

import logging
import time
from typing import Any

from core.infrastructure.pipelines.document_state import DocumentPipelineState
from core.infrastructure.services.parser_router import ParserRouter

logger = logging.getLogger(__name__)


def parse_node(state: DocumentPipelineState) -> dict[str, Any]:
    """Node: Parse document using ParserRouter (MinerU or fallback).

    Reads the file from disk and extracts structured content.
    Sets markdown_content, structured_blocks, tables, images, parse_method, page_count.
    """
    t0 = time.time()
    file_path = state["file_path"]
    logger.info("PARSE: %s", file_path)

    try:
        parser = ParserRouter()
        parsed = parser.parse(file_path)

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(
            "PARSE done: %d chars, %d tables, %d images, method=%s (%.0fms)",
            len(parsed.markdown), len(parsed.tables), len(parsed.images),
            parsed.parse_method, elapsed_ms,
        )

        return {
            "markdown_content": parsed.markdown,
            "structured_blocks": [
                {"type": b.block_type, "content": b.content, "metadata": b.metadata}
                for b in parsed.content_blocks
            ],
            "tables": [
                {"html": t.html, "rows": t.rows, "headers": t.headers}
                for t in parsed.tables
            ],
            "images": [
                {"path": i.image_path, "description": i.description, "bbox": i.bbox}
                for i in parsed.images
            ],
            "parse_method": parsed.parse_method,
            "page_count": parsed.page_count,
            "processing_log": [f"PARSE: extracted {len(parsed.markdown)} chars via {parsed.parse_method} ({elapsed_ms:.0f}ms)"],
        }
    except Exception as e:
        logger.exception("PARSE failed: %s", e)
        return {
            "status": "failed",
            "error": f"Parse failed: {e}",
            "processing_log": [f"PARSE FAILED: {e}"],
        }
