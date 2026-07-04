from django.contrib import admin

from apps.apikeys.models import ApiKey


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "prefix", "user", "is_active", "created_at", "last_used_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "prefix", "user__email")
    readonly_fields = ("id", "key_hash", "prefix", "created_at", "last_used_at")
