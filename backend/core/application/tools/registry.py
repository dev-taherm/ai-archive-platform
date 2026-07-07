from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

# Type alias for tool handler functions
ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


class ToolRegistry:
    """Registry of available tools that the LLM can invoke.

    Maintains a mapping of tool names to their definitions (for the LLM)
    and handler functions (for execution). Tools are registered at import
    time and looked up by name when the LLM requests a tool call.
    """

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(
        self,
        name: str,
        definition: dict[str, Any],
        handler: ToolHandler,
    ) -> None:
        """Register a tool with its OpenAI-format definition and handler.

        Args:
            name: Tool name (must match the function name in the definition).
            definition: OpenAI function-calling format:
                {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
            handler: Async function that executes the tool. Receives the parsed
                arguments dict and returns a dict with at least a "result" key.
        """
        self._tools[name] = definition
        self._handlers[name] = handler
        logger.debug("Registered tool: %s", name)

    def get_definitions(self) -> list[dict[str, Any]]:
        """Return all tool definitions in OpenAI format for the LLM."""
        return list(self._tools.values())

    def get_handler(self, name: str) -> ToolHandler | None:
        """Look up a tool handler by name."""
        return self._handlers.get(name)

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name with the given arguments.

        Returns:
            Dict with "result" key on success, or "error" key on failure.

        Raises:
            KeyError: If the tool name is not registered.
        """
        handler = self._handlers.get(name)
        if handler is None:
            available = ", ".join(sorted(self._tools.keys()))
            return {
                "error": f"Unknown tool: {name!r}. Available tools: {available}"
            }

        try:
            result = await handler(**arguments)
            return result
        except TypeError as e:
            # Handler received unexpected arguments
            logger.warning("Tool %s called with bad arguments: %s", name, e)
            return {"error": f"Invalid arguments for tool {name!r}: {e}"}
        except Exception:
            logger.exception("Tool %s execution failed", name)
            return {"error": f"Tool {name!r} execution failed"}

    @property
    def tool_names(self) -> list[str]:
        """Return sorted list of registered tool names."""
        return sorted(self._tools.keys())


# Singleton registry instance
registry = ToolRegistry()
