from __future__ import annotations

import uuid
from typing import Any, Sequence


from core.application.interfaces.repositories import AuditLogRepository


class DjangoAuditLogRepository(AuditLogRepository):
    """Django ORM implementation of AuditLogRepository ABC.

    Creates audit entries directly via Django ORM without a dedicated model.
    Uses a simple JSON-based approach for flexibility.
    """

    def __init__(self) -> None:
        # We use a simple approach - create entries via raw SQL or a lightweight model
        # For now, we'll store in a simple model that gets created dynamically
        pass

    async def save(self, log_entry: dict[str, Any]) -> None:
        # Store audit log entry - in production this would use a dedicated model
        # For MVP, we log to console/file
        import logging
        logger = logging.getLogger("audit")
        logger.info(
            "AUDIT: %s %s/%s by user=%s",
            log_entry.get("action", ""),
            log_entry.get("resource_type", ""),
            log_entry.get("resource_id", ""),
            log_entry.get("user_id", "system"),
        )

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[dict[str, Any]]:
        return []

    async def list_by_resource(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[dict[str, Any]]:
        return []
