from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from core.application.interfaces.parsers import ParsedDocument
from core.infrastructure.services.mineru_parser import MinerUParser

logger = logging.getLogger(__name__)

# Simple text formats that don't need MinerU
LIGHTWEIGHT_MIME_TYPES = {
    "text/plain",
    "text/csv",
    "text/markdown",
    "text/x-python",
    "text/x-java",
    "text/x-c",
    "text/x-shellscript",
    "application/json",
    "application/xml",
    "text/xml",
    "text/html",
}

LIGHTWEIGHT_EXTENSIONS = {
    ".txt", ".csv", ".md", ".py", ".js", ".ts", ".java", ".c", ".cpp",
    ".h", ".sh", ".bash", ".json", ".xml", ".html", ".css", ".yaml",
    ".yml", ".toml", ".ini", ".cfg", ".conf", ".log", ".sql", ".rb",
    ".go", ".rs", ".swift", ".kt", ".scala", ".php", ".r", ".m", ".mm",
}


class ParserRouter:
    """Routes documents to the appropriate parser based on format.

    - Complex formats (PDF, DOCX, PPTX, XLSX, images) → MinerU
    - Simple text formats (TXT, CSV, JSON, MD, code) → Lightweight reader
    """

    def __init__(
        self,
        mineru_parser: MinerUParser | None = None,
        lightweight_formats: set[str] | None = None,
    ) -> None:
        self._mineru_parser = mineru_parser or MinerUParser()
        self._lightweight_formats = lightweight_formats or LIGHTWEIGHT_MIME_TYPES

    def parse(self, file_path: str, **kwargs) -> ParsedDocument:
        """Parse a document using the appropriate parser.

        Args:
            file_path: Path to the file to parse.
            **kwargs: Additional arguments passed to the parser.

        Returns:
            ParsedDocument with structured content.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        mime_type = self._detect_mime_type(path)
        use_lightweight = self._should_use_lightweight(path, mime_type)

        if use_lightweight:
            logger.debug("Using lightweight reader for %s (mime=%s)", path.name, mime_type)
            return self._mineru_parser._parse_with_fallback(path, **kwargs)
        else:
            logger.debug("Using MinerU parser for %s (mime=%s)", path.name, mime_type)
            return self._mineru_parser.parse(file_path, **kwargs)

    def _detect_mime_type(self, path: Path) -> str:
        """Detect MIME type from file extension."""
        mime_type, _ = mimetypes.guess_type(str(path))
        return mime_type or "application/octet-stream"

    def _should_use_lightweight(self, path: Path, mime_type: str) -> bool:
        """Determine if the file should use lightweight parsing."""
        # Check by extension first (more reliable)
        if path.suffix.lower() in LIGHTWEIGHT_EXTENSIONS:
            return True

        # Check by MIME type
        if mime_type in self._lightweight_formats:
            return True

        # Small text files (< 1MB) — use lightweight
        try:
            if path.stat().st_size < 1_000_000 and mime_type.startswith("text/"):
                return True
        except OSError:
            pass

        return False

    def supports_format(self, mime_type: str) -> bool:
        """Check if any parser supports this format."""
        return (
            self._mineru_parser.supports_format(mime_type)
            or mime_type in self._lightweight_formats
            or mime_type.startswith("text/")
        )
