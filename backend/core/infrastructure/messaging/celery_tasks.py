from __future__ import annotations

import logging
import uuid
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="infrastructure.process_document",
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
    track_started=True,
    time_limit=1800,  # 30 minutes
    soft_time_limit=1500,  # 25 minutes
)
def process_document_task(
    self: Any,
    document_id: str,
    file_id: str,
) -> dict[str, Any]:
    """Process a document through the full extraction pipeline.

    Steps:
      1. Retrieve file content from storage.
      2. Extract text via OCR / text extraction.
      3. Classify the document type.
      4. Store extracted text and metadata.
      5. Queue for chunking and embedding.
    """
    import asyncio

    from core.infrastructure.db.repositories.document_repository import (
        DjangoDocumentRepository,
    )

    logger.info("Processing document %s (file=%s)", document_id, file_id)

    doc_repo = DjangoDocumentRepository()

    async def _process() -> dict[str, Any]:
        doc = await doc_repo.get_by_id(uuid.UUID(document_id))
        if doc is None:
            logger.error("Document %s not found", document_id)
            return {"error": "document_not_found"}

        doc.start_processing()
        await doc_repo.save(doc)

        try:
            # TODO: Retrieve file content from storage and extract text
            # extracted_text = await storage.retrieve(file_path)
            # text = await ocr.extract_text(extracted_text, content_type=mime_type)
            extracted_text = ""  # placeholder

            doc.extracted_text = extracted_text
            doc.mark_classified(
                doc_type=doc.doc_type,
                classification_confidence=doc.classification_confidence
                or __import__("core.domain.documents.value_objects", fromlist=["Confidence"]).Confidence(value=0.5),
            )
            await doc_repo.save(doc)

            # Create chunks for embedding
            from core.domain.documents.entities import DocumentChunk

            chunks = DocumentChunk.from_text(
                document_id=uuid.UUID(document_id),
                text=extracted_text,
            )
            await doc_repo.save_chunks(uuid.UUID(document_id), chunks)

            doc.mark_indexed(chunk_count=len(chunks))
            await doc_repo.save(doc)

            # Queue embedding generation for each chunk
            for chunk in chunks:
                generate_embedding_task.delay(
                    document_id=document_id,
                    chunk_id=str(chunk.id),
                    content=chunk.content,
                )

            return {
                "document_id": document_id,
                "status": "completed",
                "chunk_count": len(chunks),
            }

        except Exception as exc:
            doc.mark_failed(str(exc))
            await doc_repo.save(doc)
            raise

    try:
        return asyncio.run(_process())
    except Exception as exc:
        logger.exception("Document processing failed for %s", document_id)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="infrastructure.generate_embedding",
    max_retries=5,
    default_retry_delay=30,
    acks_late=True,
    track_started=True,
)
def generate_embedding_task(
    self: Any,
    document_id: str,
    chunk_id: str,
    content: str,
) -> dict[str, Any]:
    """Generate an embedding vector for a document chunk.

    Uses the configured embedding provider (e.g., granite-embedding-97m-multilingual-r2)
    and stores the result in the embedding table with pgvector.
    """
    import asyncio

    from core.infrastructure.db.repositories.ai_repository import DjangoEmbeddingRepository
    from core.infrastructure.services.embedding_service import LangChainEmbeddingProvider

    logger.info("Generating embedding for chunk %s (doc=%s)", chunk_id, document_id)

    embedding_repo = DjangoEmbeddingRepository()
    embedding_provider = LangChainEmbeddingProvider()

    async def _embed() -> dict[str, Any]:
        vector = await embedding_provider.embed_text(content)
        vector_id = f"chunk-{chunk_id}"

        await embedding_repo.save(
            vector_id=vector_id,
            embedding=vector,
            metadata={
                "document_id": document_id,
                "chunk_id": chunk_id,
                "model": embedding_provider._model_name,
            },
        )

        return {
            "chunk_id": chunk_id,
            "vector_id": vector_id,
            "dimensions": len(vector),
            "status": "completed",
        }

    try:
        return asyncio.run(_embed())
    except Exception as exc:
        logger.exception("Embedding generation failed for chunk %s", chunk_id)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="infrastructure.classify_document",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    track_started=True,
)
def classify_document_task(
    self: Any,
    document_id: str,
    text: str,
    *,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """Classify a document using an LLM provider.

    Uses the configured LLM provider to classify the document content
    into one of the predefined document type categories.
    """
    import asyncio

    from core.infrastructure.db.repositories.document_repository import (
        DjangoDocumentRepository,
    )
    from core.infrastructure.services.llm_factory import LLMFactory

    logger.info("Classifying document %s", document_id)

    doc_repo = DjangoDocumentRepository()

    default_categories = [
        "pdf", "text", "markdown", "html", "csv", "json",
        "code", "email", "spreadsheet", "presentation",
    ]
    cats = categories or default_categories

    async def _classify() -> dict[str, Any]:
        doc = await doc_repo.get_by_id(uuid.UUID(document_id))
        if doc is None:
            return {"error": "document_not_found"}

        from core.domain.ai.value_objects import ModelConfig, AIProvider

        config = ModelConfig(
            provider=AIProvider.OPENAI,
            model_name="gpt-4o-mini",
            temperature=0.0,
            max_tokens=200,
        )
        llm = LLMFactory.create("openai", config)

        category, confidence = await llm.classify(
            text[:4000],
            categories=cats,
            system_prompt=(
                "You are a document classifier. Classify the document into exactly "
                "one of the provided categories. Respond with ONLY: category (confidence)"
            ),
        )

        from core.domain.documents.value_objects import Confidence, DocumentType

        doc_type = DocumentType.from_extension(f".{category}")
        doc.mark_classified(
            doc_type=doc_type,
            confidence=Confidence(value=min(max(confidence, 0.0), 1.0)),
        )
        await doc_repo.save(doc)

        return {
            "document_id": document_id,
            "classification": category,
            "confidence": confidence,
            "status": "completed",
        }

    try:
        return asyncio.run(_classify())
    except Exception as exc:
        logger.exception("Classification failed for document %s", document_id)
        raise self.retry(exc=exc)
