import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.mark.django_db
class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register."""

    def test_register_success(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register",
            {
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "user" in response.data
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["email"] == "newuser@example.com"
        assert response.data["user"]["username"] == "newuser"

    def test_register_duplicate_email(self, api_client, test_user):
        response = api_client.post(
            "/api/v1/auth/register",
            {
                "email": "test@example.com",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "username": "anotheruser",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_username(self, api_client, test_user):
        response = api_client.post(
            "/api/v1/auth/register",
            {
                "email": "different@example.com",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "username": "testuser",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_mismatch(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register",
            {
                "email": "mismatch@example.com",
                "password": "SecurePass123!",
                "password_confirm": "DifferentPass456!",
                "username": "mismatchuser",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register",
            {
                "email": "weak@example.com",
                "password": "123",
                "password_confirm": "123",
                "username": "weakuser",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_fields(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register",
            {
                "email": "not-an-email",
                "password": "SecurePass123!",
                "password_confirm": "SecurePass123!",
                "username": "invalidemail",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(self, api_client, test_user):
        response = api_client.post(
            "/api/v1/auth/login",
            {
                "email": "test@example.com",
                "password": "testpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert response.data["user"]["email"] == "test@example.com"

    def test_login_wrong_password(self, api_client, test_user):
        response = api_client.post(
            "/api/v1/auth/login",
            {
                "email": "test@example.com",
                "password": "wrongpassword",
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_login_nonexistent_email(self, api_client):
        response = api_client.post(
            "/api/v1/auth/login",
            {
                "email": "nonexistent@example.com",
                "password": "somepass123",
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_login_missing_fields(self, api_client):
        response = api_client.post(
            "/api/v1/auth/login",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_inactive_user(self, api_client, db):
        user = User.objects.create_user(
            email="inactive@example.com",
            password="inactivepass123",
            username="inactiveuser",
            is_active=False,
        )
        response = api_client.post(
            "/api/v1/auth/login",
            {
                "email": "inactive@example.com",
                "password": "inactivepass123",
            },
            format="json",
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ]


@pytest.mark.django_db
class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout."""

    def test_logout_success(self, auth_client, test_user):
        refresh = RefreshToken.for_user(test_user)
        response = auth_client.post(
            "/api/v1/auth/logout",
            {"refresh": str(refresh)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_logout_missing_refresh_token(self, auth_client):
        response = auth_client.post(
            "/api/v1/auth/logout",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_invalid_token(self, auth_client):
        response = auth_client.post(
            "/api/v1/auth/logout",
            {"refresh": "invalid-token-value"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_unauthenticated(self, api_client):
        response = api_client.post(
            "/api/v1/auth/logout",
            {"refresh": "some-token"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenRefresh:
    """Tests for POST /api/v1/token/refresh."""

    def test_refresh_token_success(self, api_client, test_user):
        refresh = RefreshToken.for_user(test_user)
        response = api_client.post(
            "/api/v1/token/refresh",
            {"refresh": str(refresh)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_refresh_token_invalid(self, api_client):
        response = api_client.post(
            "/api/v1/token/refresh",
            {"refresh": "invalid-token"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserEndpoints:
    """Tests for user profile management endpoints."""

    def test_list_users_as_non_staff(self, auth_client, test_user):
        response = auth_client.get("/api/v1/users")
        assert response.status_code == status.HTTP_200_OK

    def test_list_users_as_admin(self, admin_client, test_user, admin_user):
        response = admin_client.get("/api/v1/users")
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_own_profile(self, auth_client, test_user):
        response = auth_client.get(f"/api/v1/users/{test_user.pk}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "test@example.com"

    def test_retrieve_user_profile_me(self, auth_client, test_user):
        response = auth_client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "test@example.com"

    def test_update_own_profile(self, auth_client, test_user):
        response = auth_client.patch(
            f"/api/v1/users/{test_user.pk}",
            {"first_name": "Updated", "last_name": "Name"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_user_access(self, api_client):
        response = api_client.get("/api/v1/users")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_nonexistent_user(self, auth_client):
        response = auth_client.get(
            "/api/v1/users/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
