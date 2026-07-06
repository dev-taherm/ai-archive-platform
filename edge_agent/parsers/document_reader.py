"""Document reader — extracts text from various file formats.

Standalone extraction from core/infrastructure/services/document_reader.py.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path

from edge_agent.core.models import ExtractionResult

logger = logging.getLogger(__name__)


class DocumentReader:
    """Extracts text from PDF, DOCX, XLSX, TXT, CSV, JSON, images."""

    def read(self, file_path: str, content: bytes | None = None) -> ExtractionResult:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if content is None:
            content = path.read_bytes()
        handler = self._get_handler(suffix)
        try:
            result = handler(content, suffix)
            logger.info("Extracted %d chars from %s", len(result.text), path.name)
            return result
        except Exception as e:
            logger.exception("Failed to extract text from %s", file_path)
            return ExtractionResult(text=f"[Extraction failed: {e}]", metadata={"error": str(e), "format": suffix})

    def _get_handler(self, suffix: str):
        handlers = {
            ".pdf": self._read_pdf, ".docx": self._read_docx, ".doc": self._read_docx,
            ".xlsx": self._read_xlsx, ".xls": self._read_xlsx,
            ".txt": self._read_text, ".md": self._read_text, ".markdown": self._read_text,
            ".csv": self._read_csv, ".json": self._read_json,
            ".xml": self._read_text, ".html": self._read_text, ".htm": self._read_text,
        }
        for ext in [".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".h",
                     ".sql", ".yaml", ".yml", ".toml", ".log", ".cfg", ".ini", ".conf",
                     ".sh", ".bash", ".rb", ".php", ".r", ".m", ".mm", ".kt", ".scala"]:
            handlers[ext] = self._read_text
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"]:
            handlers[ext] = self._read_image
        return handlers.get(suffix, self._read_binary_fallback)

    def _read_pdf(self, content: bytes, suffix: str) -> ExtractionResult:
        import pdfplumber
        pages_text, tables_all, metadata = [], [], {}
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            metadata = pdf.metadata or {}
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
                page_tables = page.extract_tables()
                if page_tables:
                    tables_all.extend(page_tables)
        return ExtractionResult(
            text="\n\n".join(t for t in pages_text if t.strip()),
            metadata={"format": "pdf", "page_count": len(pages_text)},
            page_count=len(pages_text), tables=tables_all,
        )

    def _read_docx(self, content: bytes, suffix: str) -> ExtractionResult:
        from docx import Document as DocxDocument
        doc = DocxDocument(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        tables = []
        for table in doc.tables:
            tables.append([[cell.text for cell in row.cells] for row in table.rows])
        props = doc.core_properties
        return ExtractionResult(
            text="\n\n".join(paragraphs),
            metadata={"format": "docx", "title": props.title or "", "author": props.author or ""},
            tables=tables,
        )

    def _read_xlsx(self, content: bytes, suffix: str) -> ExtractionResult:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheets_text, all_tables = [], []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            sheet_rows = []
            for row in ws.iter_rows(values_only=True):
                row_values = [str(cell) if cell is not None else "" for cell in row]
                if any(v.strip() for v in row_values):
                    sheet_rows.append(row_values)
            if sheet_rows:
                all_tables.append(sheet_rows)
                sheets_text.append(f"=== Sheet: {sheet_name} ===\n" + "\n".join(", ".join(r) for r in sheet_rows))
        wb.close()
        return ExtractionResult(
            text="\n\n".join(sheets_text),
            metadata={"format": "xlsx", "sheet_count": len(wb.sheetnames)},
            tables=all_tables,
        )

    def _read_text(self, content: bytes, suffix: str) -> ExtractionResult:
        for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252", "ascii"]:
            try:
                return ExtractionResult(text=content.decode(enc), metadata={"format": suffix.lstrip(".")})
            except (UnicodeDecodeError, LookupError):
                continue
        return ExtractionResult(text=content.decode("utf-8", errors="replace"), metadata={"format": suffix.lstrip(".")})

    def _read_csv(self, content: bytes, suffix: str) -> ExtractionResult:
        for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                text = content.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        else:
            text = content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = [row for row in reader if any(cell.strip() for cell in row)]
        return ExtractionResult(
            text="\n".join(", ".join(row) for row in rows),
            metadata={"format": "csv", "row_count": len(rows)},
            tables=[rows] if rows else [],
        )

    def _read_json(self, content: bytes, suffix: str) -> ExtractionResult:
        for enc in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                text = content.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        else:
            text = content.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
            pretty = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        except json.JSONDecodeError:
            pretty = text
        return ExtractionResult(text=pretty, metadata={"format": "json"})

    def _read_image(self, content: bytes, suffix: str) -> ExtractionResult:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            return ExtractionResult(text="", metadata={
                "format": (img.format or suffix.lstrip(".")),
                "width": img.size[0], "height": img.size[1], "mode": img.mode,
            })
        except Exception as e:
            return ExtractionResult(text="", metadata={"format": suffix.lstrip("."), "error": str(e)})

    def _read_binary_fallback(self, content: bytes, suffix: str) -> ExtractionResult:
        return ExtractionResult(text="", metadata={"format": suffix.lstrip(".") if suffix else "unknown", "size_bytes": len(content)})
