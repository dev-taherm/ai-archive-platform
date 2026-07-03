from __future__ import annotations

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="ocr.process_image_task")
def process_image_task(
    file_id: str,
    image_path: str,
    language: str = "eng",
) -> dict[str, object]:
    """Celery task to OCR an image file."""
    import asyncio
    import time

    from apps.ocr.models import OCRJob
    from apps.ocr.services import OCRService
    from core.infrastructure.services.ocr_provider import TesseractOCRProvider

    job = OCRJob.objects.create(
        file_id=uuid.UUID(file_id),
        source_type="image",
        status=OCRJob.Status.PROCESSING,
    )

    async def _run() -> dict[str, object]:
        ocr = TesseractOCRProvider()
        service = OCRService(ocr)

        with open(image_path, "rb") as f:
            image_data = f.read()

        result = await service.process_image(image_data, language=language)
        return {
            "text_length": len(result.text),
            "confidence": result.confidence,
            "language": result.language,
        }

    try:
        output = asyncio.run(_run())
        job.status = OCRJob.Status.COMPLETED
        job.confidence = output["confidence"]
        job.language = output["language"]
        from django.utils import timezone

        job.completed_at = timezone.now()
        job.save(update_fields=["status", "confidence", "language", "completed_at"])
        return output
    except Exception as e:
        job.status = OCRJob.Status.FAILED
        job.error_message = str(e)
        from django.utils import timezone

        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at"])
        raise


@shared_task(name="ocr.process_pdf_task")
def process_pdf_task(
    file_id: str,
    pdf_path: str,
    language: str = "eng",
) -> dict[str, object]:
    """Celery task to OCR a PDF file."""
    import asyncio

    from apps.ocr.models import OCRJob
    from apps.ocr.services import OCRService
    from core.infrastructure.services.ocr_provider import TesseractOCRProvider

    job = OCRJob.objects.create(
        file_id=uuid.UUID(file_id),
        source_type="pdf",
        status=OCRJob.Status.PROCESSING,
    )

    async def _run() -> dict[str, object]:
        ocr = TesseractOCRProvider()
        service = OCRService(ocr)

        with open(pdf_path, "rb") as f:
            pdf_data = f.read()

        result = await service.process_pdf(pdf_data, language=language)
        return {
            "text_length": len(result.text),
            "confidence": result.confidence,
            "language": result.language,
            "page_count": result.page_count,
        }

    try:
        output = asyncio.run(_run())
        job.status = OCRJob.Status.COMPLETED
        job.confidence = output["confidence"]
        job.language = output["language"]
        from django.utils import timezone

        job.completed_at = timezone.now()
        job.save(update_fields=["status", "confidence", "language", "completed_at"])
        return output
    except Exception as e:
        job.status = OCRJob.Status.FAILED
        job.error_message = str(e)
        from django.utils import timezone

        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at"])
        raise
