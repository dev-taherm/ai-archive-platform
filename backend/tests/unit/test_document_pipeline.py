"""Tests for DocumentProcessingPipeline."""
import asyncio
import uuid

import pytest

from core.infrastructure.pipelines.document_pipeline import (
    DocumentProcessingPipeline,
    PipelineResult,
)
from tests.mocks import (
    MockDocumentRepository,
    MockEmbeddingProvider,
    MockEmbeddingRepository,
    MockFileRepository,
    MockLLMProvider,
)
from core.domain.files.entities import FileRecord
from core.domain.files.value_objects import FilePath, MimeType, FileSize, Hash, FileFingerprint


def _make_file_record(file_id=None):
    fid = file_id or uuid.uuid4()
    fp = FileFingerprint(
        content_hash=Hash(algorithm="sha256", digest="abc123"),
        magic_bytes=b"\x00",
    )
    return FileRecord(
        id=fid,
        path=FilePath(raw="/tmp/test.pdf"),
        mime_type=MimeType(value="application/pdf"),
        size=FileSize(bytes=1024),
        fingerprint=fp,
    )


def _make_pipeline(**overrides):
    file_repo = MockFileRepository()
    doc_repo = MockDocumentRepository()
    emb_repo = MockEmbeddingRepository()
    llm = MockLLMProvider()
    emb = MockEmbeddingProvider()

    file_repo._files = overrides.pop("file_repo_files", file_repo._files)
    doc_repo._docs = overrides.pop("doc_repo_docs", doc_repo._docs)

    return DocumentProcessingPipeline(
        file_repository=overrides.get("file_repository", file_repo),
        document_repository=overrides.get("document_repository", doc_repo),
        embedding_repository=overrides.get("embedding_repository", emb_repo),
        llm_provider=overrides.get("llm_provider", llm),
        embedding_provider=overrides.get("embedding_provider", emb),
        max_retries=overrides.get("max_retries", 1),
        retry_base_delay=overrides.get("retry_base_delay", 0.01),
    )


@pytest.mark.asyncio
async def test_pipeline_result_defaults():
    r = PipelineResult()
    assert r.status == "pending"
    assert r.chunk_count == 0
    assert r.embedding_ids == []
    assert r.entities == []


@pytest.mark.asyncio
async def test_pipeline_happy_path():
    fr = _make_file_record()
    pipeline = _make_pipeline(file_repo_files={fr.id: fr})
    result = await pipeline.process(str(fr.id))
    assert result.status == "completed"
    assert result.classification == "contract"
    assert result.chunk_count >= 1
    assert result.summary
    assert "completed successfully" in result.processing_log[-2]


@pytest.mark.asyncio
async def test_pipeline_classify_returns_correct_type():
    fr = _make_file_record()
    pipeline = _make_pipeline(file_repo_files={fr.id: fr})
    result = await pipeline.process(str(fr.id))
    assert result.classification_confidence == 0.95


@pytest.mark.asyncio
async def test_pipeline_with_pre_existing_text():
    fr = _make_file_record()
    doc = type("Doc", (), {
        "id": uuid.uuid4(),
        "file_id": fr.id,
        "extracted_text": "Invoice from Acme Corp for $500.",
        "doc_type": "unknown",
        "processing_status": "pending",
    })()
    doc_repo = MockDocumentRepository()
    doc_repo._docs[doc.id] = doc
    pipeline = _make_pipeline(file_repo_files={fr.id: fr}, doc_repo_docs={doc.id: doc})
    result = await pipeline.process(str(fr.id))
    assert result.status == "completed"
    assert any("pre-existing text" in log for log in result.processing_log)


@pytest.mark.asyncio
async def test_pipeline_file_not_found():
    pipeline = _make_pipeline()
    result = await pipeline.process(str(uuid.uuid4()))
    assert result.status == "failed"
    assert result.error


@pytest.mark.asyncio
async def test_pipeline_empty_text():
    fr = _make_file_record()
    doc = type("Doc", (), {
        "id": uuid.uuid4(),
        "file_id": fr.id,
        "extracted_text": "",
        "doc_type": "unknown",
        "processing_status": "pending",
    })()
    doc_repo = MockDocumentRepository()
    doc_repo._docs[doc.id] = doc
    pipeline = _make_pipeline(file_repo_files={fr.id: fr}, doc_repo_docs={doc.id: doc})
    result = await pipeline.process(str(fr.id))
    assert result.status == "completed"
    assert result.classification == "other"
    assert result.chunk_count == 0


@pytest.mark.asyncio
async def test_pipeline_embedding_failure_is_non_fatal():
    class FailEmb(MockEmbeddingProvider):
        def embed_documents(self, texts):
            raise RuntimeError("OOM")

    fr = _make_file_record()
    pipeline = _make_pipeline(file_repo_files={fr.id: fr}, embedding_provider=FailEmb())
    result = await pipeline.process(str(fr.id))
    assert result.status == "completed"
    assert result.embedding_ids == []
    assert any("embedding failed" in log for log in result.processing_log)


@pytest.mark.asyncio
async def test_pipeline_entities_extracted():
    fr = _make_file_record()
    pipeline = _make_pipeline(file_repo_files={fr.id: fr})
    result = await pipeline.process(str(fr.id))
    assert isinstance(result.entities, list)


@pytest.mark.asyncio
async def test_pipeline_chunk_text_method():
    pipeline = _make_pipeline()
    chunks = pipeline._chunk_text("Hello world. " * 200)
    assert len(chunks) > 1


@pytest.mark.asyncio
async def test_pipeline_map_classification_to_type():
    pipeline = _make_pipeline()
    assert pipeline._map_classification_to_type("invoice").value == "invoice"
    assert pipeline._map_classification_to_type("unknown").value == "unknown"
    assert pipeline._map_classification_to_type("random_thing").value == "other"
