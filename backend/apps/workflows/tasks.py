from __future__ import annotations

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


def _handle_ocr_step(step_config: dict, input_data: dict) -> dict:
    """Execute OCR on a file."""
    from core.infrastructure.services.ocr_engine import PaddleOCREngine

    file_path = step_config.get("file_path") or input_data.get("file_path", "")
    if not file_path:
        return {"error": "No file path provided for OCR step"}

    ocr = PaddleOCREngine()

    import asyncio

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        import mimetypes

        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        text = asyncio.run(ocr.extract_text(content, content_type=content_type))
        return {"text": text, "text_length": len(text)}
    except Exception as e:
        return {"error": str(e)}


def _handle_classify_step(step_config: dict, input_data: dict) -> dict:
    """Classify a document using AI."""
    from apps.ai.models import ProviderConfig
    from core.domain.ai.value_objects import AIProvider, ModelConfig
    from core.infrastructure.services.llm_factory import LLMFactory

    text = step_config.get("text") or input_data.get("text", "")
    if not text:
        return {"error": "No text provided for classification step"}

    categories = step_config.get(
        "categories", ["contract", "invoice", "receipt", "report", "letter", "other"]
    )

    try:
        config = (
            ProviderConfig.objects.filter(
                is_active=True, capabilities__contains=["llm"]
            )
            .order_by("-is_default")
            .first()
        )

        if not config:
            return {"error": "No LLM provider configured"}

        model_config = ModelConfig(
            provider=AIProvider(config.provider_type), model_name=config.model_name
        )
        llm = LLMFactory.create(
            config.provider_type,
            model_config,
            api_key=config.api_key or None,
            base_url=config.base_url or None,
        )

        import asyncio

        category, confidence = asyncio.run(
            llm.classify(text[:4000], categories=categories)
        )
        return {"category": category, "confidence": confidence}
    except Exception as e:
        return {"error": str(e)}


def _handle_summarize_step(step_config: dict, input_data: dict) -> dict:
    """Summarize a document using AI."""
    from apps.ai.models import ProviderConfig
    from core.domain.ai.value_objects import AIProvider, ModelConfig
    from core.infrastructure.services.llm_factory import LLMFactory

    text = step_config.get("text") or input_data.get("text", "")
    if not text:
        return {"error": "No text provided for summarization step"}

    try:
        config = (
            ProviderConfig.objects.filter(
                is_active=True, capabilities__contains=["llm"]
            )
            .order_by("-is_default")
            .first()
        )

        if not config:
            return {"error": "No LLM provider configured"}

        model_config = ModelConfig(
            provider=AIProvider(config.provider_type), model_name=config.model_name
        )
        llm = LLMFactory.create(
            config.provider_type,
            model_config,
            api_key=config.api_key or None,
            base_url=config.base_url or None,
        )

        import asyncio

        summary = asyncio.run(
            llm.summarize(text[:8000], max_tokens=step_config.get("max_tokens", 500))
        )
        return {"summary": summary}
    except Exception as e:
        return {"error": str(e)}


def _handle_embed_step(step_config: dict, input_data: dict) -> dict:
    """Generate embeddings for text chunks."""
    from apps.ai.models import ProviderConfig
    from core.infrastructure.services.embedding_service import (
        LangChainEmbeddingProvider,
    )

    text = step_config.get("text") or input_data.get("text", "")
    if not text:
        return {"error": "No text provided for embedding step"}

    try:
        config = (
            ProviderConfig.objects.filter(
                is_active=True, capabilities__contains=["embedding"]
            )
            .order_by("-is_default")
            .first()
        )

        if not config:
            return {"error": "No embedding provider configured"}

        provider = LangChainEmbeddingProvider(
            model_name=config.model_name,
            provider=config.provider_type,
            api_key=config.api_key or None,
        )

        embedding = provider.embed_text(text[:8000])
        return {
            "dimension": len(embedding),
            "embedding_id": f"step_embed_{uuid.uuid4().hex[:8]}",
        }
    except Exception as e:
        return {"error": str(e)}


def _handle_extract_step(step_config: dict, input_data: dict) -> dict:
    """Extract structured data from text using AI."""
    from apps.ai.models import ProviderConfig
    from core.domain.ai.value_objects import AIProvider, ModelConfig
    from core.infrastructure.services.llm_factory import LLMFactory

    text = step_config.get("text") or input_data.get("text", "")
    fields = step_config.get("fields", [])
    if not text:
        return {"error": "No text provided for extraction step"}

    try:
        config = (
            ProviderConfig.objects.filter(
                is_active=True, capabilities__contains=["llm"]
            )
            .order_by("-is_default")
            .first()
        )

        if not config:
            return {"error": "No LLM provider configured"}

        model_config = ModelConfig(
            provider=AIProvider(config.provider_type), model_name=config.model_name
        )
        llm = LLMFactory.create(
            config.provider_type,
            model_config,
            api_key=config.api_key or None,
            base_url=config.base_url or None,
        )

        import asyncio

        extracted = asyncio.run(llm.extract(text[:6000], fields=fields))
        return {"extracted_data": extracted}
    except Exception as e:
        return {"error": str(e)}


STEP_HANDLERS = {
    "ocr": _handle_ocr_step,
    "classify": _handle_classify_step,
    "summarize": _handle_summarize_step,
    "embed": _handle_embed_step,
    "extract": _handle_extract_step,
}


@shared_task(name="workflows.execute_workflow_step")
def execute_workflow_step(
    run_id: str,
    step_index: int,
) -> dict[str, object]:
    """Execute a single step of a workflow run."""
    from core.infrastructure.pipelines.workflow_engine import WorkflowEngine

    engine = WorkflowEngine()
    result = engine.execute_step(run_id, step_index)

    return {
        "step_index": result.step_index,
        "step_type": result.step_type,
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "elapsed_ms": result.elapsed_ms,
    }


@shared_task(name="workflows.execute_full_workflow")
def execute_full_workflow(
    workflow_id: str,
    input_data: dict | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    """Execute all steps of a workflow sequentially using the WorkflowEngine."""
    from core.infrastructure.pipelines.workflow_engine import WorkflowEngine

    engine = WorkflowEngine()
    result = engine.execute(
        workflow_id,
        input_data=input_data or {},
        user_id=user_id,
    )

    return {
        "run_id": result.run_id,
        "workflow_id": result.workflow_id,
        "status": result.status,
        "total_steps": result.total_steps,
        "completed_steps": result.completed_steps,
        "failed_step_index": result.failed_step_index,
        "error": result.error,
        "elapsed_ms": result.elapsed_ms,
        "output_data": result.output_data,
    }


@shared_task(name="workflows.execute_workflow_task")
def execute_workflow_task(
    workflow_id: str,
    input_data: dict | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    """Execute a workflow via Celery task.

    This is the primary entry point for async workflow execution.
    Creates the run, executes all steps, and returns results.
    """
    from core.infrastructure.pipelines.workflow_engine import WorkflowEngine

    engine = WorkflowEngine()
    result = engine.execute(
        workflow_id,
        input_data=input_data or {},
        user_id=user_id,
    )

    logger.info(
        "Workflow task completed: run=%s status=%s steps=%d/%d",
        result.run_id,
        result.status,
        result.completed_steps,
        result.total_steps,
    )

    return {
        "run_id": result.run_id,
        "workflow_id": result.workflow_id,
        "status": result.status,
        "total_steps": result.total_steps,
        "completed_steps": result.completed_steps,
        "failed_step_index": result.failed_step_index,
        "error": result.error,
        "elapsed_ms": result.elapsed_ms,
        "output_data": result.output_data,
    }


@shared_task(name="workflows.cancel_workflow_run")
def cancel_workflow_run(run_id: str) -> dict[str, object]:
    """Cancel a running workflow."""
    from apps.workflows.models import WorkflowRun
    from apps.workflows.services import WorkflowService

    try:
        run = WorkflowRun.objects.get(pk=uuid.UUID(run_id))
    except WorkflowRun.DoesNotExist:
        return {"error": "Run not found"}

    if run.status not in (WorkflowRun.Status.PENDING, WorkflowRun.Status.RUNNING):
        return {"error": f"Cannot cancel run in '{run.status}' status"}

    WorkflowService.fail_run(run.id, "Cancelled by user")
    logger.info("Workflow run cancelled: %s", run_id)
    return {"run_id": run_id, "status": "cancelled"}


@shared_task(name="workflows.get_workflow_run_status")
def get_workflow_run_status(run_id: str) -> dict[str, object]:
    """Get the current status and progress of a workflow run."""
    from apps.workflows.models import WorkflowRun

    try:
        run = WorkflowRun.objects.select_related("workflow").get(
            pk=uuid.UUID(run_id)
        )
    except WorkflowRun.DoesNotExist:
        return {"error": "Run not found"}

    progress = 0.0
    if run.total_steps > 0:
        progress = (run.current_step / run.total_steps) * 100

    return {
        "run_id": str(run.id),
        "workflow_name": run.workflow.name,
        "status": run.status,
        "current_step": run.current_step,
        "total_steps": run.total_steps,
        "progress_percent": round(progress, 1),
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
