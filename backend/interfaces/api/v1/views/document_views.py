from __future__ import annotations

import logging
import uuid as _uuid

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.domain.common.exceptions import DomainException
from interfaces.api.v1.serializers.document_serializers import (
    DocumentClassifySerializer,
    DocumentExtractSerializer,
    DocumentMetadataSerializer,
    DocumentProcessSerializer,
    DocumentSerializer,
    DocumentUpdateSerializer,
    ExtractedEntitySerializer,
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
        if self.action in ("partial_update", "update"):
            return DocumentUpdateSerializer
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

    def partial_update(self, request, pk=None):
        """PATCH /documents/{pk}/ — update title, author, subject, doc_type, tags."""
        import uuid as _uuid
        from apps.documents.models import Document as DocModel

        try:
            document_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid document ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DocumentUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            doc = DocModel.objects.get(id=document_id)
        except DocModel.DoesNotExist:
            return Response(
                {"detail": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        update_fields = []
        for field, value in serializer.validated_data.items():
            setattr(doc, field, value)
            update_fields.append(field)
        if update_fields:
            doc.save(update_fields=update_fields)

        return Response(DocumentSerializer(doc).data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        """DELETE /documents/{pk}/ — delete a document."""
        import uuid as _uuid
        from apps.documents.models import Document as DocModel

        try:
            document_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid document ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            doc = DocModel.objects.get(id=document_id)
        except DocModel.DoesNotExist:
            return Response(
                {"detail": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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
        from apps.files.models import FileRecord as FileRecordModel

        try:
            file_record = FileRecordModel.objects.get(id=file_id)
        except FileRecordModel.DoesNotExist:
            return Response(
                {"detail": "File not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from core.infrastructure.pipelines.document_pipeline import run_document_pipeline
        try:
            result = run_document_pipeline(
                file_id=str(file_id),
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

    @action(detail=True, methods=["get"], url_path="entities")
    def entities(self, request, pk=None):
        """List extracted entities for a document."""
        import uuid as _uuid
        from apps.documents.models import Document as DocModel

        try:
            document_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid document ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            doc = DocModel.objects.get(id=document_id)
        except DocModel.DoesNotExist:
            return Response(
                {"detail": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        entities = doc.entities.all().order_by("entity_type", "name")
        serializer = ExtractedEntitySerializer(entities, many=True)
        return Response(serializer.data)

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

    @action(detail=False, methods=["post"], url_path="batch-process")
    def batch_process(self, request):
        """Batch process multiple documents.

        Accepts: {"file_ids": ["uuid1", "uuid2", ...]}
        Returns: Batch task summary with individual task IDs.
        """
        file_ids = request.data.get("file_ids", [])
        if not file_ids:
            return Response(
                {"detail": "file_ids is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.documents.tasks import batch_process_documents

        try:
            result = batch_process_documents(
                file_ids,
                user_id=str(request.user.pk) if request.user.is_authenticated else None,
            )
            return Response(result, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.exception("Batch processing failed: %s", e)
            return Response(
                {"detail": f"Batch processing failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="batch-classify")
    def batch_classify(self, request):
        """Classify multiple documents.

        Accepts: {"document_ids": ["uuid1", ...], "categories": ["optional"]}
        Returns: Batch task summary with individual task IDs.
        """
        document_ids = request.data.get("document_ids", [])
        if not document_ids:
            return Response(
                {"detail": "document_ids is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.documents.tasks import batch_classify_documents

        try:
            result = batch_classify_documents(
                document_ids,
                categories=request.data.get("categories"),
                user_id=str(request.user.pk) if request.user.is_authenticated else None,
            )
            return Response(result, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.exception("Batch classification failed: %s", e)
            return Response(
                {"detail": f"Batch classification failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="batch-index")
    def batch_index(self, request):
        """Generate embeddings for multiple documents.

        Accepts: {"document_ids": ["uuid1", ...]}
        Returns: Batch task summary with individual task IDs.
        """
        document_ids = request.data.get("document_ids", [])
        if not document_ids:
            return Response(
                {"detail": "document_ids is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.documents.tasks import batch_index_documents

        try:
            result = batch_index_documents(
                document_ids,
                user_id=str(request.user.pk) if request.user.is_authenticated else None,
            )
            return Response(result, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.exception("Batch indexing failed: %s", e)
            return Response(
                {"detail": f"Batch indexing failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="reprocess-failed")
    def reprocess_failed(self, request):
        """Reprocess all failed documents.

        Returns: Batch task summary.
        """
        from apps.documents.tasks import reprocess_failed

        try:
            result = reprocess_failed(
                user_id=str(request.user.pk) if request.user.is_authenticated else None,
            )
            return Response(result, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.exception("Reprocess failed: %s", e)
            return Response(
                {"detail": f"Reprocess failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
