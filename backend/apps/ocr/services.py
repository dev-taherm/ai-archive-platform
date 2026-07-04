from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from core.application.interfaces.services import OCRProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OCRResult:
    """Result from an OCR processing operation."""

    text: str
    confidence: float = 0.0
    language: str = "unknown"
    page_count: int = 0
    processing_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class OCRService:
    """Service for optical character recognition operations."""

    def __init__(self, ocr_provider: OCRProvider) -> None:
        self._ocr_provider = ocr_provider

    async def process_image(
        self,
        image_data: bytes,
        *,
        language: str = "eng",
    ) -> OCRResult:
        """Extract text from an image using OCR."""
        import time

        start = time.monotonic()

        text = await self._ocr_provider.extract_text(
            image_data,
            content_type="image/png",
        )

        detected_language = await self._ocr_provider.detect_language(text)
        confidence = await self._ocr_provider.get_confidence(text)

        elapsed_ms = (time.monotonic() - start) * 1000

        logger.info(
            "Image OCR completed: %d chars extracted, confidence=%.2f, lang=%s",
            len(text),
            confidence,
            detected_language,
        )

        return OCRResult(
            text=text,
            confidence=confidence,
            language=detected_language,
            processing_time_ms=round(elapsed_ms, 2),
        )

    async def process_pdf(
        self,
        pdf_data: bytes,
        *,
        language: str = "eng",
    ) -> OCRResult:
        """Extract text from a PDF document using OCR."""
        import time

        start = time.monotonic()

        text = await self._ocr_provider.extract_text(
            pdf_data,
            content_type="application/pdf",
        )

        detected_language = await self._ocr_provider.detect_language(text)
        confidence = await self._ocr_provider.get_confidence(text)

        elapsed_ms = (time.monotonic() - start) * 1000

        # Estimate page count from form feeds
        page_count = max(1, text.count("\f") + 1)

        logger.info(
            "PDF OCR completed: %d chars, %d pages, confidence=%.2f",
            len(text),
            page_count,
            confidence,
        )

        return OCRResult(
            text=text,
            confidence=confidence,
            language=detected_language,
            page_count=page_count,
            processing_time_ms=round(elapsed_ms, 2),
        )
