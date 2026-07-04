from __future__ import annotations

import logging
import uuid as _uuid

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from interfaces.api.v1.serializers.ocr_serializers import (
    OcrJobCreateSerializer,
    OcrJobSerializer,
)

logger = logging.getLogger(__name__)


class OcrJobViewSet(viewsets.GenericViewSet):
    """ViewSet for managing OCR processing jobs."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action == "create":
            return OcrJobCreateSerializer
        return OcrJobSerializer

    def _get_file_names(self, file_ids: list[str]) -> dict[str, str]:
        """Look up file names from FileRecord for the given file IDs."""
        if not file_ids:
            return {}
        from apps.files.models import FileRecord

        file_ids_uuid = []
        for fid in file_ids:
            try:
                file_ids_uuid.append(_uuid.UUID(fid))
            except (ValueError, AttributeError):
                continue

        records = FileRecord.objects.filter(id__in=file_ids_uuid).values_list("id", "path")
        return {str(fid): path.split("/")[-1] if "/" in path else path for fid, path in records}

    def list(self, request):
        from apps.ocr.models import OCRJob

        jobs = list(OCRJob.objects.order_by("-created_at")[:100])

        file_ids = [str(j.file_id) for j in jobs]
        file_names = self._get_file_names(file_ids)

        serializer = OcrJobSerializer(jobs, many=True, context={"file_names": file_names})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        from apps.ocr.models import OCRJob

        try:
            job_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid OCR job ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            job = OCRJob.objects.get(pk=job_id)
        except OCRJob.DoesNotExist:
            return Response(
                {"detail": "OCR job not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        file_names = self._get_file_names([str(job.file_id)])
        return Response(
            OcrJobSerializer(job, context={"file_names": file_names}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="rerun")
    def rerun(self, request, pk=None):
        from apps.ocr.models import OCRJob

        try:
            job_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid OCR job ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            job = OCRJob.objects.get(pk=job_id)
        except OCRJob.DoesNotExist:
            return Response(
                {"detail": "OCR job not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if job.status not in (OCRJob.Status.FAILED, OCRJob.Status.COMPLETED):
            return Response(
                {"detail": "Can only re-run failed or completed jobs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.status = OCRJob.Status.PENDING
        job.error_message = ""
        job.completed_at = None
        job.save(update_fields=["status", "error_message", "completed_at"])

        try:
            from apps.ocr.tasks import process_image_task, process_pdf_task

            if job.source_type == "pdf":
                process_pdf_task.delay(str(job.file_id), "", language=job.language or "eng")
            else:
                process_image_task.delay(str(job.file_id), "", language=job.language or "eng")
        except Exception:
            logger.exception("Failed to dispatch OCR re-run for job %s", job_id)

        file_names = self._get_file_names([str(job.file_id)])
        return Response(
            OcrJobSerializer(job, context={"file_names": file_names}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_job(self, request, pk=None):
        from apps.ocr.models import OCRJob

        try:
            job_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid OCR job ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            job = OCRJob.objects.get(pk=job_id)
        except OCRJob.DoesNotExist:
            return Response(
                {"detail": "OCR job not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
