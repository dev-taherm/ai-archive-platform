from __future__ import annotations

import logging
import uuid
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="infrastructure.scan_folder",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    track_started=True,
)
def scan_folder_task(
    self: Any,
    folder_path: str,
    *,
    recursive: bool = True,
    patterns: list[str] | None = None,
    ignore_patterns: list[str] | None = None,
) -> dict[str, Any]:
    """Scan a folder and register discovered files in the archive.

    Orchestrates the file scanning pipeline:
      1. Scan filesystem for files matching patterns.
      2. For each file, create or update a FileRecord.
      3. Compute fingerprints and detect duplicates.
      4. Queue documents for processing.
    """
    import asyncio

    from core.infrastructure.db.repositories.file_repository import DjangoFileRepository
    from core.infrastructure.services.file_scanner import FileScannerService

    logger.info("Starting folder scan: %s (recursive=%s)", folder_path, recursive)

    repo = DjangoFileRepository()
    scanner = FileScannerService()
    files_found = 0
    files_created = 0
    duplicates_found = 0

    async def _run_scan() -> dict[str, Any]:
        nonlocal files_found, files_created, duplicates_found

        async for file_meta in scanner.scan_folder(
            folder_path,
            recursive=recursive,
            patterns=patterns,
            ignore_patterns=ignore_patterns,
        ):
            files_found += 1
            # Create or update file record via repository
            file_record = _create_file_record(file_meta)
            await repo.save(file_record)
            files_created += 1

            # Check for duplicates via fingerprint
            from core.domain.files.value_objects import Hash

            fingerprint_hash = Hash(canonical=file_meta["content_hash"])
            existing = await repo.get_by_fingerprint(fingerprint_hash)
            if len(existing) > 1:
                duplicates_found += 1

        return {
            "folder_path": folder_path,
            "files_found": files_found,
            "files_created": files_created,
            "duplicates_found": duplicates_found,
        }

    try:
        result = asyncio.run(_run_scan())
        logger.info(
            "Folder scan complete: %s files found, %s created, %s duplicates",
            result["files_found"],
            result["files_created"],
            result["duplicates_found"],
        )
        return result
    except Exception as exc:
        logger.exception("Folder scan failed for %s", folder_path)
        raise self.retry(exc=exc)


def _create_file_record(file_meta: dict[str, Any]) -> Any:
    """Build a FileRecord domain entity from scanned file metadata."""
    from core.domain.files.entities import FileFingerprint, FileRecord
    from core.domain.files.value_objects import FileSize, FilePath, FileStatus, Hash, MimeType

    content_hash_raw = file_meta["content_hash"]  # e.g. "sha256:abc123..."
    algorithm, digest = content_hash_raw.split(":", 1)

    return FileRecord(
        id=uuid.uuid4(),
        path=FilePath(raw=file_meta["path"]),
        mime_type=MimeType(value=file_meta["mime_type"]),
        size=FileSize(bytes=file_meta["size_bytes"]),
        fingerprint=FileFingerprint(
            content_hash=Hash(algorithm=algorithm, digest=digest),
            size=FileSize(bytes=file_meta["size_bytes"]),
            magic_bytes=file_meta.get("magic_bytes", ""),
        ),
        status=FileStatus.PENDING,
        tags=[],
        metadata={},
    )


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

    Uses the configured embedding provider (e.g., OpenAI text-embedding-3-small)
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
