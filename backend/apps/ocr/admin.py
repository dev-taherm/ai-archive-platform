from __future__ import annotations

from django.contrib import admin

from apps.ocr.models import OCRJob


@admin.register(OCRJob)
class OCRJobAdmin(admin.ModelAdmin):
    list_display = ("id", "file_id", "source_type", "status", "language", "created_at")
    list_filter = ("status", "source_type")
    search_fields = ("file_id", "extracted_text")
    readonly_fields = (
        "id",
        "file_id",
        "document_id",
        "extracted_text",
        "confidence",
        "processing_time_ms",
        "created_at",
        "completed_at",
    )
    ordering = ("-created_at",)
