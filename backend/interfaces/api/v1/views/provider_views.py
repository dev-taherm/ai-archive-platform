from __future__ import annotations

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class ProviderConfigViewSet(viewsets.GenericViewSet):
    """ViewSet for managing AI provider configurations."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_model(self):
        from apps.ai.models import ProviderConfig

        return ProviderConfig

    def list(self, request):
        ProviderConfig = self._get_model()
        providers = ProviderConfig.objects.all()
        data = []
        for p in providers:
            data.append(
                {
                    "id": str(p.id),
                    "name": p.name,
                    "display_name": p.display_name,
                    "provider_type": p.provider_type,
                    "capabilities": p.capabilities,
                    "api_key_set": bool(p.api_key),
                    "base_url": p.base_url,
                    "model_name": p.model_name,
                    "is_active": p.is_active,
                    "is_default": p.is_default,
                    "config": p.config,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                }
            )
        return Response(data)

    def create(self, request):
        ProviderConfig = self._get_model()
        name = request.data.get("name", "")
        display_name = request.data.get("display_name", "")
        provider_type = request.data.get("provider_type", "")
        capabilities = request.data.get("capabilities", ["llm"])
        api_key = request.data.get("api_key", "")
        base_url = request.data.get("base_url", "")
        model_name = request.data.get("model_name", "")
        is_default = request.data.get("is_default", False)
        config = request.data.get("config", {})

        if not name or not provider_type:
            return Response(
                {"detail": "name and provider_type are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If setting as default, unset other defaults
        if is_default:
            ProviderConfig.objects.filter(is_default=True).update(is_default=False)

        provider = ProviderConfig.objects.create(
            name=name,
            display_name=display_name or name,
            provider_type=provider_type,
            capabilities=capabilities,
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            is_default=is_default,
            config=config,
        )

        return Response(
            {
                "id": str(provider.id),
                "name": provider.name,
                "display_name": provider.display_name,
                "provider_type": provider.provider_type,
                "capabilities": provider.capabilities,
                "api_key_set": bool(provider.api_key),
                "base_url": provider.base_url,
                "model_name": provider.model_name,
                "is_active": provider.is_active,
                "is_default": provider.is_default,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        ProviderConfig = self._get_model()
        try:
            provider = ProviderConfig.objects.get(id=pk)
        except ProviderConfig.DoesNotExist:
            return Response(
                {"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "id": str(provider.id),
                "name": provider.name,
                "display_name": provider.display_name,
                "provider_type": provider.provider_type,
                "capabilities": provider.capabilities,
                "api_key_set": bool(provider.api_key),
                "api_key": provider.api_key,  # Only on retrieve for editing
                "base_url": provider.base_url,
                "model_name": provider.model_name,
                "is_active": provider.is_active,
                "is_default": provider.is_default,
                "config": provider.config,
            }
        )

    def update(self, request, pk=None):
        ProviderConfig = self._get_model()
        try:
            provider = ProviderConfig.objects.get(id=pk)
        except ProviderConfig.DoesNotExist:
            return Response(
                {"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Update fields
        for field in [
            "name",
            "display_name",
            "provider_type",
            "capabilities",
            "api_key",
            "base_url",
            "model_name",
            "is_active",
            "is_default",
            "config",
        ]:
            if field in request.data:
                setattr(provider, field, request.data[field])

        # If setting as default, unset other defaults
        if request.data.get("is_default"):
            ProviderConfig.objects.filter(is_default=True).exclude(
                id=pk
            ).update(is_default=False)

        provider.save()

        return Response(
            {
                "id": str(provider.id),
                "name": provider.name,
                "display_name": provider.display_name,
                "provider_type": provider.provider_type,
                "capabilities": provider.capabilities,
                "api_key_set": bool(provider.api_key),
                "base_url": provider.base_url,
                "model_name": provider.model_name,
                "is_active": provider.is_active,
                "is_default": provider.is_default,
            }
        )

    def destroy(self, request, pk=None):
        ProviderConfig = self._get_model()
        try:
            provider = ProviderConfig.objects.get(id=pk)
        except ProviderConfig.DoesNotExist:
            return Response(
                {"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )

        provider.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        ProviderConfig = self._get_model()
        try:
            provider = ProviderConfig.objects.get(id=pk)
        except ProviderConfig.DoesNotExist:
            return Response(
                {"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND
            )

        ProviderConfig.objects.filter(is_default=True).update(is_default=False)
        provider.is_default = True
        provider.save()

        return Response({"status": "default set"})

    @action(detail=False, methods=["get"], url_path="active")
    def active_providers(self, request):
        ProviderConfig = self._get_model()
        providers = ProviderConfig.objects.filter(is_active=True)
        data = []
        for p in providers:
            data.append(
                {
                    "id": str(p.id),
                    "name": p.name,
                    "display_name": p.display_name,
                    "provider_type": p.provider_type,
                    "capabilities": p.capabilities,
                    "model_name": p.model_name,
                    "is_default": p.is_default,
                }
            )
        return Response(data)
