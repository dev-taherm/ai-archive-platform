from __future__ import annotations

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from interfaces.api.v1.serializers.dashboard_serializers import (
    ActivitySerializer,
    ChartDataSerializer,
    DashboardStatsSerializer,
)

logger = logging.getLogger(__name__)


class DashboardView(viewsets.GenericViewSet):
    """
    Dashboard ViewSet for statistics, charts, and activity feed.

    Delegates to application services for data aggregation.
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def stats(self, request):
        try:
            from django.apps import apps

            stats_data = {
                "total_files": 0,
                "total_documents": 0,
                "total_searches": 0,
                "total_chat_sessions": 0,
                "files_by_status": {},
                "documents_by_type": {},
                "documents_by_status": {},
                "recent_uploads_count": 0,
                "storage_used_bytes": 0,
                "avg_processing_time_ms": 0.0,
            }

            try:
                from apps.files.models import FileRecord as FileModel

                stats_data["total_files"] = FileModel.objects.count()
                from django.db.models import Count

                status_counts = (
                    FileModel.objects.values("status")
                    .annotate(count=Count("id"))
                    .order_by("status")
                )
                stats_data["files_by_status"] = {
                    item["status"]: item["count"] for item in status_counts
                }
            except (ImportError, Exception):
                pass

            try:
                from apps.documents.models import Document as DocumentModel

                stats_data["total_documents"] = DocumentModel.objects.count()
            except (ImportError, Exception):
                pass

            return Response(
                DashboardStatsSerializer(stats_data).data,
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Failed to compute dashboard stats")
            return Response(
                {"detail": f"Failed to compute stats: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def charts(self, request):
        period = request.query_params.get("period", "7d")

        charts = [
            {
                "chart_type": "bar",
                "title": "Files by Status",
                "data": [],
                "period": period,
            },
            {
                "chart_type": "line",
                "title": "Uploads Over Time",
                "data": [],
                "period": period,
            },
            {
                "chart_type": "pie",
                "title": "Documents by Type",
                "data": [],
                "period": period,
            },
            {
                "chart_type": "area",
                "title": "Search Activity",
                "data": [],
                "period": period,
            },
        ]

        return Response(
            ChartDataSerializer(charts, many=True).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def activity(self, request):
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))

        activities = []

        try:
            from apps.files.models import AuditLog

            recent_logs = AuditLog.objects.order_by("-created_at")[
                offset : offset + limit
            ]
            for log in recent_logs:
                activities.append(
                    {
                        "id": log.id,
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "user_email": (
                            log.user.email if hasattr(log, "user") and log.user else None
                        ),
                        "details": log.details if hasattr(log, "details") else {},
                        "created_at": log.created_at,
                    }
                )
        except (ImportError, Exception):
            pass

        return Response(
            {
                "activities": ActivitySerializer(activities, many=True).data,
                "total_count": len(activities),
            },
            status=status.HTTP_200_OK,
        )
