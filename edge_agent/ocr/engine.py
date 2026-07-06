"""OCR engine — PaddleOCR with Tesseract fallback.

Standalone extraction from ocr_engine.py + paddle_ocr_provider.py + ocr_worker.py.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import Any

from edge_agent.core.models import Confidence, Language

logger = logging.getLogger(__name__)

_OCR_TIMEOUT = 120

_ARABIC_SCRIPT_RANGE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
_LATIN_RANGE = re.compile(r'[a-zA-Z0-9]')

_TESS_LANG_MAP = {
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


def _content_type_to_suffix(content_type: str) -> str:
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
        "image/bmp": ".bmp",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }.get(content_type, ".bin")


def _variance(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


class OCREngine:
    """PaddleOCR with Tesseract fallback. Runs PaddleOCR in subprocess for OOM isolation."""

    def __init__(self, *, lang: str = "en", use_gpu: bool = False, timeout: int = _OCR_TIMEOUT) -> None:
        self._lang = lang
        self._use_gpu = use_gpu
        self._timeout = timeout
        self._tesseract_available: bool | None = None
        self._paddle_available: bool | None = None

    # --- PaddleOCR ---

    def _is_paddle_available(self) -> bool:
        if self._paddle_available is not None:
            return self._paddle_available
        try:
            from paddleocr import PaddleOCR  # noqa: F401
            self._paddle_available = True
        except (ImportError, Exception) as e:
            logger.warning("PaddleOCR not available: %s", e)
            self._paddle_available = False
        return self._paddle_available

    def _run_paddle_subprocess(self, temp_path: str) -> str:
        """Run PaddleOCR in a subprocess for OOM isolation."""
        worker_script = os.path.join(os.path.dirname(__file__), "worker.py")
        try:
            proc = subprocess.run(
                [sys.executable, worker_script, temp_path, self._lang],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if proc.returncode != 0:
                logger.warning("OCR worker exited %d: %s", proc.returncode, proc.stderr[:500])
                return ""
            result = json.loads(proc.stdout.strip())
            if result.get("error"):
                logger.warning("OCR worker error: %s", result["error"])
            return result.get("text", "")
        except subprocess.TimeoutExpired:
            logger.warning("OCR worker timed out after %ds", self._timeout)
            return ""
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("OCR worker failed: %s", e)
            return ""

    def _extract_paddle(self, content: bytes, content_type: str) -> str:
        suffix = _content_type_to_suffix(content_type)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            return self._run_paddle_subprocess(tmp_path)
        except Exception:
            logger.exception("PaddleOCR extraction failed")
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    # --- Tesseract ---

    def _is_tesseract_available(self) -> bool:
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

    def _get_tesseract_lang(self, language_hint: Language | None = None) -> str:
        if language_hint and language_hint in _TESS_LANG_MAP:
            return _TESS_LANG_MAP[language_hint]
        return "eng+ara"

    def _extract_tesseract(self, content: bytes, content_type: str, language_hint: Language | None = None) -> str:
        import pytesseract
        from PIL import Image

        suffix = _content_type_to_suffix(content_type)
        tmp_path = None
        try:
            if content_type == "application/pdf":
                return self._ocr_pdf_tesseract(content, language_hint)

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

    def _ocr_pdf_tesseract(self, pdf_content: bytes, language_hint: Language | None = None) -> str:
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

    # --- Public API ---

    def extract_text(
        self,
        content: bytes,
        *,
        content_type: str,
        language_hint: Language | None = None,
    ) -> str:
        if not content:
            return ""

        if self._is_paddle_available():
            text = self._extract_paddle(content, content_type)
            if text and text.strip():
                return text

        if self._is_tesseract_available():
            logger.info("PaddleOCR empty/unavailable, falling back to Tesseract")
            return self._extract_tesseract(content, content_type, language_hint)

        return ""

    def detect_language(self, text: str) -> Language:
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
        if total == 0:
            return Language.UNKNOWN
        lang_map = {"ar": Language.AR, "ru": Language.RU, "zh": Language.ZH, "ja": Language.JA, "ko": Language.KOR}
        for lang_code, count in char_counts.items():
            if count > total * 0.1:
                return lang_map.get(lang_code, Language.EN)
        return Language.EN

    def get_confidence(self, text: str) -> Confidence:
        if not text.strip():
            return Confidence(value=0.0)
        lines = text.strip().split("\n")
        non_empty = [line for line in lines if line.strip()]
        if not non_empty:
            return Confidence(value=0.0)
        total_chars = sum(len(line) for line in non_empty)
        alpha_chars = sum(c.isalpha() for line in non_empty for c in line)
        if total_chars == 0:
            return Confidence(value=0.0)
        alpha_ratio = alpha_chars / total_chars
        score = 0.5
        if alpha_ratio > 0.5:
            score += 0.15
        if len(non_empty) >= 2:
            score += 0.1
        line_variance = _variance([len(line) for line in non_empty])
        if line_variance > 10:
            score += 0.1
        score = max(0.0, min(1.0, score))
        return Confidence(value=round(score, 2))
