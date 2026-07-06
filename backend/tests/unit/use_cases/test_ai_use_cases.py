from __future__ import annotations

import uuid

import pytest

from core.application.dtos.ai_dto import ClassificationDTO, EmbeddingDTO
from core.application.use_cases.ai_use_cases import AIUseCases
from core.domain.common.exceptions import EntityNotFound, ValidationException
from core.domain.documents.entities import Document, DocumentMetadata
from core.domain.documents.value_objects import (
    Confidence,
    DocumentType,
    Language,
    ProcessingStatus,
)
from tests.mocks import (
    MockAITaskRepository,
    MockDocumentRepository,
    MockEmbeddingProvider,
    MockEmbeddingRepository,
    MockFileRepository,
    MockLLMProvider,
)


@pytest.fixture
def ai_task_repository() -> MockAITaskRepository:
    return MockAITaskRepository()


@pytest.fixture
def document_repository() -> MockDocumentRepository:
    return MockDocumentRepository()


@pytest.fixture
def embedding_repository() -> MockEmbeddingRepository:
    return MockEmbeddingRepository()


@pytest.fixture
def file_repository() -> MockFileRepository:
    return MockFileRepository()


@pytest.fixture
def llm_provider() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
def embedding_provider() -> MockEmbeddingProvider:
    return MockEmbeddingProvider()


@pytest.fixture
def ai_use_cases(
    ai_task_repository: MockAITaskRepository,
    document_repository: MockDocumentRepository,
    embedding_repository: MockEmbeddingRepository,
    file_repository: MockFileRepository,
    llm_provider: MockLLMProvider,
    embedding_provider: MockEmbeddingProvider,
) -> AIUseCases:
    return AIUseCases(
        ai_task_repository=ai_task_repository,
        document_repository=document_repository,
        embedding_repository=embedding_repository,
        file_repository=file_repository,
        llm_provider=llm_provider,
        embedding_provider=embedding_provider,
    )


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------


class TestClassify:
    def test_success(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.classify("This is a contract agreement")
        assert result.predicted_label == "contract"
        assert result.confidence == 0.95

    def test_returns_classification_dto(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.classify("Some text")
        assert isinstance(result, ClassificationDTO)

    def test_with_custom_categories(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.classify(
            "Quarterly revenue report",
            categories=["finance", "legal", "hr"],
        )
        assert result.predicted_label == "contract"
        assert result.confidence == 0.95

    def test_empty_text_raises(self, ai_use_cases: AIUseCases) -> None:
        with pytest.raises(ValidationException) as exc_info:
            ai_use_cases.classify("")
        assert "empty" in str(exc_info.value.message).lower()

    def test_whitespace_only_raises(self, ai_use_cases: AIUseCases) -> None:
        with pytest.raises(ValidationException):
            ai_use_cases.classify("   \t\n  ")

    def test_with_system_prompt(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.classify(
            "Contract text",
            system_prompt="Classify as legal document",
        )
        assert result.predicted_label == "contract"

    def test_input_text_truncated(self, ai_use_cases: AIUseCases) -> None:
        long_text = "word " * 1000
        result = ai_use_cases.classify(long_text)
        assert len(result.input_text) <= 200

    def test_all_labels_populated(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.classify("Some text")
        assert len(result.all_labels) >= 1
        assert result.predicted_label in result.all_labels


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------


class TestExtract:
    def test_success(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.extract("Invoice number 12345", fields=["invoice_number"])
        assert "invoice_number" in result
        assert result["invoice_number"] == "extracted_invoice_number"

    def test_multiple_fields(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.extract(
            "Some document text",
            fields=["title", "date", "amount"],
        )
        assert set(result.keys()) == {"title", "date", "amount"}

    def test_empty_text_raises(self, ai_use_cases: AIUseCases) -> None:
        with pytest.raises(ValidationException) as exc_info:
            ai_use_cases.extract("", fields=["test"])
        assert "empty" in str(exc_info.value.message).lower()

    def test_no_fields_raises(self, ai_use_cases: AIUseCases) -> None:
        with pytest.raises(ValidationException) as exc_info:
            ai_use_cases.extract("Some text", fields=[])
        assert "field" in str(exc_info.value.message).lower()

    def test_with_system_prompt(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.extract(
            "Invoice #1234",
            fields=["invoice_number"],
            system_prompt="Extract the invoice number",
        )
        assert "invoice_number" in result

    def test_text_truncated(self, ai_use_cases: AIUseCases) -> None:
        long_text = "word " * 2000
        result = ai_use_cases.extract(long_text, fields=["title"])
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------


class TestSummarize:
    def test_success(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.summarize("Long document text here")
        assert len(result) > 0
        assert isinstance(result, str)

    def test_returns_string(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.summarize("Document to summarize")
        assert isinstance(result, str)

    def test_with_max_tokens(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.summarize("Document to summarize", max_tokens=100)
        assert result == "This is a summary of the document."

    def test_empty_text_raises(self, ai_use_cases: AIUseCases) -> None:
        with pytest.raises(ValidationException) as exc_info:
            ai_use_cases.summarize("")
        assert "empty" in str(exc_info.value.message).lower()

    def test_whitespace_only_raises(self, ai_use_cases: AIUseCases) -> None:
        with pytest.raises(ValidationException):
            ai_use_cases.summarize("   \t\n  ")

    def test_with_system_prompt(self, ai_use_cases: AIUseCases) -> None:
        result = ai_use_cases.summarize(
            "Document text",
            system_prompt="Summarize in bullet points",
        )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# generate_embeddings
# ---------------------------------------------------------------------------


class TestGenerateEmbeddings:
    def test_success(self, ai_use_cases: AIUseCases) -> None:
        doc_id = uuid.uuid4()
        file_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            file_id=file_id,
            doc_type=DocumentType.PDF,
            processing_status=ProcessingStatus.COMPLETED,
            extracted_text="This is extracted text from the document.",
            metadata=DocumentMetadata(title="Test Doc", language=Language.EN),
        )
        ai_use_cases._document_repository.save(doc)

        results = ai_use_cases.generate_embeddings(doc_id)
        assert len(results) > 0
        assert all(isinstance(r, EmbeddingDTO) for r in results)

    def test_document_not_found_raises(self, ai_use_cases: AIUseCases) -> None:
        with pytest.raises(EntityNotFound):
            ai_use_cases.generate_embeddings(uuid.uuid4())

    def test_no_extracted_text_raises(self, ai_use_cases: AIUseCases) -> None:
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            file_id=uuid.uuid4(),
            extracted_text="",
        )
        ai_use_cases._document_repository.save(doc)

        with pytest.raises(ValidationException) as exc_info:
            ai_use_cases.generate_embeddings(doc_id)
        assert "no extracted text" in str(exc_info.value.message).lower()

    def test_embedding_dto_fields(self, ai_use_cases: AIUseCases) -> None:
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            file_id=uuid.uuid4(),
            doc_type=DocumentType.PDF,
            extracted_text="Hello world text for embedding.",
            metadata=DocumentMetadata(title="Test"),
        )
        ai_use_cases._document_repository.save(doc)

        results = ai_use_cases.generate_embeddings(doc_id)
        assert len(results) >= 1
        first = results[0]
        assert first.source_type == "document"
        assert first.source_id == doc_id
        assert first.text == "Hello world text for embedding."
        assert len(first.vector) == 384
        assert first.chunk_index == 0

    def test_embeddings_stored_in_repository(self, ai_use_cases: AIUseCases) -> None:
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            file_id=uuid.uuid4(),
            extracted_text="Some text to embed.",
        )
        ai_use_cases._document_repository.save(doc)

        ai_use_cases.generate_embeddings(doc_id)
        assert len(ai_use_cases._embedding_repository._embeddings) >= 1

    def test_chunk_size_respected(self, ai_use_cases: AIUseCases) -> None:
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            file_id=uuid.uuid4(),
            extracted_text="word " * 500,
        )
        ai_use_cases._document_repository.save(doc)

        results = ai_use_cases.generate_embeddings(doc_id, chunk_size=100, overlap=20)
        assert len(results) > 1

    def test_long_text_multiple_chunks(self, ai_use_cases: AIUseCases) -> None:
        doc_id = uuid.uuid4()
        long_text = "This is sentence number X. " * 200
        doc = Document(
            id=doc_id,
            file_id=uuid.uuid4(),
            extracted_text=long_text,
        )
        ai_use_cases._document_repository.save(doc)

        results = ai_use_cases.generate_embeddings(doc_id, chunk_size=200, overlap=50)
        assert len(results) >= 2
        for i, r in enumerate(results):
            assert r.chunk_index == i

    def test_metadata_passed_to_embedding(self, ai_use_cases: AIUseCases) -> None:
        doc_id = uuid.uuid4()
        file_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            file_id=file_id,
            doc_type=DocumentType.MARKDOWN,
            extracted_text="Embedded text.",
            metadata=DocumentMetadata(title="My Doc", language=Language.FR),
        )
        ai_use_cases._document_repository.save(doc)

        ai_use_cases.generate_embeddings(doc_id)
        embeddings = ai_use_cases._embedding_repository._embeddings
        for vector_id, data in embeddings.items():
            meta = data["metadata"]
            assert meta["document_id"] == str(doc_id)
            assert meta["file_id"] == str(file_id)
            assert meta["title"] == "My Doc"
            assert meta["doc_type"] == "markdown"
            assert meta["language"] == "fr"

    def test_vector_id_format(self, ai_use_cases: AIUseCases) -> None:
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            file_id=uuid.uuid4(),
            extracted_text="Some text.",
        )
        ai_use_cases._document_repository.save(doc)

        results = ai_use_cases.generate_embeddings(doc_id)
        for r in results:
            assert r.id.startswith(f"doc_{doc_id}_chunk_")
