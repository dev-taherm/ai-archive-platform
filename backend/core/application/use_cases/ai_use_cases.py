from __future__ import annotations

import logging
import uuid
from typing import Any

from core.application.dtos.ai_dto import AIResultDTO, ClassificationDTO, EmbeddingDTO
from core.application.interfaces.repositories import (
    AITaskRepository,
    DocumentRepository,
    EmbeddingRepository,
    FileRepository,
)
from core.application.interfaces.services import EmbeddingProvider, LLMProvider
from core.domain.common.exceptions import EntityNotFound, ValidationException
from core.domain.documents.value_objects import DocumentType

logger = logging.getLogger(__name__)


class AIUseCases:
    """Use cases for AI-powered operations on archived content."""

    def __init__(
        self,
        ai_task_repository: AITaskRepository,
        document_repository: DocumentRepository,
        embedding_repository: EmbeddingRepository,
        file_repository: FileRepository,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._ai_task_repository = ai_task_repository
        self._document_repository = document_repository
        self._embedding_repository = embedding_repository
        self._file_repository = file_repository
        self._llm_provider = llm_provider
        self._embedding_provider = embedding_provider

    async def classify(
        self,
        text: str,
        *,
        categories: list[str] | None = None,
        system_prompt: str | None = None,
    ) -> ClassificationDTO:
        """Classify text content using the LLM provider."""
        if not text.strip():
            raise ValidationException("Text to classify cannot be empty")

        if categories is None:
            categories = [dt.value for dt in DocumentType]

        predicted_label, confidence = await self._llm_provider.classify(
            text[:4000],
            categories=categories,
            system_prompt=system_prompt,
        )

        return ClassificationDTO(
            input_text=text[:200],
            predicted_label=predicted_label,
            confidence=confidence,
            all_scores={predicted_label: confidence},
        )

    async def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Extract structured data from text using the LLM provider."""
        if not text.strip():
            raise ValidationException("Text for extraction cannot be empty")
        if not fields:
            raise ValidationException("At least one field must be specified for extraction")

        result = await self._llm_provider.extract(
            text[:4000],
            fields=fields,
            system_prompt=system_prompt,
        )
        return result

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a summary of the given text."""
        if not text.strip():
            raise ValidationException("Text to summarize cannot be empty")

        summary = await self._llm_provider.summarize(
            text,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )
        return summary

    async def generate_embeddings(
        self,
        document_id: uuid.UUID,
        *,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[EmbeddingDTO]:
        """Generate and store embeddings for a document's text content."""
        from core.domain.documents.entities import DocumentChunk

        document = await self._document_repository.get_by_id(document_id)
        if document is None:
            raise EntityNotFound("Document", str(document_id))

        if not document.extracted_text:
            raise ValidationException("Document has no extracted text to embed")

        chunks = DocumentChunk.from_text(
            document_id=document_id,
            text=document.extracted_text,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        if not chunks:
            return []

        texts = [chunk.content for chunk in chunks]
        embeddings = await self._embedding_provider.embed_documents(texts)

        results: list[EmbeddingDTO] = []
        for chunk, embedding in zip(chunks, embeddings):
            vector_id = await self._embedding_repository.save(
                vector_id=f"doc_{document_id}_chunk_{chunk.chunk_index}",
                embedding=embedding,
                metadata={
                    "document_id": str(document_id),
                    "file_id": str(document.file_id),
                    "chunk_index": chunk.chunk_index,
                    "title": document.metadata.title,
                    "doc_type": document.doc_type.value,
                    "language": document.metadata.language.value,
                    "content": chunk.content[:500],
                },
            )

            results.append(
                EmbeddingDTO(
                    id=vector_id,
                    text=chunk.content,
                    vector=tuple(embedding),
                    source_type="document",
                    source_id=document_id,
                    chunk_index=chunk.chunk_index,
                )
            )

        return results
