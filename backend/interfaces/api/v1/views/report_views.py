from __future__ import annotations

import logging
import uuid as _uuid

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from interfaces.api.v1.serializers.report_serializers import (
    ReportCreateSerializer,
    ReportSerializer,
    ReportSummarySerializer,
)

logger = logging.getLogger(__name__)


class ReportView(viewsets.GenericViewSet):
    """ViewSet for analytics reports and summary data."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action == "create":
            return ReportCreateSerializer
        if self.action == "summary":
            return ReportSummarySerializer
        return ReportSerializer

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Return aggregated analytics for the Reports dashboard page."""
        storage = self._compute_storage()
        processing = self._compute_processing()
        activity = self._compute_activity()

        data = {
            "storage": storage,
            "processing": processing,
            "activity": activity,
        }
        return Response(data, status=status.HTTP_200_OK)

    def _compute_storage(self) -> dict:
        from apps.files.models import FileRecord

        try:
            agg = FileRecord.objects.aggregate(
                total_files=Count("id"),
                total_size_bytes=Sum("size_bytes"),
            )
            total_files = agg["total_files"] or 0
            total_size_bytes = agg["total_size_bytes"] or 0

            by_type_raw = (
                FileRecord.objects.values("mime_type")
                .annotate(count=Count("id"), size_bytes=Sum("size_bytes"))
                .order_by("-count")[:20]
            )
            by_type = {
                row["mime_type"]: {
                    "count": row["count"],
                    "size_bytes": row["size_bytes"] or 0,
                }
                for row in by_type_raw
            }

            return {
                "total_files": total_files,
                "total_size_bytes": total_size_bytes,
                "by_type": by_type,
            }
        except Exception:
            logger.exception("Failed to compute storage stats")
            return {"total_files": 0, "total_size_bytes": 0, "by_type": {}}

    def _compute_processing(self) -> dict:
        from apps.documents.models import Document

        try:
            total = Document.objects.count()

            completed = Document.objects.filter(processing_status="completed").count()
            success_rate = (completed / total * 100) if total > 0 else 0.0

            # Check if the model has a processing_time_ms field
            has_time_field = any(
                f.name == "processing_time_ms" for f in Document._meta.get_fields()
            )
            avg_time = 0.0
            if has_time_field:
                agg = Document.objects.aggregate(avg_time_ms=Avg("processing_time_ms"))
                avg_time = agg["avg_time_ms"] or 0.0

            by_status_raw = (
                Document.objects.values("processing_status")
                .annotate(count=Count("id"))
                .order_by("processing_status")
            )
            by_status = {row["processing_status"]: row["count"] for row in by_status_raw}

            return {
                "total_processed": total,
                "success_rate": round(success_rate, 1),
                "avg_time_ms": round(avg_time, 2),
                "by_status": by_status,
            }
        except Exception:
            logger.exception("Failed to compute processing stats")
            return {
                "total_processed": 0,
                "success_rate": 0.0,
                "avg_time_ms": 0.0,
                "by_status": {},
            }

    def _compute_activity(self) -> dict:
        from apps.files.models import FileRecord
        from apps.reports.models import Report

        result = {
            "daily_uploads": [],
            "top_tags": [],
            "recent_reports": [],
        }

        try:
            daily = (
                FileRecord.objects.annotate(date=TruncDate("created_at"))
                .values("date")
                .annotate(count=Count("id"))
                .order_by("-date")[:30]
            )
            result["daily_uploads"] = [
                {"date": row["date"].isoformat() if row["date"] else "", "count": row["count"]}
                for row in daily
            ]
        except Exception:
            logger.exception("Failed to compute daily uploads")

        try:
            tags_raw = (
                FileRecord.objects.exclude(tags=[])
                .values("tags")
                .annotate(count=Count("id"))
                .order_by("-count")[:20]
            )
            tag_counts: dict[str, int] = {}
            for row in tags_raw:
                tags_list = row["tags"] or []
                if isinstance(tags_list, list):
                    for tag in tags_list:
                        tag_counts[tag] = tag_counts.get(tag, 0) + row["count"]

            result["top_tags"] = sorted(
                [{"tag": t, "count": c} for t, c in tag_counts.items()],
                key=lambda x: x["count"],
                reverse=True,
            )[:20]
        except Exception:
            logger.exception("Failed to compute top tags")

        try:
            recent = Report.objects.filter(
                status=Report.Status.COMPLETED
            ).order_by("-created_at")[:10]

            result["recent_reports"] = [
                {
                    "id": str(r.id),
                    "name": r.title,
                    "type": r.report_type,
                    "generated_at": r.generated_at.isoformat() if r.generated_at else "",
                    "file_size": len(r.data) if r.data else 0,
                }
                for r in recent
            ]
        except Exception:
            logger.exception("Failed to compute recent reports")

        return result

    def list(self, request):
        from apps.reports.models import Report

        report_type = request.query_params.get("type")
        report_status = request.query_params.get("status")

        qs = Report.objects.all()
        if report_type:
            qs = qs.filter(report_type=report_type)
        if report_status:
            qs = qs.filter(status=report_status)

        reports = list(qs.order_by("-created_at")[:50])
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        from apps.reports.models import Report

        try:
            report_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid report ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report = Report.objects.get(pk=report_id)
        except Report.DoesNotExist:
            return Response(
                {"detail": "Report not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            ReportSerializer(report).data,
            status=status.HTTP_200_OK,
        )

    def create(self, request):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        from apps.reports.services import ReportService

        try:
            report = ReportService.create_report(
                report_type=validated["report_type"],
                title=validated["title"],
                parameters=validated.get("parameters", {}),
                generated_by_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                ReportSerializer(report).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception:
            logger.exception("Failed to create report")
            return Response(
                {"detail": "Failed to create report."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
