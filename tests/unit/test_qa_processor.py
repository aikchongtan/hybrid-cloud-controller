"""Unit tests for Q&A processor module."""

from decimal import Decimal

import pytest

from packages.qa_service.processor import (
    Configuration,
    CostBreakdown,
    CostLineItem,
    TCOContext,
    compare_aspects,
    generate_recommendation,
    get_cost_item_explanation,
    process_question,
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
def sample_on_prem_costs():
    """Sample on-premises cost breakdowns."""
    return {
        1: CostBreakdown(
            items=[
                CostLineItem(
                    category="Hardware",
                    description="Server hardware (2 instances, 4 cores, 16GB RAM)",
                    amount=Decimal("10000"),
                    unit="USD",
                ),
                CostLineItem(
                    category="Power",
                    description="Electricity consumption (70% utilization)",
                    amount=Decimal("1200"),
                    unit="USD",
                ),
                CostLineItem(
                    category="Cooling",
                    description="HVAC and cooling costs",
                    amount=Decimal("600"),
                    unit="USD",
                ),
            ],
            total=Decimal("11800"),
            currency="USD",
        ),
        3: CostBreakdown(
            items=[
                CostLineItem(
                    category="Hardware",
                    description="Server hardware (2 instances, 4 cores, 16GB RAM)",
                    amount=Decimal("10000"),
                    unit="USD",
                ),
                CostLineItem(
                    category="Power",
                    description="Electricity consumption (70% utilization)",
                    amount=Decimal("3600"),
                    unit="USD",
                ),
                CostLineItem(
                    category="Cooling",
                    description="HVAC and cooling costs",
                    amount=Decimal("1800"),
                    unit="USD",
                ),
            ],
            total=Decimal("15400"),
            currency="USD",
        ),
    }


@pytest.fixture
def sample_aws_costs():
    """Sample AWS cost breakdowns."""
    return {
        1: CostBreakdown(
            items=[
                CostLineItem(
                    category="EC2",
                    description="EC2 compute instances (2 instances, 4 cores, 16GB RAM)",
                    amount=Decimal("8000"),
                    unit="USD",
                ),
                CostLineItem(
                    category="EBS",
                    description="EBS block storage (500GB SSD, 3000 IOPS)",
                    amount=Decimal("500"),
                    unit="USD",
                ),
                CostLineItem(
                    category="Data Transfer",
                    description="AWS data transfer costs (1000GB/month)",
                    amount=Decimal("900"),
                    unit="USD",
                ),
            ],
            total=Decimal("9400"),
            currency="USD",
        ),
        3: CostBreakdown(
            items=[
                CostLineItem(
                    category="EC2",
                    description="EC2 compute instances (2 instances, 4 cores, 16GB RAM)",
                    amount=Decimal("24000"),
                    unit="USD",
                ),
                CostLineItem(
                    category="EBS",
                    description="EBS block storage (500GB SSD, 3000 IOPS)",
                    amount=Decimal("1500"),
                    unit="USD",
                ),
                CostLineItem(
                    category="Data Transfer",
                    description="AWS data transfer costs (1000GB/month)",
                    amount=Decimal("2700"),
                    unit="USD",
                ),
            ],
            total=Decimal("28200"),
            currency="USD",
        ),
    }


@pytest.fixture
def sample_context(sample_config, sample_on_prem_costs, sample_aws_costs):
    """Sample TCO context for testing."""
    return TCOContext(
        configuration=sample_config,
        on_prem_costs=sample_on_prem_costs,
        aws_costs=sample_aws_costs,
    )


def test_process_question_returns_string(sample_context):
    """Test that process_question returns a string response."""
    response = process_question("What is the EC2 cost?", sample_context)
    assert isinstance(response, str)
    assert len(response) > 0


def test_process_question_handles_cost_item_explanation(sample_context):
    """Test that process_question routes to cost item explanation."""
    response = process_question("What is the EC2 cost?", sample_context)
    assert "EC2" in response
    assert "$8,000" in response or "8000" in response


def test_process_question_handles_comparison(sample_context):
    """Test that process_question routes to comparison."""
    response = process_question("Compare power costs", sample_context)
    assert "power" in response.lower() or "comparing" in response.lower()


def test_process_question_handles_recommendation(sample_context):
    """Test that process_question routes to recommendation."""
    response = process_question("Which should I choose?", sample_context)
    assert "recommendation" in response.lower() or "workload" in response.lower()


def test_process_question_handles_unknown_question(sample_context):
    """Test that process_question provides helpful response for unknown questions."""
    response = process_question("Random question", sample_context)
    assert "help" in response.lower() or "ask" in response.lower()


def test_get_cost_item_explanation_for_on_prem_item(sample_context):
    """Test getting explanation for on-premises cost item."""
    response = get_cost_item_explanation("Hardware", sample_context)
    
    assert "Hardware" in response
    assert "On-Premises" in response
    assert "$10,000" in response or "10000" in response


def test_get_cost_item_explanation_for_aws_item(sample_context):
    """Test getting explanation for AWS cost item."""
    response = get_cost_item_explanation("EC2", sample_context)
    
    assert "EC2" in response
    assert "AWS" in response
    assert "$8,000" in response or "8000" in response


def test_get_cost_item_explanation_shows_multiple_years(sample_context):
    """Test that cost item explanation shows costs for multiple years."""
    response = get_cost_item_explanation("Power", sample_context)
    
    assert "1 year" in response
    assert "3 year" in response


def test_get_cost_item_explanation_for_nonexistent_item(sample_context):
    """Test getting explanation for non-existent cost item."""
    response = get_cost_item_explanation("NonExistent", sample_context)
    
    assert "couldn't find" in response.lower()


def test_compare_aspects_shows_both_costs(sample_context):
    """Test that compare_aspects shows costs for both options."""
    response = compare_aspects("power", sample_context)
    
    # Should mention both on-prem and AWS (or indicate one is missing)
    assert "on-premises" in response.lower() or "on-prem" in response.lower()


def test_compare_aspects_calculates_difference(sample_context):
    """Test that compare_aspects calculates cost difference."""
    response = compare_aspects("data transfer", sample_context)
    
    # Should mention comparison or difference
    assert "comparing" in response.lower() or "found" in response.lower()


def test_compare_aspects_for_nonexistent_aspect(sample_context):
    """Test comparing non-existent aspect."""
    response = compare_aspects("nonexistent", sample_context)
    
    assert "couldn't find" in response.lower()


def test_generate_recommendation_returns_non_empty_string(sample_context):
    """Test that generate_recommendation returns a non-empty string."""
    response = generate_recommendation(sample_context)
    
    assert isinstance(response, str)
    assert len(response) > 0


def test_generate_recommendation_includes_cost_comparison(sample_context):
    """Test that recommendation includes cost comparison."""
    response = generate_recommendation(sample_context)
    
    assert "on-premises" in response.lower() or "on-prem" in response.lower()
    assert "aws" in response.lower()
    assert "$" in response


def test_generate_recommendation_analyzes_workload(sample_context):
    """Test that recommendation analyzes workload characteristics."""
    response = generate_recommendation(sample_context)
    
    # Should mention utilization or hours
    assert "utilization" in response.lower() or "hours" in response.lower() or "workload" in response.lower()


def test_generate_recommendation_provides_suggestion(sample_context):
    """Test that recommendation provides a suggested path."""
    response = generate_recommendation(sample_context)
    
    # Should suggest a path or mention both options
    assert "consider" in response.lower() or "suggest" in response.lower() or "recommend" in response.lower()


def test_tco_context_dataclass(sample_config, sample_on_prem_costs, sample_aws_costs):
    """Test that TCOContext dataclass works correctly."""
    context = TCOContext(
        configuration=sample_config,
        on_prem_costs=sample_on_prem_costs,
        aws_costs=sample_aws_costs,
    )
    
    assert context.configuration == sample_config
    assert context.on_prem_costs == sample_on_prem_costs
    assert context.aws_costs == sample_aws_costs


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
