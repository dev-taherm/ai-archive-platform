from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class SearchLog(models.Model):
    """Logs search queries for analytics and improving search quality."""

    class SearchType(models.TextChoices):
        SEMANTIC = "semantic", "Semantic"
        KEYWORD = "keyword", "Keyword"
        HYBRID = "hybrid", "Hybrid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="search_logs",
        null=True,
        blank=True,
    )
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


class SavedSearch(models.Model):
    """A user's saved search query for quick re-execution."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="saved_searches",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_searches",
    )
    name = models.CharField(max_length=255)
    query = models.TextField()
    search_type = models.CharField(
        max_length=20,
        choices=SearchLog.SearchType.choices,
        default=SearchLog.SearchType.HYBRID,
    )
    filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_savedsearch"
        verbose_name = "Saved Search"
        verbose_name_plural = "Saved Searches"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_savedsearch_user_time"),
        ]

    def __str__(self) -> str:
        return f"{self.name}: {self.query[:50]}"
