"""Tests for the Reports API — CRUD and summary."""
import pytest


@pytest.mark.django_db
class TestReportCRUD:
    def test_list_reports(self, auth_client, sample_report):
        resp = auth_client.get("/api/v1/reports")
        assert resp.status_code == 200
        assert len(resp.data["results"]) >= 1

    def test_list_reports_unauthenticated(self, api_client):
        resp = api_client.get("/api/v1/reports")
        assert resp.status_code == 401

    def test_create_report(self, auth_client):
        resp = auth_client.post("/api/v1/reports", {
            "report_type": "archive_summary",
            "title": "New Report",
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["title"] == "New Report"

    def test_retrieve_report(self, auth_client, sample_report):
        resp = auth_client.get(f"/api/v1/reports/{sample_report.id}")
        assert resp.status_code == 200
        assert resp.data["title"] == "Test Report"

    def test_retrieve_nonexistent_report(self, auth_client):
        import uuid
        resp = auth_client.get(f"/api/v1/reports/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_delete_report(self, auth_client, sample_report):
        resp = auth_client.delete(f"/api/v1/reports/{sample_report.id}")
        assert resp.status_code == 204

    def test_report_summary(self, auth_client, sample_report):
        resp = auth_client.get("/api/v1/reports/summary")
        assert resp.status_code == 200

    def test_list_reports_by_type(self, auth_client, sample_report):
        resp = auth_client.get("/api/v1/reports?report_type=archive_summary")
        assert resp.status_code == 200

    def test_report_model_str(self, sample_report):
        assert str(sample_report) == "Test Report"
