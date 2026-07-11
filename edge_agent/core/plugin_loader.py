from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from edge_agent.core.providers.base import (
        EmbeddingProvider,
        LLMProvider,
        OCRProvider,
        ParserProvider,
    )

logger = logging.getLogger(__name__)


class PluginRegistry:
    def __init__(self) -> None:
        self._parsers: dict[str, type[ParserProvider]] = {}
        self._ocr: dict[str, type[OCRProvider]] = {}
        self._llm: dict[str, type[LLMProvider]] = {}
        self._embeddings: dict[str, type[EmbeddingProvider]] = {}

    @property
    def parsers(self) -> dict[str, type[ParserProvider]]:
        return dict(self._parsers)

    @property
    def ocr_providers(self) -> dict[str, type[OCRProvider]]:
        return dict(self._ocr)

    @property
    def llm_providers(self) -> dict[str, type[LLMProvider]]:
        return dict(self._llm)

    @property
    def embedding_providers(self) -> dict[str, type[EmbeddingProvider]]:
        return dict(self._embeddings)

    def discover_plugins(self, plugin_dir: str | Path) -> None:
        path = Path(plugin_dir).expanduser()
        if not path.is_dir():
            logger.info("Plugin directory %s does not exist, skipping", path)
            return

        for entry in sorted(path.iterdir()):
            if entry.name.startswith(".") or entry.name.startswith("_"):
                continue
            if entry.suffix == ".py":
                self._load_module(str(entry), entry.stem)
            elif entry.is_dir() and (entry / "__init__.py").exists():
                self._load_module(str(entry / "__init__.py"), entry.name)

    def _load_module(self, filepath: str, module_name: str) -> None:
        try:
            spec = importlib.util.spec_from_file_location(
                f"edge_agent_plugins.{module_name}", filepath
            )
            if not spec or not spec.loader:
                logger.warning("Could not load plugin %s", filepath)
                return
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            self._scan_module(mod)
        except Exception:
            logger.exception("Failed to load plugin %s", filepath)

    def _scan_module(self, mod: object) -> None:
        from edge_agent.core.providers.base import (
            EmbeddingProvider,
            LLMProvider,
            OCRProvider,
            ParserProvider,
        )

        for name in dir(mod):
            cls = getattr(mod, name)
            if not isinstance(cls, type):
                continue
            provider_name = getattr(cls, "provider_name", None) or cls.__name__.lower()
            if issubclass(cls, ParserProvider) and cls is not ParserProvider:
                self._parsers[provider_name] = cls
                logger.info("Registered parser plugin: %s", provider_name)
            if issubclass(cls, OCRProvider) and cls is not OCRProvider:
                self._ocr[provider_name] = cls
                logger.info("Registered OCR plugin: %s", provider_name)
            if issubclass(cls, LLMProvider) and cls is not LLMProvider:
                self._llm[provider_name] = cls
                logger.info("Registered LLM plugin: %s", provider_name)
            if issubclass(cls, EmbeddingProvider) and cls is not EmbeddingProvider:
                self._embeddings[provider_name] = cls
                logger.info("Registered embedding plugin: %s", provider_name)

    def list_capabilities(self) -> dict[str, list[str]]:
        return {
            "parsers": list(self._parsers),
            "ocr": list(self._ocr),
            "llm": list(self._llm),
            "embeddings": list(self._embeddings),
        }
