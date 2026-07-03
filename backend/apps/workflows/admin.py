from __future__ import annotations

from django.contrib import admin

from apps.workflows.models import Workflow, WorkflowRun


class WorkflowRunInline(admin.TabularInline):
    model = WorkflowRun
    extra = 0
    readonly_fields = (
        "id",
        "status",
        "current_step",
        "total_steps",
        "started_at",
        "completed_at",
        "created_at",
    )
    ordering = ("-created_at",)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "trigger_type", "is_active", "created_at")
    list_filter = ("trigger_type", "is_active")
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [WorkflowRunInline]


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workflow",
        "status",
        "current_step",
        "total_steps",
        "started_at",
        "completed_at",
    )
    list_filter = ("status",)
    search_fields = ("workflow__name", "error_message")
    readonly_fields = ("id", "created_at")
    raw_id_fields = ("workflow", "triggered_by")
    ordering = ("-created_at",)
