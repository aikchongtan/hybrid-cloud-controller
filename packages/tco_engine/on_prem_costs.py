"""On-premises cost calculation functions for TCO Engine."""

from decimal import Decimal


def calculate_hardware_costs(
    cpu_cores: int,
    memory_gb: int,
    instance_count: int,
    storage_capacity_gb: int,
    storage_type: str,
) -> Decimal:
    """
    Calculate hardware costs for on-premises infrastructure.

    Hardware costs include servers and storage based on compute and storage specs.
    Industry estimates:
    - Server cost: ~$100 per CPU core + ~$10 per GB RAM
    - Storage cost: SSD ~$0.30/GB, HDD ~$0.05/GB, NVME ~$0.50/GB

    Args:
        cpu_cores: Number of CPU cores per instance
        memory_gb: Memory size in GB per instance
        instance_count: Number of instances
        storage_capacity_gb: Total storage capacity in GB
        storage_type: Storage type (SSD, HDD, or NVME)

    Returns:
        Total hardware cost as Decimal
    """
    # Server cost per instance: $100/core + $10/GB RAM
    server_cost_per_instance = Decimal(cpu_cores * 100 + memory_gb * 10)
    total_server_cost = server_cost_per_instance * instance_count

    # Storage cost based on type
    storage_cost_per_gb = {
        "SSD": Decimal("0.30"),
        "HDD": Decimal("0.05"),
        "NVME": Decimal("0.50"),
    }
    storage_cost = storage_cost_per_gb.get(storage_type, Decimal("0.30")) * Decimal(
        storage_capacity_gb
    )

    return total_server_cost + storage_cost


def calculate_power_costs(
    cpu_cores: int,
    instance_count: int,
    utilization_percentage: int,
    operating_hours_per_month: int,
    years: int,
) -> Decimal:
    """
    Calculate power consumption costs for on-premises infrastructure.

    Power costs are based on:
    - Average power consumption: ~50W per CPU core at 100% utilization
    - Power scales with utilization percentage
    - Average electricity cost: $0.12 per kWh

    Args:
        cpu_cores: Number of CPU cores per instance
        instance_count: Number of instances
        utilization_percentage: CPU utilization percentage (0-100)
        operating_hours_per_month: Operating hours per month
        years: Number of years to calculate for

    Returns:
        Total power cost as Decimal
    """
    # Power consumption: 50W per core at 100% utilization
    watts_per_core = Decimal("50")
    total_cores = cpu_cores * instance_count

    # Adjust for utilization
    actual_watts = watts_per_core * total_cores * (Decimal(utilization_percentage) / 100)

    # Convert to kWh: watts * hours / 1000
    kwh_per_month = (actual_watts * Decimal(operating_hours_per_month)) / 1000

    # Cost: $0.12 per kWh
    cost_per_kwh = Decimal("0.12")
    monthly_cost = kwh_per_month * cost_per_kwh

    # Total for all years (12 months per year)
    return monthly_cost * 12 * years


def calculate_cooling_costs(
    cpu_cores: int,
    instance_count: int,
    utilization_percentage: int,
    operating_hours_per_month: int,
    years: int,
) -> Decimal:
    """
    Calculate cooling/HVAC costs for on-premises infrastructure.

    Cooling costs are typically 30-50% of power costs (using 40% as average).

    Args:
        cpu_cores: Number of CPU cores per instance
        instance_count: Number of instances
        utilization_percentage: CPU utilization percentage (0-100)
        operating_hours_per_month: Operating hours per month
        years: Number of years to calculate for

    Returns:
        Total cooling cost as Decimal
    """
    power_cost = calculate_power_costs(
        cpu_cores, instance_count, utilization_percentage, operating_hours_per_month, years
    )

    # Cooling is typically 40% of power costs
    cooling_ratio = Decimal("0.40")
    return power_cost * cooling_ratio


def calculate_maintenance_costs(
    cpu_cores: int,
    memory_gb: int,
    instance_count: int,
    storage_capacity_gb: int,
    storage_type: str,
    years: int,
) -> Decimal:
    """
    Calculate maintenance and support costs for on-premises infrastructure.

    Maintenance costs are typically 15-20% of hardware costs annually (using 17.5% as average).

    Args:
        cpu_cores: Number of CPU cores per instance
        memory_gb: Memory size in GB per instance
        instance_count: Number of instances
        storage_capacity_gb: Total storage capacity in GB
        storage_type: Storage type (SSD, HDD, or NVME)
        years: Number of years to calculate for

    Returns:
        Total maintenance cost as Decimal
    """
    hardware_cost = calculate_hardware_costs(
        cpu_cores, memory_gb, instance_count, storage_capacity_gb, storage_type
    )

    # Maintenance is typically 17.5% of hardware costs annually
    maintenance_ratio = Decimal("0.175")
    annual_maintenance = hardware_cost * maintenance_ratio

    return annual_maintenance * years


def calculate_data_transfer_costs(
    monthly_data_transfer_gb: int,
    bandwidth_mbps: int,
    years: int,
) -> Decimal:
    """
    Calculate bandwidth/data transfer costs for on-premises infrastructure.

    Data transfer costs include:
    - Bandwidth/leased line costs: ~$1-5 per Mbps per month (using $3 as average)
    - Data transfer overage: ~$0.02 per GB over included bandwidth

    Args:
        monthly_data_transfer_gb: Monthly data transfer in GB
        bandwidth_mbps: Network bandwidth in Mbps
        years: Number of years to calculate for

    Returns:
        Total data transfer cost as Decimal
    """
    # Leased line cost: $3 per Mbps per month
    cost_per_mbps = Decimal("3")
    monthly_bandwidth_cost = Decimal(bandwidth_mbps) * cost_per_mbps

    # Included data transfer: assume 1TB per 100 Mbps
    included_gb_per_month = Decimal(bandwidth_mbps) * 10
    overage_gb = max(Decimal(monthly_data_transfer_gb) - included_gb_per_month, Decimal(0))

    # Overage cost: $0.02 per GB
    overage_cost_per_gb = Decimal("0.02")
    monthly_overage_cost = overage_gb * overage_cost_per_gb

    # Total monthly cost
    monthly_total = monthly_bandwidth_cost + monthly_overage_cost

    # Total for all years (12 months per year)
    return monthly_total * 12 * years
