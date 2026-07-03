from __future__ import annotations

from django.contrib import admin

from apps.files.models import FileRecord


@admin.register(FileRecord)
class FileRecordAdmin(admin.ModelAdmin):
    list_display = ("path", "mime_type", "size_bytes", "status", "created_at")
    list_filter = ("status", "mime_type")
    search_fields = ("path", "content_hash")
    readonly_fields = ("id", "content_hash", "created_at", "updated_at")
    ordering = ("-created_at",)
