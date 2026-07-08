from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Profile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "date_joined",
    )
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (_("Archive Role"), {
            "fields": ("role", "last_login_ip"),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_("Archive Role"), {
            "fields": ("role",),
        }),
    )

    actions = ["set_role_archivist", "set_role_viewer"]

    @admin.action(description="Set role to Archivist")
    def set_role_archivist(self, request: admin.request, queryset: admin.QuerySet) -> None:
        count = queryset.update(role=User.Role.ARCHIVIST)
        self.message_user(request, f"{count} user(s) set to Archivist.")

    @admin.action(description="Set role to Viewer")
    def set_role_viewer(self, request: admin.request, queryset: admin.QuerySet) -> None:
        count = queryset.update(role=User.Role.VIEWER)
        self.message_user(request, f"{count} user(s) set to Viewer.")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "department", "timezone")
    search_fields = ("user__username", "user__email", "department")
    list_filter = ("department", "timezone")
    raw_id_fields = ("user",)
