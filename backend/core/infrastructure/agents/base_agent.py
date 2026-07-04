from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all archive platform agents.

    Each agent encapsulates a specific capability (OCR, classification, search, etc.)
    and exposes a uniform `execute(task)` interface.
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = name or self.__class__.__name__
        self._agent_id = str(uuid4())
        logger.info("Agent initialised: %s (%s)", self.name, self._agent_id)

    @abstractmethod
    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute an agent task.

        Args:
            task: Task payload describing the operation to perform.
                  Must include at least an ``action`` key identifying the sub-operation.

        Returns:
            Dict with operation results. Always contains ``status`` (``"ok"`` | ``"error"``)
            and optionally ``data``, ``error``, ``message``.
        """

    def _ok(self, data: Any = None, message: str = "") -> dict[str, Any]:
        """Build a success response."""
        resp: dict[str, Any] = {"status": "ok", "agent": self.name}
        if data is not None:
            resp["data"] = data
        if message:
            resp["message"] = message
        return resp

    def _error(self, error: str, details: Any = None) -> dict[str, Any]:
        """Build an error response."""
        resp: dict[str, Any] = {"status": "error", "agent": self.name, "error": error}
        if details is not None:
            resp["details"] = details
        return resp

    async def __call__(self, task: dict[str, Any]) -> dict[str, Any]:
        """Allow agents to be called like functions."""
        return await self.execute(task)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r} id={self._agent_id[:8]}>"
