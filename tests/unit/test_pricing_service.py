"""Unit tests for pricing service."""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from packages.database import init_database, create_tables, get_session, drop_tables
from packages.database.models import PricingDataModel
from packages.pricing_service import fetcher


@pytest.fixture
def test_db():
    """Set up test database."""
    init_database("sqlite:///:memory:")
    create_tables()
    yield
    drop_tables()


@pytest.fixture
def sample_pricing_data():
    """Sample pricing data for testing."""
    return {
        "ec2_pricing": {
            "t3.micro": Decimal("0.0104"),
            "t3.small": Decimal("0.0208"),
            "m5.large": Decimal("0.096"),
        },
        "ebs_pricing": {
            "gp3": Decimal("0.08"),
            "gp2": Decimal("0.10"),
        },
        "s3_pricing": {
            "STANDARD": Decimal("0.023"),
            "GLACIER": Decimal("0.004"),
        },
        "data_transfer_pricing": {
            "internet_egress": Decimal("0.09"),
            "inter_region": Decimal("0.02"),
        },
    }


def test_serialize_deserialize_pricing():
    """Test pricing serialization and deserialization."""
    pricing = {
        "t3.micro": Decimal("0.0104"),
        "m5.large": Decimal("0.096"),
    }
    
    # Serialize
    serialized = fetcher._serialize_pricing(pricing)
    assert isinstance(serialized, str)
    
    # Deserialize
    deserialized = fetcher._deserialize_pricing(serialized)
    assert deserialized == pricing
    assert all(isinstance(v, Decimal) for v in deserialized.values())


def test_store_and_retrieve_pricing_data(test_db, sample_pricing_data):
    """Test storing and retrieving pricing data from database."""
    # Store pricing data
    fetcher._store_pricing_data(sample_pricing_data)
    
    # Retrieve current pricing
    retrieved = fetcher.get_current_pricing()
    
    assert retrieved is not None
    assert retrieved["ec2_pricing"] == sample_pricing_data["ec2_pricing"]
    assert retrieved["ebs_pricing"] == sample_pricing_data["ebs_pricing"]
    assert retrieved["s3_pricing"] == sample_pricing_data["s3_pricing"]
    assert retrieved["data_transfer_pricing"] == sample_pricing_data["data_transfer_pricing"]


def test_get_current_pricing_empty_database(test_db):
    """Test get_current_pricing returns None when database is empty."""
    result = fetcher.get_current_pricing()
    assert result is None


def test_get_current_pricing_returns_most_recent(test_db, sample_pricing_data):
    """Test get_current_pricing returns the most recent record."""
    # Store first pricing data
    fetcher._store_pricing_data(sample_pricing_data)
    
    # Store second pricing data with different values
    updated_pricing = sample_pricing_data.copy()
    updated_pricing["ec2_pricing"] = {
        "t3.micro": Decimal("0.0110"),  # Updated price
    }
    fetcher._store_pricing_data(updated_pricing)
    
    # Retrieve should return the most recent
    retrieved = fetcher.get_current_pricing()
    assert retrieved["ec2_pricing"]["t3.micro"] == Decimal("0.0110")


def test_get_pricing_history(test_db, sample_pricing_data):
    """Test retrieving pricing history within date range."""
    # Store multiple pricing records
    base_time = datetime.utcnow()
    
    session = get_session()
    try:
        for i in range(3):
            record = PricingDataModel(
                id=str(uuid4()),
                ec2_pricing_json=fetcher._serialize_pricing(sample_pricing_data["ec2_pricing"]),
                ebs_pricing_json=fetcher._serialize_pricing(sample_pricing_data["ebs_pricing"]),
                s3_pricing_json=fetcher._serialize_pricing(sample_pricing_data["s3_pricing"]),
                data_transfer_pricing_json=fetcher._serialize_pricing(
                    sample_pricing_data["data_transfer_pricing"]
                ),
                fetched_at=base_time + timedelta(hours=i),
            )
            session.add(record)
        session.commit()
    finally:
        session.close()
    
    # Query history
    start_date = base_time - timedelta(hours=1)
    end_date = base_time + timedelta(hours=5)
    history = fetcher.get_pricing_history(start_date, end_date)
    
    assert len(history) == 3
    # Verify chronological order
    for i in range(len(history) - 1):
        assert history[i]["fetched_at"] < history[i + 1]["fetched_at"]


def test_get_pricing_history_filters_by_date(test_db, sample_pricing_data):
    """Test pricing history filtering by date range."""
    base_time = datetime.utcnow()
    
    session = get_session()
    try:
        # Store records at different times
        for i in range(5):
            record = PricingDataModel(
                id=str(uuid4()),
                ec2_pricing_json=fetcher._serialize_pricing(sample_pricing_data["ec2_pricing"]),
                ebs_pricing_json=fetcher._serialize_pricing(sample_pricing_data["ebs_pricing"]),
                s3_pricing_json=fetcher._serialize_pricing(sample_pricing_data["s3_pricing"]),
                data_transfer_pricing_json=fetcher._serialize_pricing(
                    sample_pricing_data["data_transfer_pricing"]
                ),
                fetched_at=base_time + timedelta(days=i),
            )
            session.add(record)
        session.commit()
    finally:
        session.close()
    
    # Query only middle 3 records
    start_date = base_time + timedelta(days=1)
    end_date = base_time + timedelta(days=3)
    history = fetcher.get_pricing_history(start_date, end_date)
    
    assert len(history) == 3


def test_fallback_pricing_values():
    """Test fallback pricing functions return valid Decimals."""
    # EC2 fallback
    ec2_price = fetcher._get_fallback_ec2_price("t3.micro")
    assert isinstance(ec2_price, Decimal)
    assert ec2_price > 0
    
    # Unknown instance type should return default
    unknown_price = fetcher._get_fallback_ec2_price("unknown.type")
    assert isinstance(unknown_price, Decimal)
    assert unknown_price == Decimal("0.10")
    
    # EBS fallback
    ebs_price = fetcher._get_fallback_ebs_price("gp3")
    assert isinstance(ebs_price, Decimal)
    assert ebs_price > 0
    
    # S3 fallback
    s3_price = fetcher._get_fallback_s3_price("STANDARD")
    assert isinstance(s3_price, Decimal)
    assert s3_price > 0


@patch("packages.pricing_service.fetcher.boto3.client")
def test_fetch_pricing_data_uses_fallback_on_error(mock_boto_client, test_db):
    """Test that fetch_pricing_data uses fallback values when individual API calls fail."""
    # Mock boto3 client to raise an error for individual calls
    mock_client = Mock()
    mock_client.get_products.side_effect = ClientError(
        {"Error": {"Code": "ServiceUnavailable", "Message": "Service unavailable"}},
        "GetProducts",
    )
    mock_boto_client.return_value = mock_client
    
    # Should complete successfully using fallback values
    result = fetcher.fetch_pricing_data()
    
    # Verify it returns pricing data (using fallbacks)
    assert "ec2_pricing" in result
    assert "ebs_pricing" in result
    assert "s3_pricing" in result
    assert "data_transfer_pricing" in result
    
    # Verify fallback values are used
    assert result["ec2_pricing"]["t3.micro"] == Decimal("0.0104")


@patch("packages.pricing_service.fetcher.boto3.client")
def test_fetch_ec2_pricing_uses_fallback_on_individual_failure(mock_boto_client):
    """Test that individual EC2 pricing failures use fallback values."""
    mock_client = Mock()
    # Make get_products fail for individual calls
    mock_client.get_products.side_effect = Exception("API Error")
    
    result = fetcher._fetch_ec2_pricing(mock_client)
    
    # Should return fallback prices for all instance types
    assert "t3.micro" in result
    assert isinstance(result["t3.micro"], Decimal)
    assert result["t3.micro"] > 0


def test_data_transfer_pricing_returns_expected_types():
    """Test data transfer pricing returns correct structure."""
    mock_client = Mock()
    result = fetcher._fetch_data_transfer_pricing(mock_client)
    
    assert "internet_egress" in result
    assert "inter_region" in result
    assert "inter_az" in result
    assert "inbound" in result
    
    # All values should be Decimals
    for value in result.values():
        assert isinstance(value, Decimal)
    
    # Inbound should be free
    assert result["inbound"] == Decimal("0.00")
