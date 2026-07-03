from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from core.application.interfaces.parsers import (
    ContentBlock,
    DocumentParser,
    ParsedDocument,
    ParsedImage,
    ParsedTable,
)

logger = logging.getLogger(__name__)

# MinerU-supported MIME types
MINERU_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
    "image/gif",
    "image/webp",
}

MINERU_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"}


class MinerUParser(DocumentParser):
    """MinerU document parser with graceful fallback.

    Uses MinerU for structured PDF/DOCX/PPTX/XLSX parsing when available.
    Falls back to basic extraction if MinerU dependencies are missing.
    """

    def __init__(
        self,
        backend: str = "pipeline",
        effort: str = "medium",
        language: str = "en",
        formula_enable: bool = True,
        table_enable: bool = True,
        output_dir: str = "/tmp/mineru_output",
    ) -> None:
        self._backend = backend
        self._effort = effort
        self._language = language
        self._formula_enable = formula_enable
        self._table_enable = table_enable
        self._output_dir = Path(output_dir)
        self._mineru_available: bool | None = None  # lazy check

    def _check_mineru(self) -> bool:
        """Check if MinerU is importable."""
        if self._mineru_available is not None:
            return self._mineru_available
        try:
            from mineru.cli.common import do_parse, read_fn  # noqa: F401
            self._mineru_available = True
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("MinerU not available (%s) — using fallback parser", e)
            self._mineru_available = False
        return self._mineru_available

    @property
    def parser_name(self) -> str:
        return "mineru" if self._check_mineru() else "reader-fallback"

    def supports_format(self, mime_type: str) -> bool:
        return mime_type in MINERU_MIME_TYPES

    def parse(self, file_path: str, **kwargs) -> ParsedDocument:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if self._check_mineru():
            return self._parse_with_mineru(path, **kwargs)
        else:
            return self._parse_with_fallback(path, **kwargs)

    def _parse_with_mineru(self, path: Path, **kwargs) -> ParsedDocument:
        """Parse using MinerU."""
        from mineru.cli.common import do_parse, read_fn

        start = time.monotonic()
        language = kwargs.get("language", self._language)
        output_dir = self._output_dir / path.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            file_bytes = read_fn(path)

            do_parse(
                output_dir=str(output_dir),
                pdf_file_names=[path.stem],
                pdf_bytes_list=[file_bytes],
                p_lang_list=[language],
                backend=self._backend,
                parse_method="auto",
                formula_enable=self._formula_enable,
                table_enable=self._table_enable,
                image_analysis=True,
                f_draw_layout_bbox=False,
                f_draw_span_bbox=False,
                f_dump_md=True,
                f_dump_middle_json=True,
                f_dump_model_output=False,
                f_dump_orig_pdf=False,
                f_dump_content_list=True,
                start_page_id=0,
                end_page_id=None,
                effort=self._effort,
            )

            return self._collect_results(path.stem, output_dir, time.monotonic() - start)

        except Exception as e:
            logger.exception("MinerU parsing failed for %s", path)
            logger.warning("Falling back to basic parser")
            return self._parse_with_fallback(path, **kwargs)

    def _collect_results(self, doc_name: str, output_dir: Path, elapsed: float) -> ParsedDocument:
        """Collect MinerU output files into ParsedDocument."""
        parse_dir = output_dir
        if not parse_dir.exists():
            for candidate in output_dir.rglob(f"{doc_name}*.md"):
                parse_dir = candidate.parent
                break

        result = ParsedDocument(
            document_name=doc_name,
            parse_method="mineru",
            parse_time_ms=round(elapsed * 1000, 2),
        )

        # Read markdown
        md_path = parse_dir / f"{doc_name}.md"
        if md_path.exists():
            result.markdown = md_path.read_text(encoding="utf-8")

        # Parse markdown into content blocks
        if result.markdown:
            result.content_blocks = self._markdown_to_blocks(result.markdown)

        # Read content list for tables and images
        cl_path = parse_dir / f"{doc_name}_content_list.json"
        if cl_path.exists():
            try:
                content_list = json.loads(cl_path.read_text(encoding="utf-8"))
                result.tables = self._extract_tables(content_list)
                result.images = self._extract_images(content_list)
            except (json.JSONDecodeError, KeyError):
                pass

        # Read middle JSON for detailed metadata
        middle_path = parse_dir / f"{doc_name}_middle.json"
        if middle_path.exists():
            try:
                middle_json = json.loads(middle_path.read_text(encoding="utf-8"))
                result.metadata = self._extract_metadata(middle_json)
                result.page_count = middle_json.get("pdf_info", [{}])[-1].get("page_idx", 0) + 1 if middle_json.get("pdf_info") else 0
            except (json.JSONDecodeError, KeyError):
                pass

        # Compute counts
        result.word_count = len(result.markdown.split()) if result.markdown else 0
        result.char_count = len(result.markdown) if result.markdown else 0

        return result

    def _markdown_to_blocks(self, markdown: str) -> list[ContentBlock]:
        """Convert markdown text into structured content blocks."""
        blocks: list[ContentBlock] = []
        lines = markdown.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Heading
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                content = line.lstrip("# ").strip()
                blocks.append(ContentBlock(block_type="heading", content=content, level=level))

            # Table (markdown format)
            elif line.strip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
                table_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                table_html = self._markdown_table_to_html(table_lines)
                blocks.append(ContentBlock(block_type="table", content=table_html))
                continue

            # Image
            elif line.strip().startswith("!["):
                blocks.append(ContentBlock(block_type="image", content=line.strip()))

            # Formula (LaTeX)
            elif line.strip().startswith("$$") or line.strip().startswith("$"):
                blocks.append(ContentBlock(block_type="formula", content=line.strip()))

            # List item
            elif line.strip().startswith(("- ", "* ", "+ ")) or (line.strip() and line.strip()[0].isdigit() and ". " in line[:5]):
                blocks.append(ContentBlock(block_type="list", content=line.strip()))

            # Code block
            elif line.strip().startswith("```"):
                code_lines = [line]
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    code_lines.append(lines[i])
                blocks.append(ContentBlock(block_type="code", content="\n".join(code_lines)))

            # Text paragraph
            elif line.strip():
                # Accumulate consecutive text lines
                text_lines = [line]
                while i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith("#") and not lines[i + 1].strip().startswith("|"):
                    i += 1
                    text_lines.append(lines[i])
                blocks.append(ContentBlock(block_type="text", content=" ".join(l.strip() for l in text_lines)))

            i += 1

        return blocks

    def _markdown_table_to_html(self, table_lines: list[str]) -> str:
        """Convert markdown table lines to HTML."""
        if len(table_lines) < 2:
            return ""

        headers = [cell.strip() for cell in table_lines[0].split("|")[1:-1]]
        rows = []
        for line in table_lines[2:]:  # skip header and separator
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            rows.append(cells)

        html = "<table><thead><tr>"
        for h in headers:
            html += f"<th>{h}</th>"
        html += "</tr></thead><tbody>"
        for row in rows:
            html += "<tr>"
            for cell in row:
                html += f"<td>{cell}</td>"
            html += "</tr>"
        html += "</tbody></table>"
        return html

    def _extract_tables(self, content_list: list[dict]) -> list[ParsedTable]:
        """Extract tables from MinerU content list."""
        tables = []
        for item in content_list:
            if item.get("type") == "table":
                tables.append(ParsedTable(
                    html=item.get("text", ""),
                    caption=item.get("caption", ""),
                ))
        return tables

    def _extract_images(self, content_list: list[dict]) -> list[ParsedImage]:
        """Extract images from MinerU content list."""
        images = []
        for item in content_list:
            if item.get("type") == "image":
                images.append(ParsedImage(
                    image_path=item.get("img_path", ""),
                    description=item.get("text", ""),
                ))
        return images

    def _extract_metadata(self, middle_json: dict) -> dict[str, Any]:
        """Extract metadata from MinerU middle JSON."""
        metadata: dict[str, Any] = {}
        pdf_info = middle_json.get("pdf_info", [])
        if pdf_info:
            first_page = pdf_info[0] if pdf_info else {}
            metadata["parse_type"] = middle_json.get("_parse_type", "unknown")
            metadata["total_blocks"] = sum(
                len(page.get("data", [])) for page in pdf_info
            )
        return metadata

    def _parse_with_fallback(self, path: Path, **kwargs) -> ParsedDocument:
        """Fallback parser using pdfplumber/python-docx for basic extraction."""
        start = time.monotonic()
        suffix = path.suffix.lower()

        text = ""
        metadata: dict[str, Any] = {}

        try:
            if suffix == ".pdf":
                text, metadata = self._read_pdf(path)
            elif suffix == ".docx":
                text, metadata = self._read_docx(path)
            elif suffix == ".txt":
                text = path.read_text(encoding="utf-8", errors="replace")
            elif suffix == ".md":
                text = path.read_text(encoding="utf-8", errors="replace")
            elif suffix == ".csv":
                text = path.read_text(encoding="utf-8", errors="replace")
            elif suffix == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                text = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Fallback read failed for %s: %s", path, e)
            text = f"[Error reading file: {e}]"

        elapsed = time.monotonic() - start
        blocks = self._markdown_to_blocks(text) if text else []

        return ParsedDocument(
            document_name=path.stem,
            markdown=text,
            content_blocks=blocks,
            metadata=metadata,
            page_count=metadata.get("page_count", 1),
            word_count=len(text.split()) if text else 0,
            char_count=len(text) if text else 0,
            parse_method="reader-fallback",
            parse_time_ms=round(elapsed * 1000, 2),
        )

    def _read_pdf(self, path: Path) -> tuple[str, dict[str, Any]]:
        """Read PDF using pdfplumber."""
        try:
            import pdfplumber
            text_parts = []
            metadata = {}
            with pdfplumber.open(path) as pdf:
                metadata["page_count"] = len(pdf.pages)
                if pdf.metadata:
                    metadata.update({
                        "title": pdf.metadata.get("Title", ""),
                        "author": pdf.metadata.get("Author", ""),
                        "subject": pdf.metadata.get("Subject", ""),
                    })
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts), metadata
        except ImportError:
            logger.warning("pdfplumber not available")
            return "", {}

    def _read_docx(self, path: Path) -> tuple[str, dict[str, Any]]:
        """Read DOCX using python-docx."""
        try:
            import docx
            doc = docx.Document(str(path))
            text_parts = []
            metadata = {}
            if doc.core_properties.title:
                metadata["title"] = doc.core_properties.title
            if doc.core_properties.author:
                metadata["author"] = doc.core_properties.author
            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)
            return "\n\n".join(text_parts), metadata
        except ImportError:
            logger.warning("python-docx not available")
            return "", {}
