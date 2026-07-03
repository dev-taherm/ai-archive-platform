from __future__ import annotations

from django.contrib import admin

from apps.search.models import SearchLog


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "query_preview",
        "search_type",
        "result_count",
        "search_time_ms",
        "created_at",
    )
    list_filter = ("search_type",)
    search_fields = ("query",)
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at",)

    @admin.display(description="Query")
    def query_preview(self, obj: SearchLog) -> str:
        return obj.query[:80]
