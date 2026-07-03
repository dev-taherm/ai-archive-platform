from __future__ import annotations

from django.contrib import admin

from apps.ai.models import AITask


@admin.register(AITask)
class AITaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "task_type",
        "status",
        "model_used",
        "tokens_used",
        "processing_time_ms",
        "created_at",
    )
    list_filter = ("task_type", "status", "model_used")
    search_fields = ("input_preview", "error_message")
    readonly_fields = (
        "id",
        "result",
        "processing_time_ms",
        "tokens_used",
        "created_at",
        "completed_at",
    )
    ordering = ("-created_at",)
