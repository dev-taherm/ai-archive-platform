from __future__ import annotations

import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="workflows.execute_workflow_step")
def execute_workflow_step(
    run_id: str,
    step_index: int,
) -> dict[str, object]:
    """Execute a single step of a workflow run."""
    import asyncio

    from apps.workflows.services import WorkflowService

    async def _run() -> dict[str, object]:
        from apps.workflows.models import WorkflowRun

        try:
            run = WorkflowRun.objects.select_related("workflow").get(pk=uuid.UUID(run_id))
        except WorkflowRun.DoesNotExist:
            return {"error": "Run not found"}

        steps = run.workflow.steps
        if step_index >= len(steps):
            WorkflowService.complete_run(
                uuid.UUID(run_id),
                output_data=run.output_data,
            )
            return {"status": "completed", "total_steps": len(steps)}

        step = steps[step_index]

        # Update current step
        run.current_step = step_index
        run.save(update_fields=["current_step"])

        logger.info(
            "Executing workflow step %d/%d: %s",
            step_index + 1,
            len(steps),
            step.get("type", "unknown"),
        )

        return {
            "status": "step_executed",
            "step_index": step_index,
            "step_type": step.get("type", "unknown"),
        }

    return asyncio.run(_run())


@shared_task(name="workflows.execute_full_workflow")
def execute_full_workflow(
    workflow_id: str,
    input_data: dict | None = None,
    user_id: str | None = None,
) -> dict[str, object]:
    """Execute all steps of a workflow sequentially."""
    import asyncio
    import uuid as _uuid

    from apps.workflows.services import WorkflowService

    run = WorkflowService.start_run(
        _uuid.UUID(workflow_id),
        input_data=input_data or {},
        triggered_by_id=_uuid.UUID(user_id) if user_id else None,
    )

    if run is None:
        return {"error": "Workflow not found or inactive"}

    # Chain step execution
    for i in range(run.total_steps):
        execute_workflow_step.delay(str(run.id), i)

    return {
        "run_id": str(run.id),
        "total_steps": run.total_steps,
        "status": "dispatched",
    }
