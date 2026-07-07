"""Shared DTOs for AI Archive Platform and Edge Agent."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class Language(enum.Enum):
    EN = "en"
    FR = "fr"
    DE = "de"
    ES = "es"
    IT = "it"
    PT = "pt"
    NL = "nl"
    JA = "ja"
    ZH = "zh"
    KO = "ko"
    AR = "ar"
    RU = "ru"
    TR = "tr"
    PL = "pl"
    SV = "sv"
    DA = "da"
    FI = "fi"
    NO = "no"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Confidence:
    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.value}")

    @property
    def is_high(self) -> bool:
        return self.value >= 0.8

    @property
    def is_medium(self) -> bool:
        return 0.5 <= self.value < 0.8

    @property
    def is_low(self) -> bool:
        return self.value < 0.5

    @property
    def percentage(self) -> str:
        return f"{self.value * 100:.1f}%"


@dataclass(frozen=True)
class FileMetadata:
    local_path: str = ""
    content_hash: str = ""
    size_bytes: int = 0
    mime_type: str = ""
    magic_bytes: str = ""
    modified_at: str = ""


@dataclass(frozen=True)
class ContentBlock:
    block_type: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    bbox: list[float] | None = None
    level: int | None = None


@dataclass(frozen=True)
class ParsedTable:
    html: str = ""
    rows: list[list[str]] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    caption: str = ""
    bbox: list[float] | None = None


@dataclass(frozen=True)
class ParsedImage:
    image_path: str = ""
    description: str = ""
    bbox: list[float] | None = None
    width: int = 0
    height: int = 0


@dataclass(frozen=True)
class ExtractionResult:
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    page_count: int = 0
    word_count: int = 0
    char_count: int = 0
    tables: list[ParsedTable] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.word_count == 0 and self.text:
            object.__setattr__(self, "word_count", len(self.text.split()))
        if self.char_count == 0 and self.text:
            object.__setattr__(self, "char_count", len(self.text))


@dataclass(frozen=True)
class ExtractedEntity:
    """A named entity extracted from a document."""

    entity_type: str = ""
    name: str = ""
    context: str = ""
    confidence: float | None = None
    source: str = "agent"


@dataclass(frozen=True)
class DocumentProcessedEvent:
    tenant_id: str = ""
    agent_id: str = ""
    file_id: str = ""
    checksum: str = ""
    metadata: FileMetadata | None = None
    extracted_text: str = ""
    markdown: str = ""
    content_blocks: list[ContentBlock] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    images: list[ParsedImage] = field(default_factory=list)
    agent_version: str = ""
    processing_version: str = ""
    parser_version: str = ""
    ocr_engine: str = ""
    ocr_used: bool = False
    language: str = "unknown"
    word_count: int = 0
    char_count: int = 0
    page_count: int = 0
    summary: str = ""
    entities: list[ExtractedEntity] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentProcessedResponse:
    accepted: int = 0
    rejected: int = 0
    errors: list[str] = field(default_factory=list)
    pending_commands: list[dict[str, Any]] = field(default_factory=list)
    document_ids: list[str] = field(default_factory=list)
