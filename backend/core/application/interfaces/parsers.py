from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ContentBlock:
    """A single content block from a parsed document."""

    block_type: str  # "heading", "text", "table", "image", "formula", "list", "code"
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    bbox: list[float] | None = None  # [x1, y1, x2, y2] if available
    level: int | None = None  # heading level (1-6) for heading blocks


@dataclass(frozen=True)
class ParsedTable:
    """Extracted table data."""

    html: str = ""
    rows: list[list[str]] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    caption: str = ""
    bbox: list[float] | None = None


@dataclass(frozen=True)
class ParsedImage:
    """Extracted image data."""

    image_path: str = ""
    description: str = ""
    bbox: list[float] | None = None
    width: int = 0
    height: int = 0


@dataclass(frozen=True)
class ParsedDocument:
    """Structured representation of a parsed document."""

    document_name: str = ""
    markdown: str = ""
    content_blocks: list[ContentBlock] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    images: list[ParsedImage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    page_count: int = 0
    word_count: int = 0
    char_count: int = 0
    parse_method: str = ""  # "mineru", "reader", "ocr"
    parse_time_ms: float = 0.0

    @property
    def has_tables(self) -> bool:
        return len(self.tables) > 0

    @property
    def has_images(self) -> bool:
        return len(self.images) > 0

    @property
    def heading_count(self) -> int:
        return sum(1 for b in self.content_blocks if b.block_type == "heading")


class DocumentParser(ABC):
    """Abstract interface for document structure extraction."""

    @abstractmethod
    def parse(self, file_path: str, **kwargs) -> ParsedDocument:
        """Parse a document and return structured content."""

    @abstractmethod
    def supports_format(self, mime_type: str) -> bool:
        """Check if this parser supports the given MIME type."""

    @property
    @abstractmethod
    def parser_name(self) -> str:
        """Return the name of this parser implementation."""
