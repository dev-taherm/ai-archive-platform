from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from core.infrastructure.db.models.base import BaseModel


class SearchHistoryModel(BaseModel):
    """Tracks user search queries for analytics and query improvement."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_history",
        null=True,
        blank=True,
    )
    query_text = models.CharField(max_length=1000)
    mode = models.CharField(
        max_length=20,
        choices=[
            ("keyword", "keyword"),
            ("semantic", "semantic"),
            ("hybrid", "hybrid"),
            ("exact", "exact"),
        ],
        default="hybrid",
    )
    filters = models.JSONField(default=dict, blank=True)
    result_count = models.PositiveIntegerField(default=0)
    processing_time_ms = models.FloatField(default=0.0)
    selected_result_id = models.UUIDField(null=True, blank=True)
    session_id = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        db_table = "search_history"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_searchhist_user"),
            models.Index(fields=["query_text"], name="idx_searchhist_query"),
            models.Index(fields=["created_at"], name="idx_searchhist_time"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"SearchHistory({self.query_text[:50]})"
