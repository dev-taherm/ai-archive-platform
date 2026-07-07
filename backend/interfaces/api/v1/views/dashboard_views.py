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

    Queries real data from the database for all dashboard widgets.
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def stats(self, request):
        try:
            from django.db.models import Count
            from django.utils import timezone
            from datetime import timedelta

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
                "agents_total": 0,
                "agents_online": 0,
                "duplicate_files": 0,
                "duplicate_groups": 0,
            }

            # File counts
            try:
                from apps.files.models import FileRecord as FileModel

                stats_data["total_files"] = FileModel.objects.count()

                status_counts = (
                    FileModel.objects.values("status")
                    .annotate(count=Count("id"))
                    .order_by("status")
                )
                stats_data["files_by_status"] = {
                    item["status"]: item["count"] for item in status_counts
                }

                # Storage used
                from django.db.models import Sum

                storage = FileModel.objects.aggregate(total=Sum("size_bytes"))
                stats_data["storage_used_bytes"] = storage["total"] or 0

                # Recent uploads (last 7 days)
                week_ago = timezone.now() - timedelta(days=7)
                stats_data["recent_uploads_count"] = FileModel.objects.filter(
                    created_at__gte=week_ago
                ).count()
            except Exception:
                logger.debug("Could not query file stats")

            # Document counts
            try:
                from apps.documents.models import Document as DocumentModel

                stats_data["total_documents"] = DocumentModel.objects.count()

                # Documents by type
                type_counts = (
                    DocumentModel.objects.values("doc_type")
                    .annotate(count=Count("id"))
                    .order_by("doc_type")
                )
                stats_data["documents_by_type"] = {
                    item["doc_type"]: item["count"] for item in type_counts
                }

                # Documents by status
                status_counts = (
                    DocumentModel.objects.values("processing_status")
                    .annotate(count=Count("id"))
                    .order_by("processing_status")
                )
                stats_data["documents_by_status"] = {
                    item["processing_status"]: item["count"] for item in status_counts
                }

                # Average processing time
                from django.db.models import Avg

                avg_time = DocumentModel.objects.filter(
                    processing_status="completed"
                ).aggregate(avg=Avg("processing_time_ms"))
                stats_data["avg_processing_time_ms"] = avg_time["avg"] or 0.0
            except Exception:
                logger.debug("Could not query document stats")

            # Search count
            try:
                from apps.search.models import SearchLog

                stats_data["total_searches"] = SearchLog.objects.count()
            except Exception:
                pass

            # Chat session count
            try:
                from apps.chat.models import ChatSession

                stats_data["total_chat_sessions"] = ChatSession.objects.count()
            except Exception:
                pass

            # Agent counts
            try:
                from apps.agents.models import Agent

                stats_data["agents_total"] = Agent.objects.count()
                stats_data["agents_online"] = Agent.objects.filter(
                    status="online"
                ).count()
            except Exception:
                pass

            # Duplicate files
            try:
                from apps.files.models import FileRecord as FileModel

                stats_data["duplicate_files"] = FileModel.objects.filter(
                    duplicate_group_id__isnull=False
                ).count()
                dup_groups = FileModel.objects.filter(
                    duplicate_group_id__isnull=False
                ).aggregate(groups=Count("duplicate_group_id", distinct=True))
                stats_data["duplicate_groups"] = dup_groups["groups"] or 0
            except Exception:
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
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta

        period = request.query_params.get("period", "7d")
        days = int(period.replace("d", "")) if period.endswith("d") else 7
        since = timezone.now() - timedelta(days=days)

        charts = []

        # Files by Status (bar chart)
        try:
            from apps.files.models import FileRecord as FileModel

            data = (
                FileModel.objects.values("status")
                .annotate(count=Count("id"))
                .order_by("status")
            )
            charts.append(
                {
                    "chart_type": "bar",
                    "title": "Files by Status",
                    "data": [
                        {"label": item["status"], "value": item["count"]}
                        for item in data
                    ],
                    "period": period,
                }
            )
        except Exception:
            charts.append(
                {
                    "chart_type": "bar",
                    "title": "Files by Status",
                    "data": [],
                    "period": period,
                }
            )

        # Uploads Over Time (line chart)
        try:
            from apps.files.models import FileRecord as FileModel
            from django.db.models.functions import TruncDate

            data = (
                FileModel.objects.filter(created_at__gte=since)
                .annotate(date=TruncDate("created_at"))
                .values("date")
                .annotate(count=Count("id"))
                .order_by("date")
            )
            charts.append(
                {
                    "chart_type": "line",
                    "title": "Uploads Over Time",
                    "data": [
                        {"label": item["date"].isoformat(), "value": item["count"]}
                        for item in data
                    ],
                    "period": period,
                }
            )
        except Exception:
            charts.append(
                {
                    "chart_type": "line",
                    "title": "Uploads Over Time",
                    "data": [],
                    "period": period,
                }
            )

        # Documents by Type (pie chart)
        try:
            from apps.documents.models import Document as DocumentModel

            data = (
                DocumentModel.objects.values("doc_type")
                .annotate(count=Count("id"))
                .order_by("-count")
            )
            charts.append(
                {
                    "chart_type": "pie",
                    "title": "Documents by Type",
                    "data": [
                        {"label": item["doc_type"], "value": item["count"]}
                        for item in data
                    ],
                    "period": period,
                }
            )
        except Exception:
            charts.append(
                {
                    "chart_type": "pie",
                    "title": "Documents by Type",
                    "data": [],
                    "period": period,
                }
            )

        # Search Activity (area chart)
        try:
            from apps.search.models import SearchLog
            from django.db.models.functions import TruncDate

            data = (
                SearchLog.objects.filter(created_at__gte=since)
                .annotate(date=TruncDate("created_at"))
                .values("date")
                .annotate(count=Count("id"))
                .order_by("date")
            )
            charts.append(
                {
                    "chart_type": "area",
                    "title": "Search Activity",
                    "data": [
                        {"label": item["date"].isoformat(), "value": item["count"]}
                        for item in data
                    ],
                    "period": period,
                }
            )
        except Exception:
            charts.append(
                {
                    "chart_type": "area",
                    "title": "Search Activity",
                    "data": [],
                    "period": period,
                }
            )

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

            recent_logs = AuditLog.objects.select_related("user").order_by(
                "-created_at"
            )[offset : offset + limit]
            for log in recent_logs:
                activities.append(
                    {
                        "id": log.id,
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "user_email": (
                            log.user.email
                            if hasattr(log, "user") and log.user
                            else None
                        ),
                        "details": log.details if hasattr(log, "details") else {},
                        "created_at": log.created_at,
                    }
                )
        except Exception:
            logger.debug("Could not query audit logs for activity")

        return Response(
            {
                "activities": ActivitySerializer(activities, many=True).data,
                "total_count": len(activities),
            },
            status=status.HTTP_200_OK,
        )
