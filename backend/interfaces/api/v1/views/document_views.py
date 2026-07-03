from __future__ import annotations

import logging

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.domain.common.exceptions import DomainException
from interfaces.api.v1.serializers.document_serializers import (
    DocumentChunkSerializer,
    DocumentClassifySerializer,
    DocumentExtractSerializer,
    DocumentMetadataSerializer,
    DocumentProcessSerializer,
    DocumentSerializer,
)

logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.GenericViewSet):
    """
    ViewSet for document management.

    Provides list, retrieve, process, metadata, classify, and extract actions.
    Delegates all business logic to DocumentService.
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action == "process":
            return DocumentProcessSerializer
        if self.action == "classify":
            return DocumentClassifySerializer
        if self.action == "extract":
            return DocumentExtractSerializer
        return DocumentSerializer

    @property
    def _document_service(self):
        from django.apps import apps
        return apps.get_app_config("documents").document_service

    def list(self, request):
        offset = (int(request.query_params.get("page", 1)) - 1) * int(
            request.query_params.get("page_size", 20)
        )
        limit = int(request.query_params.get("page_size", 20))

        try:
            documents = self._document_service.list_documents(offset=offset, limit=limit)
            serializer = DocumentSerializer(documents, many=True)
            return Response(serializer.data)
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    def retrieve(self, request, pk=None):
        import uuid as _uuid
        try:
            document_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid document ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            document = self._document_service.get_document(document_id)
            serializer = DocumentSerializer(document)
            return Response(serializer.data)
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["post"])
    def process(self, request):
        serializer = DocumentProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            document = self._document_service.process_document(
                file_id=serializer.validated_data["file_id"],
                user_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                DocumentSerializer(document).data,
                status=status.HTTP_201_CREATED,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["get"])
    def metadata(self, request, pk=None):
        import uuid as _uuid
        try:
            document_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid document ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            metadata = self._document_service.extract_metadata(document_id)
            return Response(
                DocumentMetadataSerializer(metadata).data,
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def classify(self, request, pk=None):
        import uuid as _uuid
        try:
            document_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid document ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DocumentClassifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self._document_service.classify_document(
                document_id,
                categories=serializer.validated_data.get("categories"),
                user_id=request.user.pk if request.user.is_authenticated else None,
            )
            return Response(
                {
                    "document_id": str(result.document_id),
                    "predicted_type": result.predicted_type,
                    "confidence": result.confidence,
                    "all_scores": result.all_scores,
                    "model_used": result.model_used,
                    "classified_at": result.classified_at.isoformat(),
                },
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def extract(self, request, pk=None):
        import uuid as _uuid
        try:
            document_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid document ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DocumentExtractSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            metadata = self._document_service.extract_metadata(
                document_id,
                fields=serializer.validated_data.get("fields"),
            )
            return Response(
                DocumentMetadataSerializer(metadata).data,
                status=status.HTTP_200_OK,
            )
        except DomainException as e:
            return Response(
                {"detail": e.message}, status=status.HTTP_400_BAD_REQUEST
            )
