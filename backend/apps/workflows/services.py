from __future__ import annotations

import logging
import uuid
from typing import Any

from apps.workflows.models import Workflow, WorkflowRun

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for managing and executing processing workflows."""

    @staticmethod
    def create_workflow(
        name: str,
        steps: list[dict[str, Any]],
        *,
        description: str = "",
        trigger_type: str = Workflow.TriggerType.MANUAL,
        created_by_id: uuid.UUID | None = None,
    ) -> Workflow:
        """Create a new workflow definition."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        created_by = None
        if created_by_id:
            try:
                created_by = User.objects.get(pk=created_by_id)
            except User.DoesNotExist:
                pass

        workflow = Workflow.objects.create(
            name=name,
            description=description,
            trigger_type=trigger_type,
            steps=steps,
            created_by=created_by,
        )
        logger.info("Workflow created: %s (%d steps)", workflow.name, len(steps))
        return workflow

    @staticmethod
    def get_workflow(workflow_id: uuid.UUID) -> Workflow | None:
        """Retrieve a workflow by ID."""
        try:
            return Workflow.objects.get(pk=workflow_id)
        except Workflow.DoesNotExist:
            return None

    @staticmethod
    def list_workflows(
        *,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Workflow]:
        """List workflows with optional filtering."""
        qs = Workflow.objects.all()
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return list(qs.order_by("-created_at")[offset:offset + limit])

    @staticmethod
    def start_run(
        workflow_id: uuid.UUID,
        *,
        input_data: dict[str, Any] | None = None,
        triggered_by_id: uuid.UUID | None = None,
    ) -> WorkflowRun | None:
        """Start a new workflow run."""
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        try:
            workflow = Workflow.objects.get(pk=workflow_id, is_active=True)
        except Workflow.DoesNotExist:
            return None

        User = get_user_model()
        triggered_by = None
        if triggered_by_id:
            try:
                triggered_by = User.objects.get(pk=triggered_by_id)
            except User.DoesNotExist:
                pass

        run = WorkflowRun.objects.create(
            workflow=workflow,
            input_data=input_data or {},
            total_steps=len(workflow.steps),
            status=WorkflowRun.Status.RUNNING,
            triggered_by=triggered_by,
            started_at=timezone.now(),
        )
        logger.info("Workflow run started: %s run_id=%s", workflow.name, run.id)
        return run

    @staticmethod
    def complete_run(
        run_id: uuid.UUID,
        *,
        output_data: dict[str, Any] | None = None,
    ) -> WorkflowRun | None:
        """Mark a workflow run as completed."""
        from django.utils import timezone

        try:
            run = WorkflowRun.objects.get(pk=run_id)
        except WorkflowRun.DoesNotExist:
            return None

        run.status = WorkflowRun.Status.COMPLETED
        run.output_data = output_data or {}
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "output_data", "completed_at"])
        logger.info("Workflow run completed: run_id=%s", run_id)
        return run

    @staticmethod
    def fail_run(
        run_id: uuid.UUID,
        error_message: str,
    ) -> WorkflowRun | None:
        """Mark a workflow run as failed."""
        from django.utils import timezone

        try:
            run = WorkflowRun.objects.get(pk=run_id)
        except WorkflowRun.DoesNotExist:
            return None

        run.status = WorkflowRun.Status.FAILED
        run.error_message = error_message
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error_message", "completed_at"])
        logger.warning("Workflow run failed: run_id=%s error=%s", run_id, error_message)
        return run

    @staticmethod
    def get_run_history(
        workflow_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[WorkflowRun]:
        """Get execution history for a workflow."""
        return list(
            WorkflowRun.objects.filter(workflow_id=workflow_id)
            .order_by("-created_at")[:limit]
        )
