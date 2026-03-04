"""Unit tests for configuration API endpoints."""

import json
import uuid

import pytest

from packages.api.app import create_app
from packages.database import create_tables, get_session, init_database
from packages.security import auth


@pytest.fixture(scope="module")
def app():
    """Create test Flask application."""
    # Initialize test database BEFORE creating app
    init_database("sqlite:///:memory:")
    create_tables()

    test_app = create_app({"TESTING": True, "REQUIRE_HTTPS": False})

    yield test_app


@pytest.fixture(scope="module")
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="module")
def authenticated_user(app):
    """Create and authenticate a user for testing."""
    db = get_session()
    try:
        # Register user
        user = auth.register_user(db, "testuser", "testpassword123")

        # Create session
        session = auth.authenticate(db, "testuser", "testpassword123")

        return {
            "user_id": user.id,
            "username": "testuser",
            "token": session.token,
        }
    finally:
        db.close()


@pytest.fixture
def valid_config_data():
    """Valid configuration data for testing."""
    return {
        "cpu_cores": 4,
        "memory_gb": 16,
        "instance_count": 2,
        "storage_type": "SSD",
        "storage_capacity_gb": 500,
        "storage_iops": 3000,
        "bandwidth_mbps": 1000,
        "monthly_data_transfer_gb": 1000,
        "utilization_percentage": 75,
        "operating_hours_per_month": 720,
    }


@pytest.fixture
def invalid_config_data():
    """Invalid configuration data for testing."""
    return {
        "cpu_cores": -1,  # Invalid: negative
        "memory_gb": 0,  # Invalid: zero
        "instance_count": 2,
        "storage_type": "INVALID",  # Invalid: not SSD/HDD/NVME
        "storage_capacity_gb": 500,
        "bandwidth_mbps": 1000,
        "monthly_data_transfer_gb": 1000,
        "utilization_percentage": 150,  # Invalid: > 100
        "operating_hours_per_month": 1000,  # Invalid: > 744
    }


class TestCreateConfiguration:
    """Tests for POST /api/configurations endpoint."""

    def test_create_configuration_success(self, client, authenticated_user, valid_config_data):
        """Test successful configuration creation."""
        response = client.post(
            "/api/configurations",
            data=json.dumps(valid_config_data),
            content_type="application/json",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert "id" in data
        assert data["user_id"] == authenticated_user["user_id"]
        assert data["cpu_cores"] == 4
        assert data["memory_gb"] == 16
        assert data["storage_type"] == "SSD"
        assert data["utilization_percentage"] == 75
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_configuration_missing_body(self, client, authenticated_user):
        """Test configuration creation with missing request body."""
        response = client.post(
            "/api/configurations",
            content_type="application/json",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "Request body is required" in data["message"]

    def test_create_configuration_validation_error(
        self, client, authenticated_user, invalid_config_data
    ):
        """Test configuration creation with invalid data."""
        response = client.post(
            "/api/configurations",
            data=json.dumps(invalid_config_data),
            content_type="application/json",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "details" in data
        # Should have multiple validation errors
        assert len(data["details"]) > 0
        assert "cpu_cores" in data["details"]
        assert "memory_gb" in data["details"]
        assert "storage_type" in data["details"]

    def test_create_configuration_no_auth(self, client, valid_config_data):
        """Test configuration creation without authentication."""
        response = client.post(
            "/api/configurations",
            data=json.dumps(valid_config_data),
            content_type="application/json",
        )

        # Should fail due to missing authentication
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "AUTHENTICATION_REQUIRED"


class TestGetConfiguration:
    """Tests for GET /api/configurations/<id> endpoint."""

    def test_get_configuration_success(self, client, authenticated_user, valid_config_data):
        """Test successful configuration retrieval."""
        # First create a configuration
        create_response = client.post(
            "/api/configurations",
            data=json.dumps(valid_config_data),
            content_type="application/json",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )
        assert create_response.status_code == 201
        created_config = json.loads(create_response.data)
        config_id = created_config["id"]

        # Now retrieve it
        response = client.get(
            f"/api/configurations/{config_id}",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["id"] == config_id
        assert data["user_id"] == authenticated_user["user_id"]
        assert data["cpu_cores"] == 4
        assert data["memory_gb"] == 16
        assert data["storage_type"] == "SSD"

    def test_get_configuration_not_found(self, client, authenticated_user):
        """Test configuration retrieval when not found."""
        fake_id = str(uuid.uuid4())

        response = client.get(
            f"/api/configurations/{fake_id}",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["error_code"] == "NOT_FOUND"

    def test_get_configuration_no_auth(self, client):
        """Test configuration retrieval without authentication."""
        fake_id = str(uuid.uuid4())

        response = client.get(f"/api/configurations/{fake_id}")

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "AUTHENTICATION_REQUIRED"


class TestValidateConfiguration:
    """Tests for POST /api/configurations/validate endpoint."""

    def test_validate_configuration_valid(self, client, valid_config_data):
        """Test validation with valid configuration."""
        response = client.post(
            "/api/configurations/validate",
            data=json.dumps(valid_config_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["valid"] is True
        assert "Configuration is valid" in data["message"]

    def test_validate_configuration_invalid(self, client, invalid_config_data):
        """Test validation with invalid configuration."""
        response = client.post(
            "/api/configurations/validate",
            data=json.dumps(invalid_config_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["valid"] is False
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "details" in data
        # Should have multiple validation errors
        assert len(data["details"]) > 0
        assert "cpu_cores" in data["details"]
        assert "memory_gb" in data["details"]
        assert "storage_type" in data["details"]
        assert "utilization_percentage" in data["details"]
        assert "operating_hours_per_month" in data["details"]

    def test_validate_configuration_missing_body(self, client):
        """Test validation with missing request body."""
        response = client.post("/api/configurations/validate", content_type="application/json")

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "Request body is required" in data["message"]

    def test_validate_configuration_partial_data(self, client):
        """Test validation with partial configuration data."""
        partial_data = {
            "cpu_cores": 4,
            "memory_gb": 16,
            # Missing other required fields
        }

        response = client.post(
            "/api/configurations/validate",
            data=json.dumps(partial_data),
            content_type="application/json",
        )

        # Should succeed since validation only checks provided fields
        # (None values are allowed in validate_configuration)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["valid"] is True
