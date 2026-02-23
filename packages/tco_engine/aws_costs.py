"""AWS cost calculation functions for TCO Engine."""

from decimal import Decimal
from typing import Optional


def calculate_ec2_costs(
    cpu_cores: int,
    memory_gb: int,
    instance_count: int,
    utilization_percentage: int,
    operating_hours_per_month: int,
    ec2_pricing: dict[str, Decimal],
    years: int,
) -> Decimal:
    """
    Calculate EC2 instance costs using pricing data.

    Selects appropriate instance type based on CPU and memory requirements,
    then calculates costs based on operating hours and utilization.

    Args:
        cpu_cores: Number of CPU cores per instance
        memory_gb: Memory size in GB per instance
        instance_count: Number of instances
        utilization_percentage: CPU utilization percentage (0-100)
        operating_hours_per_month: Operating hours per month
        ec2_pricing: Dictionary mapping instance types to hourly rates
        years: Number of years to calculate for

    Returns:
        Total EC2 cost as Decimal
    """
    # Select instance type based on requirements
    # Simple heuristic: match CPU cores and memory
    instance_type = _select_instance_type(cpu_cores, memory_gb, ec2_pricing)

    # Get hourly rate for selected instance type
    hourly_rate = ec2_pricing.get(instance_type, Decimal("0.10"))  # Default fallback

    # Calculate monthly cost per instance
    monthly_cost_per_instance = hourly_rate * Decimal(operating_hours_per_month)

    # Total monthly cost for all instances
    monthly_total = monthly_cost_per_instance * instance_count

    # Total for all years (12 months per year)
    return monthly_total * 12 * years


def calculate_ebs_costs(
    storage_capacity_gb: int,
    storage_type: str,
    storage_iops: Optional[int],
    ebs_pricing: dict[str, Decimal],
    years: int,
) -> Decimal:
    """
    Calculate EBS storage costs.

    Calculates costs based on storage type, capacity, and IOPS requirements.

    Args:
        storage_capacity_gb: Total storage capacity in GB
        storage_type: Storage type (SSD, HDD, or NVME)
        storage_iops: Storage IOPS (optional, for provisioned IOPS volumes)
        ebs_pricing: Dictionary mapping EBS volume types to GB/month rates
        years: Number of years to calculate for

    Returns:
        Total EBS cost as Decimal
    """
    # Map storage types to EBS volume types
    ebs_volume_type = _map_storage_type_to_ebs(storage_type)

    # Get monthly rate per GB
    rate_per_gb_month = ebs_pricing.get(ebs_volume_type, Decimal("0.10"))

    # Calculate base storage cost
    monthly_storage_cost = Decimal(storage_capacity_gb) * rate_per_gb_month

    # Add IOPS cost if provisioned IOPS volume
    monthly_iops_cost = Decimal(0)
    if storage_iops and ebs_volume_type == "io2":
        iops_rate = ebs_pricing.get("iops", Decimal("0.065"))
        monthly_iops_cost = Decimal(storage_iops) * iops_rate

    # Total monthly cost
    monthly_total = monthly_storage_cost + monthly_iops_cost

    # Total for all years (12 months per year)
    return monthly_total * 12 * years


def calculate_s3_costs(
    storage_capacity_gb: int,
    s3_pricing: dict[str, Decimal],
    years: int,
) -> Decimal:
    """
    Calculate S3 storage costs.

    Calculates costs for S3 Standard storage class.

    Args:
        storage_capacity_gb: Total storage capacity in GB
        s3_pricing: Dictionary mapping S3 storage classes to GB/month rates
        years: Number of years to calculate for

    Returns:
        Total S3 cost as Decimal
    """
    # Use S3 Standard storage class
    rate_per_gb_month = s3_pricing.get("standard", Decimal("0.023"))

    # Calculate monthly cost
    monthly_cost = Decimal(storage_capacity_gb) * rate_per_gb_month

    # Total for all years (12 months per year)
    return monthly_cost * 12 * years


def calculate_data_transfer_costs(
    monthly_data_transfer_gb: int,
    data_transfer_pricing: dict[str, Decimal],
    years: int,
) -> Decimal:
    """
    Calculate AWS data transfer costs.

    Includes egress (data transfer out to internet), inter-region, and inter-AZ costs.
    AWS provides first 100 GB/month free for internet egress.

    Args:
        monthly_data_transfer_gb: Monthly data transfer in GB
        data_transfer_pricing: Dictionary mapping transfer types to GB rates
        years: Number of years to calculate for

    Returns:
        Total data transfer cost as Decimal
    """
    # AWS free tier: first 100 GB/month free for internet egress
    free_tier_gb = 100
    billable_gb = max(monthly_data_transfer_gb - free_tier_gb, 0)

    # Get egress rate (data transfer out to internet)
    egress_rate = data_transfer_pricing.get("internet_egress", Decimal("0.09"))

    # Calculate monthly egress cost
    monthly_egress_cost = Decimal(billable_gb) * egress_rate

    # Add inter-AZ transfer cost (assume 10% of total transfer is inter-AZ)
    inter_az_rate = data_transfer_pricing.get("inter_az", Decimal("0.01"))
    inter_az_gb = Decimal(monthly_data_transfer_gb) * Decimal("0.10")
    monthly_inter_az_cost = inter_az_gb * inter_az_rate

    # Total monthly cost
    monthly_total = monthly_egress_cost + monthly_inter_az_cost

    # Total for all years (12 months per year)
    return monthly_total * 12 * years


def _select_instance_type(
    cpu_cores: int,
    memory_gb: int,
    ec2_pricing: dict[str, Decimal],
) -> str:
    """
    Select appropriate EC2 instance type based on CPU and memory requirements.

    Uses a simple heuristic to match requirements to common instance types.

    Args:
        cpu_cores: Number of CPU cores required
        memory_gb: Memory size in GB required
        ec2_pricing: Dictionary of available instance types

    Returns:
        Selected instance type name
    """
    # Common instance type patterns (vCPU, Memory GB)
    instance_specs = {
        "t3.micro": (2, 1),
        "t3.small": (2, 2),
        "t3.medium": (2, 4),
        "t3.large": (2, 8),
        "t3.xlarge": (4, 16),
        "t3.2xlarge": (8, 32),
        "m5.large": (2, 8),
        "m5.xlarge": (4, 16),
        "m5.2xlarge": (8, 32),
        "m5.4xlarge": (16, 64),
        "m5.8xlarge": (32, 128),
        "m5.12xlarge": (48, 192),
        "m5.16xlarge": (64, 256),
        "m5.24xlarge": (96, 384),
        "c5.large": (2, 4),
        "c5.xlarge": (4, 8),
        "c5.2xlarge": (8, 16),
        "c5.4xlarge": (16, 32),
        "c5.9xlarge": (36, 72),
        "c5.18xlarge": (72, 144),
        "r5.large": (2, 16),
        "r5.xlarge": (4, 32),
        "r5.2xlarge": (8, 64),
        "r5.4xlarge": (16, 128),
        "r5.8xlarge": (32, 256),
        "r5.12xlarge": (48, 384),
    }

    # Find smallest instance that meets requirements
    best_match = "m5.large"  # Default fallback
    best_match_cost = Decimal("999999")

    for instance_type, (vcpu, mem) in instance_specs.items():
        # Check if instance meets requirements
        if vcpu >= cpu_cores and mem >= memory_gb:
            # Check if this instance type is in pricing data
            if instance_type in ec2_pricing:
                cost = ec2_pricing[instance_type]
                # Select cheapest instance that meets requirements
                if cost < best_match_cost:
                    best_match = instance_type
                    best_match_cost = cost

    return best_match


def _map_storage_type_to_ebs(storage_type: str) -> str:
    """
    Map generic storage type to AWS EBS volume type.

    Args:
        storage_type: Generic storage type (SSD, HDD, or NVME)

    Returns:
        EBS volume type name
    """
    mapping = {
        "SSD": "gp3",  # General Purpose SSD
        "HDD": "st1",  # Throughput Optimized HDD
        "NVME": "io2",  # Provisioned IOPS SSD (NVMe)
    }
    return mapping.get(storage_type, "gp3")
