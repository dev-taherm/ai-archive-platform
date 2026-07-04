from __future__ import annotations

import logging
import uuid as _uuid

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from interfaces.api.v1.serializers.workflow_serializers import (
    WorkflowCreateSerializer,
    WorkflowRunCreateSerializer,
    WorkflowRunSerializer,
    WorkflowSerializer,
    WorkflowUpdateSerializer,
)

logger = logging.getLogger(__name__)


class WorkflowViewSet(viewsets.GenericViewSet):
    """
    Workflow ViewSet with CRUD and run actions.

    Persists workflows and runs via Django ORM through WorkflowService.
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action == "create":
            return WorkflowCreateSerializer
        if self.action in ("partial_update", "update"):
            return WorkflowUpdateSerializer
        if self.action == "run":
            return WorkflowRunCreateSerializer
        return WorkflowSerializer

    def _get_service(self):
        from apps.workflows.services import WorkflowService

        return WorkflowService

    def list(self, request):
        service = self._get_service()
        workflows = service.list_workflows(
            offset=int(request.query_params.get("offset", 0)),
            limit=int(request.query_params.get("limit", 100)),
        )
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

        service = self._get_service()
        workflow = service.get_workflow(workflow_id)
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

        service = self._get_service()
        steps = validated.get("steps", [])

        workflow = service.create_workflow(
            name=validated["name"],
            steps=steps,
            description=validated.get("description", ""),
            trigger_type=validated.get("trigger_type", "manual"),
            created_by_id=request.user.pk if request.user.is_authenticated else None,
        )

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

        service = self._get_service()
        workflow = service.get_workflow(workflow_id)
        if workflow is None:
            return Response(
                {"detail": "Workflow not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WorkflowUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        update_fields = {}
        if "name" in validated:
            workflow.name = validated["name"]
            update_fields["name"] = True
        if "description" in validated:
            workflow.description = validated["description"]
            update_fields["description"] = True
        if "steps" in validated:
            workflow.steps = validated["steps"]
            update_fields["steps"] = True
        if "trigger_type" in validated:
            workflow.trigger_type = validated["trigger_type"]
            update_fields["trigger_type"] = True
        if "is_active" in validated:
            workflow.is_active = validated["is_active"]
            update_fields["is_active"] = True

        workflow.save()
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

        service = self._get_service()
        workflow = service.get_workflow(workflow_id)
        if workflow is None:
            return Response(
                {"detail": "Workflow not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if workflow.is_active:
            return Response(
                {"detail": "Cannot delete an active workflow. Deactivate it first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow.delete()
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

        service = self._get_service()
        workflow = service.get_workflow(workflow_id)
        if workflow is None:
            return Response(
                {"detail": "Workflow not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not workflow.is_active:
            return Response(
                {"detail": "Workflow must be active to run."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = WorkflowRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        run = service.start_run(
            workflow_id,
            input_data=serializer.validated_data.get("input_data", {}),
            triggered_by_id=request.user.pk if request.user.is_authenticated else None,
        )

        if run is None:
            return Response(
                {"detail": "Failed to start workflow run."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Dispatch async workflow execution
        try:
            from apps.workflows.tasks import execute_full_workflow

            execute_full_workflow.delay(
                str(workflow_id),
                input_data=serializer.validated_data.get("input_data", {}),
                user_id=str(request.user.pk) if request.user.is_authenticated else None,
            )
        except Exception:
            logger.exception("Failed to dispatch workflow execution")

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

        service = self._get_service()
        workflow = service.get_workflow(workflow_id)
        if workflow is None:
            return Response(
                {"detail": "Workflow not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        limit = int(request.query_params.get("limit", 50))
        run_history = service.get_run_history(workflow_id, limit=limit)

        return Response(
            {
                "workflow_id": str(workflow.id),
                "run_count": workflow.runs.count() if hasattr(workflow, "runs") else 0,
                "runs": WorkflowRunSerializer(run_history, many=True).data,
            },
            status=status.HTTP_200_OK,
        )
