"""Tool definitions for the chat system — OpenAI function-calling format.

Each tool is a dict with structure:
    {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}

The parameters follow JSON Schema format.
"""

from __future__ import annotations

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search the document archive using hybrid search (semantic + keyword). "
                "Returns relevant document snippets with similarity scores."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query text",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5,
                    },
                    "doc_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional filter by document types, e.g. "
                            '["invoice", "contract"]'
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_document_details",
            "description": (
                "Retrieve detailed metadata for a specific document by its ID. "
                "Returns title, type, status, metadata, extracted text, and tags."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The UUID of the document",
                    },
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_agents",
            "description": (
                "List all registered edge agents and their current status "
                "(online/offline/syncing), file counts, and last sync times."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_agent_scan",
            "description": (
                "Send a command to an edge agent to scan a specific folder "
                "for new or modified files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent_id of the target edge agent",
                    },
                    "folder_path": {
                        "type": "string",
                        "description": (
                            "Optional folder path to scan. "
                            "If omitted, scans all configured folders."
                        ),
                    },
                },
                "required": ["agent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_agent_sync",
            "description": (
                "Send a command to an edge agent to sync its pending file "
                "metadata to the platform immediately."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent_id of the target edge agent",
                    },
                },
                "required": ["agent_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_workflow",
            "description": (
                "Trigger execution of a specific workflow by its ID. "
                "The workflow will be queued and run asynchronously."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "The UUID of the workflow to run",
                    },
                },
                "required": ["workflow_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_workflow_list",
            "description": (
                "List all available workflows with their names, descriptions, "
                "step counts, and active status."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_document",
            "description": (
                "Update a document's metadata — change its title, tags, "
                "or classification. Does not move files on disk."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The UUID of the document to update",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title for the document (optional)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New tags list (optional, replaces existing)",
                    },
                    "doc_type": {
                        "type": "string",
                        "description": (
                            "New document type (optional), e.g. "
                            '"invoice", "contract", "report"'
                        ),
                    },
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": (
                "Get AI-powered document recommendations — similar documents, "
                "related files, or suggested actions based on a given document."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "The UUID of the document to get recommendations for",
                    },
                },
                "required": ["document_id"],
            },
        },
    },
]
