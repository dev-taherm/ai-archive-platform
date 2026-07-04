from __future__ import annotations


from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from core.domain.workflows.entities import Workflow, WorkflowRun, WorkflowStep
from core.domain.workflows.value_objects import TriggerType, WorkflowStatus
from core.infrastructure.db.models.base import BaseModel


class WorkflowModel(BaseModel):
    """Django ORM model for Workflow domain entity."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in WorkflowStatus],
        default=WorkflowStatus.DRAFT.value,
        db_index=True,
    )
    trigger_type = models.CharField(
        max_length=20,
        choices=[(t.value, t.value) for t in TriggerType],
        default=TriggerType.MANUAL.value,
    )
    trigger_config = models.JSONField(default=dict, blank=True)
    tags = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
    )
    run_count = models.PositiveIntegerField(default=0)
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "workflow"
        indexes = [
            models.Index(fields=["status"], name="idx_workflow_status"),
            models.Index(fields=["trigger_type"], name="idx_workflow_trigger"),
        ]

    def __str__(self) -> str:
        return f"Workflow({self.name}, status={self.status})"

    def to_domain(self) -> Workflow:
        return Workflow(
            id=self.id,
            name=self.name,
            description=self.description,
            status=WorkflowStatus(self.status),
            trigger_type=TriggerType(self.trigger_type),
            trigger_config=dict(self.trigger_config) if self.trigger_config else {},
            steps=[],
            tags=list(self.tags) if self.tags else [],
            run_count=self.run_count,
            last_run_at=self.last_run_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, entity: Workflow) -> WorkflowModel:
        return cls(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            status=entity.status.value,
            trigger_type=entity.trigger_type.value,
            trigger_config=entity.trigger_config,
            tags=entity.tags,
            run_count=entity.run_count,
            last_run_at=entity.last_run_at,
        )


class WorkflowStepModel(BaseModel):
    """Django ORM model for WorkflowStep domain entity."""

    workflow = models.ForeignKey(
        WorkflowModel,
        on_delete=models.CASCADE,
        related_name="step_records",
    )
    name = models.CharField(max_length=255)
    step_type = models.CharField(max_length=100)
    order = models.PositiveIntegerField()
    config = models.JSONField(default=dict, blank=True)
    is_optional = models.BooleanField(default=False)
    timeout_seconds = models.PositiveIntegerField(default=300)
    retry_count = models.PositiveSmallIntegerField(default=0)
    max_retries = models.PositiveSmallIntegerField(default=3)
    dependencies = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
    )

    class Meta:
        db_table = "workflow_step"
        ordering = ["order"]
        indexes = [
            models.Index(fields=["workflow", "order"], name="idx_wstep_wf_order"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "order"],
                name="uq_wstep_workflow_order",
            ),
        ]

    def __str__(self) -> str:
        return f"WorkflowStep({self.name}, order={self.order})"

    def to_domain(self) -> WorkflowStep:
        return WorkflowStep(
            id=self.id,
            workflow_id=self.workflow_id,
            name=self.name,
            step_type=self.step_type,
            order=self.order,
            config=dict(self.config) if self.config else {},
            is_optional=self.is_optional,
            timeout_seconds=self.timeout_seconds,
            retry_count=self.retry_count,
            max_retries=self.max_retries,
            dependencies=tuple(d for d in self.dependencies) if self.dependencies else (),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, entity: WorkflowStep) -> WorkflowStepModel:
        return cls(
            id=entity.id,
            workflow_id=entity.workflow_id,
            name=entity.name,
            step_type=entity.step_type,
            order=entity.order,
            config=entity.config,
            is_optional=entity.is_optional,
            timeout_seconds=entity.timeout_seconds,
            retry_count=entity.retry_count,
            max_retries=entity.max_retries,
            dependencies=list(entity.dependencies),
        )


class WorkflowRunModel(BaseModel):
    """Django ORM model for WorkflowRun domain entity."""

    workflow = models.ForeignKey(
        WorkflowModel,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in WorkflowStatus],
        default=WorkflowStatus.RUNNING.value,
        db_index=True,
    )
    triggered_by = models.CharField(
        max_length=20,
        choices=[(t.value, t.value) for t in TriggerType],
        default=TriggerType.MANUAL.value,
    )
    trigger_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_runs",
    )
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    step_results = models.JSONField(default=dict, blank=True)
    current_step_id = models.UUIDField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "workflow_run"
        indexes = [
            models.Index(fields=["workflow", "status"], name="idx_wrun_wf_status"),
            models.Index(fields=["started_at"], name="idx_wrun_started"),
        ]

    def __str__(self) -> str:
        return f"WorkflowRun({self.workflow_id}, status={self.status})"

    def to_domain(self) -> WorkflowRun:
        return WorkflowRun(
            id=self.id,
            workflow_id=self.workflow_id,
            status=WorkflowStatus(self.status),
            triggered_by=TriggerType(self.triggered_by),
            trigger_user_id=self.trigger_user_id,
            input_data=dict(self.input_data) if self.input_data else {},
            output_data=dict(self.output_data) if self.output_data else {},
            step_results=dict(self.step_results) if self.step_results else {},
            current_step_id=self.current_step_id,
            error_message=self.error_message,
            started_at=self.started_at,
            completed_at=self.completed_at,
            duration_ms=self.duration_ms,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, entity: WorkflowRun) -> WorkflowRunModel:
        return cls(
            id=entity.id,
            workflow_id=entity.workflow_id,
            status=entity.status.value,
            triggered_by=entity.triggered_by.value,
            trigger_user_id=entity.trigger_user_id,
            input_data=entity.input_data,
            output_data=entity.output_data,
            step_results=entity.step_results,
            current_step_id=entity.current_step_id,
            error_message=entity.error_message,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            duration_ms=entity.duration_ms,
        )
