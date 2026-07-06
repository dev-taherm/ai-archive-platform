from django.contrib import admin

from apps.agents.models import Agent, AgentCommand, AgentFolder


class AgentFolderInline(admin.TabularInline):
    model = AgentFolder
    extra = 0


class AgentCommandInline(admin.TabularInline):
    model = AgentCommand
    extra = 0
    readonly_fields = ["created_at", "executed_at"]


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "agent_id",
        "user",
        "status",
        "platform",
        "files_count",
        "last_seen",
    ]
    list_filter = ["status", "platform"]
    search_fields = ["name", "agent_id", "hostname"]
    readonly_fields = ["last_seen", "last_sync_at", "created_at", "updated_at"]
    inlines = [AgentFolderInline, AgentCommandInline]


@admin.register(AgentFolder)
class AgentFolderAdmin(admin.ModelAdmin):
    list_display = ["label", "local_path", "agent", "is_active", "file_count"]
    list_filter = ["is_active"]


@admin.register(AgentCommand)
class AgentCommandAdmin(admin.ModelAdmin):
    list_display = ["command_type", "agent", "status", "created_at", "executed_at"]
    list_filter = ["command_type", "status"]
