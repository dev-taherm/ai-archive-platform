from __future__ import annotations

import enum
from dataclasses import dataclass


class DocumentType(enum.Enum):
    """Classification of document content types."""

    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    CODE = "code"
    EMAIL = "email"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    IMAGE = "image"
    UNKNOWN = "unknown"

    @classmethod
    def from_extension(cls, ext: str) -> DocumentType:
        mapping = {
            ".pdf": cls.PDF,
            ".txt": cls.TEXT,
            ".md": cls.MARKDOWN,
            ".html": cls.HTML,
            ".htm": cls.HTML,
            ".csv": cls.CSV,
            ".json": cls.JSON,
            ".xml": cls.HTML,
            ".py": cls.CODE,
            ".js": cls.CODE,
            ".ts": cls.CODE,
            ".java": cls.CODE,
            ".go": cls.CODE,
            ".rs": cls.CODE,
            ".c": cls.CODE,
            ".cpp": cls.CODE,
            ".h": cls.CODE,
            ".sql": cls.CODE,
            ".yaml": cls.CODE,
            ".yml": cls.CODE,
            ".toml": cls.CODE,
            ".eml": cls.EMAIL,
            ".xlsx": cls.SPREADSHEET,
            ".xls": cls.SPREADSHEET,
            ".pptx": cls.PRESENTATION,
            ".ppt": cls.PRESENTATION,
            ".png": cls.IMAGE,
            ".jpg": cls.IMAGE,
            ".jpeg": cls.IMAGE,
            ".tiff": cls.IMAGE,
            ".tif": cls.IMAGE,
            ".bmp": cls.IMAGE,
            ".gif": cls.IMAGE,
            ".webp": cls.IMAGE,
        }
        return mapping.get(ext.lower(), cls.UNKNOWN)


class Language(enum.Enum):
    """ISO 639-1 language codes for document content."""

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
    """Confidence score for classification/extraction results."""

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


class ProcessingStatus(enum.Enum):
    """Status of document processing pipeline."""

    QUEUED = "queued"
    EXTRACTING = "extracting"
    CLASSIFYING = "classifying"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

    @property
    def is_terminal(self) -> bool:
        return self in (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED)

    @property
    def can_retry(self) -> bool:
        return self in (ProcessingStatus.FAILED, ProcessingStatus.RETRYING)
