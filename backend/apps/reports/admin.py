from __future__ import annotations

from django.contrib import admin

from apps.reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "report_type",
        "status",
        "generated_at",
        "created_at",
    )
    list_filter = ("report_type", "status")
    search_fields = ("title", "error_message")
    readonly_fields = (
        "id",
        "data",
        "file_path",
        "generated_at",
        "created_at",
    )
    raw_id_fields = ("generated_by",)
    ordering = ("-created_at",)
