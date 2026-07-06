"""Parser router — routes documents to MinerU or lightweight reader.

Standalone extraction from core/infrastructure/services/parser_router.py.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from edge_agent.core.models import ParsedDocument
from edge_agent.parsers.mineru import MinerUParser

logger = logging.getLogger(__name__)

LIGHTWEIGHT_EXTENSIONS = {
    ".txt", ".csv", ".md", ".py", ".js", ".ts", ".java", ".c", ".cpp",
    ".h", ".sh", ".bash", ".json", ".xml", ".html", ".css", ".yaml",
    ".yml", ".toml", ".ini", ".cfg", ".conf", ".log", ".sql", ".rb",
    ".go", ".rs", ".swift", ".kt", ".scala", ".php", ".r", ".m", ".mm",
}

LIGHTWEIGHT_MIME_TYPES = {
    "text/plain", "text/csv", "text/markdown", "text/x-python",
    "text/x-java", "text/x-c", "text/x-shellscript",
    "application/json", "application/xml", "text/xml", "text/html",
}


class ParserRouter:
    """Routes documents to MinerU (complex) or lightweight reader (text)."""

    def __init__(self, mineru_parser: MinerUParser | None = None) -> None:
        self._mineru = mineru_parser or MinerUParser()

    def parse(self, file_path: str, **kwargs) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "application/octet-stream"

        if path.suffix.lower() in LIGHTWEIGHT_EXTENSIONS or mime_type in LIGHTWEIGHT_MIME_TYPES:
            logger.debug("Lightweight parse: %s", path.name)
            return self._mineru._parse_with_fallback(path, **kwargs)
        logger.debug("MinerU parse: %s", path.name)
        return self._mineru.parse(file_path, **kwargs)

    def supports_format(self, mime_type: str) -> bool:
        return self._mineru.supports_format(mime_type) or mime_type in LIGHTWEIGHT_MIME_TYPES or mime_type.startswith("text/")
