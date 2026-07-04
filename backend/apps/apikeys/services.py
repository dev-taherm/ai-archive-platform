from __future__ import annotations

import logging
import uuid

from apps.apikeys.models import ApiKey

logger = logging.getLogger(__name__)


class ApiKeyService:
    """Service for managing API keys."""

    @staticmethod
    def create_key(user, name: str) -> tuple[ApiKey, str]:
        """Create a new API key. Returns (instance, raw_key)."""
        instance, raw_key = ApiKey.create_key(user, name)
        logger.info("API key created: %s for user %s", instance.id, user.pk)
        return instance, raw_key

    @staticmethod
    def list_keys(user) -> list[ApiKey]:
        """List all API keys for a user."""
        return list(ApiKey.objects.filter(user=user).order_by("-created_at"))

    @staticmethod
    def revoke_key(key_id: uuid.UUID, user) -> bool:
        """Revoke (delete) an API key. Returns True if deleted."""
        deleted, _ = ApiKey.objects.filter(id=key_id, user=user).delete()
        return deleted > 0

    @staticmethod
    def toggle_active(key_id: uuid.UUID, user) -> ApiKey | None:
        """Toggle the active status of an API key."""
        try:
            key = ApiKey.objects.get(id=key_id, user=user)
            key.is_active = not key.is_active
            key.save(update_fields=["is_active"])
            return key
        except ApiKey.DoesNotExist:
            return None

    @staticmethod
    def verify_key(raw_key: str) -> ApiKey | None:
        """Verify a raw API key."""
        return ApiKey.verify_key(raw_key)
