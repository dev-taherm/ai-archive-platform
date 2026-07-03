from __future__ import annotations

import logging
import uuid
from typing import Any

from apps.reports.models import Report

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating and managing analytics reports."""

    @staticmethod
    def create_report(
        report_type: str,
        title: str,
        *,
        parameters: dict[str, Any] | None = None,
        generated_by_id: uuid.UUID | None = None,
    ) -> Report:
        """Create a new report record."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        generated_by = None
        if generated_by_id:
            try:
                generated_by = User.objects.get(pk=generated_by_id)
            except User.DoesNotExist:
                pass

        report = Report.objects.create(
            report_type=report_type,
            title=title,
            parameters=parameters or {},
            generated_by=generated_by,
        )
        logger.info("Report created: %s (%s)", title, report_type)
        return report

    @staticmethod
    def get_report(report_id: uuid.UUID) -> Report | None:
        """Retrieve a report by ID."""
        try:
            return Report.objects.get(pk=report_id)
        except Report.DoesNotExist:
            return None

    @staticmethod
    def list_reports(
        *,
        report_type: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Report]:
        """List reports with optional filtering."""
        qs = Report.objects.all()
        if report_type is not None:
            qs = qs.filter(report_type=report_type)
        if status is not None:
            qs = qs.filter(status=status)
        return list(qs.order_by("-created_at")[offset:offset + limit])

    @staticmethod
    def complete_report(
        report_id: uuid.UUID,
        data: dict[str, Any],
        *,
        file_path: str = "",
    ) -> Report | None:
        """Mark a report as completed with its data."""
        from django.utils import timezone

        try:
            report = Report.objects.get(pk=report_id)
        except Report.DoesNotExist:
            return None

        report.status = Report.Status.COMPLETED
        report.data = data
        report.file_path = file_path
        report.generated_at = timezone.now()
        report.save(update_fields=["status", "data", "file_path", "generated_at"])
        return report

    @staticmethod
    def generate_archive_summary(
        *,
        generated_by_id: uuid.UUID | None = None,
    ) -> Report:
        """Generate an archive summary report."""
        from django.db.models import Count
        from django.utils import timezone
        from apps.files.models import FileRecord
        from apps.documents.models import Document

        report = ReportService.create_report(
            Report.ReportType.ARCHIVE_SUMMARY,
            "Archive Summary Report",
            generated_by_id=generated_by_id,
        )

        try:
            total_files = FileRecord.objects.count()
            total_documents = Document.objects.count()
            completed = Document.objects.filter(processing_status="completed").count()
            failed = Document.objects.filter(processing_status="failed").count()
            by_type = dict(
                Document.objects.values_list("doc_type")
                .annotate(count=Count("id"))
                .values_list("doc_type", "count")
            )

            data = {
                "total_files": total_files,
                "total_documents": total_documents,
                "completed_processing": completed,
                "failed_processing": failed,
                "documents_by_type": by_type,
                "generated_at": timezone.now().isoformat(),
            }

            return ReportService.complete_report(report.id, data)
        except Exception as e:
            report.status = Report.Status.FAILED
            report.error_message = str(e)
            report.save(update_fields=["status", "error_message"])
            raise

    @staticmethod
    def generate_processing_stats(
        *,
        generated_by_id: uuid.UUID | None = None,
    ) -> Report:
        """Generate a processing statistics report."""
        from django.db.models import Count
        from django.utils import timezone
        from apps.documents.models import Document

        report = ReportService.create_report(
            Report.ReportType.PROCESSING_STATS,
            "Processing Statistics Report",
            generated_by_id=generated_by_id,
        )

        try:
            status_counts = dict(
                Document.objects.values_list("processing_status")
                .annotate(count=Count("id"))
                .values_list("processing_status", "count")
            )
            type_counts = dict(
                Document.objects.values_list("doc_type")
                .annotate(count=Count("id"))
                .values_list("doc_type", "count")
            )

            data = {
                "by_status": status_counts,
                "by_type": type_counts,
                "total": Document.objects.count(),
                "generated_at": timezone.now().isoformat(),
            }

            return ReportService.complete_report(report.id, data)
        except Exception as e:
            report.status = Report.Status.FAILED
            report.error_message = str(e)
            report.save(update_fields=["status", "error_message"])
            raise
