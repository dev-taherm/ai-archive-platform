"""Standalone value objects — no Django dependency."""

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
class ContentBlock:
    block_type: str  # "heading", "text", "table", "image", "formula", "list", "code"
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
class ParsedDocument:
    document_name: str = ""
    markdown: str = ""
    content_blocks: list[ContentBlock] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    images: list[ParsedImage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    page_count: int = 0
    word_count: int = 0
    char_count: int = 0
    language: str = "unknown"
    parse_method: str = ""  # "mineru", "reader", "ocr"
    parse_time_ms: float = 0.0

    @property
    def has_tables(self) -> bool:
        return len(self.tables) > 0

    @property
    def has_images(self) -> bool:
        return len(self.images) > 0


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    page_count: int = 1
    word_count: int = 0
    char_count: int = 0
    tables: list[list[list[str]]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.word_count == 0 and self.text:
            object.__setattr__(self, "word_count", len(self.text.split()))
        if self.char_count == 0 and self.text:
            object.__setattr__(self, "char_count", len(self.text))
