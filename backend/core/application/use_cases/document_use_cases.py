from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from core.application.dtos.document_dto import (
    ClassificationResultDTO,
    DocumentDTO,
    DocumentMetadataDTO,
)
from core.application.interfaces.repositories import (
    DocumentRepository,
    EmbeddingRepository,
    FileRepository,
)
from core.application.interfaces.services import LLMProvider, OCRProvider
from core.domain.common.exceptions import EntityNotFound, ValidationException
from core.domain.documents.entities import Document, DocumentChunk, DocumentMetadata
from core.domain.documents.value_objects import (
    Confidence,
    DocumentType,
    Language,
    ProcessingStatus,
)

logger = logging.getLogger(__name__)


class DocumentUseCases:
    """Use cases for document processing and management."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        file_repository: FileRepository,
        embedding_repository: EmbeddingRepository,
        ocr_provider: OCRProvider,
        llm_provider: LLMProvider,
        document_reader: Any = None,
    ) -> None:
        self._document_repository = document_repository
        self._file_repository = file_repository
        self._embedding_repository = embedding_repository
        self._ocr_provider = ocr_provider
        self._llm_provider = llm_provider
        self._document_reader = document_reader

    def process_document(self, file_id: uuid.UUID) -> DocumentDTO:
        file_record = self._file_repository.get_by_id(file_id)
        if file_record is None:
            raise EntityNotFound("FileRecord", str(file_id))

        document = Document(file_id=file_id)
        document.start_processing()

        try:
            extracted_text = ""
            page_count = 0
            doc_metadata: dict[str, Any] = {}

            if self._document_reader is not None:
                file_path = file_record.path.normalized
                try:
                    result = self._document_reader.read(file_path)
                    extracted_text = result.text
                    page_count = result.page_count
                    doc_metadata = result.metadata
                except Exception as e:
                    logger.warning("DocumentReader failed for %s: %s", file_path, e)

            if not extracted_text:
                extracted_text = self._ocr_provider.extract_text(
                    b"",
                    content_type=file_record.mime_type.value,
                )

            from core.domain.documents.value_objects import Language as LangValue

            lang_value = LangValue.UNKNOWN
            try:
                detected_lang = self._ocr_provider.detect_language(extracted_text)
                lang_value = detected_lang
            except Exception:
                pass

            title = doc_metadata.get("title", "")
            author = doc_metadata.get("author", "")
            subject = doc_metadata.get("subject", "")

            if not title:
                title = Path(file_record.path.normalized).stem

            categories = [dt.value for dt in DocumentType]
            predicted_type_str, type_confidence = self._llm_provider.classify(
                extracted_text[:2000] if extracted_text else "",
                categories=categories,
                system_prompt="Classify this document by type.",
            )
            try:
                predicted_type = DocumentType(predicted_type_str)
            except ValueError:
                predicted_type = DocumentType.UNKNOWN

            doc_type_confidence = Confidence(value=type_confidence)
            document.mark_classified(predicted_type, doc_type_confidence)

            metadata = DocumentMetadata(
                title=title,
                author=author,
                subject=subject,
                page_count=page_count,
                language=lang_value,
            )

            document = Document(
                id=document.id,
                file_id=file_id,
                doc_type=predicted_type,
                processing_status=ProcessingStatus.INDEXING,
                metadata=metadata,
                classification_confidence=doc_type_confidence,
                extracted_text=extracted_text,
                created_at=document.created_at,
                updated_at=document.updated_at,
            )

            chunks = DocumentChunk.from_text(
                document_id=document.id,
                text=extracted_text,
            )

            chunk_count = len(chunks)

            document.mark_indexed(chunk_count)
            saved = self._document_repository.save(document)

            return DocumentDTO.from_entity(saved)

        except Exception as e:
            document.mark_failed(str(e))
            self._document_repository.save(document)
            logger.exception("Document processing failed for file_id=%s", file_id)
            raise

    def get_document(self, document_id: uuid.UUID) -> DocumentDTO:
        document = self._document_repository.get_by_id(document_id)
        if document is None:
            raise EntityNotFound("Document", str(document_id))
        return DocumentDTO.from_entity(document)

    def list_documents(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[DocumentDTO]:
        documents = self._document_repository.list_all(offset=offset, limit=limit)
        return [DocumentDTO.from_entity(d) for d in documents]

    def classify_document(
        self,
        document_id: uuid.UUID,
        categories: list[str] | None = None,
    ) -> ClassificationResultDTO:
        document = self._document_repository.get_by_id(document_id)
        if document is None:
            raise EntityNotFound("Document", str(document_id))

        if not document.extracted_text:
            raise ValidationException("Document has no extracted text to classify")

        if categories is None:
            categories = [dt.value for dt in DocumentType]

        predicted_label, confidence = self._llm_provider.classify(
            document.extracted_text[:2000],
            categories=categories,
        )

        return ClassificationResultDTO(
            document_id=document_id,
            predicted_type=predicted_label,
            confidence=confidence,
            all_scores={predicted_label: confidence},
        )

    def extract_metadata(
        self,
        document_id: uuid.UUID,
        fields: list[str] | None = None,
    ) -> DocumentMetadataDTO:
        document = self._document_repository.get_by_id(document_id)
        if document is None:
            raise EntityNotFound("Document", str(document_id))

        if not document.extracted_text:
            raise ValidationException("Document has no extracted text for metadata extraction")

        if fields is None:
            fields = ["title", "author", "subject", "keywords", "page_count", "word_count"]

        extracted = self._llm_provider.extract(
            document.extracted_text[:3000],
            fields=fields,
        )

        return DocumentMetadataDTO(
            title=extracted.get("title", document.metadata.title),
            author=extracted.get("author", document.metadata.author),
            subject=extracted.get("subject", document.metadata.subject),
            keywords=tuple(extracted.get("keywords", list(document.metadata.keywords))),
            creation_date=extracted.get("creation_date", document.metadata.creation_date),
            modification_date=extracted.get("modification_date", document.metadata.modification_date),
            page_count=int(extracted.get("page_count", document.metadata.page_count)),
            word_count=int(extracted.get("word_count", document.word_count)),
            char_count=int(extracted.get("char_count", len(document.extracted_text))),
            language=document.metadata.language.value,
            extra={k: v for k, v in extracted.items() if k not in fields},
        )
