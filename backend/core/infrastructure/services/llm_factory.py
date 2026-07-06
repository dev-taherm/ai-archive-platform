from __future__ import annotations

import logging
import os
from typing import Any

from core.application.interfaces.services import LLMProvider
from core.domain.ai.value_objects import ModelConfig

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    """OpenAI-compatible LLM provider using the openai SDK."""

    def __init__(
        self,
        config: ModelConfig,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._config = config
        self._api_key = api_key
        self._base_url = base_url
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import openai

            api_key = self._api_key or os.environ.get("OPENAI_API_KEY", "")
            base_url = self._base_url or os.environ.get("OPENAI_BASE_URL")
            self._client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
            )
        except ImportError:
            raise ImportError("openai package is required: pip install openai")
        return self._client

    async def classify(
        self,
        text: str,
        *,
        categories: list[str],
        system_prompt: str | None = None,
    ) -> tuple[str, float]:
        client = self._get_client()
        prompt = system_prompt or "Classify the following text into exactly one category."
        category_list = ", ".join(categories)
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Categories: [{category_list}]\n\nText:\n{text[:4000]}",
            },
        ]
        response = await client.chat.completions.create(
            model=self._config.model_name,
            messages=messages,
            temperature=0.0,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()
        # Parse "category (0.95)" format
        if "(" in raw and raw.endswith(")"):
            category = raw[: raw.rindex("(")].strip()
            confidence_str = raw[raw.rindex("(") + 1 : -1].strip()
            try:
                confidence = float(confidence_str)
            except ValueError:
                confidence = 0.5
        else:
            category = raw
            confidence = 0.5
        return category, confidence

    async def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        prompt = system_prompt or "Extract the following fields from the text as JSON."
        field_list = ", ".join(fields)
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Fields to extract: [{field_list}]\n\nText:\n{text[:6000]}",
            },
        ]
        response = await client.chat.completions.create(
            model=self._config.model_name,
            messages=messages,
            temperature=0.0,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        import json

        return json.loads(response.choices[0].message.content)

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
    ) -> str:
        client = self._get_client()
        messages = [
            {
                "role": "system",
                "content": system_prompt or "Summarize the following text concisely.",
            },
            {"role": "user", "content": text[:8000]},
        ]
        response = await client.chat.completions.create(
            model=self._config.model_name,
            messages=messages,
            temperature=0.3,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        client = self._get_client()
        full_messages: list[dict[str, str]] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        response = await client.chat.completions.create(
            model=self._config.model_name,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()


class GoogleLLMProvider(LLMProvider):
    """Google Gemini / Vertex AI LLM provider."""

    def __init__(
        self,
        config: ModelConfig,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._config = config
        self._api_key = api_key
        self._base_url = base_url
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import google.generativeai as genai

            api_key = self._api_key or os.environ.get("GOOGLE_API_KEY", "")
            genai.configure(api_key=api_key)
            self._client = genai.GenerativeModel(self._config.model_name)
        except ImportError:
            raise ImportError(
                "google-generativeai package is required: pip install google-generativeai"
            )
        return self._client

    async def classify(
        self,
        text: str,
        *,
        categories: list[str],
        system_prompt: str | None = None,
    ) -> tuple[str, float]:
        client = self._get_client()
        prompt = (
            f"{system_prompt or 'Classify the following text.'}\n"
            f"Categories: {', '.join(categories)}\n\n"
            f"Text:\n{text[:4000]}\n\n"
            f"Respond with ONLY: category_name (confidence_score)"
        )
        response = client.generate_content(prompt)
        raw = response.text.strip()
        if "(" in raw and raw.endswith(")"):
            category = raw[: raw.rindex("(")].strip()
            try:
                confidence = float(raw[raw.rindex("(") + 1 : -1].strip())
            except ValueError:
                confidence = 0.5
        else:
            category = raw
            confidence = 0.5
        return category, confidence

    async def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        prompt = (
            f"{system_prompt or 'Extract fields as JSON.'}\n"
            f"Fields: {', '.join(fields)}\n\n"
            f"Text:\n{text[:6000]}"
        )
        response = client.generate_content(prompt)
        import json

        return json.loads(response.text)

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
    ) -> str:
        client = self._get_client()
        prompt = f"{system_prompt or 'Summarize concisely.'}\n\n{text[:8000]}"
        response = client.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        return response.text.strip()

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        client = self._get_client()
        history: list[dict[str, Any]] = []
        if system_prompt:
            history.append({"role": "user", "parts": [system_prompt]})
            history.append({"role": "model", "parts": ["Understood."]})
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})
        chat_session = client.start_chat(history=history)
        last_msg = messages[-1]["content"] if messages else ""
        response = chat_session.send_message(
            last_msg,
            generation_config={"max_output_tokens": max_tokens, "temperature": temperature},
        )
        return response.text.strip()


class OllamaLLMProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(
        self,
        config: ModelConfig,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._config = config
        self._api_key = api_key
        self._base_url = (
            base_url
            or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        )

    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        import aiohttp

        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}{endpoint}", json=payload, headers=headers
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    error_msg = data.get("error", f"HTTP {resp.status}")
                    raise Exception(f"Ollama error ({resp.status}): {error_msg}")
                return data

    async def classify(
        self,
        text: str,
        *,
        categories: list[str],
        system_prompt: str | None = None,
    ) -> tuple[str, float]:
        prompt = (
            f"{system_prompt or 'Classify the following text.'}\n"
            f"Categories: {', '.join(categories)}\n\n"
            f"Text:\n{text[:4000]}\n\n"
            f"Respond with ONLY: category_name (confidence_score)"
        )
        result = await self._post("/api/generate", {
            "model": self._config.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0},
        })
        raw = result.get("response", "").strip()
        if "(" in raw and raw.endswith(")"):
            category = raw[: raw.rindex("(")].strip()
            try:
                confidence = float(raw[raw.rindex("(") + 1 : -1].strip())
            except ValueError:
                confidence = 0.5
        else:
            category = raw
            confidence = 0.5
        return category, confidence

    async def extract(
        self,
        text: str,
        *,
        fields: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        import json

        prompt = (
            f"{system_prompt or 'Extract fields as JSON.'}\n"
            f"Fields: {', '.join(fields)}\n\n"
            f"Text:\n{text[:6000]}\n\n"
            f"Respond with valid JSON only."
        )
        result = await self._post("/api/generate", {
            "model": self._config.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0},
        })
        return json.loads(result.get("response", "{}"))

    async def summarize(
        self,
        text: str,
        *,
        max_tokens: int = 500,
        system_prompt: str | None = None,
    ) -> str:
        result = await self._post("/api/generate", {
            "model": self._config.model_name,
            "prompt": f"{system_prompt or 'Summarize concisely.'}\n\n{text[:8000]}",
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": max_tokens},
        })
        return result.get("response", "").strip()

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        ollama_messages: list[dict[str, str]] = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        ollama_messages.extend(messages)
        result = await self._post("/api/chat", {
            "model": self._config.model_name,
            "messages": ollama_messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        })
        return result.get("message", {}).get("content", "").strip()


class LLMFactory:
    """Factory for creating LLMProvider instances by provider name."""

    _providers: dict[str, type[LLMProvider]] = {
        "openai": OpenAILLMProvider,
        "google": GoogleLLMProvider,
        "ollama": OllamaLLMProvider,
    }

    @classmethod
    def create(cls, provider_name: str, config: ModelConfig, **kwargs) -> LLMProvider:
        """Create an LLMProvider for the given provider name.

        Supported providers: openai, google, ollama.

        Raises:
            ValueError: If the provider is not supported.
        """
        provider_cls = cls._providers.get(provider_name.lower())
        if provider_cls is None:
            supported = ", ".join(sorted(cls._providers.keys()))
            raise ValueError(
                f"Unsupported LLM provider: {provider_name!r}. "
                f"Supported providers: {supported}"
            )
        return provider_cls(config, **kwargs)

    @classmethod
    def register(cls, name: str, provider_cls: type[LLMProvider]) -> None:
        """Register a custom LLM provider."""
        cls._providers[name.lower()] = provider_cls

    @classmethod
    def supported_providers(cls) -> list[str]:
        return sorted(cls._providers.keys())
