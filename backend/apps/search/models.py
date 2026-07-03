from __future__ import annotations

import uuid

from django.db import models


class SearchLog(models.Model):
    """Logs search queries for analytics and improving search quality."""

    class SearchType(models.TextChoices):
        SEMANTIC = "semantic", "Semantic"
        KEYWORD = "keyword", "Keyword"
        HYBRID = "hybrid", "Hybrid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    query = models.TextField()
    search_type = models.CharField(
        max_length=20,
        choices=SearchType.choices,
        default=SearchType.HYBRID,
    )
    result_count = models.PositiveIntegerField(default=0)
    search_time_ms = models.FloatField(default=0.0)
    filters_used = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_searchlog"
        verbose_name = "Search Log"
        verbose_name_plural = "Search Logs"
        indexes = [
            models.Index(fields=["user_id", "created_at"], name="idx_searchlog_user_time"),
            models.Index(fields=["search_type"], name="idx_searchlog_type"),
            models.Index(fields=["created_at"], name="idx_searchlog_created"),
        ]

    def __str__(self) -> str:
        return f"Search({self.query[:50]}) [{self.search_type}]"
