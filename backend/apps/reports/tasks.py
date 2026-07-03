from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="reports.generate_archive_summary")
def generate_archive_summary_task(user_id: str | None = None) -> dict[str, object]:
    """Celery task to generate an archive summary report."""
    import uuid

    from apps.reports.services import ReportService

    try:
        report = ReportService.generate_archive_summary(
            generated_by_id=uuid.UUID(user_id) if user_id else None,
        )
        return {
            "report_id": str(report.id),
            "status": report.status,
            "title": report.title,
        }
    except Exception as e:
        logger.exception("Failed to generate archive summary report")
        return {"error": str(e)}


@shared_task(name="reports.generate_processing_stats")
def generate_processing_stats_task(user_id: str | None = None) -> dict[str, object]:
    """Celery task to generate a processing statistics report."""
    import uuid

    from apps.reports.services import ReportService

    try:
        report = ReportService.generate_processing_stats(
            generated_by_id=uuid.UUID(user_id) if user_id else None,
        )
        return {
            "report_id": str(report.id),
            "status": report.status,
            "title": report.title,
        }
    except Exception as e:
        logger.exception("Failed to generate processing stats report")
        return {"error": str(e)}


@shared_task(name="reports.cleanup_old_reports")
def cleanup_old_reports(days_old: int = 90) -> str:
    """Remove reports older than the specified number of days."""
    from datetime import timedelta

    from django.utils import timezone
    from apps.reports.models import Report

    cutoff = timezone.now() - timedelta(days=days_old)
    old_reports = Report.objects.filter(created_at__lt=cutoff)
    count, _ = old_reports.delete()
    logger.info("Cleaned up %d reports older than %d days", count, days_old)
    return f"Cleaned up {count} old reports"
