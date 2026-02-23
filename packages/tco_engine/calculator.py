"""TCO calculation engine for Hybrid Cloud Controller.

This module orchestrates the complete TCO calculation by combining on-premises
and AWS cost calculations, generating itemized breakdowns, and projecting costs
for multiple time periods.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from packages.tco_engine import aws_costs, on_prem_costs


@dataclass
class CostLineItem:
    """Individual cost line item in a breakdown."""

    category: str
    description: str
    amount: Decimal
    unit: str  # e.g., "USD/month", "USD/year", "USD"


@dataclass
class CostBreakdown:
    """Complete cost breakdown with itemized line items."""

    items: list[CostLineItem]
    total: Decimal
    currency: str = "USD"


@dataclass
class Configuration:
    """Configuration data for TCO calculation."""

    # Compute specifications
    cpu_cores: int
    memory_gb: int
    instance_count: int

    # Storage specifications
    storage_type: str
    storage_capacity_gb: int
    storage_iops: Optional[int]

    # Network specifications
    bandwidth_mbps: int
    monthly_data_transfer_gb: int

    # Workload profile
    utilization_percentage: int
    operating_hours_per_month: int


@dataclass
class AWSPricing:
    """AWS pricing data."""

    ec2_pricing: dict[str, Decimal]
    ebs_pricing: dict[str, Decimal]
    s3_pricing: dict[str, Decimal]
    data_transfer_pricing: dict[str, Decimal]


def calculate_tco(
    config: Configuration,
    pricing: AWSPricing,
) -> dict[str, dict[int, CostBreakdown]]:
    """
    Calculate complete TCO for both on-premises and AWS cloud paths.

    This is the main orchestrator function that:
    1. Calculates on-premises costs for 1, 3, and 5 years
    2. Calculates AWS costs for 1, 3, and 5 years
    3. Returns itemized breakdowns for both paths

    Args:
        config: Configuration with compute, storage, network, and workload specs
        pricing: AWS pricing data

    Returns:
        Dictionary with 'on_prem' and 'aws' keys, each containing a dict
        mapping years (1, 3, 5) to CostBreakdown objects
    """
    # Calculate costs for each time period
    years_to_project = [1, 3, 5]

    on_prem_costs_by_year = {}
    aws_costs_by_year = {}

    for years in years_to_project:
        on_prem_costs_by_year[years] = _calculate_on_prem_breakdown(config, years)
        aws_costs_by_year[years] = _calculate_aws_breakdown(config, pricing, years)

    return {
        "on_prem": on_prem_costs_by_year,
        "aws": aws_costs_by_year,
    }


def project_costs(
    base_breakdown: CostBreakdown,
    years: list[int],
) -> dict[int, CostBreakdown]:
    """
    Project costs for multiple time periods.

    This function takes a base cost breakdown and projects it for different
    time periods. It ensures that 3-year >= 1-year and 5-year >= 3-year for
    recurring costs.

    Args:
        base_breakdown: Base cost breakdown (typically for 1 year)
        years: List of years to project for (e.g., [1, 3, 5])

    Returns:
        Dictionary mapping years to projected CostBreakdown objects
    """
    projections = {}

    for year_count in years:
        projected_items = []
        total = Decimal(0)

        for item in base_breakdown.items:
            # Scale recurring costs by year count
            # One-time costs (like hardware) don't scale
            if "hardware" in item.category.lower():
                # Hardware is a one-time cost
                projected_amount = item.amount
            else:
                # Recurring costs scale with years
                projected_amount = item.amount * year_count

            projected_items.append(
                CostLineItem(
                    category=item.category,
                    description=item.description,
                    amount=projected_amount,
                    unit=item.unit,
                )
            )
            total += projected_amount

        projections[year_count] = CostBreakdown(
            items=projected_items,
            total=total,
            currency=base_breakdown.currency,
        )

    return projections


def _calculate_on_prem_breakdown(config: Configuration, years: int) -> CostBreakdown:
    """
    Calculate on-premises cost breakdown with itemized line items.

    Args:
        config: Configuration with compute, storage, network, and workload specs
        years: Number of years to calculate for

    Returns:
        CostBreakdown with itemized costs for hardware, power, cooling,
        maintenance, and data transfer
    """
    # Calculate individual cost components
    hardware_cost = on_prem_costs.calculate_hardware_costs(
        cpu_cores=config.cpu_cores,
        memory_gb=config.memory_gb,
        instance_count=config.instance_count,
        storage_capacity_gb=config.storage_capacity_gb,
        storage_type=config.storage_type,
    )

    power_cost = on_prem_costs.calculate_power_costs(
        cpu_cores=config.cpu_cores,
        instance_count=config.instance_count,
        utilization_percentage=config.utilization_percentage,
        operating_hours_per_month=config.operating_hours_per_month,
        years=years,
    )

    cooling_cost = on_prem_costs.calculate_cooling_costs(
        cpu_cores=config.cpu_cores,
        instance_count=config.instance_count,
        utilization_percentage=config.utilization_percentage,
        operating_hours_per_month=config.operating_hours_per_month,
        years=years,
    )

    maintenance_cost = on_prem_costs.calculate_maintenance_costs(
        cpu_cores=config.cpu_cores,
        memory_gb=config.memory_gb,
        instance_count=config.instance_count,
        storage_capacity_gb=config.storage_capacity_gb,
        storage_type=config.storage_type,
        years=years,
    )

    data_transfer_cost = on_prem_costs.calculate_data_transfer_costs(
        monthly_data_transfer_gb=config.monthly_data_transfer_gb,
        bandwidth_mbps=config.bandwidth_mbps,
        years=years,
    )

    # Create itemized line items
    items = [
        CostLineItem(
            category="Hardware",
            description=f"Server hardware and storage ({config.instance_count} instances, "
            f"{config.cpu_cores} cores, {config.memory_gb}GB RAM, "
            f"{config.storage_capacity_gb}GB {config.storage_type})",
            amount=hardware_cost,
            unit="USD",
        ),
        CostLineItem(
            category="Power",
            description=f"Electricity consumption ({config.utilization_percentage}% utilization, "
            f"{config.operating_hours_per_month} hours/month, {years} year(s))",
            amount=power_cost,
            unit="USD",
        ),
        CostLineItem(
            category="Cooling",
            description=f"HVAC and cooling costs ({years} year(s))",
            amount=cooling_cost,
            unit="USD",
        ),
        CostLineItem(
            category="Maintenance",
            description=f"Hardware maintenance and support ({years} year(s))",
            amount=maintenance_cost,
            unit="USD",
        ),
        CostLineItem(
            category="Data Transfer",
            description=f"Bandwidth and data transfer ({config.bandwidth_mbps} Mbps, "
            f"{config.monthly_data_transfer_gb}GB/month, {years} year(s))",
            amount=data_transfer_cost,
            unit="USD",
        ),
    ]

    # Calculate total
    total = sum(item.amount for item in items)

    return CostBreakdown(items=items, total=total, currency="USD")


def _calculate_aws_breakdown(
    config: Configuration,
    pricing: AWSPricing,
    years: int,
) -> CostBreakdown:
    """
    Calculate AWS cost breakdown with itemized line items.

    Args:
        config: Configuration with compute, storage, network, and workload specs
        pricing: AWS pricing data
        years: Number of years to calculate for

    Returns:
        CostBreakdown with itemized costs for EC2, EBS, S3, and data transfer
    """
    # Calculate individual cost components
    ec2_cost = aws_costs.calculate_ec2_costs(
        cpu_cores=config.cpu_cores,
        memory_gb=config.memory_gb,
        instance_count=config.instance_count,
        utilization_percentage=config.utilization_percentage,
        operating_hours_per_month=config.operating_hours_per_month,
        ec2_pricing=pricing.ec2_pricing,
        years=years,
    )

    ebs_cost = aws_costs.calculate_ebs_costs(
        storage_capacity_gb=config.storage_capacity_gb,
        storage_type=config.storage_type,
        storage_iops=config.storage_iops,
        ebs_pricing=pricing.ebs_pricing,
        years=years,
    )

    s3_cost = aws_costs.calculate_s3_costs(
        storage_capacity_gb=config.storage_capacity_gb,
        s3_pricing=pricing.s3_pricing,
        years=years,
    )

    data_transfer_cost = aws_costs.calculate_data_transfer_costs(
        monthly_data_transfer_gb=config.monthly_data_transfer_gb,
        data_transfer_pricing=pricing.data_transfer_pricing,
        years=years,
    )

    # Create itemized line items
    items = [
        CostLineItem(
            category="EC2",
            description=f"EC2 compute instances ({config.instance_count} instances, "
            f"{config.cpu_cores} cores, {config.memory_gb}GB RAM, "
            f"{config.operating_hours_per_month} hours/month, {years} year(s))",
            amount=ec2_cost,
            unit="USD",
        ),
        CostLineItem(
            category="EBS",
            description=f"EBS block storage ({config.storage_capacity_gb}GB {config.storage_type}"
            + (f", {config.storage_iops} IOPS" if config.storage_iops else "")
            + f", {years} year(s))",
            amount=ebs_cost,
            unit="USD",
        ),
        CostLineItem(
            category="S3",
            description=f"S3 object storage ({config.storage_capacity_gb}GB, {years} year(s))",
            amount=s3_cost,
            unit="USD",
        ),
        CostLineItem(
            category="Data Transfer",
            description=f"AWS data transfer costs ({config.monthly_data_transfer_gb}GB/month, "
            f"{years} year(s))",
            amount=data_transfer_cost,
            unit="USD",
        ),
    ]

    # Calculate total
    total = sum(item.amount for item in items)

    return CostBreakdown(items=items, total=total, currency="USD")
