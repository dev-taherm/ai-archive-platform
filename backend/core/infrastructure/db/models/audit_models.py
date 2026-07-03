from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db import models

from core.infrastructure.db.models.base import BaseModel


class AuditLogModel(BaseModel):
    """Immutable audit log entry tracking all significant system actions.

    Uses append-only semantics (no update/delete in normal operation) to
    maintain a tamper-evident record of who did what and when.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.CharField(max_length=100, blank=True, default="")
    changes = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "audit_log"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_audit_user"),
            models.Index(fields=["resource_type", "resource_id"], name="idx_audit_resource"),
            models.Index(fields=["action"], name="idx_audit_action"),
            models.Index(fields=["-created_at"], name="idx_audit_time"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"AuditLog({self.action} on {self.resource_type}/{self.resource_id})"

    @classmethod
    def log(
        cls,
        action: str,
        resource_type: str,
        resource_id: str | uuid.UUID = "",
        user: Any = None,
        changes: dict | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> AuditLogModel:
        """Convenience factory for creating audit entries."""
        return cls(
            user=user,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            changes=changes or {},
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
