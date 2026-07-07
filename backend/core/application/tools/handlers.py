"""Tool handler implementations — async functions that execute each tool.

Each handler receives keyword arguments matching the tool's JSON Schema
parameters and returns a dict with a "result" key containing the response
text or data that gets sent back to the LLM.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def handle_search_documents(
    query: str,
    max_results: int = 5,
    doc_types: list[str] | None = None,
) -> dict[str, Any]:
    """Search the document archive using hybrid search."""
    try:
        from core.infrastructure.services.hybrid_search import HybridSearchService
        from core.infrastructure.services.vector_store import VectorStore
        from core.infrastructure.services.embedding_service import EmbeddingService

        search = HybridSearchService(
            vector_store=VectorStore(),
            embedding_service=EmbeddingService(),
        )

        results = search.search(
            query,
            top_k=max_results,
            threshold=0.3,
        )

        if not results:
            return {"result": f"No documents found for query: {query!r}"}

        snippets = []
        for i, r in enumerate(results, 1):
            snippet = r.text[:300].replace("\n", " ")
            snippets.append(f"{i}. {snippet}...")

        return {
            "result": (
                f"Found {len(results)} documents for query: {query!r}\n\n"
                + "\n\n".join(snippets)
            )
        }
    except Exception as e:
        logger.exception("search_documents failed")
        return {"result": f"Search failed: {e}"}


async def handle_get_document_details(document_id: str) -> dict[str, Any]:
    """Retrieve detailed metadata for a specific document."""
    try:
        import uuid
        from apps.documents.models import Document

        doc = Document.objects.get(id=uuid.UUID(document_id))
        details = {
            "title": doc.title or "Untitled",
            "type": doc.doc_type,
            "status": doc.processing_status,
            "language": doc.language,
            "word_count": doc.word_count,
            "page_count": doc.page_count,
            "tags": doc.tags,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "extracted_text_preview": (doc.extracted_text or "")[:500],
        }
        return {"result": f"Document details:\n{details}"}
    except Exception as e:
        return {"result": f"Could not retrieve document {document_id}: {e}"}


async def handle_list_agents() -> dict[str, Any]:
    """List all registered edge agents."""
    try:
        from apps.agents.models import Agent

        agents = Agent.objects.all()
        if not agents:
            return {"result": "No agents registered."}

        lines = []
        for agent in agents:
            lines.append(
                f"- {agent.name} ({agent.agent_id}): status={agent.status}, "
                f"files={agent.files_count}, last_sync={agent.last_sync_at or 'never'}"
            )
        return {"result": f"Registered agents:\n" + "\n".join(lines)}
    except Exception as e:
        return {"result": f"Failed to list agents: {e}"}


async def handle_trigger_agent_scan(
    agent_id: str,
    folder_path: str | None = None,
) -> dict[str, Any]:
    """Send a scan command to an edge agent."""
    try:
        from apps.agents.models import Agent, AgentCommand

        agent = Agent.objects.get(agent_id=agent_id)
        payload: dict[str, Any] = {}
        if folder_path:
            payload["folder_path"] = folder_path

        cmd = AgentCommand.objects.create(
            agent=agent,
            command_type=AgentCommand.CommandType.SCAN,
            payload=payload,
        )
        return {
            "result": (
                f"Scan command sent to agent '{agent.name}'. "
                f"Command ID: {cmd.id}. The agent will pick it up on next heartbeat."
            )
        }
    except Exception as e:
        return {"result": f"Failed to send scan command to agent {agent_id}: {e}"}


async def handle_trigger_agent_sync(agent_id: str) -> dict[str, Any]:
    """Send a sync command to an edge agent."""
    try:
        from apps.agents.models import Agent, AgentCommand

        agent = Agent.objects.get(agent_id=agent_id)
        cmd = AgentCommand.objects.create(
            agent=agent,
            command_type=AgentCommand.CommandType.SYNC,
            payload={},
        )
        return {
            "result": (
                f"Sync command sent to agent '{agent.name}'. "
                f"Command ID: {cmd.id}. The agent will pick it up on next heartbeat."
            )
        }
    except Exception as e:
        return {"result": f"Failed to send sync command to agent {agent_id}: {e}"}


async def handle_run_workflow(workflow_id: str) -> dict[str, Any]:
    """Trigger execution of a workflow."""
    try:
        import uuid
        from apps.workflows.models import Workflow, WorkflowRun

        workflow = Workflow.objects.get(id=uuid.UUID(workflow_id))
        if not workflow.is_active:
            return {"result": f"Workflow '{workflow.name}' is not active."}

        run = WorkflowRun.objects.create(
            workflow=workflow,
            status=WorkflowRun.Status.PENDING,
            input_data={},
        )

        # Dispatch via Celery if available
        try:
            from apps.workflows.tasks import execute_full_workflow
            execute_full_workflow.delay(str(run.id))
        except Exception:
            logger.debug("Celery not available, workflow queued without dispatch")

        return {
            "result": (
                f"Workflow '{workflow.name}' triggered. Run ID: {run.id}"
            )
        }
    except Exception as e:
        return {"result": f"Failed to run workflow {workflow_id}: {e}"}


async def handle_get_workflow_list() -> dict[str, Any]:
    """List all available workflows."""
    try:
        from apps.workflows.models import Workflow

        workflows = Workflow.objects.all()
        if not workflows:
            return {"result": "No workflows configured."}

        lines = []
        for wf in workflows:
            step_count = len(wf.steps) if isinstance(wf.steps, list) else 0
            lines.append(
                f"- {wf.name} (ID: {wf.id}): "
                f"steps={step_count}, active={wf.is_active}, "
                f"trigger={wf.trigger_type}"
            )
        return {"result": f"Available workflows:\n" + "\n".join(lines)}
    except Exception as e:
        return {"result": f"Failed to list workflows: {e}"}


async def handle_move_document(
    document_id: str,
    title: str | None = None,
    tags: list[str] | None = None,
    doc_type: str | None = None,
) -> dict[str, Any]:
    """Update a document's metadata."""
    try:
        import uuid
        from apps.documents.models import Document

        doc = Document.objects.get(id=uuid.UUID(document_id))
        updates = []
        if title is not None:
            doc.title = title
            updates.append(f"title={title!r}")
        if tags is not None:
            doc.tags = tags
            updates.append(f"tags={tags}")
        if doc_type is not None:
            valid_types = [c[0] for c in Document.DocType.choices]
            if doc_type in valid_types:
                doc.doc_type = doc_type
                updates.append(f"type={doc_type!r}")
            else:
                return {
                    "result": (
                        f"Invalid doc_type: {doc_type!r}. "
                        f"Valid types: {valid_types}"
                    )
                }

        if not updates:
            return {"result": "No changes specified."}

        doc.save()
        return {"result": f"Document updated: {', '.join(updates)}"}
    except Exception as e:
        return {"result": f"Failed to update document {document_id}: {e}"}


async def handle_get_recommendations(document_id: str) -> dict[str, Any]:
    """Get recommendations for a document based on its content."""
    try:
        import uuid
        from apps.documents.models import Document
        from core.infrastructure.services.hybrid_search import HybridSearchService
        from core.infrastructure.services.vector_store import VectorStore
        from core.infrastructure.services.embedding_service import EmbeddingService

        doc = Document.objects.get(id=uuid.UUID(document_id))
        if not doc.extracted_text:
            return {
                "result": (
                    f"Document '{doc.title}' has no extracted text, "
                    "cannot generate recommendations."
                )
            }

        # Use first 200 chars as query to find similar documents
        query = doc.extracted_text[:200]
        search = HybridSearchService(
            vector_store=VectorStore(),
            embedding_service=EmbeddingService(),
        )
        results = search.search(query, top_k=5, threshold=0.3)

        # Filter out the source document itself
        similar = [
            r for r in results
            if str(getattr(r, "document_id", "")) != document_id
        ]

        if not similar:
            return {"result": "No similar documents found."}

        lines = []
        for i, r in enumerate(similar[:5], 1):
            snippet = r.text[:200].replace("\n", " ")
            lines.append(f"{i}. {snippet}...")
        return {
            "result": (
                f"Documents similar to '{doc.title}':\n"
                + "\n\n".join(lines)
            )
        }
    except Exception as e:
        return {"result": f"Failed to get recommendations: {e}"}
