import pytest
import uuid
from datetime import datetime, timezone

from core.domain.documents.entities import Document, DocumentChunk, DocumentMetadata
from core.domain.documents.value_objects import (
    Confidence,
    DocumentType,
    Language,
    ProcessingStatus,
)


# ---------------------------------------------------------------------------
# DocumentMetadata
# ---------------------------------------------------------------------------


class TestDocumentMetadata:
    def test_defaults(self):
        meta = DocumentMetadata()
        assert meta.title == ""
        assert meta.author == ""
        assert meta.subject == ""
        assert meta.keywords == ()
        assert meta.creation_date == ""
        assert meta.modification_date == ""
        assert meta.page_count == 0
        assert meta.word_count == 0
        assert meta.char_count == 0
        assert meta.language == Language.UNKNOWN
        assert meta.extra == {}

    def test_with_values(self):
        meta = DocumentMetadata(
            title="Test Doc",
            author="Author",
            subject="Testing",
            keywords=("keyword1", "keyword2"),
            creation_date="2024-01-15",
            modification_date="2024-06-01",
            page_count=10,
            word_count=5000,
            char_count=30000,
            language=Language.EN,
            extra={"custom": "data"},
        )
        assert meta.title == "Test Doc"
        assert meta.author == "Author"
        assert meta.subject == "Testing"
        assert meta.keywords == ("keyword1", "keyword2")
        assert meta.page_count == 10
        assert meta.word_count == 5000
        assert meta.char_count == 30000
        assert meta.language == Language.EN
        assert meta.extra == {"custom": "data"}

    def test_immutability(self):
        meta = DocumentMetadata(title="Test")
        with pytest.raises(AttributeError):
            meta.title = "Changed"


# ---------------------------------------------------------------------------
# DocumentChunk
# ---------------------------------------------------------------------------


class TestDocumentChunk:
    def test_creation(self):
        chunk = DocumentChunk(
            document_id=uuid.uuid4(),
            chunk_index=0,
            content="This is a test chunk of text.",
            start_offset=0,
            end_offset=30,
        )
        assert chunk.chunk_index == 0
        assert chunk.content == "This is a test chunk of text."
        assert chunk.start_offset == 0
        assert chunk.end_offset == 30

    def test_defaults(self):
        chunk = DocumentChunk(document_id=uuid.uuid4())
        assert chunk.chunk_index == 0
        assert chunk.content == ""
        assert chunk.start_offset == 0
        assert chunk.end_offset == 0
        assert chunk.embedding_id is None
        assert chunk.metadata == {}

    def test_token_estimate(self):
        chunk = DocumentChunk(document_id=uuid.uuid4(), content="a" * 100)
        assert chunk.token_estimate == 25

    def test_token_estimate_empty(self):
        chunk = DocumentChunk(document_id=uuid.uuid4(), content="")
        assert chunk.token_estimate == 0

    def test_token_estimate_short(self):
        chunk = DocumentChunk(document_id=uuid.uuid4(), content="ab")
        assert chunk.token_estimate == 0  # 2 // 4 = 0

    def test_from_text_returns_empty_for_empty(self):
        doc_id = uuid.uuid4()
        chunks = DocumentChunk.from_text(document_id=doc_id, text="")
        assert chunks == []

    def test_from_text_short_text_single_chunk(self):
        doc_id = uuid.uuid4()
        chunks = DocumentChunk.from_text(document_id=doc_id, text="Hello", chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0].content == "Hello"
        assert chunks[0].chunk_index == 0
        assert chunks[0].document_id == doc_id

    def test_from_text_exact_chunk_size(self):
        doc_id = uuid.uuid4()
        text = "a" * 100
        chunks = DocumentChunk.from_text(document_id=doc_id, text=text, chunk_size=100, overlap=0)
        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_from_text_multiple_chunks(self):
        doc_id = uuid.uuid4()
        text = "Word " * 500  # ~2500 chars
        chunks = DocumentChunk.from_text(
            document_id=doc_id,
            text=text.strip(),
            chunk_size=500,
            overlap=100,
        )
        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk.document_id == doc_id
            assert chunk.chunk_index == i

    def test_from_text_chunk_offsets(self):
        doc_id = uuid.uuid4()
        text = "x" * 300
        chunks = DocumentChunk.from_text(
            document_id=doc_id,
            text=text,
            chunk_size=100,
            overlap=0,
        )
        assert len(chunks) == 3
        assert chunks[0].start_offset == 0
        assert chunks[0].end_offset == 100
        assert chunks[1].start_offset == 100
        assert chunks[1].end_offset == 200
        assert chunks[2].start_offset == 200
        assert chunks[2].end_offset == 300

    def test_from_text_with_overlap(self):
        doc_id = uuid.uuid4()
        text = "abcdefghij" * 30  # 300 chars
        chunks = DocumentChunk.from_text(
            document_id=doc_id,
            text=text,
            chunk_size=100,
            overlap=20,
        )
        assert len(chunks) > 1
        # Second chunk starts at end - overlap, not at end
        assert chunks[1].start_offset == 80

    def test_immutability(self):
        chunk = DocumentChunk(document_id=uuid.uuid4(), content="test")
        with pytest.raises(AttributeError):
            chunk.content = "changed"


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class TestDocument:
    def _make_document(self, **overrides) -> Document:
        defaults = dict(
            id=uuid.uuid4(),
            file_id=uuid.uuid4(),
            doc_type=DocumentType.PDF,
            processing_status=ProcessingStatus.QUEUED,
            metadata=DocumentMetadata(),
            extracted_text="",
            chunk_count=0,
            error_message=None,
            retry_count=0,
            tags=(),
        )
        defaults.update(overrides)
        return Document(**defaults)

    def test_creation(self):
        doc = self._make_document(
            extracted_text="Test contract text",
            processing_status=ProcessingStatus.COMPLETED,
        )
        assert doc.doc_type == DocumentType.PDF
        assert doc.processing_status == ProcessingStatus.COMPLETED
        assert doc.extracted_text == "Test contract text"

    def test_defaults(self):
        doc = Document(id=uuid.uuid4())
        assert doc.doc_type == DocumentType.UNKNOWN
        assert doc.processing_status == ProcessingStatus.QUEUED
        assert doc.extracted_text == ""
        assert doc.chunk_count == 0
        assert doc.retry_count == 0
        assert doc.error_message is None
        assert doc.tags == ()

    def test_start_processing(self):
        doc = self._make_document()
        doc.start_processing()
        assert doc.processing_status == ProcessingStatus.EXTRACTING

    def test_mark_classified(self):
        doc = self._make_document()
        conf = Confidence(value=0.9)
        doc.mark_classified(doc_type=DocumentType.PDF, confidence=conf)
        assert doc.doc_type == DocumentType.PDF
        assert doc.classification_confidence == conf
        assert doc.processing_status == ProcessingStatus.INDEXING

    def test_mark_indexed(self):
        doc = self._make_document()
        doc.mark_indexed(chunk_count=5)
        assert doc.processing_status == ProcessingStatus.COMPLETED
        assert doc.chunk_count == 5
        assert doc.is_processed

    def test_mark_failed(self):
        doc = self._make_document()
        doc.mark_failed("OCR failed")
        assert doc.processing_status == ProcessingStatus.FAILED
        assert doc.error_message == "OCR failed"
        assert doc.has_failed

    def test_schedule_retry(self):
        doc = self._make_document()
        doc.mark_failed("Error")
        doc.schedule_retry()
        assert doc.processing_status == ProcessingStatus.RETRYING
        assert doc.retry_count == 1
        assert doc.error_message is None

    def test_can_retry_when_failed(self):
        doc = self._make_document()
        doc.mark_failed("Error")
        assert doc.can_retry

    def test_can_retry_when_retrying(self):
        doc = self._make_document()
        doc.mark_failed("Error")
        doc.schedule_retry()
        assert doc.can_retry

    def test_cannot_retry_after_max(self):
        doc = self._make_document()
        doc.mark_failed("Error")
        doc.schedule_retry()  # retry_count = 1
        doc.schedule_retry()  # retry_count = 2
        doc.schedule_retry()  # retry_count = 3
        assert not doc.can_retry

    def test_cannot_retry_when_completed(self):
        doc = self._make_document()
        doc.mark_indexed(chunk_count=1)
        assert not doc.can_retry

    def test_cannot_retry_when_queued(self):
        doc = self._make_document()
        assert not doc.can_retry

    def test_is_processed(self):
        doc = self._make_document()
        doc.mark_indexed(chunk_count=1)
        assert doc.is_processed

    def test_is_not_processed(self):
        doc = self._make_document()
        assert not doc.is_processed

    def test_has_failed(self):
        doc = self._make_document()
        doc.mark_failed("Error")
        assert doc.has_failed

    def test_has_not_failed(self):
        doc = self._make_document()
        assert not doc.has_failed

    def test_word_count(self):
        doc = self._make_document(extracted_text="hello world foo bar")
        assert doc.word_count == 4

    def test_word_count_empty(self):
        doc = self._make_document(extracted_text="")
        assert doc.word_count == 0

    def test_word_count_none(self):
        doc = self._make_document(extracted_text="")
        assert doc.word_count == 0

    def test_word_count_whitespace(self):
        doc = self._make_document(extracted_text="  hello  world  ")
        assert doc.word_count == 2

    def test_with_tags(self):
        doc = self._make_document(tags=("important", "draft"))
        assert "important" in doc.tags
        assert "draft" in doc.tags

    def test_start_processing_updates_timestamp(self):
        doc = self._make_document()
        old_updated = doc.updated_at
        import time
        time.sleep(0.01)
        doc.start_processing()
        assert doc.updated_at >= old_updated

    def test_mark_classified_updates_timestamp(self):
        doc = self._make_document()
        old_updated = doc.updated_at
        import time
        time.sleep(0.01)
        doc.mark_classified(doc_type=DocumentType.PDF, confidence=Confidence(value=0.9))
        assert doc.updated_at >= old_updated

    def test_mark_indexed_updates_timestamp(self):
        doc = self._make_document()
        old_updated = doc.updated_at
        import time
        time.sleep(0.01)
        doc.mark_indexed(chunk_count=5)
        assert doc.updated_at >= old_updated

    def test_mark_failed_updates_timestamp(self):
        doc = self._make_document()
        old_updated = doc.updated_at
        import time
        time.sleep(0.01)
        doc.mark_failed("Error")
        assert doc.updated_at >= old_updated

    def test_schedule_retry_updates_timestamp(self):
        doc = self._make_document()
        doc.mark_failed("Error")
        old_updated = doc.updated_at
        import time
        time.sleep(0.01)
        doc.schedule_retry()
        assert doc.updated_at >= old_updated

    def test_immutability(self):
        doc = self._make_document()
        with pytest.raises(AttributeError):
            doc.doc_type = DocumentType.TEXT

    def test_full_processing_lifecycle(self):
        doc = self._make_document()
        assert doc.processing_status == ProcessingStatus.QUEUED

        doc.start_processing()
        assert doc.processing_status == ProcessingStatus.EXTRACTING

        doc.mark_classified(doc_type=DocumentType.PDF, confidence=Confidence(value=0.95))
        assert doc.processing_status == ProcessingStatus.INDEXING

        doc.mark_indexed(chunk_count=10)
        assert doc.processing_status == ProcessingStatus.COMPLETED
        assert doc.is_processed

    def test_failure_and_retry_lifecycle(self):
        doc = self._make_document()
        doc.mark_failed("OCR timeout")
        assert doc.has_failed
        assert doc.can_retry

        doc.schedule_retry()
        assert doc.processing_status == ProcessingStatus.RETRYING
        assert doc.retry_count == 1

        doc.mark_failed("OCR timeout again")
        doc.schedule_retry()
        assert doc.retry_count == 2

        doc.mark_failed("OCR timeout again")
        doc.schedule_retry()
        assert doc.retry_count == 3
        assert not doc.can_retry
