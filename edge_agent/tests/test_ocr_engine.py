"""Tests for edge_agent.ocr.engine — OCR engine."""
import pytest
from unittest.mock import patch, MagicMock

from edge_agent.core.models import Language
from edge_agent.ocr.engine import OCREngine


class TestOCREngineDetectLanguage:
    def test_detect_english(self):
        eng = OCREngine()
        lang = eng.detect_language("This is an English sentence with enough words to detect.")
        assert lang in (Language.EN, Language.UNKNOWN)

    def test_detect_arabic(self):
        eng = OCREngine()
        lang = eng.detect_language("هذه جملة عربية كافية للكشف عنها في النص")
        assert lang == Language.AR

    def test_empty_text(self):
        eng = OCREngine()
        lang = eng.detect_language("")
        assert lang == Language.UNKNOWN


class TestOCREngineConfidence:
    def test_high_confidence_text(self):
        eng = OCREngine()
        conf = eng.get_confidence("This is a normal English sentence with letters and spaces.")
        assert conf.value > 0.5

    def test_empty_text_low_confidence(self):
        eng = OCREngine()
        conf = eng.get_confidence("")
        assert conf.value == 0.0


class TestOCREngineExtractText:
    def test_extract_text_returns_string(self):
        eng = OCREngine()
        with patch.object(eng, "_is_paddle_available", return_value=False), \
             patch.object(eng, "_is_tesseract_available", return_value=False):
            result = eng.extract_text(b"fake image bytes", content_type="image/png")
            assert isinstance(result, str)
