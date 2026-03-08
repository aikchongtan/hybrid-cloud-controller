"""Unit tests for configuration routes."""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from packages.web_ui.routes import configuration


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
    from packages.web_ui.routes import auth, monitoring, provisioning, qa

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

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_configuration_input_get_renders_template(client):
    """Test GET /configuration renders configuration template."""
    response = client.get("/configuration")
    assert response.status_code == 200
    assert b"Application Configuration" in response.data
    assert b"Compute Specifications" in response.data
    assert b"Storage Specifications" in response.data
    assert b"Network Specifications" in response.data
    assert b"Workload Profile" in response.data


@patch("packages.web_ui.routes.configuration.requests.post")
def test_submit_configuration_success(mock_post, client):
    """Test successful configuration submission redirects to home page."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": "config-123",
        "user_id": "user-123",
        "cpu_cores": 4,
        "memory_gb": 16,
        "instance_count": 2,
        "storage_type": "SSD",
        "storage_capacity_gb": 500,
        "storage_iops": 3000,
        "bandwidth_mbps": 1000,
        "monthly_data_transfer_gb": 5000,
        "utilization_percentage": 70,
        "operating_hours_per_month": 720,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }
    mock_post.return_value = mock_response

    # Submit configuration form with session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.post(
        "/configuration",
        data={
            "cpu_cores": "4",
            "memory_gb": "16",
            "instance_count": "2",
            "storage_type": "SSD",
            "storage_capacity_gb": "500",
            "storage_iops": "3000",
            "bandwidth_mbps": "1000",
            "monthly_data_transfer_gb": "5000",
            "utilization_percentage": "70",
            "operating_hours_per_month": "720",
        },
        follow_redirects=False,
    )

    # Should redirect to TCO results page
    assert response.status_code == 302
    assert response.location == "/tco/results/config-123"

    # Verify API was called correctly
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "http://localhost:8000/api/configurations"
    assert call_args[1]["json"]["cpu_cores"] == 4
    assert call_args[1]["json"]["memory_gb"] == 16
    assert call_args[1]["json"]["storage_type"] == "SSD"


@patch("packages.web_ui.routes.configuration.requests.post")
def test_submit_configuration_validation_error(mock_post, client):
    """Test configuration submission with validation errors."""
    # Mock validation error response
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "error_code": "VALIDATION_ERROR",
        "message": "Configuration validation failed",
        "details": {
            "cpu_cores": "CPU cores must be a positive integer",
            "utilization_percentage": "Utilization percentage must be between 0 and 100",
        },
    }
    mock_post.return_value = mock_response

    # Submit configuration form with session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.post(
        "/configuration",
        data={
            "cpu_cores": "-1",
            "memory_gb": "16",
            "instance_count": "2",
            "storage_type": "SSD",
            "storage_capacity_gb": "500",
            "bandwidth_mbps": "1000",
            "monthly_data_transfer_gb": "5000",
            "utilization_percentage": "150",
            "operating_hours_per_month": "720",
        },
        follow_redirects=True,
    )

    # Should re-render form with errors
    assert response.status_code == 200
    assert b"Application Configuration" in response.data


def test_submit_configuration_no_auth(client):
    """Test configuration submission without authentication redirects to login."""
    response = client.post(
        "/configuration",
        data={
            "cpu_cores": "4",
            "memory_gb": "16",
            "instance_count": "2",
            "storage_type": "SSD",
            "storage_capacity_gb": "500",
            "bandwidth_mbps": "1000",
            "monthly_data_transfer_gb": "5000",
            "utilization_percentage": "70",
            "operating_hours_per_month": "720",
        },
        follow_redirects=False,
    )

    # Should redirect to login page
    assert response.status_code == 302
    assert "/login" in response.location


@patch("packages.web_ui.routes.configuration.requests.post")
def test_submit_configuration_api_timeout(mock_post, client):
    """Test configuration submission with API timeout."""
    import requests

    # Mock timeout exception
    mock_post.side_effect = requests.exceptions.Timeout()

    # Submit configuration form with session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.post(
        "/configuration",
        data={
            "cpu_cores": "4",
            "memory_gb": "16",
            "instance_count": "2",
            "storage_type": "SSD",
            "storage_capacity_gb": "500",
            "bandwidth_mbps": "1000",
            "monthly_data_transfer_gb": "5000",
            "utilization_percentage": "70",
            "operating_hours_per_month": "720",
        },
        follow_redirects=True,
    )

    # Should re-render form with error message
    assert response.status_code == 200
    assert b"Application Configuration" in response.data
