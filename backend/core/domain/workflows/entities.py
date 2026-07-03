from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.domain.common.entities import BaseEntity
from core.domain.workflows.value_objects import TriggerType, WorkflowStatus


@dataclass(frozen=True)
class WorkflowStep(BaseEntity):
    """A single step within a workflow."""

    workflow_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    step_type: str = ""
    order: int = 0
    config: dict[str, Any] = field(default_factory=dict)
    is_optional: bool = False
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    dependencies: tuple[uuid.UUID, ...] = ()

    def increment_retry(self) -> None:
        object.__setattr__(self, "retry_count", self.retry_count + 1)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    @property
    def is_ready(self) -> bool:
        """Whether all dependencies are satisfied."""
        return len(self.dependencies) == 0


@dataclass(frozen=True)
class WorkflowRun(BaseEntity):
    """Execution record of a workflow run."""

    workflow_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: WorkflowStatus = WorkflowStatus.RUNNING
    triggered_by: TriggerType = TriggerType.MANUAL
    trigger_user_id: uuid.UUID | None = None
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    step_results: dict[str, Any] = field(default_factory=dict)
    current_step_id: uuid.UUID | None = None
    error_message: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    duration_ms: float | None = None

    def complete(self, output: dict[str, Any] | None = None) -> None:
        now = datetime.now(timezone.utc)
        object.__setattr__(self, "status", WorkflowStatus.COMPLETED)
        object.__setattr__(self, "output_data", output or {})
        object.__setattr__(self, "completed_at", now)
        object.__setattr__(self, "duration_ms", (now - self.started_at).total_seconds() * 1000)
        object.__setattr__(self, "updated_at", now)

    def fail(self, error: str) -> None:
        now = datetime.now(timezone.utc)
        object.__setattr__(self, "status", WorkflowStatus.FAILED)
        object.__setattr__(self, "error_message", error)
        object.__setattr__(self, "completed_at", now)
        object.__setattr__(self, "duration_ms", (now - self.started_at).total_seconds() * 1000)
        object.__setattr__(self, "updated_at", now)

    def record_step_result(self, step_id: uuid.UUID, result: dict[str, Any]) -> None:
        step_results = dict(self.step_results)
        step_results[str(step_id)] = result
        object.__setattr__(self, "step_results", step_results)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    @property
    def is_running(self) -> bool:
        return self.status == WorkflowStatus.RUNNING

    @property
    def completed_steps(self) -> int:
        return len(self.step_results)


@dataclass(frozen=True)
class Workflow(BaseEntity):
    """Top-level workflow definition."""

    name: str = ""
    description: str = ""
    status: WorkflowStatus = WorkflowStatus.DRAFT
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_config: dict[str, Any] = field(default_factory=dict)
    steps: tuple[WorkflowStep, ...] = ()
    tags: tuple[str, ...] = ()
    run_count: int = 0
    last_run_at: datetime | None = None

    def activate(self) -> None:
        if not self.status.can_transition_to(WorkflowStatus.ACTIVE):
            raise ValueError(
                f"Cannot activate workflow in status {self.status.value}"
            )
        object.__setattr__(self, "status", WorkflowStatus.ACTIVE)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def pause(self) -> None:
        if not self.status.can_transition_to(WorkflowStatus.PAUSED):
            raise ValueError(
                f"Cannot pause workflow in status {self.status.value}"
            )
        object.__setattr__(self, "status", WorkflowStatus.PAUSED)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def cancel(self) -> None:
        if not self.status.can_transition_to(WorkflowStatus.CANCELLED):
            raise ValueError(
                f"Cannot cancel workflow in status {self.status.value}"
            )
        object.__setattr__(self, "status", WorkflowStatus.CANCELLED)
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def add_step(self, step: WorkflowStep) -> None:
        object.__setattr__(self, "steps", self.steps + (step,))
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    def record_run(self) -> None:
        object.__setattr__(self, "run_count", self.run_count + 1)
        object.__setattr__(self, "last_run_at", datetime.now(timezone.utc))
        object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def is_active(self) -> bool:
        return self.status == WorkflowStatus.ACTIVE

    @property
    def has_runs(self) -> bool:
        return self.run_count > 0
