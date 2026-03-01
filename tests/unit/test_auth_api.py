"""Unit tests for authentication API endpoints."""

import json
import pytest

from packages.api.app import create_app
from packages.database import init_database, create_tables, get_session
from packages.security import auth


@pytest.fixture
def app():
    """Create Flask app for testing."""
    test_app = create_app({"TESTING": True, "REQUIRE_HTTPS": False})
    
    # Initialize test database
    init_database("sqlite:///:memory:")
    create_tables()
    
    yield test_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def registered_user():
    """Create a registered user for testing."""
    db = get_session()
    try:
        user = auth.register_user(db, "testuser", "testpassword123")
        return {"username": "testuser", "password": "testpassword123", "user_id": user.id}
    finally:
        db.close()


class TestRegisterEndpoint:
    """Tests for POST /api/auth/register endpoint."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            data=json.dumps({"username": "newuser", "password": "password123"}),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert "id" in data
        assert data["username"] == "newuser"
        assert "created_at" in data
        assert "password" not in data  # Password should not be returned

    def test_register_missing_username(self, client):
        """Test registration with missing username."""
        response = client.post(
            "/api/auth/register",
            data=json.dumps({"password": "password123"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "username" in data["message"].lower()

    def test_register_missing_password(self, client):
        """Test registration with missing password."""
        response = client.post(
            "/api/auth/register",
            data=json.dumps({"username": "newuser"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "password" in data["message"].lower()

    def test_register_empty_body(self, client):
        """Test registration with empty request body."""
        response = client.post(
            "/api/auth/register",
            data="",
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error_code"] == "VALIDATION_ERROR"

    def test_register_duplicate_username(self, client, registered_user):
        """Test registration with duplicate username."""
        response = client.post(
            "/api/auth/register",
            data=json.dumps({"username": "testuser", "password": "newpassword"}),
            content_type="application/json",
        )

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data["error_code"] == "CONFLICT"
        assert "already exists" in data["message"]


class TestLoginEndpoint:
    """Tests for POST /api/auth/login endpoint."""

    def test_login_success(self, client, registered_user):
        """Test successful login."""
        response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"username": registered_user["username"], "password": registered_user["password"]}
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "token" in data
        assert data["user_id"] == registered_user["user_id"]
        assert "created_at" in data
        assert len(data["token"]) > 0

    def test_login_invalid_username(self, client):
        """Test login with non-existent username."""
        response = client.post(
            "/api/auth/login",
            data=json.dumps({"username": "nonexistent", "password": "password123"}),
            content_type="application/json",
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "AUTHENTICATION_REQUIRED"
        assert "invalid credentials" in data["message"].lower()

    def test_login_invalid_password(self, client, registered_user):
        """Test login with incorrect password."""
        response = client.post(
            "/api/auth/login",
            data=json.dumps({"username": registered_user["username"], "password": "wrongpassword"}),
            content_type="application/json",
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "AUTHENTICATION_REQUIRED"
        assert "invalid credentials" in data["message"].lower()

    def test_login_missing_username(self, client):
        """Test login with missing username."""
        response = client.post(
            "/api/auth/login",
            data=json.dumps({"password": "password123"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "username" in data["message"].lower()

    def test_login_missing_password(self, client):
        """Test login with missing password."""
        response = client.post(
            "/api/auth/login",
            data=json.dumps({"username": "testuser"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "password" in data["message"].lower()

    def test_login_empty_body(self, client):
        """Test login with empty request body."""
        response = client.post(
            "/api/auth/login",
            data="",
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error_code"] == "VALIDATION_ERROR"


class TestLogoutEndpoint:
    """Tests for POST /api/auth/logout endpoint."""

    def test_logout_success(self, client, registered_user):
        """Test successful logout."""
        # First login to get a token
        login_response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"username": registered_user["username"], "password": registered_user["password"]}
            ),
            content_type="application/json",
        )
        token = json.loads(login_response.data)["token"]

        # Then logout
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data
        assert "successful" in data["message"].lower()

    def test_logout_missing_authorization_header(self, client):
        """Test logout without Authorization header."""
        response = client.post("/api/auth/logout")

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "AUTHENTICATION_REQUIRED"
        assert "authorization header" in data["message"].lower()

    def test_logout_invalid_authorization_format(self, client):
        """Test logout with invalid Authorization header format."""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "InvalidFormat token123"},
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "AUTHENTICATION_REQUIRED"
        assert "invalid authorization header" in data["message"].lower()

    def test_logout_missing_bearer_prefix(self, client):
        """Test logout without Bearer prefix."""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "token123"},
        )

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "AUTHENTICATION_REQUIRED"

    def test_logout_with_invalid_token(self, client):
        """Test logout with invalid token (should still succeed)."""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer invalidtoken123"},
        )

        # Logout should succeed even with invalid token (idempotent)
        assert response.status_code == 200

    def test_logout_twice_with_same_token(self, client, registered_user):
        """Test logout twice with the same token."""
        # Login to get a token
        login_response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"username": registered_user["username"], "password": registered_user["password"]}
            ),
            content_type="application/json",
        )
        token = json.loads(login_response.data)["token"]

        # First logout
        response1 = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 200

        # Second logout with same token (should still succeed - idempotent)
        response2 = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 200


class TestAuthenticationFlow:
    """Integration tests for complete authentication flow."""

    def test_register_login_logout_flow(self, client):
        """Test complete authentication flow."""
        # Register
        register_response = client.post(
            "/api/auth/register",
            data=json.dumps({"username": "flowuser", "password": "flowpass123"}),
            content_type="application/json",
        )
        assert register_response.status_code == 201

        # Login
        login_response = client.post(
            "/api/auth/login",
            data=json.dumps({"username": "flowuser", "password": "flowpass123"}),
            content_type="application/json",
        )
        assert login_response.status_code == 200
        token = json.loads(login_response.data)["token"]

        # Logout
        logout_response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logout_response.status_code == 200

    def test_multiple_logins_create_different_tokens(self, client, registered_user):
        """Test that multiple logins create different session tokens."""
        # First login
        response1 = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"username": registered_user["username"], "password": registered_user["password"]}
            ),
            content_type="application/json",
        )
        token1 = json.loads(response1.data)["token"]

        # Second login
        response2 = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"username": registered_user["username"], "password": registered_user["password"]}
            ),
            content_type="application/json",
        )
        token2 = json.loads(response2.data)["token"]

        # Tokens should be different
        assert token1 != token2
