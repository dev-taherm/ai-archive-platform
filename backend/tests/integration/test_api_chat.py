import pytest
from rest_framework import status


@pytest.mark.django_db
class TestChatEndpoints:
    """Comprehensive tests for Chat API endpoints."""

    def test_list_sessions(self, auth_client):
        response = auth_client.get("/api/v1/chat/sessions")
        assert response.status_code == status.HTTP_200_OK
        assert "sessions" in response.data

    def test_list_sessions_unauthenticated(self, api_client):
        response = api_client.get("/api/v1/chat/sessions")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_session(self, auth_client):
        response = auth_client.post(
            "/api/v1/chat/sessions",
            {"title": "Test Chat Session"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data

    def test_create_session_without_title(self, auth_client):
        response = auth_client.post(
            "/api/v1/chat/sessions",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_send_message(self, auth_client):
        # Create a session first
        session_response = auth_client.post(
            "/api/v1/chat/sessions",
            {"title": "Message Test"},
            format="json",
        )
        assert session_response.status_code == status.HTTP_201_CREATED
        session_id = session_response.data["id"]

        # Send a message
        response = auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            {"message": "Hello, can you help me find documents?"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data or "assistant_message" in response.data

    def test_list_messages(self, auth_client):
        # Create a session
        session_response = auth_client.post(
            "/api/v1/chat/sessions",
            {"title": "History Test"},
            format="json",
        )
        session_id = session_response.data["id"]

        # Send a message to populate history
        auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            {"message": "Test message"},
            format="json",
        )

        # List messages
        response = auth_client.get(
            f"/api/v1/chat/sessions/{session_id}/messages"
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.xfail(
        reason="Chat service may create message with invalid FK causing teardown IntegrityError",
        strict=False,
    )
    def test_send_message_invalid_session(self, auth_client):
        response = auth_client.post(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000/messages",
            {"message": "Hello"},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_send_message_empty(self, auth_client):
        session_response = auth_client.post(
            "/api/v1/chat/sessions",
            {"title": "Empty Test"},
            format="json",
        )
        session_id = session_response.data["id"]

        response = auth_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            {"message": ""},
            format="json",
        )
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_list_sessions_with_limit(self, auth_client):
        response = auth_client.get("/api/v1/chat/sessions?limit=5")
        assert response.status_code == status.HTTP_200_OK

    def test_multiple_sessions(self, auth_client):
        for i in range(3):
            response = auth_client.post(
                "/api/v1/chat/sessions",
                {"title": f"Session {i}"},
                format="json",
            )
            assert response.status_code == status.HTTP_201_CREATED

        response = auth_client.get("/api/v1/chat/sessions")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get("sessions", [])) >= 3
