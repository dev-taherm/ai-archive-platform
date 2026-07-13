"""Server-side sanitization for data received from edge agents.

Defense-in-depth: strip control characters that PostgreSQL rejects in
text/jsonb columns, even if the edge agent already sanitized before sending.
"""
from __future__ import annotations

import re
from typing import Any

_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def sanitize_text(value: Any) -> str:
    """Strip control characters that PostgreSQL rejects in text columns.

    Handles str, bytes, and other types gracefully.
    """
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="replace")
        except Exception:
            return ""
    if not isinstance(value, str):
        return str(value) if value else ""
    return _CONTROL_CHARS_RE.sub('', value)


def sanitize_json_recursive(obj: Any) -> Any:
    """Recursively sanitize control chars in all strings within a JSON-like structure.

    Also coerces bytes to str via lossy decode.
    """
    if isinstance(obj, bytes):
        try:
            obj = obj.decode("utf-8", errors="replace")
        except Exception:
            return ""
    if isinstance(obj, str):
        return _CONTROL_CHARS_RE.sub('', obj)
    if isinstance(obj, dict):
        return {k: sanitize_json_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_json_recursive(item) for item in obj]
    return obj


def sanitize_file_data(file_data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize all text and JSON fields in a file sync payload.

    Covers extracted_text, markdown, summary, content_blocks, tables, images,
    metadata, entities, and tags — anything that could carry control characters
    to PostgreSQL.
    """
    file_data["extracted_text"] = sanitize_text(file_data.get("extracted_text", ""))
    file_data["markdown"] = sanitize_text(file_data.get("markdown", ""))
    file_data["summary"] = sanitize_text(file_data.get("summary", ""))
    for key in ("content_blocks", "tables", "images"):
        file_data[key] = sanitize_json_recursive(file_data.get(key, []))
    # Recursively sanitize the entire metadata dict — raw edge agent metadata
    # can carry arbitrary nested data with control characters.
    file_data["metadata"] = sanitize_json_recursive(file_data.get("metadata", {}))
    # Sanitize extracted entities (name/context fields can contain junk text).
    file_data["entities"] = sanitize_json_recursive(file_data.get("entities", []))
    # Tags can also carry control chars.
    file_data["tags"] = sanitize_json_recursive(file_data.get("tags", []))
    return file_data
