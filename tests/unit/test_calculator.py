"""Unit tests for TCO calculator module."""

from decimal import Decimal

import pytest

from packages.tco_engine.calculator import (
    AWSPricing,
    Configuration,
    CostBreakdown,
    CostLineItem,
    calculate_tco,
)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return Configuration(
        cpu_cores=4,
        memory_gb=16,
        instance_count=2,
        storage_type="SSD",
        storage_capacity_gb=500,
        storage_iops=3000,
        bandwidth_mbps=100,
        monthly_data_transfer_gb=1000,
        utilization_percentage=70,
        operating_hours_per_month=720,
    )


@pytest.fixture
def sample_pricing():
    """Sample AWS pricing data for testing."""
    return AWSPricing(
        ec2_pricing={
            "t3.micro": Decimal("0.0104"),
            "t3.small": Decimal("0.0208"),
            "t3.medium": Decimal("0.0416"),
            "t3.large": Decimal("0.0832"),
            "m5.large": Decimal("0.096"),
            "m5.xlarge": Decimal("0.192"),
            "m5.2xlarge": Decimal("0.384"),
        },
        ebs_pricing={
            "gp3": Decimal("0.08"),
            "io2": Decimal("0.125"),
            "iops": Decimal("0.065"),
        },
        s3_pricing={
            "standard": Decimal("0.023"),
        },
        data_transfer_pricing={
            "internet_egress": Decimal("0.09"),
            "inter_az": Decimal("0.01"),
        },
    )


def test_calculate_tco_returns_both_paths(sample_config, sample_pricing):
    """Test that calculate_tco returns both on_prem and aws cost breakdowns."""
    result = calculate_tco(sample_config, sample_pricing)

    assert "on_prem" in result
    assert "aws" in result
    assert isinstance(result["on_prem"], dict)
    assert isinstance(result["aws"], dict)


def test_calculate_tco_returns_three_year_periods(sample_config, sample_pricing):
    """Test that calculate_tco returns costs for 1, 3, and 5 years."""
    result = calculate_tco(sample_config, sample_pricing)

    # Check on_prem has all three periods
    assert 1 in result["on_prem"]
    assert 3 in result["on_prem"]
    assert 5 in result["on_prem"]

    # Check aws has all three periods
    assert 1 in result["aws"]
    assert 3 in result["aws"]
    assert 5 in result["aws"]


def test_calculate_tco_returns_cost_breakdowns(sample_config, sample_pricing):
    """Test that calculate_tco returns CostBreakdown objects."""
    result = calculate_tco(sample_config, sample_pricing)

    # Check on_prem breakdowns
    for years in [1, 3, 5]:
        breakdown = result["on_prem"][years]
        assert isinstance(breakdown, CostBreakdown)
        assert isinstance(breakdown.items, list)
        assert isinstance(breakdown.total, Decimal)
        assert breakdown.currency == "USD"

    # Check aws breakdowns
    for years in [1, 3, 5]:
        breakdown = result["aws"][years]
        assert isinstance(breakdown, CostBreakdown)
        assert isinstance(breakdown.items, list)
        assert isinstance(breakdown.total, Decimal)
        assert breakdown.currency == "USD"


def test_on_prem_breakdown_has_all_categories(sample_config, sample_pricing):
    """Test that on_prem breakdown includes all required cost categories."""
    result = calculate_tco(sample_config, sample_pricing)
    breakdown = result["on_prem"][1]

    categories = {item.category for item in breakdown.items}
    expected_categories = {"Hardware", "Power", "Cooling", "Maintenance", "Data Transfer"}

    assert categories == expected_categories


def test_aws_breakdown_has_all_categories(sample_config, sample_pricing):
    """Test that aws breakdown includes all required cost categories."""
    result = calculate_tco(sample_config, sample_pricing)
    breakdown = result["aws"][1]

    categories = {item.category for item in breakdown.items}
    expected_categories = {"EC2", "EBS", "S3", "Data Transfer"}

    assert categories == expected_categories


def test_cost_breakdown_total_matches_sum_of_items(sample_config, sample_pricing):
    """Test that breakdown total equals sum of all line items."""
    result = calculate_tco(sample_config, sample_pricing)

    # Check on_prem
    for years in [1, 3, 5]:
        breakdown = result["on_prem"][years]
        calculated_total = sum(item.amount for item in breakdown.items)
        assert breakdown.total == calculated_total

    # Check aws
    for years in [1, 3, 5]:
        breakdown = result["aws"][years]
        calculated_total = sum(item.amount for item in breakdown.items)
        assert breakdown.total == calculated_total


def test_costs_are_non_negative(sample_config, sample_pricing):
    """Test that all costs are non-negative."""
    result = calculate_tco(sample_config, sample_pricing)

    # Check on_prem
    for years in [1, 3, 5]:
        breakdown = result["on_prem"][years]
        assert breakdown.total >= 0
        for item in breakdown.items:
            assert item.amount >= 0

    # Check aws
    for years in [1, 3, 5]:
        breakdown = result["aws"][years]
        assert breakdown.total >= 0
        for item in breakdown.items:
            assert item.amount >= 0


def test_multi_year_costs_scale_appropriately(sample_config, sample_pricing):
    """Test that 3-year >= 1-year and 5-year >= 3-year for recurring costs."""
    result = calculate_tco(sample_config, sample_pricing)

    # Check on_prem scaling
    on_prem_1yr = result["on_prem"][1].total
    on_prem_3yr = result["on_prem"][3].total
    on_prem_5yr = result["on_prem"][5].total

    assert on_prem_3yr >= on_prem_1yr
    assert on_prem_5yr >= on_prem_3yr

    # Check aws scaling
    aws_1yr = result["aws"][1].total
    aws_3yr = result["aws"][3].total
    aws_5yr = result["aws"][5].total

    assert aws_3yr >= aws_1yr
    assert aws_5yr >= aws_3yr


def test_cost_line_items_have_required_fields():
    """Test that CostLineItem has all required fields."""
    item = CostLineItem(
        category="Test",
        description="Test description",
        amount=Decimal("100"),
        unit="USD",
    )

    assert item.category == "Test"
    assert item.description == "Test description"
    assert item.amount == Decimal("100")
    assert item.unit == "USD"


def test_cost_breakdown_has_required_fields():
    """Test that CostBreakdown has all required fields."""
    items = [
        CostLineItem(
            category="Test",
            description="Test",
            amount=Decimal("100"),
            unit="USD",
        )
    ]
    breakdown = CostBreakdown(items=items, total=Decimal("100"), currency="USD")

    assert breakdown.items == items
    assert breakdown.total == Decimal("100")
    assert breakdown.currency == "USD"


def test_configuration_dataclass():
    """Test that Configuration dataclass works correctly."""
    config = Configuration(
        cpu_cores=4,
        memory_gb=16,
        instance_count=2,
        storage_type="SSD",
        storage_capacity_gb=500,
        storage_iops=3000,
        bandwidth_mbps=100,
        monthly_data_transfer_gb=1000,
        utilization_percentage=70,
        operating_hours_per_month=720,
    )

    assert config.cpu_cores == 4
    assert config.memory_gb == 16
    assert config.instance_count == 2
    assert config.storage_type == "SSD"
    assert config.storage_capacity_gb == 500
    assert config.storage_iops == 3000
    assert config.bandwidth_mbps == 100
    assert config.monthly_data_transfer_gb == 1000
    assert config.utilization_percentage == 70
    assert config.operating_hours_per_month == 720


def test_aws_pricing_dataclass():
    """Test that AWSPricing dataclass works correctly."""
    pricing = AWSPricing(
        ec2_pricing={"m5.large": Decimal("0.096")},
        ebs_pricing={"gp3": Decimal("0.08")},
        s3_pricing={"standard": Decimal("0.023")},
        data_transfer_pricing={"internet_egress": Decimal("0.09")},
    )

    assert pricing.ec2_pricing == {"m5.large": Decimal("0.096")}
    assert pricing.ebs_pricing == {"gp3": Decimal("0.08")}
    assert pricing.s3_pricing == {"standard": Decimal("0.023")}
    assert pricing.data_transfer_pricing == {"internet_egress": Decimal("0.09")}
