"""Unit tests for Q&A web UI routes."""

import pytest
from flask import session

from packages.web_ui.app import create_app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SESSION_COOKIE_SECURE"] = False  # Disable for testing
    app.debug = True  # Disable HTTPS redirect in tests

    with app.test_client() as client:
        yield client


def test_qa_interface_requires_authentication(client):
    """Test that Q&A interface requires authentication."""
    # Attempt to access Q&A interface without authentication
    response = client.get("/qa/test-config-id")

    # Should redirect to login
    assert response.status_code == 302
    assert "/login" in response.location


def test_qa_interface_renders_with_authentication(client):
    """Test that Q&A interface renders when authenticated."""
    # Set up session with authentication token
    with client.session_transaction() as sess:
        sess["token"] = "test-token"

    # Access Q&A interface
    response = client.get("/qa/test-config-id")

    # Should render successfully
    assert response.status_code == 200
    assert b"TCO Analysis Assistant" in response.data
    assert b"Ask questions about your cost analysis" in response.data


def test_qa_interface_includes_chat_elements(client):
    """Test that Q&A interface includes necessary chat elements."""
    # Set up session with authentication token
    with client.session_transaction() as sess:
        sess["token"] = "test-token"

    # Access Q&A interface
    response = client.get("/qa/test-config-id")

    # Check for chat interface elements
    assert response.status_code == 200
    assert b"chat-container" in response.data
    assert b"chat-messages" in response.data
    assert b"questionInput" in response.data
    assert b"sendButton" in response.data


def test_qa_interface_includes_config_id(client):
    """Test that Q&A interface includes the config_id in JavaScript."""
    # Set up session with authentication token
    with client.session_transaction() as sess:
        sess["token"] = "test-token"

    # Access Q&A interface with specific config_id
    config_id = "abc-123-def-456"
    response = client.get(f"/qa/{config_id}")

    # Check that config_id is included in the page
    assert response.status_code == 200
    assert config_id.encode() in response.data


def test_qa_interface_includes_api_endpoints(client):
    """Test that Q&A interface includes API endpoint references."""
    # Set up session with authentication token
    with client.session_transaction() as sess:
        sess["token"] = "test-token"

    # Access Q&A interface
    response = client.get("/qa/test-config-id")

    # Check for API endpoint references
    assert response.status_code == 200
    assert b"/api/qa/" in response.data
    assert b"/ask" in response.data
    assert b"/history" in response.data


def test_qa_interface_includes_back_link(client):
    """Test that Q&A interface includes a back link to TCO results."""
    # Set up session with authentication token
    with client.session_transaction() as sess:
        sess["token"] = "test-token"

    # Access Q&A interface
    config_id = "test-config-id"
    response = client.get(f"/qa/{config_id}")

    # Check for back link
    assert response.status_code == 200
    assert b"Back to TCO Results" in response.data
    assert b"/tco/results/" in response.data
