from __future__ import annotations

from core.application.tools.definitions import TOOL_DEFINITIONS
from core.application.tools.handlers import (
    handle_get_document_details,
    handle_get_recommendations,
    handle_get_workflow_list,
    handle_list_agents,
    handle_move_document,
    handle_run_workflow,
    handle_search_documents,
    handle_trigger_agent_scan,
    handle_trigger_agent_sync,
)
from core.application.tools.registry import ToolRegistry, registry

# Register all tools at import time
_TOOL_HANDLERS = {
    "search_documents": handle_search_documents,
    "get_document_details": handle_get_document_details,
    "list_agents": handle_list_agents,
    "trigger_agent_scan": handle_trigger_agent_scan,
    "trigger_agent_sync": handle_trigger_agent_sync,
    "run_workflow": handle_run_workflow,
    "get_workflow_list": handle_get_workflow_list,
    "move_document": handle_move_document,
    "get_recommendations": handle_get_recommendations,
}

for tool_def in TOOL_DEFINITIONS:
    name = tool_def["function"]["name"]
    handler = _TOOL_HANDLERS.get(name)
    if handler:
        registry.register(name, tool_def, handler)

__all__ = ["TOOL_DEFINITIONS", "ToolRegistry", "registry"]
