"""Unit tests for provisioning routes."""

from pathlib import Path

import pytest
from flask import Flask

from packages.web_ui.routes import provisioning


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

    # Register all blueprints for url_for to work
    from packages.web_ui.routes import auth, configuration, monitoring, qa

    app.register_blueprint(auth.bp)
    app.register_blueprint(configuration.bp)
    app.register_blueprint(monitoring.bp)
    app.register_blueprint(qa.bp)
    app.register_blueprint(provisioning.bp)

    # Register index route for testing
    @app.route("/")
    def index():
        return "Home Page"

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_provision_page_get_renders_template(client):
    """Test GET /provision/<config_id> renders provisioning template."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/provision/config-123")
    assert response.status_code == 200
    assert b"Resource Provisioning" in response.data
    assert b"Select Cloud Path" in response.data
    assert b"AWS Cloud" in response.data
    assert b"On-Premises IaaS" in response.data
    assert b"On-Premises CaaS" in response.data


def test_provision_page_no_auth_redirects_to_login(client):
    """Test provision page without authentication redirects to login."""
    response = client.get("/provision/config-123", follow_redirects=False)

    # Should redirect to login page
    assert response.status_code == 302
    assert "/login" in response.location


def test_provision_page_stores_config_id_in_session(client):
    """Test provision page stores config_id in session."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/provision/config-123")
    assert response.status_code == 200

    # Check session contains config_id
    with client.session_transaction() as sess:
        assert sess.get("config_id") == "config-123"


def test_provision_page_contains_cloud_path_cards(client):
    """Test provision page contains all cloud path selection cards."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/provision/config-123")
    assert response.status_code == 200

    # Check for AWS card
    assert b"AWS Cloud" in response.data
    assert b"EC2 instances" in response.data
    assert b"EBS storage" in response.data

    # Check for IaaS card
    assert b"On-Premises IaaS" in response.data
    assert b"QEMU/KVM VMs" in response.data
    assert b"SSH access" in response.data

    # Check for CaaS card
    assert b"On-Premises CaaS" in response.data
    assert b"Docker/Podman" in response.data
    assert b"Container-based deployment" in response.data


def test_provision_page_contains_configuration_sections(client):
    """Test provision page contains configuration sections for each cloud path."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/provision/config-123")
    assert response.status_code == 200

    # Check for AWS configuration
    assert b"aws-container-image" in response.data
    assert b"aws-env-vars" in response.data

    # Check for IaaS configuration
    assert b"iaas-mock-mode" in response.data

    # Check for CaaS configuration
    assert b"caas-container-image" in response.data
    assert b"caas-env-vars" in response.data


def test_provision_page_contains_step_indicator(client):
    """Test provision page contains step indicator."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/provision/config-123")
    assert response.status_code == 200

    # Check for step indicator
    assert b"Select Cloud Path" in response.data
    assert b"Configure" in response.data
    assert b"Provision" in response.data
    assert b"Deploy" in response.data


def test_provision_page_contains_aws_confirmation_modal(client):
    """Test provision page contains AWS confirmation modal."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/provision/config-123")
    assert response.status_code == 200

    # Check for AWS confirmation modal
    assert b"Confirm AWS Provisioning" in response.data
    assert b"LocalStack emulation" in response.data


def test_provision_page_contains_provisioning_logs_section(client):
    """Test provision page contains provisioning logs section."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/provision/config-123")
    assert response.status_code == 200

    # Check for logs container
    assert b"provisioning-logs" in response.data
    assert b"log-container" in response.data


def test_provision_page_contains_results_section(client):
    """Test provision page contains results section."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/provision/config-123")
    assert response.status_code == 200

    # Check for results section
    assert b"resources-container" in response.data
    assert b"Provisioning Complete" in response.data


def test_provision_page_contains_javascript_functions(client):
    """Test provision page contains required JavaScript functions."""
    # Set session token
    with client.session_transaction() as sess:
        sess["token"] = "test-token-123"

    response = client.get("/provision/config-123")
    assert response.status_code == 200

    # Check for JavaScript functions
    assert b"selectCloudPath" in response.data
    assert b"continueToConfiguration" in response.data
    assert b"startProvisioning" in response.data
    assert b"pollProvisioningStatus" in response.data
    assert b"displayResults" in response.data
