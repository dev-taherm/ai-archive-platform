"""Shared audit logging service."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from core.application.interfaces.repositories import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditService:
    """Thin wrapper that persists audit log entries via the repository port."""

    def __init__(self, audit_log_repository: AuditLogRepository) -> None:
        self._audit_log_repository = audit_log_repository

    async def log(
        self,
        action: str,
        user_id: uuid.UUID | None,
        resource_type: str,
        resource_id: uuid.UUID | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Persist an audit log entry."""
        try:
            await self._audit_log_repository.save({
                "action": action,
                "user_id": str(user_id) if user_id else None,
                "resource_type": resource_type,
                "resource_id": str(resource_id) if resource_id else None,
                "details": details or {},
            })
        except Exception as e:
            logger.warning("Failed to write audit log: %s", e)
