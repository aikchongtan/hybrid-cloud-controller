"""Unit tests for Monitoring API endpoints."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from packages.api.routes import monitoring
from packages.monitoring import dashboard


@pytest.fixture
def mock_resource_model():
    """Create a mock resource model."""
    resource = MagicMock()
    resource.id = "resource-123"
    resource.resource_type = "ec2"
    resource.status = "running"
    resource.provision = MagicMock()
    return resource


@pytest.fixture
def mock_current_metrics():
    """Create mock current metrics."""
    return dashboard.CurrentMetrics(
        resource_id="resource-123",
        cpu_percent=45.5,
        memory_percent=62.3,
        storage_percent=38.7,
        network_mbps=12.4,
        timestamp=datetime.utcnow(),
    )


@pytest.fixture
def mock_historical_metrics():
    """Create mock historical metrics."""
    return dashboard.HistoricalMetrics(
        resource_id="resource-123",
        time_range=dashboard.TimeRange.ONE_HOUR,
        data_points=[
            {
                "timestamp": "2026-03-06T10:00:00",
                "cpu": 45.0,
                "memory": 60.0,
                "storage": 40.0,
                "network": 10.0,
            },
            {
                "timestamp": "2026-03-06T10:30:00",
                "cpu": 50.0,
                "memory": 65.0,
                "storage": 42.0,
                "network": 15.0,
            },
        ],
    )


@pytest.fixture
def mock_alerts():
    """Create mock alerts."""
    return [
        dashboard.Alert(
            resource_id="resource-123",
            metric_type="cpu",
            current_value=85.0,
            threshold=80.0,
            severity="warning",
            timestamp=datetime.utcnow(),
        )
    ]


@pytest.fixture
def mock_resource_health():
    """Create mock resource health."""
    return dashboard.ResourceHealth(
        resource_id="resource-123",
        is_reachable=True,
        last_successful_collection=datetime.utcnow(),
        status="healthy",
    )


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_error_response(self):
        """Test error response formatting."""
        response = monitoring._error_response(
            "TEST_ERROR", "Test message", {"field": "test"}
        )

        assert response["error_code"] == "TEST_ERROR"
        assert response["message"] == "Test message"
        assert response["details"]["field"] == "test"
        assert "timestamp" in response

    def test_error_response_without_details(self):
        """Test error response without details."""
        response = monitoring._error_response("TEST_ERROR", "Test message")

        assert response["error_code"] == "TEST_ERROR"
        assert response["message"] == "Test message"
        assert "details" not in response
        assert "timestamp" in response


# NOTE: Full integration tests for the API endpoints should be added in tests/integration/
# These would use Flask's test_client() to properly test the routes with authentication,
# database interactions, and monitoring dashboard integration. The helper functions above
# provide unit test coverage for the core logic.
