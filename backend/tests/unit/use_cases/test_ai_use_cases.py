from __future__ import annotations

import pytest

from core.application.use_cases.ai_use_cases import AIUseCases
from core.domain.common.exceptions import ValidationException
from tests.mocks import (
    MockAITaskRepository,
    MockDocumentRepository,
    MockEmbeddingProvider,
    MockEmbeddingRepository,
    MockFileRepository,
    MockLLMProvider,
)


@pytest.fixture
def ai_use_cases() -> AIUseCases:
    return AIUseCases(
        ai_task_repository=MockAITaskRepository(),
        document_repository=MockDocumentRepository(),
        embedding_repository=MockEmbeddingRepository(),
        file_repository=MockFileRepository(),
        llm_provider=MockLLMProvider(),
        embedding_provider=MockEmbeddingProvider(),
    )


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------


def test_classify_success(ai_use_cases: AIUseCases) -> None:
    result = ai_use_cases.classify("This is a contract agreement")
    assert result.predicted_label == "contract"
    assert result.confidence == 0.95


def test_classify_with_custom_categories(ai_use_cases: AIUseCases) -> None:
    result = ai_use_cases.classify(
        "Quarterly revenue report",
        categories=["finance", "legal", "hr"],
    )
    assert result.predicted_label == "contract"
    assert result.confidence == 0.95


def test_classify_empty_text_raises(ai_use_cases: AIUseCases) -> None:
    with pytest.raises(ValidationException):
        ai_use_cases.classify("")


def test_classify_whitespace_only_raises(ai_use_cases: AIUseCases) -> None:
    with pytest.raises(ValidationException):
        ai_use_cases.classify("   \t\n  ")


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------


def test_extract_success(ai_use_cases: AIUseCases) -> None:
    result = ai_use_cases.extract("Invoice number 12345", fields=["invoice_number"])
    assert "invoice_number" in result
    assert result["invoice_number"] == "extracted_invoice_number"


def test_extract_multiple_fields(ai_use_cases: AIUseCases) -> None:
    result = ai_use_cases.extract(
        "Some document text",
        fields=["title", "date", "amount"],
    )
    assert set(result.keys()) == {"title", "date", "amount"}


def test_extract_empty_text_raises(ai_use_cases: AIUseCases) -> None:
    with pytest.raises(ValidationException):
        ai_use_cases.extract("", fields=["test"])


def test_extract_no_fields_raises(ai_use_cases: AIUseCases) -> None:
    with pytest.raises(ValidationException):
        ai_use_cases.extract("Some text", fields=[])


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------


def test_summarize_success(ai_use_cases: AIUseCases) -> None:
    result = ai_use_cases.summarize("Long document text here")
    assert len(result) > 0
    assert isinstance(result, str)


def test_summarize_with_max_tokens(ai_use_cases: AIUseCases) -> None:
    result = ai_use_cases.summarize("Document to summarize", max_tokens=100)
    assert result == "This is a summary of the document."


def test_summarize_empty_text_raises(ai_use_cases: AIUseCases) -> None:
    with pytest.raises(ValidationException):
        ai_use_cases.summarize("")
