from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Custom user model with role-based access for the archive platform."""

    class Role(models.TextChoices):
        ADMIN = "admin", _("Admin")
        ARCHIVIST = "archivist", _("Archivist")
        RESEARCHER = "researcher", _("Researcher")
        VIEWER = "viewer", _("Viewer")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )

    class Meta:
        db_table = "accounts_user"
        verbose_name = _("user")
        verbose_name_plural = _("users")
        indexes = [
            models.Index(fields=["role"], name="idx_user_role"),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_archivist(self) -> bool:
        return self.role in (self.Role.ADMIN, self.Role.ARCHIVIST)


class Profile(models.Model):
    """Extended user profile with additional metadata."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone = models.CharField(max_length=30, blank=True, default="")
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
    )
    department = models.CharField(max_length=100, blank=True, default="")
    job_title = models.CharField(max_length=150, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    timezone = models.CharField(max_length=50, default="UTC")

    class Meta:
        db_table = "accounts_profile"
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    def __str__(self) -> str:
        return f"Profile({self.user})"
