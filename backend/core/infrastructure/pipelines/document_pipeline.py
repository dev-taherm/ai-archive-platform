from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.application.interfaces.repositories import (
    DocumentRepository,
    EmbeddingRepository,
    FileRepository,
)
from core.application.interfaces.services import EmbeddingProvider, LLMProvider, OCRProvider
from core.domain.documents.entities import Document, DocumentMetadata
from core.domain.documents.value_objects import (
    Confidence,
    DocumentType,
    Language,
    ProcessingStatus,
)
from core.domain.files.entities import FileRecord
from core.infrastructure.services.document_reader import DocumentReader

logger = logging.getLogger(__name__)

DOCUMENT_CATEGORIES = [
    "invoice",
    "receipt",
    "contract",
    "report",
    "letter",
    "memo",
    "email",
    "resume",
    "academic_paper",
    "legal_document",
    "financial_statement",
    "technical_specification",
    "meeting_notes",
    "proposal",
    "presentation",
    "spreadsheet",
    "code",
    "data_export",
    "other",
]

IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"})


@dataclass
class PipelineResult:
    """Result of a pipeline run."""

    document_id: str = ""
    file_id: str = ""
    status: str = "pending"
    classification: str = ""
    classification_confidence: float = 0.0
    chunk_count: int = 0
    embedding_ids: list[str] = field(default_factory=list)
    summary: str = ""
    entities: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    processing_log: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0


class DocumentProcessingPipeline:
    """End-to-end document processing pipeline.

    Orchestrates: load file -> read content -> OCR (if needed) -> classify ->
    extract entities -> summarize -> chunk -> embed -> index.

    All LLM and OCR operations use async/await. Error handling includes
    configurable retry logic with exponential backoff.
    """

    def __init__(
        self,
        *,
        file_repository: FileRepository,
        document_repository: DocumentRepository,
        embedding_repository: EmbeddingRepository,
        document_reader: DocumentReader,
        ocr_engine: OCRProvider,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        self._file_repo = file_repository
        self._doc_repo = document_repository
        self._embedding_repo = embedding_repository
        self._reader = document_reader
        self._ocr = ocr_engine
        self._llm = llm_provider
        self._embeddings = embedding_provider
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    async def process(self, file_id: str) -> PipelineResult:
        """Run the full processing pipeline for a file.

        Args:
            file_id: UUID string of the source file record.

        Returns:
            PipelineResult with all processing outcomes.
        """
        t0 = time.time()
        result = PipelineResult(file_id=file_id)
        result.processing_log.append(f"PIPELINE: started for file {file_id}")
        logger.info("Pipeline started: file_id=%s", file_id)

        document: Document | None = None

        try:
            # Step 1: Load file record
            file_record = await self._load_file_record(file_id)
            result.processing_log.append(
                f"LOAD: file record loaded ({file_record.path.filename})"
            )

            # Step 2: Create or fetch document entity
            document = await self._create_document(file_record)
            result.document_id = str(document.id)
            result.processing_log.append(f"DOCUMENT: entity created {document.id}")

            # Step 3: Read document content
            extraction = await self._read_content(file_record)
            result.processing_log.append(
                f"READ: {len(extraction.text)} chars extracted"
            )

            # Step 4: Run OCR if needed
            parsed_text = extraction.text
            if self._needs_ocr(file_record, extraction):
                from datetime import timezone as _tz, datetime as _dt

                ext = Path(file_record.path.raw).suffix.lower()
                source_type = "image" if ext in IMAGE_EXTENSIONS else "pdf"

                def _create_ocr_job():
                    from apps.ocr.models import OCRJob
                    return OCRJob.objects.create(
                        file_id=file_record.id,
                        document_id=document.id,
                        status="processing",
                        source_type=source_type,
                    )
                ocr_job = await self._sync_to_async(_create_ocr_job)
                t_ocr = time.time()

                try:
                    ocr_text = await self._run_ocr(file_record)
                    ocr_ms = (time.time() - t_ocr) * 1000

                    def _save_ocr_job(job, text, ms, status, error=""):
                        job.extracted_text = (text or "")[:10000]
                        job.processing_time_ms = ms
                        job.completed_at = _dt.now(_tz.utc)
                        job.status = status
                        if error:
                            job.error_message = error
                        job.save()

                    if ocr_text and len(ocr_text.strip()) > len(parsed_text.strip()):
                        parsed_text = ocr_text
                        await self._sync_to_async(_save_ocr_job, ocr_job, ocr_text, ocr_ms, "completed")
                        result.processing_log.append(
                            f"OCR: used OCR text ({len(ocr_text)} chars)"
                        )
                    else:
                        await self._sync_to_async(_save_ocr_job, ocr_job, ocr_text, ocr_ms, "completed")
                        result.processing_log.append("OCR: skipped — parsed text is richer")
                except Exception as ocr_err:
                    ocr_ms = (time.time() - t_ocr) * 1000
                    await self._sync_to_async(_save_ocr_job, ocr_job, "", ocr_ms, "failed", str(ocr_err))
                    logger.warning("OCR failed for file %s, continuing without OCR: %s", file_id, ocr_err)
                    result.processing_log.append(f"OCR: failed ({ocr_err}), continuing without OCR")
            else:
                result.processing_log.append("OCR: not needed")

            # Save extracted text to document (enables word_count, preview, keyword search)
            object.__setattr__(document, "extracted_text", parsed_text[:10000])

            # Step 5: Classify document
            classification, confidence = await self._classify(parsed_text)
            result.classification = classification
            result.classification_confidence = confidence
            result.processing_log.append(
                f"CLASSIFY: {classification} ({confidence:.2f})"
            )

            # Update document with classification
            doc_type = self._map_classification_to_type(classification)
            conf = Confidence(value=confidence)
            document.mark_classified(doc_type, conf)
            await self._save_document(document)

            # Step 6: Extract entities
            entities = await self._extract_entities(parsed_text)
            result.entities = entities
            result.processing_log.append(f"ENTITIES: extracted {len(entities)} entities")

            # Step 7: Generate summary
            summary = await self._summarize(parsed_text, classification)
            result.summary = summary
            result.processing_log.append(f"SUMMARY: {len(summary)} chars")

            # Step 8: Chunk text
            chunks = self._chunk_text(parsed_text)
            result.chunk_count = len(chunks)
            result.processing_log.append(f"CHUNK: {len(chunks)} chunks created")

            # Step 9: Generate embeddings and index (non-fatal if embedding fails)
            embedding_ids: list[str] = []
            try:
                embedding_ids = await self._embed_and_index(
                    document=document,
                    chunks=chunks,
                    file_id=file_id,
                )
                result.embedding_ids = embedding_ids
                result.processing_log.append(
                    f"INDEX: {len(embedding_ids)} embeddings stored"
                )
            except Exception as emb_err:
                result.processing_log.append(
                    f"INDEX: embedding failed ({emb_err}), continuing without embeddings"
                )
                logger.warning(
                    "Embedding failed for file %s, document will be keyword-searchable only: %s",
                    file_id, emb_err,
                )

            # Step 10: Mark document as completed
            document.mark_indexed(chunk_count=len(chunks))
            await self._save_document(document)

            result.status = "completed"
            result.processing_log.append("PIPELINE: completed successfully")
            logger.info(
                "Pipeline completed: file=%s, doc=%s, chunks=%d, embeddings=%d",
                file_id, document.id, len(chunks), len(embedding_ids),
            )

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            result.processing_log.append(f"PIPELINE FAILED: {e}")
            logger.exception("Pipeline failed for file %s", file_id)

            if document is not None:
                await self._handle_failure(document, e)

        result.elapsed_ms = (time.time() - t0) * 1000
        result.processing_log.append(f"PIPELINE: total {result.elapsed_ms:.0f}ms")
        return result

    async def _load_file_record(self, file_id: str) -> FileRecord:
        """Load a file record from the repository with retry."""
        return await self._retry_async(
            lambda: self._sync_to_async(
                self._file_repo.get_by_id, uuid.UUID(file_id)
            ),
            operation="load_file_record",
        )

    async def _create_document(self, file_record: FileRecord) -> Document:
        """Create a new Document entity in QUEUED status."""
        ext = Path(file_record.path.raw).suffix.lower()
        doc_type = DocumentType.from_extension(ext)
        title = Path(file_record.path.raw).stem

        document = Document(
            file_id=file_record.id,
            doc_type=doc_type,
            processing_status=ProcessingStatus.QUEUED,
            metadata=DocumentMetadata(
                title=title,
                language=Language.UNKNOWN,
                page_count=0,
            ),
        )

        saved = await self._retry_async(
            lambda: self._sync_to_async(self._doc_repo.save, document),
            operation="create_document",
        )
        logger.info("Document created: %s (file=%s)", saved.id, file_record.id)
        return saved

    async def _read_content(self, file_record: FileRecord) -> Any:
        """Read document content using DocumentReader (sync operation)."""
        return await asyncio.to_thread(self._reader.read, file_record.path.raw)

    def _needs_ocr(self, file_record: FileRecord, extraction: Any) -> bool:
        """Determine if OCR is needed for this file."""
        ext = Path(file_record.path.raw).suffix.lower()

        # Images always need OCR
        if ext in IMAGE_EXTENSIONS:
            return True

        # PDFs with no/little extracted text likely need OCR
        if ext == ".pdf":
            text = extraction.text.strip() if extraction.text else ""
            if len(text) < 50:
                return True

        # Any file with insufficient text from parsing
        text = extraction.text.strip() if extraction.text else ""
        if len(text) < 50 and file_record.size.bytes > 1000:
            return True

        return False

    async def _run_ocr(self, file_record: FileRecord) -> str:
        """Run OCR on the file content with retry."""
        content = await asyncio.to_thread(Path(file_record.path.raw).read_bytes)

        mime_type = file_record.mime_type.value

        async def _do_ocr() -> str:
            return await self._ocr.extract_text(
                content, content_type=mime_type
            )

        return await self._retry_async(_do_ocr, operation="ocr")

    async def _classify(self, text: str) -> tuple[str, float]:
        """Classify document using LLM with retry."""
        if not text or not text.strip():
            return "other", 0.0

        classification_text = text[:3000]

        async def _do_classify() -> tuple[str, float]:
            return await self._llm.classify(
                classification_text,
                categories=DOCUMENT_CATEGORIES,
                system_prompt=(
                    "Classify this document into one of the given categories. "
                    "Return only the category name followed by confidence in parentheses, "
                    "e.g. 'invoice (0.95)'."
                ),
            )

        return await self._retry_async(_do_classify, operation="classify")

    async def _extract_entities(self, text: str) -> list[dict[str, Any]]:
        """Extract named entities from text using LLM."""
        if not text or not text.strip():
            return []

        entity_types = [
            "person", "organization", "date", "amount",
            "location", "email", "phone", "reference_number",
        ]

        async def _do_extract() -> list[dict[str, Any]]:
            return await self._llm.extract(
                text[:4000],
                fields=entity_types,
                system_prompt=(
                    "Extract named entities from the text. "
                    "Return a JSON object with entity types as keys and lists of "
                    "objects with 'name' and 'context' fields as values."
                ),
            )

        try:
            result = await self._retry_async(_do_extract, operation="extract_entities")
            if isinstance(result, dict):
                entities = []
                for etype, items in result.items():
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                entities.append({
                                    "type": etype,
                                    "name": item.get("name", ""),
                                    "context": item.get("context", ""),
                                })
                return entities
            return []
        except Exception as e:
            logger.warning("Entity extraction failed (non-fatal): %s", e)
            return []

    async def _summarize(self, text: str, classification: str) -> str:
        """Generate document summary using LLM with retry."""
        if not text or not text.strip():
            return ""

        async def _do_summarize() -> str:
            return await self._llm.summarize(
                text[:6000],
                max_tokens=500,
                system_prompt=(
                    f"This is a {classification} document. "
                    "Provide a concise summary in 2-4 sentences covering the "
                    "key information, purpose, and main points."
                ),
            )

        return await self._retry_async(_do_summarize, operation="summarize")

    def _chunk_text(self, text: str) -> list[dict[str, Any]]:
        """Split text into overlapping chunks for embedding."""
        if not text or not text.strip():
            return []

        chunk_size = 1000
        overlap = 200
        chunks: list[dict[str, Any]] = []
        start = 0
        idx = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Try to break at a natural boundary
            if end < len(text):
                para_break = text.rfind("\n\n", start + chunk_size // 2, end)
                if para_break > start:
                    end = para_break + 2
                else:
                    for sep in (". ", ".\n", "! ", "? ", "\n"):
                        sent_break = text.rfind(sep, start + chunk_size // 2, end)
                        if sent_break > start:
                            end = sent_break + len(sep)
                            break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append({
                    "text": chunk,
                    "index": idx,
                    "start": start,
                    "end": end,
                })
                idx += 1

            start = end - overlap
            if start <= (chunks[-1]["start"] if chunks else 0):
                start = end

        return chunks

    async def _embed_and_index(
        self,
        document: Document,
        chunks: list[dict[str, Any]],
        file_id: str,
    ) -> list[str]:
        """Generate embeddings and store in vector index."""
        if not chunks:
            return []

        chunk_texts = [c["text"] for c in chunks]

        # Generate embeddings (sync, run in thread)
        embeddings = await asyncio.to_thread(
            self._embeddings.embed_documents, chunk_texts
        )

        # Store embeddings
        embedding_ids: list[str] = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            emb_id = f"{document.id}_chunk_{i}"
            metadata = {
                "document_id": str(document.id),
                "file_id": file_id,
                "chunk_index": i,
                "start": chunk.get("start", 0),
                "end": chunk.get("end", 0),
            }
            await self._retry_async(
                lambda eid=emb_id, emb=embedding, meta=metadata: (
                    self._embedding_repo.save(eid, emb, meta)
                ),
                operation="save_embedding",
            )
            embedding_ids.append(emb_id)

        return embedding_ids

    async def _save_document(self, document: Document) -> None:
        """Persist document changes to repository."""
        await self._retry_async(
            lambda: self._sync_to_async(self._doc_repo.save, document),
            operation="save_document",
        )

    async def _handle_failure(self, document: Document, error: Exception) -> None:
        """Handle pipeline failure by updating document status."""
        try:
            if document.can_retry:
                document.schedule_retry()
                await self._save_document(document)
                logger.info(
                    "Document scheduled for retry: %s (attempt %d)",
                    document.id, document.retry_count,
                )
            else:
                document.mark_failed(str(error))
                await self._save_document(document)
                logger.warning(
                    "Document marked as failed (max retries exceeded): %s",
                    document.id,
                )
        except Exception as save_err:
            logger.exception(
                "Failed to persist failure state for document %s: %s",
                document.id, save_err,
            )

    def _map_classification_to_type(self, classification: str) -> DocumentType:
        """Map a classification category to a DocumentType enum."""
        mapping = {
            "invoice": DocumentType.PDF,
            "receipt": DocumentType.PDF,
            "contract": DocumentType.PDF,
            "report": DocumentType.PDF,
            "letter": DocumentType.TEXT,
            "memo": DocumentType.TEXT,
            "email": DocumentType.EMAIL,
            "resume": DocumentType.PDF,
            "academic_paper": DocumentType.PDF,
            "legal_document": DocumentType.PDF,
            "financial_statement": DocumentType.SPREADSHEET,
            "technical_specification": DocumentType.TEXT,
            "meeting_notes": DocumentType.TEXT,
            "proposal": DocumentType.PDF,
            "presentation": DocumentType.PRESENTATION,
            "spreadsheet": DocumentType.SPREADSHEET,
            "code": DocumentType.CODE,
            "data_export": DocumentType.CSV,
        }
        return mapping.get(classification.lower(), DocumentType.UNKNOWN)

    async def _retry_async(self, coro_fn, *, operation: str) -> Any:
        """Execute an async operation with exponential backoff retry.

        Args:
            coro_fn: A callable that returns an awaitable.
            operation: Name of the operation for logging.

        Returns:
            The result of the operation.

        Raises:
            The last exception after all retries are exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                return await coro_fn()
            except Exception as e:
                last_error = e
                if attempt < self._max_retries:
                    delay = self._retry_base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Operation %s failed (attempt %d/%d): %s. "
                        "Retrying in %.1fs...",
                        operation, attempt, self._max_retries, e, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Operation %s failed after %d attempts: %s",
                        operation, self._max_retries, e,
                    )

        raise last_error  # type: ignore[misc]

    async def _sync_to_async(self, fn, *args, **kwargs):
        """Run a synchronous function in a thread."""
        return await asyncio.to_thread(fn, *args, **kwargs)


def run_document_pipeline(
    file_id: str,
    file_path: str,
    mime_type: str,
) -> dict[str, Any]:
    """Convenience function that wires up all dependencies and runs the pipeline.

    Called by the ``process_pipeline`` API view.
    """
    from apps.ai.models import ProviderConfig
    from core.domain.ai.value_objects import AIProvider, ModelConfig
    from core.infrastructure.db.repositories.document_repository import DjangoDocumentRepository
    from core.infrastructure.db.repositories.embedding_repository import PgvectorEmbeddingRepository
    from core.infrastructure.db.repositories.file_repository import DjangoFileRepository
    from core.infrastructure.services.document_reader import DocumentReader
    from core.infrastructure.services.embedding_service import FastEmbedProvider, LangChainEmbeddingProvider
    from core.infrastructure.services.llm_factory import LLMFactory
    from core.infrastructure.services.ocr_engine import PaddleOCREngine

    # ---- Load active LLM provider from DB ----
    llm_config = (
        ProviderConfig.objects.filter(
            is_active=True, capabilities__contains=["llm"]
        )
        .order_by("-is_default")
        .first()
    )
    if not llm_config:
        raise ValueError(
            "No active LLM provider configured. Go to /settings and add one."
        )

    model_config = ModelConfig(
        provider=AIProvider(llm_config.provider_type),
        model_name=llm_config.model_name,
    )
    llm = LLMFactory.create(
        llm_config.provider_type,
        model_config,
        api_key=llm_config.api_key or None,
        base_url=llm_config.base_url or None,
    )

    # ---- Load active embedding provider from DB ----
    emb_config = (
        ProviderConfig.objects.filter(
            is_active=True, capabilities__contains=["embedding"]
        )
        .order_by("-is_default")
        .first()
    )

    if emb_config:
        embeddings = LangChainEmbeddingProvider(
            model_name=emb_config.model_name,
            provider=emb_config.provider_type,
            api_key=emb_config.api_key or None,
            base_url=emb_config.base_url or None,
        )
    else:
        embeddings = FastEmbedProvider()

    # ---- Instantiate and run the pipeline ----
    pipeline = DocumentProcessingPipeline(
        file_repository=DjangoFileRepository(),
        document_repository=DjangoDocumentRepository(),
        embedding_repository=PgvectorEmbeddingRepository(),
        document_reader=DocumentReader(),
        ocr_engine=PaddleOCREngine(),
        llm_provider=llm,
        embedding_provider=embeddings,
    )

    result = asyncio.run(pipeline.process(file_id))

    # Update the file record status to match pipeline result
    from apps.files.models import FileRecord as FileRecordModel
    file_status = "completed" if result.status == "completed" else "failed"
    FileRecordModel.objects.filter(id=file_id).update(status=file_status)

    return {
        "status": result.status,
        "document_id": result.document_id,
        "classification": result.classification,
        "classification_confidence": result.classification_confidence,
        "entities": result.entities,
        "summary": result.summary,
        "chunk_count": result.chunk_count,
        "embedding_ids": result.embedding_ids,
        "processing_log": result.processing_log,
        "error": result.error,
    }
