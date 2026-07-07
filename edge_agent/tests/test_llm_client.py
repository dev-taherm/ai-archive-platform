"""Tests for edge_agent.llm.client — LLM client and entity extraction."""
import json
from unittest.mock import MagicMock, patch

import pytest

from edge_agent.config import LLMConfig
from edge_agent.llm.client import ENTITY_EXTRACTION_PROMPT, ExtractedEntity, LLMClient


@pytest.fixture
def client():
    return LLMClient(LLMConfig(provider="openai", api_key="test-key", model="gpt-4o-mini"))


class TestExtractedEntity:
    def test_creation(self):
        e = ExtractedEntity(entity_type="person", name="John Doe", context="CEO", confidence=0.9)
        assert e.entity_type == "person"
        assert e.name == "John Doe"

    def test_defaults(self):
        e = ExtractedEntity(entity_type="org", name="Acme")
        assert e.context == ""
        assert e.confidence is None

    def test_frozen(self):
        e = ExtractedEntity(entity_type="person", name="X")
        with pytest.raises(AttributeError):
            e.name = "Y"  # type: ignore


class TestLLMClientExtractEntities:
    def test_short_text_returns_empty(self, client):
        assert client.extract_entities("hi") == []

    def test_empty_text_returns_empty(self, client):
        assert client.extract_entities("") == []

    def test_whitespace_returns_empty(self, client):
        assert client.extract_entities("   ") == []

    @patch.object(LLMClient, "_call_llm")
    def test_parses_json_array(self, mock_call, client):
        mock_call.return_value = json.dumps([
            {"entity_type": "person", "name": "John", "context": "CEO"},
            {"entity_type": "organization", "name": "Acme", "context": "Company"},
        ])
        result = client.extract_entities("This is a long enough text for entity extraction.")
        assert len(result) == 2
        assert result[0].name == "John"

    @patch.object(LLMClient, "_call_llm")
    def test_parses_entities_wrapper(self, mock_call, client):
        mock_call.return_value = json.dumps({
            "entities": [
                {"entity_type": "person", "name": "Jane", "context": "Engineer"},
            ]
        })
        result = client.extract_entities("This is a long enough text for entity extraction.")
        assert len(result) == 1
        assert result[0].name == "Jane"

    @patch.object(LLMClient, "_call_llm")
    def test_handles_malformed_json(self, mock_call, client):
        mock_call.return_value = "not valid json"
        result = client.extract_entities("This is a long enough text for extraction.")
        assert result == []

    @patch.object(LLMClient, "_call_llm")
    def test_maps_entity_types(self, mock_call, client):
        mock_call.return_value = json.dumps([
            {"entity_type": "org", "name": "Test", "context": ""},
        ])
        result = client.extract_entities("This is a long enough text for entity extraction.")
        assert result[0].entity_type == "organization"

    @patch.object(LLMClient, "_call_llm")
    def test_extracts_confidence(self, mock_call, client):
        mock_call.return_value = json.dumps([
            {"entity_type": "person", "name": "X", "context": "", "confidence": 0.95},
        ])
        result = client.extract_entities("This is a long enough text for entity extraction.")
        assert result[0].confidence == 0.95


class TestLLMClientProviders:
    @patch("edge_agent.llm.client.httpx")
    def test_unsupported_provider(self, mock_httpx):
        client = LLMClient(LLMConfig(provider="unsupported"))
        with pytest.raises(ValueError, match="Unsupported"):
            client._call_llm("prompt")
