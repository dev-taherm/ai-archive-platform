from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any

from core.application.interfaces.services import OCRProvider
from core.domain.documents.value_objects import Confidence, Language

logger = logging.getLogger(__name__)

# Subprocess OCR timeout (seconds) — PaddleOCR can hang on large images
_OCR_TIMEOUT = 120


class PaddleOCREngine(OCRProvider):
    """PaddleOCR-based implementation of OCRProvider ABC.

    Uses PaddleOCR for text extraction from images and scanned PDFs.
    OCR runs in a subprocess to isolate OOM crashes from the main Django process.
    Falls back to Tesseract when PaddleOCR is not installed.
    """

    def __init__(self, *, lang: str = "en", use_gpu: bool = False) -> None:
        self._lang = lang
        self._use_gpu = use_gpu
        self._tesseract_available: bool | None = None

    def _run_ocr_subprocess(self, temp_path: str) -> str:
        """Run PaddleOCR in a subprocess to isolate OOM crashes."""
        worker_script = os.path.join(os.path.dirname(__file__), "ocr_worker.py")
        try:
            proc = subprocess.run(
                [sys.executable, worker_script, temp_path, self._lang],
                capture_output=True,
                text=True,
                timeout=_OCR_TIMEOUT,
            )
            if proc.returncode != 0:
                logger.warning("OCR worker exited with code %d: %s", proc.returncode, proc.stderr[:500])
                return ""
            result = json.loads(proc.stdout.strip())
            if result.get("error"):
                logger.warning("OCR worker error: %s", result["error"])
            return result.get("text", "")
        except subprocess.TimeoutExpired:
            logger.warning("OCR worker timed out after %ds", _OCR_TIMEOUT)
            return ""
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("OCR worker failed: %s", e)
            return ""

    def _get_tesseract_lang(self, language_hint: Language | None = None) -> str:
        """Map Language enum to Tesseract language code."""
        lang_map = {
            Language.EN: "eng",
            Language.AR: "ara",
            Language.FR: "fra",
            Language.DE: "deu",
            Language.ES: "spa",
            Language.ZH: "chi_sim",
            Language.JA: "jpn",
            Language.KO: "kor",
            Language.RU: "rus",
            Language.PT: "por",
            Language.IT: "ita",
            Language.NL: "nld",
            Language.SV: "swe",
            Language.PL: "pol",
            Language.TR: "tur",
        }
        if language_hint and language_hint in lang_map:
            return lang_map[language_hint]
        return "eng+ara"

    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available as a fallback."""
        if self._tesseract_available is not None:
            return self._tesseract_available
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            self._tesseract_available = True
        except (ImportError, Exception):
            self._tesseract_available = False
            logger.warning("Tesseract not available as OCR fallback")
        return self._tesseract_available

    async def extract_text(
        self,
        content: bytes,
        *,
        content_type: str,
        language_hint: Language | None = None,
    ) -> str:
        # Try PaddleOCR in subprocess first
        text = await self._extract_with_paddle_subprocess(content, content_type)
        if text and text.strip():
            return text

        # Fallback to Tesseract if PaddleOCR failed or returned empty
        if self._check_tesseract():
            logger.info("PaddleOCR returned empty, falling back to Tesseract")
            return await self._extract_with_tesseract(content, content_type, language_hint)

        return text

    async def _extract_with_paddle_subprocess(self, content: bytes, content_type: str) -> str:
        """Extract text using PaddleOCR in a subprocess for OOM isolation."""
        import asyncio

        def _run() -> str:
            suffix = _content_type_to_suffix(content_type)
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                return self._run_ocr_subprocess(tmp_path)
            except Exception:
                logger.exception("Subprocess OCR failed")
                return ""

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run)

    async def _extract_with_tesseract(
        self,
        content: bytes,
        content_type: str,
        language_hint: Language | None = None,
    ) -> str:
        """Extract text using Tesseract as fallback."""
        import asyncio

        def _run_tesseract() -> str:
            import pytesseract
            from PIL import Image

            suffix = _content_type_to_suffix(content_type)
            tmp_path = None
            try:
                if content_type == "application/pdf":
                    return self._ocr_pdf_with_tesseract(content, language_hint)

                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                img = Image.open(tmp_path)
                lang = self._get_tesseract_lang(language_hint)
                text = pytesseract.image_to_string(img, lang=lang)
                return text.strip() if text else ""
            except Exception:
                logger.exception("Tesseract extraction failed")
                return ""
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _run_tesseract)

    def _ocr_pdf_with_tesseract(
        self, pdf_content: bytes, language_hint: Language | None = None
    ) -> str:
        """OCR a PDF by converting pages to images first."""
        try:
            import fitz  # PyMuPDF
            import pytesseract
            from PIL import Image

            doc = fitz.open(stream=pdf_content, filetype="pdf")
            lang = self._get_tesseract_lang(language_hint)
            all_text = []

            for page_num in range(min(len(doc), 50)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img, lang=lang)
                if text and text.strip():
                    all_text.append(text.strip())

            doc.close()
            return "\n\n".join(all_text)
        except Exception:
            logger.exception("Tesseract PDF OCR failed")
            return ""

    async def detect_language(self, text: str) -> Language:
        """Detect the primary language of the given text using Unicode ranges."""
        if not text.strip():
            return Language.UNKNOWN

        sample = text[:5000]
        char_counts: dict[str, int] = {}
        total = 0

        for c in sample:
            if c.isalpha():
                total += 1
                if "\u0600" <= c <= "\u06ff" or "\u0750" <= c <= "\u077f":
                    char_counts["ar"] = char_counts.get("ar", 0) + 1
                elif "\u0400" <= c <= "\u04ff":
                    char_counts["ru"] = char_counts.get("ru", 0) + 1
                elif "\u4e00" <= c <= "\u9fff":
                    char_counts["zh"] = char_counts.get("zh", 0) + 1
                elif "\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff":
                    char_counts["ja"] = char_counts.get("ja", 0) + 1
                elif "\uac00" <= c <= "\ud7af":
                    char_counts["ko"] = char_counts.get("ko", 0) + 1
                elif "\u0900" <= c <= "\u097f":
                    char_counts["hi"] = char_counts.get("hi", 0) + 1
                elif "\u0e00" <= c <= "\u0e7f":
                    char_counts["th"] = char_counts.get("th", 0) + 1

        if total == 0:
            return Language.UNKNOWN

        lang_map = {
            "ar": Language.AR,
            "ru": Language.RU,
            "zh": Language.ZH,
            "ja": Language.JA,
            "ko": Language.KOR,
            "hi": Language.UNKNOWN,
            "th": Language.UNKNOWN,
        }

        for lang_code, count in char_counts.items():
            if count > total * 0.1:
                return lang_map.get(lang_code, Language.EN)

        return Language.EN

    async def get_confidence(self, text: str) -> Confidence:
        """Return the confidence score of the OCR extraction.

        Uses heuristics based on text quality indicators.
        """
        if not text.strip():
            return Confidence(value=0.0)

        lines = text.strip().split("\n")
        non_empty = [line for line in lines if line.strip()]
        if not non_empty:
            return Confidence(value=0.0)

        total_chars = sum(len(line) for line in non_empty)
        alpha_chars = sum(c.isalpha() for line in non_empty for c in line)
        digit_chars = sum(c.isdigit() for line in non_empty for c in line)
        space_chars = sum(c.isspace() for line in non_empty for c in line)

        if total_chars == 0:
            return Confidence(value=0.0)

        alpha_ratio = alpha_chars / total_chars
        has_structure = len(non_empty) >= 2
        has_mixed_content = digit_chars > 0 and alpha_chars > 0
        line_length_variance = _variance([len(line) for line in non_empty])

        score = 0.5
        if alpha_ratio > 0.5:
            score += 0.15
        if has_structure:
            score += 0.1
        if has_mixed_content:
            score += 0.05
        if line_length_variance > 10:
            score += 0.1
        if space_chars / max(total_chars, 1) > 0.05:
            score += 0.05

        score = max(0.0, min(1.0, score))
        return Confidence(value=round(score, 2))


def _content_type_to_suffix(content_type: str) -> str:
    """Map a MIME type to a file suffix for temporary files."""
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
        "image/bmp": ".bmp",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }
    return mapping.get(content_type, ".bin")


def _variance(values: list[int]) -> float:
    """Compute variance of a list of numbers."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)
