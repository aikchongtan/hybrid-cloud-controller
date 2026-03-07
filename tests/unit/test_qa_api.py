"""Unit tests for Q&A API endpoints."""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from packages.api.routes import qa


@pytest.fixture
def mock_config_model():
    """Create a mock configuration model."""
    config = MagicMock()
    config.id = "config-123"
    config.user_id = "user-456"
    config.cpu_cores = 4
    config.memory_gb = 16
    config.instance_count = 2
    config.storage_type = "SSD"
    config.storage_capacity_gb = 500
    config.storage_iops = 3000
    config.bandwidth_mbps = 1000
    config.monthly_data_transfer_gb = 1000
    config.utilization_percentage = 70
    config.operating_hours_per_month = 720
    return config


@pytest.fixture
def mock_tco_model():
    """Create a mock TCO result model."""
    tco = MagicMock()
    tco.id = "tco-789"
    tco.configuration_id = "config-123"

    # Create sample cost breakdown
    costs = {
        "1": {
            "items": [
                {
                    "category": "Hardware",
                    "description": "Server hardware costs",
                    "amount": "10000.00",
                    "unit": "USD/year"
                }
            ],
            "total": "10000.00",
            "currency": "USD"
        }
    }

    tco.on_prem_costs_json = json.dumps(costs)
    tco.aws_costs_json = json.dumps(costs)
    tco.calculated_at = datetime.utcnow()
    return tco


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_build_tco_context(self, mock_config_model, mock_tco_model):
        """Test TCO context building from database models."""
        context = qa._build_tco_context(mock_config_model, mock_tco_model)

        assert context.configuration.cpu_cores == 4
        assert context.configuration.memory_gb == 16
        assert context.configuration.instance_count == 2
        assert 1 in context.on_prem_costs
        assert 1 in context.aws_costs

    def test_deserialize_costs(self):
        """Test cost deserialization from JSON."""
        costs_json = json.dumps({
            "1": {
                "items": [
                    {
                        "category": "Hardware",
                        "description": "Server costs",
                        "amount": "10000.00",
                        "unit": "USD/year"
                    }
                ],
                "total": "10000.00",
                "currency": "USD"
            }
        })

        costs = qa._deserialize_costs(costs_json)

        assert 1 in costs
        assert costs[1].total == Decimal("10000.00")
        assert len(costs[1].items) == 1
        assert costs[1].items[0].category == "Hardware"

    def test_error_response(self):
        """Test error response formatting."""
        response = qa._error_response("TEST_ERROR", "Test message", {"field": "test"})

        assert response["error_code"] == "TEST_ERROR"
        assert response["message"] == "Test message"
        assert response["details"]["field"] == "test"
        assert "timestamp" in response


# NOTE: Full integration tests for the API endpoints should be added in tests/integration/
# These would use Flask's test_client() to properly test the routes with authentication,
# database interactions, and Q&A processing. The helper functions above provide unit test
# coverage for the core logic.
