from __future__ import annotations

import hashlib
import secrets
import uuid

from django.conf import settings
from django.db import models


class ApiKey(models.Model):
    """API key for programmatic access to the platform."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="api_keys",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    name = models.CharField(max_length=255)
    prefix = models.CharField(
        max_length=12,
        help_text="First 8 chars of the key for identification.",
    )
    key_hash = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="SHA-256 hash of the full API key.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "api_key"
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}...)"

    @classmethod
    def create_key(cls, user, name: str) -> tuple[ApiKey, str]:
        """Create a new API key. Returns (instance, raw_key)."""
        raw_key = f"ak_{secrets.token_hex(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:12]

        instance = cls.objects.create(
            user=user,
            name=name,
            prefix=prefix,
            key_hash=key_hash,
        )
        return instance, raw_key

    @classmethod
    def verify_key(cls, raw_key: str) -> ApiKey | None:
        """Verify a raw API key and return the instance if valid."""
        if not raw_key.startswith("ak_"):
            return None
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        try:
            instance = cls.objects.select_related("user").get(
                key_hash=key_hash,
                is_active=True,
            )
            from django.utils import timezone

            instance.last_used_at = timezone.now()
            instance.save(update_fields=["last_used_at"])
            return instance
        except cls.DoesNotExist:
            return None
