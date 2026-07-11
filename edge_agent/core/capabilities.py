from __future__ import annotations

import logging
import platform
import sys
from typing import Any

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] | None = None


def detect_capabilities() -> dict[str, Any]:
    """Detect available providers and system capabilities at startup.

    Result is cached for the lifetime of the process.
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    result: dict[str, Any] = {
        "agent_version": "0.1.0",
        "python_version": sys.version,
        "platform": sys.platform,
        "gpu": False,
        "capabilities": {},
    }

    # GPU
    try:
        import torch
        result["gpu"] = torch.cuda.is_available()
    except ImportError:
        result["gpu"] = False

    # Parser providers
    result["capabilities"]["mineru"] = _module_available("mineru")
    result["capabilities"]["markitdown"] = _module_available("markitdown")

    # OCR providers
    result["capabilities"]["paddleocr"] = _module_available("paddleocr")
    try:
        import subprocess
        subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            check=False,
        )
        result["capabilities"]["tesseract"] = True
    except (FileNotFoundError, OSError):
        result["capabilities"]["tesseract"] = False

    # LLM providers
    result["capabilities"]["openai"] = _module_available("openai")
    result["capabilities"]["anthropic"] = _module_available("anthropic")
    try:
        import ollama  # noqa: F401
        result["capabilities"]["ollama"] = True
    except ImportError:
        result["capabilities"]["ollama"] = False

    # Embedding providers
    result["capabilities"]["embeddings"] = _module_available("sentence_transformers")

    # Platform
    result["capabilities"]["watcher"] = True  # watchdog is always available
    result["capabilities"]["desktop_notifications"] = platform.system() != "Linux" or bool(
        _find_binary("notify-send")
    )

    _CACHE = result
    logger.info("Detected capabilities: %s", result)
    return result


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def _find_binary(name: str) -> str | None:
    import shutil
    return shutil.which(name)
