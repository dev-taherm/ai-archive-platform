import pytest
import uuid
from unittest.mock import patch

from rest_framework import status

from apps.workflows.models import Workflow, WorkflowRun


@pytest.mark.django_db
class TestWorkflowListEndpoint:
    """Tests for GET /api/v1/workflows."""

    def test_list_workflows_empty(self, auth_client):
        response = auth_client.get("/api/v1/workflows")
        assert response.status_code == status.HTTP_200_OK

    def test_list_workflows_with_data(self, auth_client, sample_workflow):
        response = auth_client.get("/api/v1/workflows")
        assert response.status_code == status.HTTP_200_OK

    def test_list_workflows_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/workflows")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_workflows_returns_list(self, auth_client, sample_workflow):
        response = auth_client.get("/api/v1/workflows")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


@pytest.mark.django_db
class TestWorkflowCreateEndpoint:
    """Tests for POST /api/v1/workflows."""

    def test_create_workflow_success(self, auth_client):
        response = auth_client.post(
            "/api/v1/workflows",
            {
                "name": "New Test Workflow",
                "description": "A new test processing workflow",
                "trigger_type": "manual",
                "steps": [
                    {"name": "OCR Step", "step_type": "ocr", "order": 0},
                    {"name": "Classify Step", "step_type": "classify", "order": 1},
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data

    def test_create_workflow_minimal(self, auth_client):
        response = auth_client.post(
            "/api/v1/workflows",
            {"name": "Minimal Workflow", "steps": []},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_workflow_missing_name(self, auth_client):
        response = auth_client.post(
            "/api/v1/workflows",
            {"steps": []},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_workflow_with_all_steps(self, auth_client):
        response = auth_client.post(
            "/api/v1/workflows",
            {
                "name": "Multi-Step Workflow",
                "steps": [
                    {"name": "OCR", "step_type": "ocr", "order": 0, "config": {}},
                    {
                        "name": "Classify",
                        "step_type": "classify",
                        "order": 1,
                        "config": {"categories": ["invoice", "contract"]},
                    },
                    {
                        "name": "Summarize",
                        "step_type": "summarize",
                        "order": 2,
                        "config": {"max_tokens": 300},
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_workflow_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/workflows",
            {"name": "Unauth Workflow", "steps": []},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_workflow_with_trigger_types(self, auth_client):
        for trigger in ["manual", "scheduled", "event", "file_created"]:
            response = auth_client.post(
                "/api/v1/workflows",
                {
                    "name": f"Workflow {trigger}",
                    "trigger_type": trigger,
                    "steps": [],
                },
                format="json",
            )
            assert response.status_code == status.HTTP_201_CREATED

    def test_create_workflow_invalid_trigger(self, auth_client):
        response = auth_client.post(
            "/api/v1/workflows",
            {
                "name": "Invalid Trigger",
                "trigger_type": "invalid_trigger",
                "steps": [],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestWorkflowRetrieveEndpoint:
    """Tests for GET /api/v1/workflows/{id}."""

    def test_retrieve_existing_workflow(self, auth_client, sample_workflow):
        response = auth_client.get(f"/api/v1/workflows/{sample_workflow.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Test Workflow"

    def test_retrieve_nonexistent_workflow(self, auth_client):
        response = auth_client.get(
            "/api/v1/workflows/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_invalid_uuid(self, auth_client):
        response = auth_client.get("/api/v1/workflows/invalid-id")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_unauthenticated(self, api_client, sample_workflow):
        response = api_client.get(f"/api/v1/workflows/{sample_workflow.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_workflow_contains_steps(self, auth_client, sample_workflow):
        response = auth_client.get(f"/api/v1/workflows/{sample_workflow.id}")
        assert response.status_code == status.HTTP_200_OK
        assert "steps" in response.data
        assert isinstance(response.data["steps"], list)


@pytest.mark.django_db
class TestWorkflowUpdateEndpoint:
    """Tests for PATCH /api/v1/workflows/{id}."""

    def test_update_workflow_name(self, auth_client, sample_workflow):
        response = auth_client.patch(
            f"/api/v1/workflows/{sample_workflow.id}",
            {"name": "Updated Workflow Name"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Workflow Name"

    def test_update_workflow_description(self, auth_client, sample_workflow):
        response = auth_client.patch(
            f"/api/v1/workflows/{sample_workflow.id}",
            {"description": "Updated description"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_update_workflow_trigger_type(self, auth_client, sample_workflow):
        response = auth_client.patch(
            f"/api/v1/workflows/{sample_workflow.id}",
            {"trigger_type": "scheduled"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_update_nonexistent_workflow(self, auth_client):
        response = auth_client.patch(
            "/api/v1/workflows/00000000-0000-0000-0000-000000000000",
            {"name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_unauthenticated(self, api_client, sample_workflow):
        response = api_client.patch(
            f"/api/v1/workflows/{sample_workflow.id}",
            {"name": "Updated"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestWorkflowDeleteEndpoint:
    """Tests for DELETE /api/v1/workflows/{id}."""

    def test_delete_inactive_workflow(self, auth_client, inactive_workflow):
        response = auth_client.delete(f"/api/v1/workflows/{inactive_workflow.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_active_workflow_fails(self, auth_client, sample_workflow):
        response = auth_client.delete(f"/api/v1/workflows/{sample_workflow.id}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_nonexistent_workflow(self, auth_client):
        response = auth_client.delete(
            "/api/v1/workflows/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_unauthenticated(self, api_client, inactive_workflow):
        response = api_client.delete(f"/api/v1/workflows/{inactive_workflow.id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestWorkflowRunEndpoint:
    """Tests for POST /api/v1/workflows/{id}/run."""

    def test_run_active_workflow(self, auth_client, sample_workflow):
        response = auth_client.post(
            f"/api/v1/workflows/{sample_workflow.id}/run",
            {"input_data": {"file_path": "/tmp/test.pdf"}},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_run_inactive_workflow_fails(self, auth_client, inactive_workflow):
        response = auth_client.post(
            f"/api/v1/workflows/{inactive_workflow.id}/run",
            {"input_data": {}},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_run_nonexistent_workflow(self, auth_client):
        response = auth_client.post(
            "/api/v1/workflows/00000000-0000-0000-0000-000000000000/run",
            {"input_data": {}},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_run_workflow_unauthenticated(self, api_client, sample_workflow):
        response = api_client.post(
            f"/api/v1/workflows/{sample_workflow.id}/run",
            {"input_data": {}},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_run_workflow_with_empty_input(self, auth_client, sample_workflow):
        response = auth_client.post(
            f"/api/v1/workflows/{sample_workflow.id}/run",
            {},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.django_db
class TestWorkflowRunsHistoryEndpoint:
    """Tests for GET /api/v1/workflows/{id}/runs."""

    def test_get_workflow_runs_empty(self, auth_client, sample_workflow):
        response = auth_client.get(f"/api/v1/workflows/{sample_workflow.id}/runs")
        assert response.status_code == status.HTTP_200_OK
        assert "runs" in response.data

    def test_get_workflow_runs_nonexistent(self, auth_client):
        response = auth_client.get(
            "/api/v1/workflows/00000000-0000-0000-0000-000000000000/runs"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_workflow_runs_invalid_id(self, auth_client):
        response = auth_client.get("/api/v1/workflows/invalid-id/runs")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_workflow_runs_unauthenticated(self, api_client, sample_workflow):
        response = api_client.get(f"/api/v1/workflows/{sample_workflow.id}/runs")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_workflow_runs_with_limit(self, auth_client, sample_workflow):
        response = auth_client.get(
            f"/api/v1/workflows/{sample_workflow.id}/runs?limit=5"
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestWorkflowModelBehavior:
    """Tests verifying workflow model behavior."""

    def test_workflow_str_representation(self, sample_workflow):
        assert str(sample_workflow) == "Test Workflow"

    def test_workflow_default_values(self, db, test_user):
        workflow = Workflow.objects.create(
            name="Defaults Test",
            steps=[],
            created_by=test_user,
        )
        assert workflow.is_active is True
        assert workflow.trigger_type == "manual"
        assert workflow.description == ""

    def test_workflow_run_str_representation(self, db, sample_workflow):
        run = WorkflowRun.objects.create(
            workflow=sample_workflow,
            status="pending",
            input_data={"key": "value"},
        )
        assert "Test Workflow" in str(run)
        assert "pending" in str(run)

    def test_workflow_run_default_values(self, db, sample_workflow):
        run = WorkflowRun.objects.create(
            workflow=sample_workflow,
        )
        assert run.status == "pending"
        assert run.input_data == {}
        assert run.output_data == {}
        assert run.current_step == 0
        assert run.total_steps == 0
