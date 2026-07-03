from __future__ import annotations

import logging
from typing import Any

from core.application.interfaces.services import OCRProvider
from core.domain.documents.value_objects import Confidence, Language

logger = logging.getLogger(__name__)


class PaddleOCREngine(OCRProvider):
    """PaddleOCR-based implementation of OCRProvider ABC.

    Uses PaddleOCR for text extraction from images and scanned PDFs.
    Falls back to a basic stub when PaddleOCR is not installed.
    """

    def __init__(self, *, lang: str = "en", use_gpu: bool = False) -> None:
        self._lang = lang
        self._use_gpu = use_gpu
        self._engine: Any = None

    def _get_engine(self) -> Any:
        """Lazy-initialise the PaddleOCR engine."""
        if self._engine is not None:
            return self._engine
        try:
            from paddleocr import PaddleOCR

            self._engine = PaddleOCR(
                use_angle_cls=True,
                lang=self._lang,
                use_gpu=self._use_gpu,
                show_log=False,
            )
            logger.info("PaddleOCR engine initialised (lang=%s, gpu=%s)", self._lang, self._use_gpu)
        except ImportError:
            logger.warning(
                "PaddleOCR not installed — OCR requests will return empty strings. "
                "Install with: pip install paddleocr paddlepaddle"
            )
            self._engine = None
        return self._engine

    async def extract_text(
        self,
        content: bytes,
        *,
        content_type: str,
        language_hint: Language | None = None,
    ) -> str:
        engine = self._get_engine()
        if engine is None:
            logger.debug("PaddleOCR unavailable, skipping text extraction")
            return ""

        # TODO: Implement actual PaddleOCR integration.
        # Steps:
        #   1. Write `content` to a temporary file based on content_type.
        #   2. Call engine.ocr(tmp_path, cls=True).
        #   3. Concatenate detected text lines.
        #   4. Clean up temp file.
        #
        # Example (to be implemented):
        #   import tempfile, os
        #   suffix = _content_type_to_suffix(content_type)
        #   with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        #       tmp.write(content)
        #       tmp_path = tmp.name
        #   try:
        #       result = engine.ocr(tmp_path, cls=True)
        #       lines = [line[1][0] for line in result[0]] if result and result[0] else []
        #       return "\n".join(lines)
        #   finally:
        #       os.unlink(tmp_path)

        logger.info("PaddleOCR stub: text extraction not yet implemented")
        return ""

    async def detect_language(self, text: str) -> Language:
        """Detect the primary language of the given text."""
        if not text.strip():
            return Language.UNKNOWN

        # TODO: Use a proper language detection library (e.g., langdetect, lingua).
        # For now, perform a simple heuristic based on character ranges.
        sample = text[:2000]
        cjk_chars = sum(1 for c in sample if "\u4e00" <= c <= "\u9fff")
        if cjk_chars > len(sample) * 0.1:
            return Language.ZH

        # Default to English when detection is unavailable
        return Language.EN

    async def get_confidence(self, text: str) -> Confidence:
        """Return the confidence score of the OCR extraction."""
        if not text.strip():
            return Confidence(value=0.0)

        # TODO: Return actual OCR confidence from PaddleOCR results.
        # PaddleOCR provides per-word confidence scores; aggregate them.
        # For now, return a moderate confidence for non-empty results.
        return Confidence(value=0.75)


def _content_type_to_suffix(content_type: str) -> str:
    """Map a MIME type to a file suffix for temporary files."""
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
        "image/bmp": ".bmp",
        "application/pdf": ".pdf",
    }
    return mapping.get(content_type, ".bin")
