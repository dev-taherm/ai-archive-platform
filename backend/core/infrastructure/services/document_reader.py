from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractionResult:
    """Result from a document text extraction operation."""

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


class DocumentReader:
    """Extracts text from various document formats.

    Supports: PDF, DOCX, XLSX, TXT, MD, CSV, JSON, XML, HTML, images.
    Falls back to raw bytes for unsupported formats.
    """

    def read(self, file_path: str, content: bytes | None = None) -> ExtractionResult:
        """Read a file and extract text content.

        Args:
            file_path: Path to the file (used to determine format).
            content: Raw file bytes. If None, reads from file_path.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if content is None:
            content = path.read_bytes()

        handler = self._get_handler(suffix)
        try:
            result = handler(content, suffix)
            logger.info(
                "Extracted %d chars from %s (format=%s, pages=%d)",
                len(result.text), path.name, suffix, result.page_count,
            )
            return result
        except Exception as e:
            logger.exception("Failed to extract text from %s", file_path)
            return ExtractionResult(
                text=f"[Extraction failed: {e}]",
                metadata={"error": str(e), "format": suffix},
            )

    def _get_handler(self, suffix: str):
        """Route to the correct extraction handler based on file extension."""
        handlers = {
            ".pdf": self._read_pdf,
            ".docx": self._read_docx,
            ".doc": self._read_docx,
            ".xlsx": self._read_xlsx,
            ".xls": self._read_xlsx,
            ".txt": self._read_text,
            ".md": self._read_text,
            ".markdown": self._read_text,
            ".csv": self._read_csv,
            ".json": self._read_json,
            ".xml": self._read_text,
            ".html": self._read_text,
            ".htm": self._read_text,
            ".py": self._read_text,
            ".js": self._read_text,
            ".ts": self._read_text,
            ".java": self._read_text,
            ".go": self._read_text,
            ".rs": self._read_text,
            ".c": self._read_text,
            ".cpp": self._read_text,
            ".h": self._read_text,
            ".sql": self._read_text,
            ".yaml": self._read_text,
            ".yml": self._read_text,
            ".toml": self._read_text,
            ".log": self._read_text,
            ".cfg": self._read_text,
            ".ini": self._read_text,
            ".conf": self._read_text,
            ".png": self._read_image,
            ".jpg": self._read_image,
            ".jpeg": self._read_image,
            ".gif": self._read_image,
            ".bmp": self._read_image,
            ".tiff": self._read_image,
            ".tif": self._read_image,
            ".webp": self._read_image,
        }
        return handlers.get(suffix, self._read_binary_fallback)

    def _read_pdf(self, content: bytes, suffix: str) -> ExtractionResult:
        """Extract text from PDF using pdfplumber."""
        import pdfplumber

        pages_text = []
        tables_all = []
        metadata = {}

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            metadata = pdf.metadata or {}
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)

                page_tables = page.extract_tables()
                if page_tables:
                    tables_all.extend(page_tables)

        full_text = "\n\n".join(t for t in pages_text if t.strip())

        return ExtractionResult(
            text=full_text,
            metadata={
                "format": "pdf",
                "page_count": len(pages_text),
                "pdf_metadata": {k: str(v) for k, v in metadata.items() if v},
            },
            page_count=len(pages_text),
            tables=tables_all,
        )

    def _read_docx(self, content: bytes, suffix: str) -> ExtractionResult:
        """Extract text from DOCX using python-docx."""
        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)

        tables = []
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [cell.text for cell in row.cells]
                table_data.append(row_data)
            tables.append(table_data)

        core_props = doc.core_properties
        metadata = {
            "format": "docx",
            "title": core_props.title or "",
            "author": core_props.author or "",
            "subject": core_props.subject or "",
            "created": str(core_props.created) if core_props.created else "",
            "modified": str(core_props.modified) if core_props.modified else "",
        }

        return ExtractionResult(
            text=full_text,
            metadata=metadata,
            tables=tables,
        )

    def _read_xlsx(self, content: bytes, suffix: str) -> ExtractionResult:
        """Extract text from XLSX using openpyxl."""
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheets_text = []
        all_tables = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            sheet_rows = []
            for row in ws.iter_rows(values_only=True):
                row_values = [str(cell) if cell is not None else "" for cell in row]
                if any(v.strip() for v in row_values):
                    sheet_rows.append(row_values)

            if sheet_rows:
                all_tables.append(sheet_rows)
                lines = [", ".join(row) for row in sheet_rows]
                sheets_text.append(f"=== Sheet: {sheet_name} ===\n" + "\n".join(lines))

        wb.close()
        full_text = "\n\n".join(sheets_text)

        return ExtractionResult(
            text=full_text,
            metadata={
                "format": "xlsx",
                "sheet_count": len(wb.sheetnames),
                "sheet_names": wb.sheetnames,
            },
            tables=all_tables,
        )

    def _read_text(self, content: bytes, suffix: str) -> ExtractionResult:
        """Extract text from plain text files."""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "ascii"]
        text = None
        for enc in encodings:
            try:
                text = content.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if text is None:
            text = content.decode("utf-8", errors="replace")

        return ExtractionResult(
            text=text,
            metadata={"format": suffix.lstrip("."), "encoding": "detected"},
        )

    def _read_csv(self, content: bytes, suffix: str) -> ExtractionResult:
        """Extract text from CSV files."""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        text = None
        for enc in encodings:
            try:
                text = content.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if text is None:
            text = content.decode("utf-8", errors="replace")

        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        table = [row for row in rows if any(cell.strip() for cell in row)]

        lines = [", ".join(row) for row in table]
        full_text = "\n".join(lines)

        return ExtractionResult(
            text=full_text,
            metadata={
                "format": "csv",
                "row_count": len(table),
                "column_count": max((len(row) for row in table), default=0),
            },
            tables=[table] if table else [],
        )

    def _read_json(self, content: bytes, suffix: str) -> ExtractionResult:
        """Extract text from JSON files."""
        encodings = ["utf-8", "utf-8-sig", "latin-1"]
        text = None
        for enc in encodings:
            try:
                text = content.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if text is None:
            text = content.decode("utf-8", errors="replace")

        try:
            data = json.loads(text)
            pretty = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        except json.JSONDecodeError:
            pretty = text

        return ExtractionResult(
            text=pretty,
            metadata={"format": "json"},
        )

    def _read_image(self, content: bytes, suffix: str) -> ExtractionResult:
        """Extract metadata from images (actual OCR is handled by OCRProvider)."""
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(content))
            width, height = img.size
            fmt = img.format or suffix.lstrip(".")
            mode = img.mode

            info = dict(img.info) if img.info else {}

            return ExtractionResult(
                text="",
                metadata={
                    "format": fmt,
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "dpi": info.get("dpi"),
                    "format_info": {k: str(v) for k, v in info.items() if isinstance(v, (str, int, float))},
                },
            )
        except Exception as e:
            logger.warning("Failed to read image metadata: %s", e)
            return ExtractionResult(
                text="",
                metadata={"format": suffix.lstrip("."), "error": str(e)},
            )

    def _read_binary_fallback(self, content: bytes, suffix: str) -> ExtractionResult:
        """Fallback for unsupported binary formats."""
        return ExtractionResult(
            text="",
            metadata={
                "format": suffix.lstrip(".") if suffix else "unknown",
                "size_bytes": len(content),
                "note": "Binary format not supported for text extraction",
            },
        )
