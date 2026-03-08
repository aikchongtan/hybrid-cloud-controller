"""Unit tests for monitoring routes."""

from pathlib import Path

import pytest
from flask import Flask

from packages.web_ui.routes import monitoring


@pytest.fixture
def app():
    """Create Flask app for testing."""
    # Get the web_ui package directory
    web_ui_dir = Path(__file__).parent.parent.parent / "packages" / "web_ui"

    app = Flask(
        __name__,
        template_folder=str(web_ui_dir / "templates"),
        static_folder=str(web_ui_dir / "static"),
    )
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True

    # Register auth blueprint for url_for to work
    from packages.web_ui.routes import auth, configuration

    app.register_blueprint(auth.bp)
    app.register_blueprint(configuration.bp)

    # Register monitoring blueprint
    app.register_blueprint(monitoring.bp)

    # Register index route for testing
    @app.route("/")
    def index():
        return "Home Page"

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_monitoring_dashboard_get_renders_template(client):
    """Test GET /monitoring renders monitoring dashboard template."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200
    assert b"Monitoring Dashboard" in response.data
    assert b"Real-time resource metrics" in response.data


def test_monitoring_dashboard_no_auth_redirects_to_login(client):
    """Test monitoring dashboard without authentication redirects to login."""
    response = client.get("/monitoring", follow_redirects=False)

    # Should redirect to login page
    assert response.status_code == 302
    assert "/login" in response.location


def test_monitoring_dashboard_contains_time_range_selector(client):
    """Test monitoring dashboard contains time range selector buttons."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200

    # Check for time range buttons
    assert b"Current" in response.data
    assert b"1 Hour" in response.data
    assert b"24 Hours" in response.data
    assert b"7 Days" in response.data
    assert b"time-range-btn" in response.data


def test_monitoring_dashboard_contains_loading_spinner(client):
    """Test monitoring dashboard contains loading spinner."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200

    # Check for loading spinner
    assert b'id="loading"' in response.data
    assert b"loading-spinner" in response.data


def test_monitoring_dashboard_contains_no_resources_message(client):
    """Test monitoring dashboard contains no resources message."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200

    # Check for no resources message
    assert b'id="no-resources"' in response.data
    assert b"No Resources Provisioned" in response.data


def test_monitoring_dashboard_contains_resources_grid(client):
    """Test monitoring dashboard contains resources grid container."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200

    # Check for resources grid
    assert b'id="resources-grid"' in response.data
    assert b"resource-grid" in response.data


def test_monitoring_dashboard_contains_javascript_functions(client):
    """Test monitoring dashboard contains required JavaScript functions."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200

    # Check for JavaScript functions
    assert b"loadResources" in response.data
    assert b"loadAllResources" in response.data
    assert b"loadSpecificResource" in response.data
    assert b"renderResourceCards" in response.data
    assert b"createResourceCard" in response.data
    assert b"startAutoRefresh" in response.data


def test_monitoring_dashboard_auto_refresh_interval(client):
    """Test monitoring dashboard has 30-second auto-refresh interval."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200

    # Check for 30-second refresh interval (30000 milliseconds)
    assert b"30000" in response.data
    assert b"REFRESH_INTERVAL" in response.data


def test_monitoring_resource_get_renders_template(client):
    """Test GET /monitoring/<resource_id> renders monitoring dashboard for specific resource."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring/resource-123")
    assert response.status_code == 200
    assert b"Monitoring Dashboard" in response.data


def test_monitoring_resource_no_auth_redirects_to_login(client):
    """Test monitoring resource page without authentication redirects to login."""
    response = client.get("/monitoring/resource-123", follow_redirects=False)

    # Should redirect to login page
    assert response.status_code == 302
    assert "/login" in response.location


def test_monitoring_dashboard_contains_metric_cards_styling(client):
    """Test monitoring dashboard contains metric card styling."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200

    # Check for metric card styling
    assert b"metric-card" in response.data
    assert b"metric-value" in response.data
    assert b"metric-label" in response.data
    assert b"health-indicator" in response.data


def test_monitoring_dashboard_contains_api_endpoint_configuration(client):
    """Test monitoring dashboard contains API endpoint configuration."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200

    # Check for API endpoint configuration
    assert b"API_BASE_URL" in response.data
    assert b"/api/monitoring" in response.data


def test_monitoring_dashboard_contains_metric_color_functions(client):
    """Test monitoring dashboard contains metric color coding functions."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200

    # Check for color coding functions
    assert b"getMetricColor" in response.data
    assert b"getProgressClass" in response.data
    assert b"getHealthIcon" in response.data
    assert b"getHealthTagClass" in response.data


def test_monitoring_dashboard_contains_alert_handling(client):
    """Test monitoring dashboard contains alert handling for >80% utilization."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/monitoring")
    assert response.status_code == 200

    # Check for alert handling
    assert b"alerts" in response.data
    assert b"alert-banner" in response.data
    assert b"threshold" in response.data
