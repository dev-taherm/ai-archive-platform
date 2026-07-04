import pytest
import uuid

from core.domain.documents.entities import Document, DocumentChunk, DocumentMetadata
from core.domain.documents.value_objects import (
    DocumentType,
    Language,
    Confidence,
    ProcessingStatus,
)


def test_document_creation():
    doc = Document(
        id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        doc_type=DocumentType.PDF,
        processing_status=ProcessingStatus.COMPLETED,
        extracted_text="Test contract text",
    )
    assert doc.doc_type == DocumentType.PDF
    assert doc.processing_status == ProcessingStatus.COMPLETED
    assert doc.extracted_text == "Test contract text"


def test_document_defaults():
    doc = Document(id=uuid.uuid4())
    assert doc.doc_type == DocumentType.UNKNOWN
    assert doc.processing_status == ProcessingStatus.QUEUED
    assert doc.extracted_text == ""
    assert doc.chunk_count == 0
    assert doc.retry_count == 0


def test_document_start_processing():
    doc = Document(id=uuid.uuid4(), file_id=uuid.uuid4())
    doc.start_processing()
    assert doc.processing_status == ProcessingStatus.EXTRACTING


def test_document_mark_classified():
    doc = Document(id=uuid.uuid4(), file_id=uuid.uuid4())
    doc.mark_classified(
        doc_type=DocumentType.PDF,
        confidence=Confidence(value=0.9),
    )
    assert doc.doc_type == DocumentType.PDF
    assert doc.classification_confidence == Confidence(value=0.9)
    assert doc.processing_status == ProcessingStatus.INDEXING


def test_document_mark_indexed():
    doc = Document(id=uuid.uuid4(), file_id=uuid.uuid4())
    doc.mark_indexed(chunk_count=5)
    assert doc.processing_status == ProcessingStatus.COMPLETED
    assert doc.chunk_count == 5
    assert doc.is_processed


def test_document_mark_failed():
    doc = Document(id=uuid.uuid4(), file_id=uuid.uuid4())
    doc.mark_failed("OCR failed")
    assert doc.processing_status == ProcessingStatus.FAILED
    assert doc.error_message == "OCR failed"
    assert doc.has_failed


def test_document_schedule_retry():
    doc = Document(id=uuid.uuid4(), file_id=uuid.uuid4())
    doc.mark_failed("Error")
    doc.schedule_retry()
    assert doc.processing_status == ProcessingStatus.RETRYING
    assert doc.retry_count == 1
    assert doc.error_message is None


def test_document_can_retry():
    doc = Document(id=uuid.uuid4(), file_id=uuid.uuid4())
    doc.mark_failed("Error")
    assert doc.can_retry

    # After 3 retries, should not be able to retry
    doc.schedule_retry()  # retry_count = 1
    doc.schedule_retry()  # retry_count = 2
    doc.schedule_retry()  # retry_count = 3
    assert not doc.can_retry


def test_document_word_count():
    doc = Document(id=uuid.uuid4(), file_id=uuid.uuid4(), extracted_text="hello world foo bar")
    assert doc.word_count == 4


def test_document_word_count_empty():
    doc = Document(id=uuid.uuid4(), file_id=uuid.uuid4(), extracted_text="")
    assert doc.word_count == 0


def test_document_chunk_creation():
    chunk = DocumentChunk(
        document_id=uuid.uuid4(),
        chunk_index=0,
        content="This is a test chunk of text.",
        start_offset=0,
        end_offset=30,
    )
    assert chunk.chunk_index == 0
    assert len(chunk.content) > 0
    assert chunk.start_offset == 0
    assert chunk.end_offset == 30


def test_document_chunk_token_estimate():
    chunk = DocumentChunk(
        document_id=uuid.uuid4(),
        content="a" * 100,
    )
    assert chunk.token_estimate == 25  # 100 // 4


def test_document_chunk_from_text():
    doc_id = uuid.uuid4()
    text = "Word " * 200  # ~1000 chars
    chunks = DocumentChunk.from_text(
        document_id=doc_id,
        text=text.strip(),
        chunk_size=200,
        overlap=50,
    )
    assert len(chunks) > 0
    for i, chunk in enumerate(chunks):
        assert chunk.document_id == doc_id
        assert chunk.chunk_index == i


def test_document_chunk_from_text_empty():
    doc_id = uuid.uuid4()
    chunks = DocumentChunk.from_text(document_id=doc_id, text="")
    assert chunks == []


def test_document_chunk_from_text_short():
    doc_id = uuid.uuid4()
    chunks = DocumentChunk.from_text(document_id=doc_id, text="Hello", chunk_size=1000)
    assert len(chunks) == 1
    assert chunks[0].content == "Hello"


def test_document_metadata_defaults():
    meta = DocumentMetadata()
    assert meta.title == ""
    assert meta.author == ""
    assert meta.page_count == 0
    assert meta.language == Language.UNKNOWN


def test_document_metadata_with_values():
    meta = DocumentMetadata(
        title="Test Doc",
        author="Author",
        page_count=10,
        language=Language.EN,
    )
    assert meta.title == "Test Doc"
    assert meta.page_count == 10
    assert meta.language == Language.EN


def test_document_type_from_extension():
    assert DocumentType.from_extension(".pdf") == DocumentType.PDF
    assert DocumentType.from_extension(".txt") == DocumentType.TEXT
    assert DocumentType.from_extension(".md") == DocumentType.MARKDOWN
    assert DocumentType.from_extension(".html") == DocumentType.HTML
    assert DocumentType.from_extension(".py") == DocumentType.CODE
    assert DocumentType.from_extension(".unknown") == DocumentType.UNKNOWN


def test_processing_status_terminal():
    assert ProcessingStatus.COMPLETED.is_terminal
    assert ProcessingStatus.FAILED.is_terminal
    assert not ProcessingStatus.QUEUED.is_terminal
    assert not ProcessingStatus.EXTRACTING.is_terminal


def test_processing_status_can_retry():
    assert ProcessingStatus.FAILED.can_retry
    assert ProcessingStatus.RETRYING.can_retry
    assert not ProcessingStatus.COMPLETED.can_retry
    assert not ProcessingStatus.QUEUED.can_retry


def test_language_values():
    assert Language.EN.value == "en"
    assert Language.FR.value == "fr"
    assert Language.UNKNOWN.value == "unknown"


def test_confidence_value():
    conf = Confidence(value=0.85)
    assert conf.value == 0.85
    assert 0 <= conf.value <= 1


def test_confidence_high():
    conf = Confidence(value=0.9)
    assert conf.is_high
    assert not conf.is_medium
    assert not conf.is_low


def test_confidence_medium():
    conf = Confidence(value=0.6)
    assert not conf.is_high
    assert conf.is_medium
    assert not conf.is_low


def test_confidence_low():
    conf = Confidence(value=0.3)
    assert not conf.is_high
    assert not conf.is_medium
    assert conf.is_low


def test_confidence_percentage():
    conf = Confidence(value=0.856)
    assert conf.percentage == "85.6%"


def test_confidence_boundary():
    assert Confidence(value=0.0).value == 0.0
    assert Confidence(value=1.0).value == 1.0
    with pytest.raises(ValueError):
        Confidence(value=-0.1)
    with pytest.raises(ValueError):
        Confidence(value=1.1)
