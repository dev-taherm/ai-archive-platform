"""Shared constants for the AI Archive Platform."""

from __future__ import annotations

DOCUMENT_CATEGORIES: list[str] = [
    "invoice",
    "receipt",
    "contract",
    "report",
    "letter",
    "memo",
    "email",
    "resume",
    "academic_paper",
    "legal_document",
    "financial_statement",
    "technical_specification",
    "meeting_notes",
    "proposal",
    "presentation",
    "spreadsheet",
    "code",
    "data_export",
    "other",
]

IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp",
})

LIGHTWEIGHT_EXTENSIONS: frozenset[str] = frozenset({
    ".txt", ".csv", ".md", ".json", ".xml", ".yaml", ".yml",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".h", ".hpp",
    ".rb", ".go", ".rs", ".sh", ".bash", ".zsh",
})

DEFAULT_CHUNK_SIZE: int = 1000
DEFAULT_CHUNK_OVERLAP: int = 200

PROCESSING_VERSION: str = "edge-document-pipeline-v2"
