from __future__ import annotations

import logging
import uuid as _uuid

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.domain.common.exceptions import DomainException
from core.domain.workflows.entities import Workflow, WorkflowStep
from core.domain.workflows.value_objects import TriggerType, WorkflowStatus
from interfaces.api.v1.serializers.workflow_serializers import (
    WorkflowCreateSerializer,
    WorkflowRunCreateSerializer,
    WorkflowRunSerializer,
    WorkflowSerializer,
    WorkflowStepCreateSerializer,
    WorkflowStepSerializer,
    WorkflowUpdateSerializer,
)

logger = logging.getLogger(__name__)


class WorkflowViewSet(viewsets.GenericViewSet):
    """
    Workflow ViewSet with CRUD and run actions.

    Delegates persistence to an in-memory store for demonstration.
    Replace with proper repository in production.
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "_workflows"):
            WorkflowViewSet._workflows: dict[_uuid.UUID, Workflow] = {}

    def get_serializer_class(self):
        if self.action == "create":
            return WorkflowCreateSerializer
        if self.action in ("partial_update", "update"):
            return WorkflowUpdateSerializer
        if self.action == "run":
            return WorkflowRunCreateSerializer
        return WorkflowSerializer

    def list(self, request):
        workflows = list(self._workflows.values())
        serializer = WorkflowSerializer(workflows, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        try:
            workflow_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid workflow ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return Response(
                {"detail": "Workflow not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            WorkflowSerializer(workflow).data,
            status=status.HTTP_200_OK,
        )

    def create(self, request):
        serializer = WorkflowCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        steps = []
        for i, step_data in enumerate(validated.get("steps", [])):
            step = WorkflowStep(
                workflow_id=_uuid.uuid4(),
                name=step_data["name"],
                step_type=step_data["step_type"],
                order=step_data.get("order", i),
                config=step_data.get("config", {}),
                is_optional=step_data.get("is_optional", False),
                timeout_seconds=step_data.get("timeout_seconds", 300),
                max_retries=step_data.get("max_retries", 3),
                dependencies=tuple(
                    _uuid.UUID(str(d)) for d in step_data.get("dependencies", [])
                ),
            )
            steps.append(step)

        workflow = Workflow(
            name=validated["name"],
            description=validated.get("description", ""),
            status=WorkflowStatus.DRAFT,
            trigger_type=TriggerType(validated.get("trigger_type", "manual")),
            trigger_config=validated.get("trigger_config", {}),
            steps=steps,
            tags=validated.get("tags", []),
        )

        for step in steps:
            step.workflow_id = workflow.id

        self._workflows[workflow.id] = workflow

        return Response(
            WorkflowSerializer(workflow).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, pk=None):
        try:
            workflow_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid workflow ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return Response(
                {"detail": "Workflow not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WorkflowUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        if "name" in validated:
            workflow.name = validated["name"]
        if "description" in validated:
            workflow.description = validated["description"]
        if "status" in validated:
            try:
                new_status = WorkflowStatus(validated["status"])
                if workflow.status.can_transition_to(new_status):
                    object.__setattr__(workflow, "status", new_status)
                else:
                    return Response(
                        {
                            "detail": f"Cannot transition from {workflow.status.value} to {new_status.value}."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except ValueError:
                return Response(
                    {"detail": "Invalid status value."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if "trigger_type" in validated:
            workflow.trigger_type = TriggerType(validated["trigger_type"])
        if "trigger_config" in validated:
            workflow.trigger_config = validated["trigger_config"]
        if "tags" in validated:
            workflow.tags = validated["tags"]

        from datetime import datetime, timezone

        object.__setattr__(workflow, "updated_at", datetime.now(timezone.utc))

        return Response(
            WorkflowSerializer(workflow).data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, pk=None):
        try:
            workflow_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid workflow ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if workflow_id not in self._workflows:
            return Response(
                {"detail": "Workflow not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        workflow = self._workflows[workflow_id]
        if workflow.is_active:
            return Response(
                {"detail": "Cannot delete an active workflow. Deactivate it first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        del self._workflows[workflow_id]

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        try:
            workflow_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid workflow ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return Response(
                {"detail": "Workflow not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not workflow.is_active and workflow.status != WorkflowStatus.DRAFT:
            return Response(
                {
                    "detail": f"Workflow in '{workflow.status.value}' status cannot be run."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = WorkflowRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from datetime import datetime, timezone

        from core.domain.workflows.entities import WorkflowRun

        run = WorkflowRun(
            workflow_id=workflow.id,
            status=WorkflowStatus.RUNNING,
            triggered_by=TriggerType.MANUAL,
            trigger_user_id=request.user.pk if request.user.is_authenticated else None,
            input_data=serializer.validated_data.get("input_data", {}),
        )

        workflow.record_run()

        return Response(
            WorkflowRunSerializer(run).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="runs")
    def runs(self, request, pk=None):
        try:
            workflow_id = _uuid.UUID(str(pk))
        except ValueError:
            return Response(
                {"detail": "Invalid workflow ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return Response(
                {"detail": "Workflow not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "workflow_id": str(workflow.id),
                "run_count": workflow.run_count,
                "last_run_at": (
                    workflow.last_run_at.isoformat() if workflow.last_run_at else None
                ),
                "runs": [],
                "message": "Run history requires a persistent store.",
            },
            status=status.HTTP_200_OK,
        )
