from __future__ import annotations

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.organizations.mixins import OrgScopedMixin, get_user_organization
from interfaces.api.v1.serializers.dashboard_serializers import (
    ActivitySerializer,
    ChartDataSerializer,
    DashboardStatsSerializer,
    RecommendationSerializer,
    RecommendationListSerializer,
)

logger = logging.getLogger(__name__)


class DashboardView(OrgScopedMixin, viewsets.GenericViewSet):
    """
    Dashboard ViewSet for statistics, charts, and activity feed.

    Queries real data from the database for all dashboard widgets.
    Scoped to the user's organization.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_org(self):
        return get_user_organization(self.request.user)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        try:
            from django.db.models import Count, Sum, Avg
            from django.utils import timezone
            from datetime import timedelta

            org = self._get_org()

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

            # File counts (org-scoped)
            try:
                from apps.files.models import FileRecord as FileModel

                file_qs = FileModel.objects.filter(organization=org)
                stats_data["total_files"] = file_qs.count()

                status_counts = (
                    file_qs.values("status")
                    .annotate(count=Count("id"))
                    .order_by("status")
                )
                stats_data["files_by_status"] = {
                    item["status"]: item["count"] for item in status_counts
                }

                # Storage used
                storage = file_qs.aggregate(total=Sum("size_bytes"))
                stats_data["storage_used_bytes"] = storage["total"] or 0

                # Recent uploads (last 7 days)
                week_ago = timezone.now() - timedelta(days=7)
                stats_data["recent_uploads_count"] = file_qs.filter(
                    created_at__gte=week_ago
                ).count()
            except Exception:
                logger.debug("Could not query file stats")

            # Document counts (org-scoped)
            try:
                from apps.documents.models import Document as DocumentModel

                doc_qs = DocumentModel.objects.filter(organization=org)
                stats_data["total_documents"] = doc_qs.count()

                # Documents by type
                type_counts = (
                    doc_qs.values("doc_type")
                    .annotate(count=Count("id"))
                    .order_by("doc_type")
                )
                stats_data["documents_by_type"] = {
                    item["doc_type"]: item["count"] for item in type_counts
                }

                # Documents by status
                status_counts = (
                    doc_qs.values("processing_status")
                    .annotate(count=Count("id"))
                    .order_by("processing_status")
                )
                stats_data["documents_by_status"] = {
                    item["processing_status"]: item["count"] for item in status_counts
                }

                # Average processing time
                avg_time = doc_qs.filter(
                    processing_status="completed"
                ).aggregate(avg=Avg("processing_time_ms"))
                stats_data["avg_processing_time_ms"] = avg_time["avg"] or 0.0
            except Exception:
                logger.debug("Could not query document stats")

            # Search count (org-scoped)
            try:
                from apps.search.models import SearchLog

                stats_data["total_searches"] = SearchLog.objects.filter(
                    organization=org
                ).count()
            except Exception:
                pass

            # Chat session count (org-scoped)
            try:
                from apps.chat.models import ChatSession

                stats_data["total_chat_sessions"] = ChatSession.objects.filter(
                    organization=org
                ).count()
            except Exception:
                pass

            # Agent counts (org-scoped)
            try:
                from apps.agents.models import Agent

                agent_qs = Agent.objects.filter(organization=org)
                stats_data["agents_total"] = agent_qs.count()
                stats_data["agents_online"] = agent_qs.filter(
                    status="online"
                ).count()
            except Exception:
                pass

            # Duplicate files (org-scoped)
            try:
                from apps.files.models import FileRecord as FileModel

                file_qs = FileModel.objects.filter(organization=org)
                stats_data["duplicate_files"] = file_qs.filter(
                    duplicate_group_id__isnull=False
                ).count()
                dup_groups = file_qs.filter(
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
        from django.db.models.functions import TruncDate
        from datetime import timedelta

        org = self._get_org()
        period = request.query_params.get("period", "7d")
        days = int(period.replace("d", "")) if period.endswith("d") else 7
        since = timezone.now() - timedelta(days=days)

        charts = []

        # Files by Status (bar chart)
        try:
            from apps.files.models import FileRecord as FileModel

            data = (
                FileModel.objects.filter(organization=org)
                .values("status")
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

            data = (
                FileModel.objects.filter(organization=org, created_at__gte=since)
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
                DocumentModel.objects.filter(organization=org)
                .values("doc_type")
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

            data = (
                SearchLog.objects.filter(organization=org, created_at__gte=since)
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
        org = self._get_org()
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))

        activities = []

        try:
            from apps.files.models import AuditLog

            recent_logs = AuditLog.objects.select_related("user").filter(
                organization=org
            ).order_by("-created_at")[offset : offset + limit]
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

    @action(detail=False, methods=["get"])
    def recommendations(self, request):
        """Generate AI-powered recommendations based on current system state."""
        from django.utils import timezone
        from datetime import timedelta

        org = self._get_org()
        recommendations = []
        rec_id = 0

        # 1. Failed documents → suggest reprocessing
        try:
            from apps.documents.models import Document as DocumentModel

            failed_count = DocumentModel.objects.filter(
                organization=org, processing_status="failed"
            ).count()
            if failed_count > 0:
                recommendations.append({
                    "id": f"rec-{rec_id}",
                    "type": "action",
                    "title": "Reprocess failed documents",
                    "description": f"{failed_count} document{'s' if failed_count != 1 else ''} failed processing. Reprocessing may resolve transient errors.",
                    "action_label": "Reprocess All",
                    "action_url": "/documents?status=failed",
                    "priority": "high",
                    "count": failed_count,
                })
                rec_id += 1
        except Exception:
            pass

        # 2. Queued documents → processing backlog
        try:
            from apps.documents.models import Document as DocumentModel

            queued_count = DocumentModel.objects.filter(
                organization=org, processing_status="queued"
            ).count()
            if queued_count > 0:
                recommendations.append({
                    "id": f"rec-{rec_id}",
                    "type": "insight",
                    "title": "Processing backlog detected",
                    "description": f"{queued_count} document{'s' if queued_count != 1 else ''} are queued for processing. Consider checking your AI provider configuration or increasing processing capacity.",
                    "action_label": "View Documents",
                    "action_url": "/documents?status=queued",
                    "priority": "medium",
                    "count": queued_count,
                })
                rec_id += 1
        except Exception:
            pass

        # 3. Duplicate files
        try:
            from apps.files.models import FileRecord as FileModel

            dup_count = FileModel.objects.filter(
                organization=org, duplicate_group_id__isnull=False
            ).count()
            if dup_count > 0:
                recommendations.append({
                    "id": f"rec-{rec_id}",
                    "type": "warning",
                    "title": "Duplicate files detected",
                    "description": f"{dup_count} file{'s' if dup_count != 1 else ''} are duplicates. Review and remove unnecessary copies to save storage.",
                    "action_label": "View Duplicates",
                    "action_url": "/ai-workspace?tab=duplicates",
                    "priority": "medium",
                    "count": dup_count,
                })
                rec_id += 1
        except Exception:
            pass

        # 4. Documents without summaries
        try:
            from apps.documents.models import Document as DocumentModel

            doc_qs = DocumentModel.objects.filter(organization=org)
            completed = doc_qs.filter(processing_status="completed").count()
            with_summary = doc_qs.filter(
                processing_status="completed",
                summary__isnull=False,
            ).exclude(summary="").count()
            missing = completed - with_summary
            if missing > 0 and completed > 0:
                recommendations.append({
                    "id": f"rec-{rec_id}",
                    "type": "insight",
                    "title": "Documents without AI summaries",
                    "description": f"{missing} of {completed} completed documents lack AI summaries. Generate summaries to improve search and discovery.",
                    "action_label": "AI Workspace",
                    "action_url": "/ai-workspace?tab=summaries",
                    "priority": "low",
                    "count": missing,
                })
                rec_id += 1
        except Exception:
            pass

        # 5. Stale agents (no heartbeat in >1 hour)
        try:
            from apps.agents.models import Agent

            threshold = timezone.now() - timedelta(hours=1)
            stale = Agent.objects.filter(
                organization=org,
                status="online",
                last_seen__lt=threshold,
            ).count()
            if stale > 0:
                recommendations.append({
                    "id": f"rec-{rec_id}",
                    "type": "warning",
                    "title": "Agents may be offline",
                    "description": f"{stale} agent{'s' if stale != 1 else ''} marked online but haven't sent a heartbeat recently. They may have lost connectivity.",
                    "action_label": "View Agents",
                    "action_url": "/agents",
                    "priority": "high",
                    "count": stale,
                })
                rec_id += 1
        except Exception:
            pass

        # 6. No AI providers configured
        try:
            from apps.ai.models import ProviderConfig

            active_providers = ProviderConfig.objects.filter(
                is_active=True
            ).count()
            if active_providers == 0:
                recommendations.append({
                    "id": f"rec-{rec_id}",
                    "type": "action",
                    "title": "Configure an AI provider",
                    "description": "No active AI providers found. Add an AI provider (OpenAI, Google, or Ollama) to enable document processing, classification, and search.",
                    "action_label": "Settings",
                    "action_url": "/settings",
                    "priority": "high",
                    "count": None,
                })
                rec_id += 1
        except Exception:
            pass

        # 7. Documents without entities (richness indicator)
        try:
            from apps.documents.models import Document as DocumentModel

            doc_qs = DocumentModel.objects.filter(organization=org)
            completed = doc_qs.filter(processing_status="completed").count()
            with_entities = doc_qs.filter(
                processing_status="completed",
                entities__isnull=False,
            ).distinct().count()
            without = completed - with_entities
            if without > 3 and completed > 0:
                pct = (without / completed) * 100
                recommendations.append({
                    "id": f"rec-{rec_id}",
                    "type": "insight",
                    "title": "Entity extraction coverage",
                    "description": f"{without} of {completed} documents ({pct:.0f}%) lack extracted entities. Enable entity extraction to build a knowledge graph.",
                    "action_label": "AI Workspace",
                    "action_url": "/ai-workspace?tab=entities",
                    "priority": "low",
                    "count": without,
                })
                rec_id += 1
        except Exception:
            pass

        from django.utils import timezone as tz

        return Response(
            RecommendationListSerializer({
                "recommendations": RecommendationSerializer(recommendations, many=True).data,
                "generated_at": tz.now(),
            }).data,
            status=status.HTTP_200_OK,
        )
