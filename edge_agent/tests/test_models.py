"""Tests for edge_agent.core.models — value objects."""
import pytest

from edge_agent.core.models import (
    Confidence,
    ContentBlock,
    ExtractionResult,
    Language,
    ParsedDocument,
    ParsedImage,
    ParsedTable,
)


class TestLanguage:
    def test_language_enum_members(self):
        assert Language.EN.value == "en"
        assert Language.AR.value == "ar"
        assert Language.UNKNOWN.value == "unknown"

    def test_language_count(self):
        assert len(Language) == 19


class TestConfidence:
    def test_valid_confidence(self):
        c = Confidence(value=0.75)
        assert c.value == 0.75

    def test_confidence_out_of_range(self):
        with pytest.raises(ValueError):
            Confidence(value=1.5)
        with pytest.raises(ValueError):
            Confidence(value=-0.1)

    def test_is_high(self):
        assert Confidence(value=0.9).is_high
        assert Confidence(value=0.8).is_high
        assert not Confidence(value=0.79).is_high

    def test_is_medium(self):
        assert Confidence(value=0.5).is_medium
        assert Confidence(value=0.79).is_medium
        assert not Confidence(value=0.8).is_medium
        assert not Confidence(value=0.49).is_medium

    def test_is_low(self):
        assert Confidence(value=0.1).is_low
        assert not Confidence(value=0.5).is_low

    def test_percentage(self):
        assert Confidence(value=0.95).percentage == "95.0%"
        assert Confidence(value=0.0).percentage == "0.0%"

    def test_frozen(self):
        c = Confidence(value=0.5)
        with pytest.raises(AttributeError):
            c.value = 0.9  # type: ignore


class TestContentBlock:
    def test_creation(self):
        block = ContentBlock(block_type="heading", content="Title", level=1)
        assert block.block_type == "heading"
        assert block.level == 1

    def test_defaults(self):
        block = ContentBlock(block_type="text")
        assert block.content == ""
        assert block.metadata == {}
        assert block.bbox is None
        assert block.level is None

    def test_frozen(self):
        block = ContentBlock(block_type="text")
        with pytest.raises(AttributeError):
            block.content = "changed"  # type: ignore


class TestParsedDocument:
    def test_creation(self):
        doc = ParsedDocument(document_name="test.pdf", markdown="# Hello")
        assert doc.document_name == "test.pdf"
        assert doc.has_tables is False
        assert doc.has_images is False

    def test_has_tables(self):
        table = ParsedTable(html="<table></table>")
        doc = ParsedDocument(tables=[table])
        assert doc.has_tables is True

    def test_has_images(self):
        img = ParsedImage(image_path="/tmp/img.png")
        doc = ParsedDocument(images=[img])
        assert doc.has_images is True


class TestExtractionResult:
    def test_auto_word_count(self):
        result = ExtractionResult(text="hello world foo bar")
        assert result.word_count == 4

    def test_auto_char_count(self):
        result = ExtractionResult(text="hello")
        assert result.char_count == 5

    def test_explicit_counts_not_overridden(self):
        result = ExtractionResult(text="hello", word_count=10, char_count=99)
        assert result.word_count == 10
        assert result.char_count == 99

    def test_empty_text(self):
        result = ExtractionResult(text="")
        assert result.word_count == 0
        assert result.char_count == 0
