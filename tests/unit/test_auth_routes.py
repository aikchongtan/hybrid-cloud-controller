"""Unit tests for authentication routes."""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from packages.web_ui.routes import auth


@pytest.fixture
def app():
    """Create Flask app for testing."""
    import os
    from pathlib import Path

    # Get the web_ui package directory
    web_ui_dir = Path(__file__).parent.parent.parent / "packages" / "web_ui"

    app = Flask(
        __name__,
        template_folder=str(web_ui_dir / "templates"),
        static_folder=str(web_ui_dir / "static"),
    )
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    
    # Register all blueprints for url_for to work
    from packages.web_ui.routes import configuration, monitoring, provisioning, qa
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(configuration.bp)
    app.register_blueprint(monitoring.bp)
    app.register_blueprint(provisioning.bp)
    app.register_blueprint(qa.bp)

    # Register index route for testing
    @app.route("/")
    def index():
        return "Home Page"

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_login_get_renders_template(client):
    """Test GET /login renders login template."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_register_get_renders_template(client):
    """Test GET /register renders registration template."""
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Create Account" in response.data


@patch("packages.web_ui.routes.auth.requests.post")
def test_login_post_success(mock_post, client):
    """Test successful login redirects to home page."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "token": "test-token-123",
        "user_id": "user-123",
        "created_at": "2024-01-01T00:00:00",
    }
    mock_post.return_value = mock_response

    # Submit login form
    response = client.post(
        "/login",
        data={"username": "testuser", "password": "testpass123"},
        follow_redirects=False,
    )

    # Should redirect to home page
    assert response.status_code == 302
    assert response.location == "/"

    # Verify API was called correctly
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "http://localhost:8000/api/auth/login"
    assert call_args[1]["json"] == {"username": "testuser", "password": "testpass123"}


@patch("packages.web_ui.routes.auth.requests.post")
def test_login_post_invalid_credentials(mock_post, client):
    """Test login with invalid credentials shows error."""
    # Mock failed API response
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "error_code": "AUTHENTICATION_REQUIRED",
        "message": "Invalid credentials",
    }
    mock_post.return_value = mock_response

    # Submit login form
    response = client.post(
        "/login",
        data={"username": "testuser", "password": "wrongpass"},
        follow_redirects=True,
    )

    # Should stay on login page with error
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


@patch("packages.web_ui.routes.auth.requests.post")
def test_register_post_success(mock_post, client):
    """Test successful registration redirects to login page."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": "user-123",
        "username": "newuser",
        "created_at": "2024-01-01T00:00:00",
    }
    mock_post.return_value = mock_response

    # Submit registration form
    response = client.post(
        "/register",
        data={
            "username": "newuser",
            "password": "newpass123",
            "confirm_password": "newpass123",
        },
        follow_redirects=False,
    )

    # Should redirect to login page
    assert response.status_code == 302
    assert "/login" in response.location

    # Verify API was called correctly
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "http://localhost:8000/api/auth/register"
    assert call_args[1]["json"] == {"username": "newuser", "password": "newpass123"}


@patch("packages.web_ui.routes.auth.requests.post")
def test_register_post_username_exists(mock_post, client):
    """Test registration with existing username shows error."""
    # Mock conflict API response
    mock_response = MagicMock()
    mock_response.status_code = 409
    mock_response.json.return_value = {
        "error_code": "CONFLICT",
        "message": "Username already exists",
    }
    mock_post.return_value = mock_response

    # Submit registration form
    response = client.post(
        "/register",
        data={
            "username": "existinguser",
            "password": "newpass123",
            "confirm_password": "newpass123",
        },
        follow_redirects=True,
    )

    # Should stay on registration page with error
    assert response.status_code == 200
    assert b"Username already exists" in response.data


def test_register_post_password_mismatch(client):
    """Test registration with mismatched passwords shows error."""
    # Submit registration form with mismatched passwords
    response = client.post(
        "/register",
        data={
            "username": "newuser",
            "password": "password123",
            "confirm_password": "different123",
        },
        follow_redirects=True,
    )

    # Should stay on registration page with error
    assert response.status_code == 200
    assert b"Passwords do not match" in response.data


def test_register_post_short_password(client):
    """Test registration with short password shows error."""
    # Submit registration form with short password
    response = client.post(
        "/register",
        data={"username": "newuser", "password": "short", "confirm_password": "short"},
        follow_redirects=True,
    )

    # Should stay on registration page with error
    assert response.status_code == 200
    assert b"Password must be at least 8 characters long" in response.data


@patch("packages.web_ui.routes.auth.requests.post")
def test_logout_clears_session(mock_post, client):
    """Test logout clears session and redirects to home page."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    # Set up session
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"
        sess["user_id"] = "user-123"

    # Submit logout request
    response = client.post("/logout", follow_redirects=False)

    # Should redirect to home page
    assert response.status_code == 302
    assert response.location == "/"

    # Verify session is cleared
    with client.session_transaction() as sess:
        assert "token" not in sess
        assert "user_id" not in sess
