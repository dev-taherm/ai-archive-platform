from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_STEP_TYPES = frozenset({
    "scan",
    "ocr",
    "extract_metadata",
    "classify",
    "summarize",
    "embed",
    "index",
    "notify",
    "store",
})


@dataclass
class StepResult:
    """Result of executing a single workflow step."""

    step_index: int
    step_type: str
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    elapsed_ms: float = 0.0


@dataclass
class WorkflowResult:
    """Comprehensive result of a full workflow execution."""

    run_id: str
    workflow_id: str
    status: str
    total_steps: int
    completed_steps: int
    failed_step_index: int | None = None
    step_results: list[StepResult] = field(default_factory=list)
    output_data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    elapsed_ms: float = 0.0


class StepExecutorRegistry:
    """Registry of step type handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {}

    def register(self, step_type: str, handler: Any) -> None:
        self._handlers[step_type] = handler

    def get(self, step_type: str) -> Any | None:
        return self._handlers.get(step_type)

    def supported_types(self) -> set[str]:
        return set(self._handlers.keys())


def _handle_scan_step(config: dict, context: dict) -> dict:
    """Scan a folder or file path for processing."""
    from core.infrastructure.services.file_scanner import FileScannerService

    scan_path = config.get("path") or context.get("file_path", "")
    if not scan_path:
        return {"error": "No path provided for scan step"}

    recursive = config.get("recursive", True)
    patterns = config.get("patterns")
    ignore_patterns = config.get("ignore_patterns")

    try:
        scanner = FileScannerService()
        files = list(scanner.scan_folder(
            scan_path,
            recursive=recursive,
            patterns=patterns,
            ignore_patterns=ignore_patterns,
        ))
        return {
            "scanned_path": scan_path,
            "files_found": len(files),
            "files": files[:100],
        }
    except Exception as e:
        return {"error": f"Scan failed: {e}"}


def _handle_ocr_step(config: dict, context: dict) -> dict:
    """Execute OCR on a file."""
    from core.infrastructure.services.ocr_engine import PaddleOCREngine

    file_path = config.get("file_path") or context.get("file_path", "")
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


def _handle_extract_metadata_step(config: dict, context: dict) -> dict:
    """Extract metadata from text or file using AI."""
    from apps.ai.models import ProviderConfig
    from core.domain.ai.value_objects import AIProvider, ModelConfig
    from core.infrastructure.services.llm_factory import LLMFactory

    text = config.get("text") or context.get("text", "")
    fields = config.get("fields", [
        "title", "author", "date", "subject", "keywords",
        "language", "word_count", "page_count",
    ])

    if not text:
        return {"error": "No text provided for metadata extraction step"}

    try:
        config_obj = (
            ProviderConfig.objects.filter(
                is_active=True, capabilities__contains=["llm"]
            )
            .order_by("-is_default")
            .first()
        )

        if not config_obj:
            return {"error": "No LLM provider configured"}

        model_config = ModelConfig(
            provider=AIProvider(config_obj.provider_type),
            model_name=config_obj.model_name,
        )
        llm = LLMFactory.create(
            config_obj.provider_type,
            model_config,
            api_key=config_obj.api_key or None,
            base_url=config_obj.base_url or None,
        )

        import asyncio

        extracted = asyncio.run(llm.extract(text[:6000], fields=fields))
        return {"metadata": extracted, "fields_extracted": fields}
    except Exception as e:
        return {"error": str(e)}


def _handle_classify_step(config: dict, context: dict) -> dict:
    """Classify a document using AI."""
    from apps.ai.models import ProviderConfig
    from core.domain.ai.value_objects import AIProvider, ModelConfig
    from core.infrastructure.services.llm_factory import LLMFactory

    text = config.get("text") or context.get("text", "")
    if not text:
        return {"error": "No text provided for classification step"}

    categories = config.get(
        "categories", ["contract", "invoice", "receipt", "report", "letter", "other"]
    )

    try:
        config_obj = (
            ProviderConfig.objects.filter(
                is_active=True, capabilities__contains=["llm"]
            )
            .order_by("-is_default")
            .first()
        )

        if not config_obj:
            return {"error": "No LLM provider configured"}

        model_config = ModelConfig(
            provider=AIProvider(config_obj.provider_type),
            model_name=config_obj.model_name,
        )
        llm = LLMFactory.create(
            config_obj.provider_type,
            model_config,
            api_key=config_obj.api_key or None,
            base_url=config_obj.base_url or None,
        )

        import asyncio

        category, confidence = asyncio.run(
            llm.classify(text[:4000], categories=categories)
        )
        return {"category": category, "confidence": confidence}
    except Exception as e:
        return {"error": str(e)}


def _handle_summarize_step(config: dict, context: dict) -> dict:
    """Summarize a document using AI."""
    from apps.ai.models import ProviderConfig
    from core.domain.ai.value_objects import AIProvider, ModelConfig
    from core.infrastructure.services.llm_factory import LLMFactory

    text = config.get("text") or context.get("text", "")
    if not text:
        return {"error": "No text provided for summarization step"}

    try:
        config_obj = (
            ProviderConfig.objects.filter(
                is_active=True, capabilities__contains=["llm"]
            )
            .order_by("-is_default")
            .first()
        )

        if not config_obj:
            return {"error": "No LLM provider configured"}

        model_config = ModelConfig(
            provider=AIProvider(config_obj.provider_type),
            model_name=config_obj.model_name,
        )
        llm = LLMFactory.create(
            config_obj.provider_type,
            model_config,
            api_key=config_obj.api_key or None,
            base_url=config_obj.base_url or None,
        )

        import asyncio

        summary = asyncio.run(
            llm.summarize(text[:8000], max_tokens=config.get("max_tokens", 500))
        )
        return {"summary": summary}
    except Exception as e:
        return {"error": str(e)}


def _handle_embed_step(config: dict, context: dict) -> dict:
    """Generate embeddings for text chunks."""
    from apps.ai.models import ProviderConfig
    from core.infrastructure.services.embedding_service import (
        LangChainEmbeddingProvider,
    )

    text = config.get("text") or context.get("text", "")
    if not text:
        return {"error": "No text provided for embedding step"}

    try:
        config_obj = (
            ProviderConfig.objects.filter(
                is_active=True, capabilities__contains=["embedding"]
            )
            .order_by("-is_default")
            .first()
        )

        if not config_obj:
            return {"error": "No embedding provider configured"}

        provider = LangChainEmbeddingProvider(
            model_name=config_obj.model_name,
            provider=config_obj.provider_type,
            api_key=config_obj.api_key or None,
        )

        embedding = provider.embed_text(text[:8000])
        return {
            "dimension": len(embedding),
            "embedding_id": f"embed_{uuid.uuid4().hex[:8]}",
        }
    except Exception as e:
        return {"error": str(e)}


def _handle_index_step(config: dict, context: dict) -> dict:
    """Index a document into the vector store."""
    try:
        from core.infrastructure.services.vector_store import VectorStore

        document_id = config.get("document_id") or context.get("document_id", "")
        text = config.get("text") or context.get("text", "")
        embedding = config.get("embedding") or context.get("embedding")

        if not text:
            return {"error": "No text provided for index step"}

        vector_store = VectorStore()

        if not document_id:
            document_id = f"doc_{uuid.uuid4().hex[:12]}"

        if not embedding:
            from apps.ai.models import ProviderConfig
            from core.infrastructure.services.embedding_service import (
                LangChainEmbeddingProvider,
            )

            config_obj = (
                ProviderConfig.objects.filter(
                    is_active=True, capabilities__contains=["embedding"]
                )
                .order_by("-is_default")
                .first()
            )

            if config_obj:
                provider = LangChainEmbeddingProvider(
                    model_name=config_obj.model_name,
                    provider=config_obj.provider_type,
                    api_key=config_obj.api_key or None,
                )
                embedding = provider.embed_text(text[:8000])

        if embedding:
            vector_store.add(
                entry_id=document_id,
                text=text[:10000],
                embedding=embedding,
                metadata={
                    "source": "workflow_engine",
                    "indexed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            vector_store._save()

        return {
            "document_id": document_id,
            "indexed": True,
            "text_length": len(text),
        }
    except Exception as e:
        return {"error": str(e)}


def _handle_notify_step(config: dict, context: dict) -> dict:
    """Send a notification (email, webhook, or system)."""
    message = config.get("message", "Workflow step completed")
    notify_type = config.get("type", "system")
    recipients = config.get("recipients", [])
    webhook_url = config.get("webhook_url", "")

    try:
        from django.core.mail import send_mail

        if notify_type == "email" and recipients:
            subject = config.get("subject", "Workflow Notification")
            send_mail(
                subject,
                message,
                None,
                recipients,
                fail_silently=True,
            )
            return {
                "notification_sent": True,
                "type": "email",
                "recipients": recipients,
            }

        if notify_type == "webhook" and webhook_url:
            import json
            import urllib.request

            payload = json.dumps({
                "message": message,
                "context": context,
            }).encode("utf-8")

            req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)

            return {
                "notification_sent": True,
                "type": "webhook",
                "url": webhook_url,
            }

        logger.info("System notification: %s", message)
        return {
            "notification_sent": True,
            "type": "system",
            "message": message,
        }
    except Exception as e:
        return {"error": str(e)}


def _handle_store_step(config: dict, context: dict) -> dict:
    """Store processed data or results to storage."""
    storage_path = config.get("path", "")
    data = config.get("data") or context.get("output_data", {})
    storage_type = config.get("storage_type", "local")

    if not storage_path:
        storage_path = f"workflow_results/{uuid.uuid4().hex[:12]}"

    try:
        import json

        if storage_type == "local":
            from core.infrastructure.storage.local import LocalStorage

            storage = LocalStorage(root_dir=config.get("root_dir", "/tmp/archive-storage"))
            content = json.dumps(data, default=str).encode("utf-8")
            stored_path = storage.save(
                content,
                storage_path,
                content_type="application/json",
            )
            return {
                "stored": True,
                "path": stored_path,
                "storage_type": "local",
                "size_bytes": len(content),
            }

        return {
            "stored": False,
            "error": f"Unsupported storage type: {storage_type}",
        }
    except Exception as e:
        return {"error": str(e)}


STEP_HANDLERS: dict[str, Any] = {
    "scan": _handle_scan_step,
    "ocr": _handle_ocr_step,
    "extract_metadata": _handle_extract_metadata_step,
    "classify": _handle_classify_step,
    "summarize": _handle_summarize_step,
    "embed": _handle_embed_step,
    "index": _handle_index_step,
    "notify": _handle_notify_step,
    "store": _handle_store_step,
}


class WorkflowEngine:
    """Orchestrates step-by-step execution of workflow definitions.

    Loads a workflow from the database, creates a WorkflowRun record,
    executes each step sequentially, and tracks progress/status throughout.
    """

    def __init__(self) -> None:
        self._registry = StepExecutorRegistry()
        for step_type, handler in STEP_HANDLERS.items():
            self._registry.register(step_type, handler)

    def register_step_handler(self, step_type: str, handler: Any) -> None:
        """Register a custom step handler."""
        self._registry.register(step_type, handler)

    def execute(
        self,
        workflow_id: str,
        *,
        input_data: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> WorkflowResult:
        """Execute a full workflow from start to finish.

        Args:
            workflow_id: UUID string of the workflow to execute.
            input_data: Optional input data for the workflow run.
            user_id: Optional UUID string of the user triggering the run.

        Returns:
            WorkflowResult with comprehensive execution details.
        """
        from apps.workflows.models import Workflow
        from apps.workflows.services import WorkflowService

        t0 = time.time()
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()

        try:
            workflow = Workflow.objects.get(pk=uuid.UUID(workflow_id))
        except Workflow.DoesNotExist:
            return WorkflowResult(
                run_id=run_id,
                workflow_id=workflow_id,
                status="failed",
                total_steps=0,
                completed_steps=0,
                error=f"Workflow not found: {workflow_id}",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        steps = workflow.steps
        total_steps = len(steps)

        if total_steps == 0:
            return WorkflowResult(
                run_id=run_id,
                workflow_id=workflow_id,
                status="completed",
                total_steps=0,
                completed_steps=0,
                output_data={},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        run = WorkflowService.start_run(
            uuid.UUID(workflow_id),
            input_data=input_data or {},
            triggered_by_id=uuid.UUID(user_id) if user_id else None,
        )

        if run is None:
            return WorkflowResult(
                run_id=run_id,
                workflow_id=workflow_id,
                status="failed",
                total_steps=total_steps,
                completed_steps=0,
                error="Failed to create workflow run (workflow may be inactive)",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                elapsed_ms=(time.time() - t0) * 1000,
            )

        actual_run_id = str(run.id)

        logger.info(
            "Workflow engine started: workflow=%s run=%s steps=%d",
            workflow.name, actual_run_id, total_steps,
        )

        context: dict[str, Any] = dict(input_data) if input_data else {}
        step_results: list[StepResult] = []
        completed_steps = 0

        for i, step in enumerate(steps):
            step_type = step.get("type", "unknown")
            step_config = step.get("config", {})
            step_name = step.get("name", f"step_{i}")

            logger.info(
                "Executing step %d/%d (%s): %s",
                i + 1, total_steps, step_type, step_name,
            )

            step_start = time.time()

            try:
                run.current_step = i
                run.save(update_fields=["current_step"])
            except Exception:
                logger.warning("Failed to update current_step for run %s", actual_run_id)

            handler = self._registry.get(step_type)
            if handler is None:
                result = StepResult(
                    step_index=i,
                    step_type=step_type,
                    success=False,
                    error=f"Unknown step type: {step_type}",
                    elapsed_ms=(time.time() - step_start) * 1000,
                )
                step_results.append(result)

                self._fail_run(actual_run_id, f"Step {i} failed: unknown type '{step_type}'")

                return WorkflowResult(
                    run_id=actual_run_id,
                    workflow_id=workflow_id,
                    status="failed",
                    total_steps=total_steps,
                    completed_steps=completed_steps,
                    failed_step_index=i,
                    step_results=step_results,
                    error=f"Unknown step type: {step_type}",
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    elapsed_ms=(time.time() - t0) * 1000,
                )

            try:
                output = handler(step_config, context)
            except Exception as e:
                logger.exception(
                    "Step %d (%s) raised exception: %s", i, step_type, e,
                )
                output = {"error": str(e)}

            step_elapsed = (time.time() - step_start) * 1000
            has_error = isinstance(output, dict) and "error" in output

            step_result = StepResult(
                step_index=i,
                step_type=step_type,
                success=not has_error,
                output=output if not has_error else {},
                error=output.get("error") if has_error else None,
                elapsed_ms=step_elapsed,
            )
            step_results.append(step_result)

            if has_error:
                error_msg = output["error"]
                logger.warning(
                    "Step %d (%s) failed: %s", i, step_type, error_msg,
                )

                self._save_step_output(actual_run_id, i, step_type, output)
                self._fail_run(actual_run_id, f"Step {i} ({step_type}) failed: {error_msg}")

                return WorkflowResult(
                    run_id=actual_run_id,
                    workflow_id=workflow_id,
                    status="failed",
                    total_steps=total_steps,
                    completed_steps=completed_steps,
                    failed_step_index=i,
                    step_results=step_results,
                    error=error_msg,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    elapsed_ms=(time.time() - t0) * 1000,
                )

            completed_steps += 1
            context.update(output)

            self._save_step_output(actual_run_id, i, step_type, output)

            logger.info(
                "Step %d/%d (%s) completed in %.0fms",
                i + 1, total_steps, step_type, step_elapsed,
            )

        WorkflowService.complete_run(
            run.id,
            output_data=context,
        )

        elapsed_ms = (time.time() - t0) * 1000
        completed_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Workflow engine completed: run=%s steps=%d elapsed=%.0fms",
            actual_run_id, total_steps, elapsed_ms,
        )

        return WorkflowResult(
            run_id=actual_run_id,
            workflow_id=workflow_id,
            status="completed",
            total_steps=total_steps,
            completed_steps=completed_steps,
            step_results=step_results,
            output_data=context,
            started_at=started_at,
            completed_at=completed_at,
            elapsed_ms=elapsed_ms,
        )

    def execute_step(
        self,
        run_id: str,
        step_index: int,
    ) -> StepResult:
        """Execute a single step of an existing workflow run.

        Args:
            run_id: UUID string of the workflow run.
            step_index: Zero-based index of the step to execute.

        Returns:
            StepResult for the executed step.
        """
        from apps.workflows.models import WorkflowRun

        try:
            run = WorkflowRun.objects.select_related("workflow").get(
                pk=uuid.UUID(run_id)
            )
        except WorkflowRun.DoesNotExist:
            return StepResult(
                step_index=step_index,
                step_type="unknown",
                success=False,
                error="Run not found",
            )

        steps = run.workflow.steps
        if step_index >= len(steps):
            return StepResult(
                step_index=step_index,
                step_type="unknown",
                success=False,
                error=f"Step index {step_index} out of range (total: {len(steps)})",
            )

        step = steps[step_index]
        step_type = step.get("type", "unknown")
        step_config = step.get("config", {})

        t0 = time.time()

        try:
            run.current_step = step_index
            run.save(update_fields=["current_step"])
        except Exception:
            logger.warning("Failed to update current_step")

        handler = self._registry.get(step_type)
        if handler is None:
            return StepResult(
                step_index=step_index,
                step_type=step_type,
                success=False,
                error=f"Unknown step type: {step_type}",
                elapsed_ms=(time.time() - t0) * 1000,
            )

        context = dict(run.input_data) if run.input_data else {}
        output: dict[str, Any] = {}

        try:
            output = handler(step_config, context)
        except Exception as e:
            logger.exception("Step %d raised exception: %s", step_index, e)
            output = {"error": str(e)}

        elapsed_ms = (time.time() - t0) * 1000
        has_error = isinstance(output, dict) and "error" in output

        self._save_step_output(run_id, step_index, step_type, output)

        return StepResult(
            step_index=step_index,
            step_type=step_type,
            success=not has_error,
            output=output if not has_error else {},
            error=output.get("error") if has_error else None,
            elapsed_ms=elapsed_ms,
        )

    def _save_step_output(
        self,
        run_id: str,
        step_index: int,
        step_type: str,
        output: dict,
    ) -> None:
        """Persist step output to the WorkflowRun record."""
        from apps.workflows.models import WorkflowRun

        try:
            run = WorkflowRun.objects.get(pk=uuid.UUID(run_id))
            output_data = dict(run.output_data) if run.output_data else {}
            output_data[f"step_{step_index}"] = {
                "type": step_type,
                "result": output,
            }
            run.output_data = output_data
            run.save(update_fields=["output_data"])
        except WorkflowRun.DoesNotExist:
            logger.warning("Run %s not found when saving step output", run_id)
        except Exception as e:
            logger.warning("Failed to save step output for run %s: %s", run_id, e)

    def _fail_run(self, run_id: str, error_message: str) -> None:
        """Mark a workflow run as failed."""
        from apps.workflows.services import WorkflowService

        try:
            WorkflowService.fail_run(uuid.UUID(run_id), error_message)
        except Exception as e:
            logger.warning("Failed to mark run %s as failed: %s", run_id, e)
