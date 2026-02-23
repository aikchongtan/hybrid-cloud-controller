"""Configuration validation for TCO Engine."""

from typing import Optional


class ValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__(f"Configuration validation failed: {errors}")


def validate_configuration(
    cpu_cores: Optional[int] = None,
    memory_gb: Optional[int] = None,
    instance_count: Optional[int] = None,
    storage_type: Optional[str] = None,
    storage_capacity_gb: Optional[int] = None,
    storage_iops: Optional[int] = None,
    bandwidth_mbps: Optional[int] = None,
    monthly_data_transfer_gb: Optional[int] = None,
    utilization_percentage: Optional[int] = None,
    operating_hours_per_month: Optional[int] = None,
) -> dict[str, str]:
    """
    Validate configuration fields against their valid ranges.

    Args:
        cpu_cores: Number of CPU cores (must be positive integer)
        memory_gb: Memory size in GB (must be positive integer)
        instance_count: Number of instances (must be positive integer)
        storage_type: Storage type (must be one of: SSD, HDD, NVME)
        storage_capacity_gb: Storage capacity in GB (must be positive integer)
        storage_iops: Storage IOPS (must be positive integer if provided)
        bandwidth_mbps: Network bandwidth in Mbps (must be positive integer)
        monthly_data_transfer_gb: Monthly data transfer in GB (must be positive integer)
        utilization_percentage: CPU/resource utilization percentage (must be 0-100)
        operating_hours_per_month: Operating hours per month (must be 0-744)

    Returns:
        Dictionary of field names to error messages. Empty dict if all valid.

    Raises:
        ValidationError: If any validation fails (contains errors dict)
    """
    errors = {}

    # Validate compute specs
    if cpu_cores is not None:
        if not isinstance(cpu_cores, int) or cpu_cores <= 0:
            errors["cpu_cores"] = "CPU cores must be a positive integer"

    if memory_gb is not None:
        if not isinstance(memory_gb, int) or memory_gb <= 0:
            errors["memory_gb"] = "Memory must be a positive integer"

    if instance_count is not None:
        if not isinstance(instance_count, int) or instance_count <= 0:
            errors["instance_count"] = "Instance count must be a positive integer"

    # Validate storage specs
    if storage_type is not None:
        valid_types = {"SSD", "HDD", "NVME"}
        if storage_type not in valid_types:
            errors["storage_type"] = (
                f"Storage type must be one of: {', '.join(sorted(valid_types))}"
            )

    if storage_capacity_gb is not None:
        if not isinstance(storage_capacity_gb, int) or storage_capacity_gb <= 0:
            errors["storage_capacity_gb"] = "Storage capacity must be a positive integer"

    if storage_iops is not None:
        if not isinstance(storage_iops, int) or storage_iops <= 0:
            errors["storage_iops"] = "Storage IOPS must be a positive integer"

    # Validate network specs
    if bandwidth_mbps is not None:
        if not isinstance(bandwidth_mbps, int) or bandwidth_mbps <= 0:
            errors["bandwidth_mbps"] = "Bandwidth must be a positive integer"

    if monthly_data_transfer_gb is not None:
        if (
            not isinstance(monthly_data_transfer_gb, int)
            or monthly_data_transfer_gb <= 0
        ):
            errors["monthly_data_transfer_gb"] = (
                "Data transfer must be a positive integer"
            )

    # Validate workload profile
    if utilization_percentage is not None:
        if (
            not isinstance(utilization_percentage, int)
            or utilization_percentage < 0
            or utilization_percentage > 100
        ):
            errors["utilization_percentage"] = (
                "Utilization percentage must be between 0 and 100"
            )

    if operating_hours_per_month is not None:
        if (
            not isinstance(operating_hours_per_month, int)
            or operating_hours_per_month < 0
            or operating_hours_per_month > 744
        ):
            errors["operating_hours_per_month"] = (
                "Operating hours must be between 0 and 744"
            )

    if errors:
        raise ValidationError(errors)

    return errors
