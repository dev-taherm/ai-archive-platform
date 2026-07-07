"""Edge Agent LLM client — supports OpenAI, Anthropic, and Ollama."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from edge_agent.config import LLMConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractedEntity:
    """A named entity extracted from document text."""

    entity_type: str
    name: str
    context: str = ""
    confidence: float | None = None


ENTITY_EXTRACTION_PROMPT = """Extract all named entities from the following document text.

Return a JSON array of objects, each with:
- "entity_type": one of "person", "organization", "date", "amount", "location", "email", "phone", "reference_number", "project_name"
- "name": the entity text (e.g. "John Doe", "Acme Corp", "2024-01-15")
- "context": a brief surrounding text snippet that provides context (max 100 chars)

Rules:
- Extract ALL entities you can identify, even if uncertain.
- For "amount", include currency symbols (e.g. "$1,234.56").
- For "date", use ISO format when possible (YYYY-MM-DD).
- For "reference_number", extract any document/invoice/PO numbers.
- Do NOT include generic words or common nouns.
- Return ONLY the JSON array, no other text.

Document text:
"""


class LLMClient:
    """Unified LLM client for entity extraction."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._provider = config.provider.lower()

    def extract_entities(self, text: str) -> list[ExtractedEntity]:
        """Extract named entities from text using the configured LLM provider."""
        if not text or len(text.strip()) < 20:
            return []

        truncated = text[:8000]
        prompt = ENTITY_EXTRACTION_PROMPT + truncated

        try:
            raw_response = self._call_llm(prompt)
            return self._parse_entities(raw_response)
        except Exception:
            logger.exception("Entity extraction failed")
            return []

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM and return raw text response."""
        if self._provider == "openai":
            return self._call_openai(prompt)
        elif self._provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self._provider == "ollama":
            return self._call_ollama(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self._provider}")

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI-compatible API."""
        import httpx

        base_url = self._config.base_url or "https://api.openai.com/v1"
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": "You are a precise entity extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        import httpx

        base_url = self._config.base_url or "https://api.anthropic.com"
        headers = {
            "x-api-key": self._config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._config.model,
            "max_tokens": self._config.max_tokens,
            "system": "You are a precise entity extraction assistant. Return only valid JSON.",
            "messages": [{"role": "user", "content": prompt}],
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{base_url}/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama API."""
        import httpx

        base_url = self._config.base_url or "http://localhost:11434"
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": "You are a precise entity extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self._config.temperature,
                "num_predict": self._config.max_tokens,
            },
            "format": "json",
        }

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]

    def _parse_entities(self, raw: str) -> list[ExtractedEntity]:
        """Parse LLM JSON response into ExtractedEntity objects."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            import re
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                logger.warning("Could not parse entity extraction response")
                return []

        if not isinstance(data, list):
            # Handle {"entities": [...]} wrapper
            if isinstance(data, dict) and "entities" in data:
                data = data["entities"]
            else:
                logger.warning("Expected list, got %s", type(data).__name__)
                return []

        valid_types = {
            "person", "organization", "date", "amount", "location",
            "email", "phone", "reference_number", "project_name",
        }

        entities = []
        for item in data:
            if not isinstance(item, dict):
                continue
            etype = item.get("entity_type", "").lower().strip()
            name = item.get("name", "").strip()
            if not etype or not name:
                continue
            if etype not in valid_types:
                # Try to map common variations
                etype_map = {
                    "org": "organization", "person_name": "person",
                    "company": "organization", "date_time": "date",
                    "money": "amount", "location_name": "location",
                    "email_address": "email", "phone_number": "phone",
                    "ref": "reference_number", "project": "project_name",
                }
                etype = etype_map.get(etype, etype)
                if etype not in valid_types:
                    continue

            entities.append(ExtractedEntity(
                entity_type=etype,
                name=name,
                context=item.get("context", "")[:200],
                confidence=item.get("confidence"),
            ))

        return entities
