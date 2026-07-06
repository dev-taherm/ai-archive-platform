"""Text chunker — splits documents into embeddable chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    index: int
    start_char: int
    end_char: int


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Chunk]:
    """Split text into overlapping chunks at paragraph/sentence boundaries."""
    if not text or not text.strip():
        return []

    text = text.strip()
    if len(text) <= chunk_size:
        return [Chunk(text=text, index=0, start_char=0, end_char=len(text))]

    chunks: list[Chunk] = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            split_pos = _find_split_point(text, start, end)
            if split_pos > start:
                end = split_pos

        chunk_text_str = text[start:end].strip()
        if chunk_text_str:
            chunks.append(Chunk(text=chunk_text_str, index=idx, start_char=start, end_char=end))
            idx += 1

        start = end - chunk_overlap
        if start >= len(text):
            break

    return chunks


def _find_split_point(text: str, start: int, end: int) -> int:
    """Find the best split point (paragraph > sentence > word boundary)."""
    search_range = text[start:end]

    # Try paragraph break
    para_break = search_range.rfind("\n\n")
    if para_break > chunk_size_min(end - start):
        return start + para_break + 2

    # Try single newline
    nl = search_range.rfind("\n")
    if nl > chunk_size_min(end - start):
        return start + nl + 1

    # Try sentence boundary
    for sep in [". ", "! ", "? ", "؟ "]:
        pos = search_range.rfind(sep)
        if pos > chunk_size_min(end - start):
            return start + pos + len(sep)

    # Fall back to word boundary
    space = search_range.rfind(" ")
    if space > 0:
        return start + space + 1

    return end


def chunk_size_min(total: int) -> int:
    """Minimum acceptable chunk size (30% of total)."""
    return max(total * 3 // 10, 100)
