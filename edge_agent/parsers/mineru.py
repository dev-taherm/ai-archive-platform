"""MinerU parser — structured document extraction with fallback.

Standalone extraction from core/infrastructure/services/mineru_parser.py.
"""

from __future__ import annotations

import json
import logging
import time
from html import escape as html_escape
from pathlib import Path
from typing import Any

from edge_agent.core.models import ContentBlock, ParsedDocument, ParsedImage, ParsedTable

logger = logging.getLogger(__name__)

MINERU_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png", "image/jpeg", "image/tiff", "image/bmp", "image/gif", "image/webp",
}


class MinerUParser:
    """MinerU parser with pdfplumber/python-docx fallback."""

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
        self._mineru_available: bool | None = None

    def _check_mineru(self) -> bool:
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
        return self._parse_with_fallback(path, **kwargs)

    def _parse_with_mineru(self, path: Path, **kwargs) -> ParsedDocument:
        from mineru.cli.common import do_parse, read_fn
        start = time.monotonic()
        language = kwargs.get("language", self._language)
        output_dir = self._output_dir / path.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            file_bytes = read_fn(path)
            do_parse(
                output_dir=str(output_dir), pdf_file_names=[path.stem],
                pdf_bytes_list=[file_bytes], p_lang_list=[language],
                backend=self._backend, parse_method="auto",
                formula_enable=self._formula_enable, table_enable=self._table_enable,
                image_analysis=True, f_draw_layout_bbox=False, f_draw_span_bbox=False,
                f_dump_md=True, f_dump_middle_json=True, f_dump_model_output=False,
                f_dump_orig_pdf=False, f_dump_content_list=True,
                start_page_id=0, end_page_id=None, effort=self._effort,
            )
            return self._collect_results(path.stem, output_dir, time.monotonic() - start)
        except Exception:
            logger.exception("MinerU parsing failed for %s", path)
            return self._parse_with_fallback(path, **kwargs)

    def _collect_results(self, doc_name: str, output_dir: Path, elapsed: float) -> ParsedDocument:
        parse_dir = output_dir
        if not parse_dir.exists():
            for candidate in output_dir.rglob(f"{doc_name}*.md"):
                parse_dir = candidate.parent
                break
        result = ParsedDocument(document_name=doc_name, parse_method="mineru", parse_time_ms=round(elapsed * 1000, 2))
        md_path = parse_dir / f"{doc_name}.md"
        if md_path.exists():
            result.markdown = md_path.read_text(encoding="utf-8")
        if result.markdown:
            result.content_blocks = self._markdown_to_blocks(result.markdown)
        cl_path = parse_dir / f"{doc_name}_content_list.json"
        if cl_path.exists():
            try:
                content_list = json.loads(cl_path.read_text(encoding="utf-8"))
                result.tables = [ParsedTable(html=item.get("text", ""), caption=item.get("caption", "")) for item in content_list if item.get("type") == "table"]
                result.images = [ParsedImage(image_path=item.get("img_path", ""), description=item.get("text", "")) for item in content_list if item.get("type") == "image"]
            except (json.JSONDecodeError, KeyError):
                logger.debug("Failed to parse content list from %s", cl_path, exc_info=True)
        middle_path = parse_dir / f"{doc_name}_middle.json"
        if middle_path.exists():
            try:
                middle_json = json.loads(middle_path.read_text(encoding="utf-8"))
                pdf_info = middle_json.get("pdf_info", [])
                result.metadata = {"parse_type": middle_json.get("_parse_type", "unknown"), "total_blocks": sum(len(p.get("data", [])) for p in pdf_info)}
                result.page_count = pdf_info[-1].get("page_idx", 0) + 1 if pdf_info else 0
            except (json.JSONDecodeError, KeyError):
                logger.debug("Failed to parse middle JSON from %s", middle_path, exc_info=True)
        result.word_count = len(result.markdown.split()) if result.markdown else 0
        result.char_count = len(result.markdown) if result.markdown else 0
        return result

    def _markdown_to_blocks(self, markdown: str) -> list[ContentBlock]:
        blocks: list[ContentBlock] = []
        lines = markdown.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                blocks.append(ContentBlock(block_type="heading", content=line.lstrip("# ").strip(), level=level))
            elif line.strip().startswith("|") and i + 1 < len(lines) and "---" in lines[i + 1]:
                table_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                blocks.append(ContentBlock(block_type="table", content=self._md_table_to_html(table_lines)))
                continue
            elif line.strip().startswith("!["):
                blocks.append(ContentBlock(block_type="image", content=line.strip()))
            elif line.strip().startswith("$$") or line.strip().startswith("$"):
                blocks.append(ContentBlock(block_type="formula", content=line.strip()))
            elif line.strip().startswith(("- ", "* ", "+ ")) or (line.strip() and line.strip()[0].isdigit() and ". " in line[:5]):
                blocks.append(ContentBlock(block_type="list", content=line.strip()))
            elif line.strip().startswith("```"):
                code_lines = [line]
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    code_lines.append(lines[i])
                blocks.append(ContentBlock(block_type="code", content="\n".join(code_lines)))
            elif line.strip():
                text_lines = [line]
                while i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith("#") and not lines[i + 1].strip().startswith("|"):
                    i += 1
                    text_lines.append(lines[i])
                blocks.append(ContentBlock(block_type="text", content=" ".join(l.strip() for l in text_lines)))
            i += 1
        return blocks

    def _md_table_to_html(self, table_lines: list[str]) -> str:
        if len(table_lines) < 2:
            return ""
        headers = [c.strip() for c in table_lines[0].split("|")[1:-1]]
        rows = [[c.strip() for c in line.split("|")[1:-1]] for line in table_lines[2:]]
        html = "<table><thead><tr>" + "".join(f"<th>{html_escape(h)}</th>" for h in headers) + "</tr></thead><tbody>"
        for row in rows:
            html += "<tr>" + "".join(f"<td>{html_escape(c)}</td>" for c in row) + "</tr>"
        return html + "</tbody></table>"

    def _parse_with_fallback(self, path: Path, **kwargs) -> ParsedDocument:
        start = time.monotonic()
        language = kwargs.get("language", self._language)
        suffix = path.suffix.lower()
        text, metadata = "", {}
        try:
            if suffix == ".pdf":
                import pdfplumber
                parts = []
                with pdfplumber.open(path) as pdf:
                    metadata["page_count"] = len(pdf.pages)
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            parts.append(t)
                text = "\n\n".join(parts)
            elif suffix == ".docx":
                import docx
                doc = docx.Document(str(path))
                if doc.core_properties.title:
                    metadata["title"] = doc.core_properties.title
                if doc.core_properties.author:
                    metadata["author"] = doc.core_properties.author
                text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
            elif suffix in (".txt", ".md", ".csv"):
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
            document_name=path.stem, markdown=text, content_blocks=blocks,
            metadata=metadata, page_count=metadata.get("page_count", 1),
            word_count=len(text.split()) if text else 0, char_count=len(text) if text else 0,
            parse_method="reader-fallback", parse_time_ms=round(elapsed * 1000, 2),
        )
