from __future__ import annotations

from django.contrib import admin

from apps.chat.models import ChatMessage, ChatSession


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("id", "role", "content", "tokens_used", "model_used", "created_at")
    ordering = ("created_at",)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("title", "user__username")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("user",)
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "content_preview", "tokens_used", "created_at")
    list_filter = ("role",)
    search_fields = ("content",)
    readonly_fields = ("id", "created_at")
    raw_id_fields = ("session",)

    @admin.display(description="Content")
    def content_preview(self, obj: ChatMessage) -> str:
        return obj.content[:80]
