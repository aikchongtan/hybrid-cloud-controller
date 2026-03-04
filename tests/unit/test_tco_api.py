"""Unit tests for TCO API endpoints."""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from packages.api.app import create_app
from packages.database import create_tables, get_session, init_database
from packages.database.models import ConfigurationModel, TCOResultModel
from packages.security import auth
from packages.tco_engine.calculator import AWSPricing, CostBreakdown, CostLineItem


@pytest.fixture(scope="module")
def app():
    """Create Flask app for testing."""
    # Initialize test database BEFORE creating app
    init_database("sqlite:///:memory:")
    create_tables()

    test_app = create_app({"TESTING": True, "REQUIRE_HTTPS": False})
    return test_app


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
def test_configuration(authenticated_user):
    """Create a test configuration in the database."""
    db = get_session()
    try:
        config_id = str(uuid4())
        now = datetime.utcnow()

        config = ConfigurationModel(
            id=config_id,
            user_id=authenticated_user["user_id"],
            cpu_cores=4,
            memory_gb=16,
            instance_count=2,
            storage_type="SSD",
            storage_capacity_gb=500,
            storage_iops=3000,
            bandwidth_mbps=1000,
            monthly_data_transfer_gb=1000,
            utilization_percentage=70,
            operating_hours_per_month=720,
            created_at=now,
            updated_at=now,
        )

        db.add(config)
        db.commit()

        # Return just the ID to avoid detached instance issues
        return config_id
    finally:
        db.close()


@pytest.fixture
def mock_pricing_data():
    """Create mock pricing data."""
    return {
        "ec2_pricing": {"t3.medium": Decimal("0.0416")},
        "ebs_pricing": {"gp3": Decimal("0.08")},
        "s3_pricing": {"STANDARD": Decimal("0.023")},
        "data_transfer_pricing": {"internet_egress": Decimal("0.09")},
    }


@pytest.fixture
def mock_tco_result():
    """Create mock TCO calculation result."""
    on_prem_breakdown = CostBreakdown(
        items=[
            CostLineItem(
                category="Hardware",
                description="Server hardware",
                amount=Decimal("10000.00"),
                unit="USD",
            ),
            CostLineItem(
                category="Power",
                description="Electricity",
                amount=Decimal("1200.00"),
                unit="USD",
            ),
        ],
        total=Decimal("11200.00"),
        currency="USD",
    )

    aws_breakdown = CostBreakdown(
        items=[
            CostLineItem(
                category="EC2",
                description="EC2 instances",
                amount=Decimal("5000.00"),
                unit="USD",
            ),
            CostLineItem(
                category="EBS",
                description="EBS storage",
                amount=Decimal("480.00"),
                unit="USD",
            ),
        ],
        total=Decimal("5480.00"),
        currency="USD",
    )

    return {
        "on_prem": {1: on_prem_breakdown, 3: on_prem_breakdown, 5: on_prem_breakdown},
        "aws": {1: aws_breakdown, 3: aws_breakdown, 5: aws_breakdown},
    }


class TestCalculateTCO:
    """Tests for POST /api/tco/<config_id>/calculate endpoint."""

    @patch("packages.api.routes.tco.pricing_fetcher.get_current_pricing")
    @patch("packages.api.routes.tco.calculator.calculate_tco")
    def test_calculate_tco_success(
        self,
        mock_calculate_tco,
        mock_get_pricing,
        client,
        authenticated_user,
        test_configuration,
        mock_pricing_data,
        mock_tco_result,
    ):
        """Test successful TCO calculation."""
        # Setup mocks
        mock_get_pricing.return_value = mock_pricing_data
        mock_calculate_tco.return_value = mock_tco_result

        # Make request
        response = client.post(
            f"/api/tco/{test_configuration}/calculate",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)

        assert "id" in data
        assert data["configuration_id"] == test_configuration
        assert "on_prem_costs" in data
        assert "aws_costs" in data
        assert "recommendation" in data
        assert "calculated_at" in data

        # Verify cost structure
        assert "1" in data["on_prem_costs"]
        assert "3" in data["on_prem_costs"]
        assert "5" in data["on_prem_costs"]
        assert "items" in data["on_prem_costs"]["1"]
        assert "total" in data["on_prem_costs"]["1"]

    def test_calculate_tco_no_auth(self, client, test_configuration):
        """Test TCO calculation without authentication."""
        # Make request without auth header
        response = client.post(f"/api/tco/{test_configuration}/calculate")

        # Verify response
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "AUTHENTICATION_REQUIRED"

    def test_calculate_tco_config_not_found(self, client, authenticated_user):
        """Test TCO calculation with non-existent configuration."""
        fake_id = str(uuid4())

        # Make request
        response = client.post(
            f"/api/tco/{fake_id}/calculate",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        # Verify response
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["error_code"] == "NOT_FOUND"

    @patch("packages.api.routes.tco.pricing_fetcher.get_current_pricing")
    def test_calculate_tco_no_pricing_data(
        self,
        mock_get_pricing,
        client,
        authenticated_user,
        test_configuration,
    ):
        """Test TCO calculation when pricing data is unavailable."""
        # Setup mock to return None
        mock_get_pricing.return_value = None

        # Make request
        response = client.post(
            f"/api/tco/{test_configuration}/calculate",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        # Verify response
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["error_code"] == "EXTERNAL_SERVICE_ERROR"


class TestGetTCOResults:
    """Tests for GET /api/tco/<config_id> endpoint."""

    def test_get_tco_results_success(
        self, client, authenticated_user, test_configuration, mock_tco_result
    ):
        """Test successful TCO results retrieval."""
        # First create a TCO result
        db = get_session()
        try:
            tco_id = str(uuid4())
            now = datetime.utcnow()

            # Serialize costs
            from packages.api.routes.tco import _serialize_costs

            tco_model = TCOResultModel(
                id=tco_id,
                configuration_id=test_configuration,
                on_prem_costs_json=_serialize_costs(mock_tco_result["on_prem"]),
                aws_costs_json=_serialize_costs(mock_tco_result["aws"]),
                recommendation="AWS is recommended",
                calculated_at=now,
            )

            db.add(tco_model)
            db.commit()
        finally:
            db.close()

        # Now retrieve it
        response = client.get(
            f"/api/tco/{test_configuration}",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)

        assert data["id"] == tco_id
        assert data["configuration_id"] == test_configuration
        assert "on_prem_costs" in data
        assert "aws_costs" in data
        assert data["recommendation"] == "AWS is recommended"
        assert "calculated_at" in data

    def test_get_tco_results_no_auth(self, client, test_configuration):
        """Test TCO results retrieval without authentication."""
        # Make request without auth header
        response = client.get(f"/api/tco/{test_configuration}")

        # Verify response
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "AUTHENTICATION_REQUIRED"

    def test_get_tco_results_not_found(self, client, authenticated_user):
        """Test TCO results retrieval when no results exist."""
        fake_id = str(uuid4())

        # Make request
        response = client.get(
            f"/api/tco/{fake_id}",
            headers={"Authorization": f"Bearer {authenticated_user['token']}"},
        )

        # Verify response
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["error_code"] == "NOT_FOUND"


class TestRecommendationGeneration:
    """Tests for recommendation generation logic."""

    def test_recommendation_on_prem_cheaper(self):
        """Test recommendation when on-premises is cheaper."""
        from packages.api.routes.tco import _generate_recommendation

        on_prem_breakdown = CostBreakdown(
            items=[],
            total=Decimal("10000.00"),
            currency="USD",
        )
        aws_breakdown = CostBreakdown(
            items=[],
            total=Decimal("15000.00"),
            currency="USD",
        )

        tco_result = {
            "on_prem": {1: on_prem_breakdown, 3: on_prem_breakdown, 5: on_prem_breakdown},
            "aws": {1: aws_breakdown, 3: aws_breakdown, 5: aws_breakdown},
        }

        recommendation = _generate_recommendation(tco_result)

        assert "On-premises hosting is recommended" in recommendation
        assert "5,000.00" in recommendation
        assert "33.3%" in recommendation

    def test_recommendation_aws_cheaper(self):
        """Test recommendation when AWS is cheaper."""
        from packages.api.routes.tco import _generate_recommendation

        on_prem_breakdown = CostBreakdown(
            items=[],
            total=Decimal("15000.00"),
            currency="USD",
        )
        aws_breakdown = CostBreakdown(
            items=[],
            total=Decimal("10000.00"),
            currency="USD",
        )

        tco_result = {
            "on_prem": {1: on_prem_breakdown, 3: on_prem_breakdown, 5: on_prem_breakdown},
            "aws": {1: aws_breakdown, 3: aws_breakdown, 5: aws_breakdown},
        }

        recommendation = _generate_recommendation(tco_result)

        assert "AWS cloud hosting is recommended" in recommendation
        assert "5,000.00" in recommendation
        assert "33.3%" in recommendation

    def test_recommendation_similar_costs(self):
        """Test recommendation when costs are similar."""
        from packages.api.routes.tco import _generate_recommendation

        breakdown = CostBreakdown(
            items=[],
            total=Decimal("10000.00"),
            currency="USD",
        )

        tco_result = {
            "on_prem": {1: breakdown, 3: breakdown, 5: breakdown},
            "aws": {1: breakdown, 3: breakdown, 5: breakdown},
        }

        recommendation = _generate_recommendation(tco_result)

        assert "Both options have similar 3-year costs" in recommendation


class TestCostSerialization:
    """Tests for cost serialization and deserialization."""

    def test_serialize_and_deserialize_costs(self):
        """Test round-trip serialization of costs."""
        from packages.api.routes.tco import _deserialize_costs, _serialize_costs

        # Create original costs
        breakdown = CostBreakdown(
            items=[
                CostLineItem(
                    category="Hardware",
                    description="Server hardware",
                    amount=Decimal("10000.50"),
                    unit="USD",
                ),
                CostLineItem(
                    category="Power",
                    description="Electricity",
                    amount=Decimal("1200.25"),
                    unit="USD",
                ),
            ],
            total=Decimal("11200.75"),
            currency="USD",
        )

        original_costs = {1: breakdown, 3: breakdown, 5: breakdown}

        # Serialize and deserialize
        serialized = _serialize_costs(original_costs)
        deserialized = _deserialize_costs(serialized)

        # Verify round-trip
        assert len(deserialized) == 3
        assert 1 in deserialized
        assert 3 in deserialized
        assert 5 in deserialized

        for year in [1, 3, 5]:
            assert deserialized[year].total == Decimal("11200.75")
            assert deserialized[year].currency == "USD"
            assert len(deserialized[year].items) == 2
            assert deserialized[year].items[0].category == "Hardware"
            assert deserialized[year].items[0].amount == Decimal("10000.50")
            assert deserialized[year].items[1].category == "Power"
            assert deserialized[year].items[1].amount == Decimal("1200.25")
