from __future__ import annotations

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.domain.common.exceptions import DomainException
from interfaces.api.v1.serializers.ai_serializers import (
    AIProviderSerializer,
    ClassificationSerializer,
    ExtractionSerializer,
    SummarizeSerializer,
)

logger = logging.getLogger(__name__)


class AIView(viewsets.GenericViewSet):
    """
    AI operations ViewSet.

    Provides classify, extract, summarize, and providers actions.
    Delegates all business logic to AIService.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "classify":
            return ClassificationSerializer
        if self.action == "extract":
            return ExtractionSerializer
        if self.action == "summarize":
            return SummarizeSerializer
        return ClassificationSerializer

    @property
    def _ai_service(self):
        from django.apps import apps
        return apps.get_app_config("ai").ai_service

    @action(detail=False, methods=["post"])
    def classify(self, request):
        serializer = ClassificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            result = self._ai_service.classify(
                text=validated["text"],
                categories=validated.get("categories"),
                system_prompt=validated.get("system_prompt"),
                user_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                {
                    "input_text": result.input_text,
                    "predicted_label": result.predicted_label,
                    "confidence": result.confidence,
                    "all_labels": result.all_labels,
                    "model_used": result.model_used,
                    "classified_at": result.classified_at.isoformat(),
                },
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["post"])
    def extract(self, request):
        serializer = ExtractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            result = self._ai_service.extract(
                text=validated["text"],
                fields=validated["fields"],
                system_prompt=validated.get("system_prompt"),
                user_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                {
                    "extracted_data": result,
                    "fields": validated["fields"],
                },
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["post"])
    def summarize(self, request):
        serializer = SummarizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            summary = self._ai_service.summarize(
                text=validated["text"],
                max_tokens=validated.get("max_tokens", 500),
                system_prompt=validated.get("system_prompt"),
                user_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                {"summary": summary},
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["get"])
    def providers(self, request):
        providers = [
            {
                "name": "openai",
                "display_name": "OpenAI",
                "is_available": True,
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
                "capabilities": ["classify", "extract", "summarize", "chat"],
            },
            {
                "name": "anthropic",
                "display_name": "Anthropic",
                "is_available": True,
                "models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
                "capabilities": ["classify", "extract", "summarize", "chat"],
            },
            {
                "name": "local",
                "display_name": "Local Models",
                "is_available": False,
                "models": [],
                "capabilities": ["classify", "extract"],
            },
        ]
        return Response(
            AIProviderSerializer(providers, many=True).data,
            status=status.HTTP_200_OK,
        )
