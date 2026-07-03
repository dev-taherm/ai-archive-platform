from __future__ import annotations

from django.contrib import admin

from apps.documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "doc_type",
        "processing_status",
        "language",
        "chunk_count",
        "created_at",
    )
    list_filter = ("doc_type", "processing_status", "language")
    search_fields = ("title", "author", "subject", "extracted_text")
    readonly_fields = (
        "id",
        "file_id",
        "chunk_count",
        "classification_confidence",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)
