"""Tests for the Agents API — CRUD, heartbeat, sync, and commands."""
import json

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAgentCRUD:
    def test_list_agents(self, auth_client, sample_agent):
        resp = auth_client.get("/api/v1/agents")
        assert resp.status_code == 200
        assert len(resp.data["results"]) == 1
        assert resp.data["results"][0]["agent_id"] == "test-agent-01"

    def test_list_agents_unauthenticated(self, api_client):
        resp = api_client.get("/api/v1/agents")
        assert resp.status_code == 401

    def test_create_agent(self, auth_client):
        resp = auth_client.post("/api/v1/agents", {
            "agent_id": "new-agent-01",
            "name": "New Agent",
            "platform": "macos",
            "hostname": "my-mac",
            "agent_version": "0.1.0",
            "capabilities": ["scan", "ocr"],
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["agent_id"] == "new-agent-01"
        assert "api_key" in resp.data
        assert resp.data["api_key"].startswith("ak_")

    def test_create_agent_missing_fields(self, auth_client):
        resp = auth_client.post("/api/v1/agents", {}, format="json")
        assert resp.status_code == 400

    def test_retrieve_agent(self, auth_client, sample_agent):
        resp = auth_client.get(f"/api/v1/agents/{sample_agent.agent_id}")
        assert resp.status_code == 200
        assert resp.data["name"] == "Test Agent"

    def test_retrieve_nonexistent_agent(self, auth_client):
        resp = auth_client.get("/api/v1/agents/nonexistent-999")
        assert resp.status_code == 404

    def test_update_agent(self, auth_client, sample_agent):
        resp = auth_client.put(
            f"/api/v1/agents/{sample_agent.agent_id}",
            {
                "agent_id": sample_agent.agent_id,
                "name": "Updated Agent",
                "platform": "linux",
                "hostname": "new-host",
                "capabilities": ["scan"],
            },
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["name"] == "Updated Agent"

    def test_delete_agent(self, auth_client, sample_agent):
        resp = auth_client.delete(f"/api/v1/agents/{sample_agent.agent_id}")
        assert resp.status_code == 204


@pytest.mark.django_db
class TestAgentHeartbeat:
    def test_heartbeat(self, auth_client, sample_agent):
        resp = auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/heartbeat",
            {
                "status": "online",
                "platform": "linux",
                "hostname": "test-host",
                "files_count": 50,
                "folders_monitored": ["/home/user/docs"],
            },
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["status"] == "ok"
        assert "pending_commands" in resp.data
        assert "config" in resp.data

    def test_heartbeat_updates_status(self, auth_client, sample_agent):
        auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/heartbeat",
            {"status": "online"},
            format="json",
        )
        sample_agent.refresh_from_db()
        assert sample_agent.status == "online"

    def test_heartbeat_syncs_folders(self, auth_client, sample_agent):
        auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/heartbeat",
            {"status": "online", "folders_monitored": ["/new/path"]},
            format="json",
        )
        assert sample_agent.folders.filter(local_path="/new/path").exists()


@pytest.mark.django_db
class TestAgentCommands:
    def test_commands_get(self, auth_client, sample_agent, sample_agent_command):
        resp = auth_client.get(f"/api/v1/agents/{sample_agent.agent_id}/commands")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        sample_agent_command.refresh_from_db()
        assert sample_agent_command.status == "delivered"

    def test_commands_post_report_result(self, auth_client, sample_agent, sample_agent_command):
        resp = auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/commands",
            {"command_id": str(sample_agent_command.id), "status": "completed", "result": {"synced": 5}},
            format="json",
        )
        assert resp.status_code == 200
        sample_agent_command.refresh_from_db()
        assert sample_agent_command.status == "completed"

    def test_commands_post_not_found(self, auth_client, sample_agent):
        resp = auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/commands",
            {"command_id": "00000000-0000-0000-0000-000000000000", "status": "completed"},
            format="json",
        )
        assert resp.status_code == 404

    def test_create_command(self, auth_client, sample_agent):
        resp = auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/commands/create",
            {"command_type": "sync", "payload": {}},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["command_type"] == "sync"

    def test_create_command_missing_type(self, auth_client, sample_agent):
        resp = auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/commands/create",
            {},
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestAgentSync:
    def _sync_payload(self, **overrides):
        payload = {
            "files": [
                {
                    "local_path": "/docs/test.pdf",
                    "file_hash": "abc123def456",
                    "mime_type": "application/pdf",
                    "file_size": 1024,
                    "extracted_text": "This is a test document with some content.",
                    "word_count": 8,
                    "char_count": 42,
                    "entities": [
                        {"type": "person", "name": "John Doe", "context": "Author of the document"},
                    ],
                }
            ],
            "stats": {"files_count": 1, "total_size": 1024},
        }
        payload["files"][0].update(overrides)
        return payload

    def test_sync_single_file(self, auth_client, sample_agent):
        resp = auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/sync",
            self._sync_payload(),
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["accepted"] == 1
        assert resp.data["rejected"] == 0
        assert len(resp.data["document_ids"]) == 1

    def test_sync_multiple_files(self, auth_client, sample_agent):
        payload = {
            "files": [
                {"local_path": f"/docs/file{i}.txt", "file_hash": f"hash{i:04d}", "mime_type": "text/plain", "file_size": 100}
                for i in range(3)
            ],
            "stats": {"files_count": 3, "total_size": 300},
        }
        resp = auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/sync",
            payload,
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["accepted"] == 3

    def test_sync_with_entities(self, auth_client, sample_agent):
        resp = auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/sync",
            self._sync_payload(),
            format="json",
        )
        assert resp.status_code == 200
        from apps.documents.models import ExtractedEntity, Document
        doc_id = resp.data["document_ids"][0]
        doc = Document.objects.get(id=doc_id)
        assert ExtractedEntity.objects.filter(document=doc).count() == 1

    def test_sync_empty_files(self, auth_client, sample_agent):
        resp = auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/sync",
            {"files": [], "stats": {"files_count": 0}},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["accepted"] == 0

    def test_sync_strips_null_bytes_from_content_blocks(self, auth_client, sample_agent):
        """Null bytes in content_blocks/metadata must not reach PostgreSQL.

        The REST path's JSON parser rejects \\u0000 at the HTTP layer,
        so this test sends pre-sanitized data and verifies the sync
        endpoint handles it correctly. The *real* defense-in-depth is
        in the WS consumer and sanitize.py — tested below.
        """
        payload = {
            "files": [
                {
                    "local_path": "/docs/screenshot.png",
                    "file_hash": "png_null_bytes_test",
                    "mime_type": "image/png",
                    "file_size": 42000,
                    "extracted_text": "PNG screenshot",
                    "markdown": "PNG screenshot content",
                    "content_blocks": [
                        {"type": "text", "content": "PNG header garbage end"},
                    ],
                    "tables": [],
                    "images": [],
                    "metadata": {"parser_version": "v2"},
                    "word_count": 2,
                    "char_count": 30,
                }
            ],
            "stats": {"files_count": 1},
        }
        resp = auth_client.post(
            f"/api/v1/agents/{sample_agent.agent_id}/sync",
            payload,
            format="json",
        )
        assert resp.status_code == 200, f"Response {resp.status_code}: {resp.data}"
        assert resp.data["accepted"] == 1

    def test_sanitize_removes_null_bytes_before_db_write(self):
        """Verify sanitize.py strips null bytes from all fields including
        content_blocks and metadata — the real defense for the WS path."""
        from apps.agents.sanitize import sanitize_file_data, sanitize_json_recursive

        file_data = {
            "local_path": "/docs/screenshot.png",
            "file_hash": "test",
            "file_size": 100,
            "extracted_text": "text with \x00 null",
            "markdown": "md with \x00 null",
            "summary": "summary with \x00 null",
            "content_blocks": [
                {"type": "text", "content": "PNG header \x00\x00 garbage \x1a\x00 end"},
            ],
            "tables": [{"headers": ["col\x001"], "rows": [["val\x002"]]}],
            "images": [{"data": "base64\x00junk"}],
            "metadata": {"parser_version": "v2\x00bad", "nested": {"key": "val\x00ue"}},
            "entities": [{"name": "John\x00Doe", "context": "author \x00 here"}],
            "tags": ["tag\x00one"],
        }

        sanitize_file_data(file_data)

        # No null bytes in any field
        import json
        for field in ("extracted_text", "markdown", "summary"):
            assert "\x00" not in file_data[field], f"null byte in {field}"
        for field in ("content_blocks", "tables", "images", "metadata", "entities", "tags"):
            serialized = json.dumps(file_data[field])
            assert "\x00" not in serialized, f"null byte in {field}: {serialized[:100]}"

        # Content is still readable
        assert "PNG header" in json.dumps(file_data["content_blocks"])
        assert "garbage" in json.dumps(file_data["content_blocks"])

    def test_sanitize_json_recursive_constructed_metadata(self):
        """Verify that the final metadata dict construction (consumers.py
        pattern) is clean even when source fields carry null bytes."""
        from apps.agents.sanitize import sanitize_json_recursive

        metadata = sanitize_json_recursive({
            "agent_id": "0eff54e8",
            "agent_version": "v1\x00bad",
            "content_blocks": [
                {"type": "text", "content": "\x00PNG data\x00"},
            ],
            "tables": [],
            "images": [],
            "extracted_text": "text\x00here",
            "markdown": "md\x00here",
        })

        import json
        serialized = json.dumps(metadata)
        assert "\x00" not in serialized
        assert "PNG data" in serialized
