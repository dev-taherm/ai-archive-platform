from __future__ import annotations

import logging
import uuid
from typing import Any

from django.db import models

from core.infrastructure.cache.redis_cache import cache

logger = logging.getLogger(__name__)

DASHBOARD_CACHE_TTL = 60  # 1 minute for dashboard stats


class DashboardService:
    """Service for aggregating data for dashboard views."""

    @staticmethod
    def get_overview(user_id: uuid.UUID | None = None) -> dict[str, Any]:
        """Get high-level overview statistics for the dashboard."""
        cache_key = "dashboard:overview"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        from apps.files.models import FileRecord
        from apps.documents.models import Document
        from apps.search.models import SearchLog

        total_files = FileRecord.objects.count()
        total_documents = Document.objects.count()
        completed_documents = Document.objects.filter(
            processing_status="completed"
        ).count()
        failed_documents = Document.objects.filter(
            processing_status="failed"
        ).count()
        pending_documents = Document.objects.filter(
            processing_status__in=["pending", "processing", "indexing"]
        ).count()

        total_searches = SearchLog.objects.count()

        result = {
            "total_files": total_files,
            "total_documents": total_documents,
            "completed_documents": completed_documents,
            "failed_documents": failed_documents,
            "pending_documents": pending_documents,
            "total_searches": total_searches,
        }

        cache.set(cache_key, result, ttl=DASHBOARD_CACHE_TTL)
        return result

    @staticmethod
    def get_recent_activity(limit: int = 20) -> list[dict[str, Any]]:
        """Get recent activity across the platform."""
        from django.utils import timezone
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=7)

        activities: list[dict[str, Any]] = []

        from apps.documents.models import Document

        recent_docs = Document.objects.filter(
            created_at__gte=cutoff
        ).order_by("-created_at")[:limit]

        for doc in recent_docs:
            activities.append({
                "type": "document_processed",
                "document_id": str(doc.id),
                "title": doc.title,
                "doc_type": doc.doc_type,
                "status": doc.processing_status,
                "timestamp": doc.created_at.isoformat(),
            })

        from apps.search.models import SearchLog

        recent_searches = SearchLog.objects.filter(
            created_at__gte=cutoff
        ).order_by("-created_at")[:limit]

        for search in recent_searches:
            activities.append({
                "type": "search",
                "query": search.query[:100],
                "search_type": search.search_type,
                "result_count": search.result_count,
                "timestamp": search.created_at.isoformat(),
            })

        activities.sort(key=lambda a: a["timestamp"], reverse=True)
        return activities[:limit]

    @staticmethod
    def get_storage_stats() -> dict[str, Any]:
        """Get storage usage statistics."""
        cache_key = "dashboard:storage"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        from apps.files.models import FileRecord
        from django.db.models import Sum

        stats = FileRecord.objects.aggregate(
            total_size=Sum("size_bytes"),
            file_count=models.Count("id"),
        )

        mime_distribution = dict(
            FileRecord.objects.values_list("mime_type")
            .annotate(count=models.Count("id"))
            .order_by("-count")[:10]
        )

        result = {
            "total_size_bytes": stats["total_size"] or 0,
            "total_files": stats["file_count"] or 0,
            "mime_type_distribution": mime_distribution,
        }

        cache.set(cache_key, result, ttl=DASHBOARD_CACHE_TTL)
        return result

    @staticmethod
    def get_document_type_breakdown() -> dict[str, int]:
        """Get document counts grouped by type."""
        cache_key = "dashboard:doc_types"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        from apps.documents.models import Document

        result = dict(
            Document.objects.values_list("doc_type")
            .annotate(count=models.Count("id"))
            .order_by("-count")
            .values_list("doc_type", "count")
        )

        cache.set(cache_key, result, ttl=DASHBOARD_CACHE_TTL)
        return result

    @staticmethod
    def get_processing_queue() -> dict[str, Any]:
        """Get current processing queue status."""
        cache_key = "dashboard:queue"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        from apps.documents.models import Document

        statuses = dict(
            Document.objects.values_list("processing_status")
            .annotate(count=models.Count("id"))
            .values_list("processing_status", "count")
        )

        result = {
            "pending": statuses.get("pending", 0),
            "processing": statuses.get("processing", 0),
            "indexing": statuses.get("indexing", 0),
            "completed": statuses.get("completed", 0),
            "failed": statuses.get("failed", 0),
        }

        cache.set(cache_key, result, ttl=DASHBOARD_CACHE_TTL)
        return result

    @staticmethod
    def invalidate_cache() -> int:
        """Clear all dashboard cache keys. Returns number of keys cleared."""
        return cache.clear_pattern("dashboard:*")
