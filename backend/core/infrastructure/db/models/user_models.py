from __future__ import annotations

import uuid
from typing import Any

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.infrastructure.db.models.base import BaseModel


class CustomUserManager(BaseUserManager["User"]):
    """Custom manager for User model with role-based creation helpers."""

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_approved", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email: str) -> User:
        return self.get(email__iexact=email)


class User(AbstractUser):
    """Custom user model with role-based access for the archive platform.

    Mirrors the existing accounts.User to keep infrastructure models self-contained
    within the core layer. AUTH_USER_MODEL should be pointed at accounts.User in
    production; this model exists so that repository and infrastructure code can
    reference a user model without importing from the apps layer.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", _("Admin")
        ARCHIVIST = "archivist", _("Archivist")
        RESEARCHER = "researcher", _("Researcher")
        VIEWER = "viewer", _("Viewer")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    is_approved = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = ["username"]

    class Meta:
        db_table = "core_user"
        verbose_name = _("user")
        verbose_name_plural = _("users")
        indexes = [
            models.Index(fields=["role"], name="idx_core_user_role"),
            models.Index(fields=["is_approved"], name="idx_core_user_approved"),
        ]

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_archivist(self) -> bool:
        return self.role in (self.Role.ADMIN, self.Role.ARCHIVIST)
