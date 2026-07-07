"""Tests for the API Keys API — CRUD, toggle, and verify."""
import pytest


@pytest.mark.django_db
class TestApiKeyCRUD:
    def test_list_keys(self, auth_client, sample_api_key):
        resp = auth_client.get("/api/v1/api-keys")
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_list_keys_unauthenticated(self, api_client):
        resp = api_client.get("/api/v1/api-keys")
        assert resp.status_code == 401

    def test_create_key(self, auth_client):
        resp = auth_client.post("/api/v1/api-keys", {"name": "my-key"}, format="json")
        assert resp.status_code == 201
        assert resp.data["name"] == "my-key"
        assert resp.data["key"].startswith("ak_")
        assert resp.data["is_active"] is True

    def test_create_key_missing_name(self, auth_client):
        resp = auth_client.post("/api/v1/api-keys", {}, format="json")
        assert resp.status_code == 400

    def test_delete_key(self, auth_client, sample_api_key):
        resp = auth_client.delete(f"/api/v1/api-keys/{sample_api_key.id}")
        assert resp.status_code == 204

    def test_delete_nonexistent_key(self, auth_client):
        import uuid
        resp = auth_client.delete(f"/api/v1/api-keys/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_toggle_active(self, auth_client, sample_api_key):
        assert sample_api_key.is_active is True
        resp = auth_client.post(f"/api/v1/api-keys/{sample_api_key.id}/toggle-active")
        assert resp.status_code == 200
        assert resp.data["is_active"] is False

    def test_toggle_active_nonexistent(self, auth_client):
        import uuid
        resp = auth_client.post(f"/api/v1/api-keys/{uuid.uuid4()}/toggle-active")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestApiKeyModel:
    def test_verify_key_valid(self, test_user):
        from apps.apikeys.models import ApiKey
        key_instance, raw_key = ApiKey.create_key(test_user, name="verify-test")
        verified = ApiKey.verify_key(raw_key)
        assert verified is not None
        assert verified.id == key_instance.id

    def test_verify_key_invalid(self):
        from apps.apikeys.models import ApiKey
        result = ApiKey.verify_key("ak_invalidkey1234567890abcdef")
        assert result is None
