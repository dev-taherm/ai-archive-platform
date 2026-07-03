from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

from core.infrastructure.pipelines.document_state import DocumentPipelineState

logger = logging.getLogger(__name__)


def embed_index_node(state: DocumentPipelineState) -> dict[str, Any]:
    """Node: Embed document chunks and index into pgvector.

    Generates embeddings for each chunk and stores the document + chunks
    in the database for semantic search.
    """
    t0 = time.time()
    chunks = state.get("chunks", [])
    file_id = state.get("file_id", "")
    file_path = state.get("file_path", "")
    logger.info("INDEX: %d chunks for %s", len(chunks), file_path)

    if not chunks:
        elapsed_ms = (time.time() - t0) * 1000
        return {
            "document_id": "",
            "embedding_ids": [],
            "processing_log": [f"INDEX: skipped — no chunks ({elapsed_ms:.0f}ms)"],
        }

    try:
        from django.apps import apps

        # Get providers from app configs
        ai_config = apps.get_app_config("ai")
        embedding_provider = ai_config.embedding_provider

        # Create document record in DB
        from core.infrastructure.db.repositories.document_repository import (
            DjangoDocumentRepository,
        )
        document_repo = DjangoDocumentRepository()

        # Build document entity
        from core.domain.documents.entities import Document, DocumentMetadata
        from core.domain.documents.value_objects import (
            Confidence,
            DocumentType,
            Language,
            ProcessingStatus,
        )

        doc_type = DocumentType.from_extension(
            file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        )

        import uuid
        try:
            source_file_id = uuid.UUID(file_id)
        except (ValueError, AttributeError):
            source_file_id = uuid4()

        metadata = DocumentMetadata(
            language=Language(state.get("detected_language", "unknown")) if state.get("detected_language") != "unknown" else Language.UNKNOWN,
            word_count=len((state.get("markdown_content") or "").split()),
            char_count=len(state.get("markdown_content") or ""),
            page_count=state.get("page_count", 0),
        )

        classification_conf = state.get("classification_confidence", 0.0)
        conf = Confidence(value=classification_conf) if classification_conf > 0 else None

        document = Document(
            file_id=source_file_id,
            doc_type=doc_type,
            processing_status=ProcessingStatus.COMPLETED,
            metadata=metadata,
            classification_confidence=conf,
            extracted_text=(state.get("markdown_content") or "")[:10000],
            chunk_count=state.get("chunk_count", 0),
            error_message=None,
        )

        document_id = document_repository_save(document_repo, document)

        # Generate embeddings for chunks
        chunk_texts = [c["text"] for c in chunks]
        embeddings = embedding_provider.embed_documents(chunk_texts)

        # Store embeddings in vector store for semantic search
        from core.infrastructure.services.vector_store import VectorStore
        vector_store = VectorStore()

        embedding_ids = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            emb_id = f"{document_id}_chunk_{i}"
            vector_store.add(
                entry_id=emb_id,
                text=chunk["text"],
                embedding=embedding,
                metadata={
                    "document_id": str(document_id),
                    "chunk_index": i,
                    "start": chunk.get("start", 0),
                    "end": chunk.get("end", 0),
                },
            )
            embedding_ids.append(emb_id)

        vector_store._save()

        elapsed_ms = (time.time() - t0) * 1000
        logger.info(
            "INDEX done: doc=%s, %d embeddings (%.0fms)",
            document_id, len(embedding_ids), elapsed_ms,
        )

        return {
            "document_id": str(document_id),
            "embedding_ids": embedding_ids,
            "processing_log": [f"INDEX: doc={document_id}, {len(embedding_ids)} embeddings ({elapsed_ms:.0f}ms)"],
        }
    except Exception as e:
        logger.exception("INDEX failed: %s", e)
        return {
            "document_id": "",
            "embedding_ids": [],
            "processing_log": [f"INDEX FAILED: {e}"],
        }


def document_repository_save(repo, document) -> str:
    """Save document via repository, returning document ID."""
    try:
        saved = repo.save(document)
        return saved.id
    except Exception as e:
        logger.warning("Document save failed, using generated ID: %s", e)
        return str(document.id)
