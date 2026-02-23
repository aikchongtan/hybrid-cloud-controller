"""Unit tests for configuration validation."""

import pytest

from packages.tco_engine.validation import ValidationError, validate_configuration


def test_validate_configuration_all_valid():
    """Test that valid configuration passes validation."""
    # Should not raise any errors
    errors = validate_configuration(
        cpu_cores=4,
        memory_gb=16,
        instance_count=2,
        storage_type="SSD",
        storage_capacity_gb=500,
        storage_iops=3000,
        bandwidth_mbps=1000,
        monthly_data_transfer_gb=1000,
        utilization_percentage=75,
        operating_hours_per_month=720,
    )
    assert errors == {}


def test_validate_configuration_invalid_cpu_cores():
    """Test that invalid CPU cores raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(cpu_cores=0)
    assert "cpu_cores" in exc_info.value.errors
    assert "positive integer" in exc_info.value.errors["cpu_cores"]


def test_validate_configuration_invalid_memory():
    """Test that invalid memory raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(memory_gb=-1)
    assert "memory_gb" in exc_info.value.errors


def test_validate_configuration_invalid_instance_count():
    """Test that invalid instance count raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(instance_count=0)
    assert "instance_count" in exc_info.value.errors


def test_validate_configuration_invalid_storage_type():
    """Test that invalid storage type raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(storage_type="INVALID")
    assert "storage_type" in exc_info.value.errors
    assert "SSD" in exc_info.value.errors["storage_type"]


def test_validate_configuration_invalid_storage_capacity():
    """Test that invalid storage capacity raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(storage_capacity_gb=0)
    assert "storage_capacity_gb" in exc_info.value.errors


def test_validate_configuration_invalid_storage_iops():
    """Test that invalid storage IOPS raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(storage_iops=-100)
    assert "storage_iops" in exc_info.value.errors


def test_validate_configuration_invalid_bandwidth():
    """Test that invalid bandwidth raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(bandwidth_mbps=0)
    assert "bandwidth_mbps" in exc_info.value.errors


def test_validate_configuration_invalid_data_transfer():
    """Test that invalid data transfer raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(monthly_data_transfer_gb=-1)
    assert "monthly_data_transfer_gb" in exc_info.value.errors


def test_validate_configuration_invalid_utilization_percentage_negative():
    """Test that negative utilization percentage raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(utilization_percentage=-1)
    assert "utilization_percentage" in exc_info.value.errors
    assert "0 and 100" in exc_info.value.errors["utilization_percentage"]


def test_validate_configuration_invalid_utilization_percentage_over_100():
    """Test that utilization percentage over 100 raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(utilization_percentage=101)
    assert "utilization_percentage" in exc_info.value.errors


def test_validate_configuration_invalid_operating_hours_negative():
    """Test that negative operating hours raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(operating_hours_per_month=-1)
    assert "operating_hours_per_month" in exc_info.value.errors
    assert "0 and 744" in exc_info.value.errors["operating_hours_per_month"]


def test_validate_configuration_invalid_operating_hours_over_744():
    """Test that operating hours over 744 raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(operating_hours_per_month=745)
    assert "operating_hours_per_month" in exc_info.value.errors


def test_validate_configuration_multiple_errors():
    """Test that multiple validation errors are collected."""
    with pytest.raises(ValidationError) as exc_info:
        validate_configuration(
            cpu_cores=-1,
            memory_gb=0,
            storage_type="INVALID",
            utilization_percentage=150,
        )
    errors = exc_info.value.errors
    assert "cpu_cores" in errors
    assert "memory_gb" in errors
    assert "storage_type" in errors
    assert "utilization_percentage" in errors


def test_validate_configuration_valid_boundary_values():
    """Test that boundary values are accepted."""
    # Should not raise any errors
    errors = validate_configuration(
        utilization_percentage=0,  # Min valid
        operating_hours_per_month=0,  # Min valid
    )
    assert errors == {}

    errors = validate_configuration(
        utilization_percentage=100,  # Max valid
        operating_hours_per_month=744,  # Max valid
    )
    assert errors == {}


def test_validate_configuration_storage_types():
    """Test all valid storage types."""
    for storage_type in ["SSD", "HDD", "NVME"]:
        errors = validate_configuration(storage_type=storage_type)
        assert errors == {}
