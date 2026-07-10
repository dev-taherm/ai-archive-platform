from __future__ import annotations

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.apikeys.models import ApiKey
from apps.apikeys.services import ApiKeyService

logger = logging.getLogger(__name__)


class ApiKeyViewSet(viewsets.GenericViewSet):
    """ViewSet for managing API keys."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ApiKey.objects.filter(user=self.request.user)

    def list(self, request):
        keys = ApiKeyService.list_keys(request.user)
        data = [
            {
                "id": str(k.id),
                "name": k.name,
                "prefix": k.prefix,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat(),
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ]
        return Response(data, status=status.HTTP_200_OK)

    def create(self, request):
        name = request.data.get("name", "").strip()
        if not name:
            return Response(
                {"detail": "Name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance, raw_key = ApiKeyService.create_key(request.user, name)

        # Set organization from the creating user
        if hasattr(request.user, "current_organization") and request.user.current_organization:
            instance.organization = request.user.current_organization
            instance.save(update_fields=["organization"])

        return Response(
            {
                "id": str(instance.id),
                "name": instance.name,
                "prefix": instance.prefix,
                "key": raw_key,
                "is_active": instance.is_active,
                "created_at": instance.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, pk=None):
        try:
            import uuid

            key_id = uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid key ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted = ApiKeyService.revoke_key(key_id, request.user)
        if not deleted:
            return Response(
                {"detail": "API key not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        try:
            import uuid

            key_id = uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid key ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        key = ApiKeyService.toggle_active(key_id, request.user)
        if key is None:
            return Response(
                {"detail": "API key not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "id": str(key.id),
                "name": key.name,
                "is_active": key.is_active,
            },
            status=status.HTTP_200_OK,
        )
