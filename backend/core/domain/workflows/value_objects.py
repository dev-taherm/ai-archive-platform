from __future__ import annotations

import enum


class WorkflowStatus(enum.Enum):
    """Lifecycle status of a workflow."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        )

    @property
    def is_executable(self) -> bool:
        return self in (WorkflowStatus.ACTIVE, WorkflowStatus.RUNNING)

    def can_transition_to(self, target: WorkflowStatus) -> bool:
        allowed_transitions: dict[WorkflowStatus, set[WorkflowStatus]] = {
            WorkflowStatus.DRAFT: {WorkflowStatus.ACTIVE, WorkflowStatus.CANCELLED},
            WorkflowStatus.ACTIVE: {
                WorkflowStatus.PAUSED,
                WorkflowStatus.RUNNING,
                WorkflowStatus.CANCELLED,
            },
            WorkflowStatus.PAUSED: {
                WorkflowStatus.ACTIVE,
                WorkflowStatus.CANCELLED,
            },
            WorkflowStatus.RUNNING: {
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
            },
            WorkflowStatus.COMPLETED: set(),
            WorkflowStatus.FAILED: {WorkflowStatus.ACTIVE, WorkflowStatus.DRAFT},
            WorkflowStatus.CANCELLED: {WorkflowStatus.DRAFT},
        }
        return target in allowed_transitions.get(self, set())


class TriggerType(enum.Enum):
    """How a workflow is triggered."""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    API_WEBHOOK = "api_webhook"

    @property
    def is_automated(self) -> bool:
        return self != TriggerType.MANUAL
