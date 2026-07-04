from __future__ import annotations

import logging
import uuid as _uuid

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
        try:
            documents = self._document_service.list_documents()
            page = self.paginate_queryset(documents)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(documents, many=True)
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

    @action(detail=False, methods=["post"], url_path="process-pipeline")
    def process_pipeline(self, request):
        """Process a document through the full LangGraph pipeline.

        Accepts: {"file_id": "uuid"}
        Returns: Full pipeline results with classification, entities, summary, chunks, embeddings.
        """
        file_id_str = request.data.get("file_id")
        if not file_id_str:
            return Response(
                {"detail": "file_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            file_id = _uuid.UUID(str(file_id_str))
        except ValueError:
            return Response(
                {"detail": "Invalid file_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Look up file record to get path and mime type
        from core.infrastructure.db.repositories.file_repository import DjangoFileRepository
        file_repo = DjangoFileRepository()
        file_record = file_repo.get_by_id(file_id)

        if not file_record:
            return Response(
                {"detail": "File not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from core.infrastructure.pipelines.document_pipeline import run_document_pipeline
        try:
            result = run_document_pipeline(
                file_id=str(file_id),
                file_path=str(file_record.path.normalized),
                mime_type=file_record.mime_type.value,
            )
        except Exception as e:
            logger.exception("Pipeline failed: %s", e)
            return Response(
                {"detail": f"Pipeline failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "status": result.get("status"),
                "document_id": result.get("document_id"),
                "parse_method": result.get("parse_method"),
                "classification": result.get("classification"),
                "classification_confidence": result.get("classification_confidence"),
                "entities": result.get("entities", []),
                "summary": result.get("summary"),
                "chunk_count": result.get("chunk_count"),
                "embedding_count": len(result.get("embedding_ids", [])),
                "processing_log": result.get("processing_log", []),
                "error": result.get("error"),
            },
            status=status.HTTP_201_CREATED,
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
