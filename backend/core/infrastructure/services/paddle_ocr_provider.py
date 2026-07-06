from __future__ import annotations

import logging
import os
import re
import tempfile
from typing import Any

from core.application.interfaces.services import OCRProvider
from core.domain.documents.value_objects import Confidence, Language

logger = logging.getLogger(__name__)

_ARABIC_SCRIPT_RANGE = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
)
_LATIN_RANGE = re.compile(r'[a-zA-Z0-9]')


class PaddleOCRProvider(OCRProvider):
    """PaddleOCR-based OCR provider with Arabic + English support.

    Uses PaddleOCR for text extraction from images and scanned documents.
    Supports Arabic and English text recognition with confidence scores.
    """

    def __init__(
        self,
        lang: str = "ar",
        use_gpu: bool = False,
    ) -> None:
        self._lang = lang
        self._use_gpu = use_gpu
        self._engine = None
        self._available: bool | None = None

    def _is_available(self) -> bool:
        """Check if PaddleOCR is usable."""
        if self._available is not None:
            return self._available
        try:
            from paddleocr import PaddleOCR  # noqa: F401
            self._available = True
        except (ImportError, Exception) as e:
            logger.warning("PaddleOCR not available: %s", e)
            self._available = False
        return self._available

    def _get_engine(self):
        """Lazy-initialize PaddleOCR engine."""
        if self._engine is None:
            try:
                from paddleocr import PaddleOCR
                self._engine = PaddleOCR(lang=self._lang)
                logger.info("PaddleOCR initialized with lang=%s", self._lang)
            except Exception as e:
                logger.warning("PaddleOCR init failed: %s — OCR unavailable", e)
                self._engine = False
        return self._engine if self._engine is not False else None

    def _bytes_to_temp_file(self, content: bytes) -> tuple[str, bool]:
        """Convert bytes to a temp file for PaddleOCR."""
        suffix = ".png"
        if content[:8] == b'\x89PNG\r\n\x1a\n':
            suffix = ".png"
        elif content[:2] == b'\xff\xd8':
            suffix = ".jpg"
        elif content[:4] in (b'II\x2a\x00', b'MM\x00\x2a'):
            suffix = ".tiff"
        elif content[:4] == b'BM':
            suffix = ".bmp"

        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(content)
        tmp.close()
        return tmp.name, True

    def _run_ocr(self, temp_path: str) -> list[dict[str, Any]]:
        """Run PaddleOCR on a file and return detections."""
        engine = self._get_engine()

        # Try new API (predict) first, fallback to old API (ocr)
        try:
            result = engine.predict(temp_path)
            detections = []
            if result is not None:
                for r in result:
                    if hasattr(r, 'rec_texts') and hasattr(r, 'rec_scores'):
                        for text, score in zip(r.rec_texts, r.rec_scores):
                            if score > 0.3:
                                detections.append({"text": text, "confidence": float(score)})
                    elif isinstance(r, dict):
                        for text, score in zip(r.get("rec_texts", []), r.get("rec_scores", [])):
                            if score > 0.3:
                                detections.append({"text": text, "confidence": float(score)})
            return detections
        except Exception:
            pass

        # Fallback to old API
        try:
            result = engine.ocr(temp_path)
            detections = []
            if result is not None:
                for page in result:
                    if page is None:
                        continue
                    for line in page:
                        text = line[1][0]
                        confidence = float(line[1][1])
                        if confidence > 0.3:
                            detections.append({"text": text, "confidence": confidence})
            return detections
        except Exception as e:
            logger.warning("PaddleOCR OCR failed: %s", e)
            return []

    def extract_text(
        self,
        content: bytes,
        *,
        content_type: str,
        language_hint: Language | None = None,
    ) -> str:
        if not content or not self._is_available():
            return ""

        temp_path = None
        try:
            temp_path, _ = self._bytes_to_temp_file(content)
            detections = self._run_ocr(temp_path)
            return "\n".join(d["text"] for d in detections)
        except Exception as e:
            logger.warning("PaddleOCR extraction failed: %s", e)
            return ""
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def detect_language(self, text: str) -> Language:
        if not text or not text.strip():
            return Language.UNKNOWN

        arabic_chars = len(_ARABIC_SCRIPT_RANGE.findall(text))
        latin_chars = len(_LATIN_RANGE.findall(text))
        total = arabic_chars + latin_chars

        if total == 0:
            return Language.UNKNOWN

        arabic_ratio = arabic_chars / total

        if arabic_ratio > 0.5:
            return Language.ARABIC
        elif arabic_ratio < 0.1:
            return Language.ENGLISH
        else:
            return Language.ARABIC  # mixed

    def get_confidence(self, text: str) -> Confidence:
        if not text or not text.strip():
            return Confidence(value=0.0)
        return Confidence(value=0.85)

    def extract_with_boxes(
        self,
        content: bytes,
        *,
        content_type: str,
    ) -> list[dict[str, Any]]:
        if not content or not self._is_available():
            return []

        temp_path = None
        try:
            temp_path, _ = self._bytes_to_temp_file(content)
            detections = self._run_ocr(temp_path)
            return [
                {"bbox": d.get("bbox", []), "text": d["text"], "confidence": d["confidence"]}
                for d in detections
            ]
        except Exception as e:
            logger.warning("PaddleOCR extract_with_boxes failed: %s", e)
            return []
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
