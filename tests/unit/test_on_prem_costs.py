"""Unit tests for on-premises cost calculation functions."""

from decimal import Decimal

import pytest

from packages.tco_engine import on_prem_costs


class TestCalculateHardwareCosts:
    """Tests for calculate_hardware_costs function."""

    def test_basic_hardware_cost_calculation(self):
        """Test hardware cost with typical values."""
        cost = on_prem_costs.calculate_hardware_costs(
            cpu_cores=8,
            memory_gb=32,
            instance_count=2,
            storage_capacity_gb=1000,
            storage_type="SSD",
        )

        # Expected: (8*100 + 32*10) * 2 + 1000*0.30
        # = (800 + 320) * 2 + 300
        # = 1120 * 2 + 300 = 2540
        assert cost == Decimal("2540")

    def test_hardware_cost_with_hdd_storage(self):
        """Test hardware cost with HDD storage type."""
        cost = on_prem_costs.calculate_hardware_costs(
            cpu_cores=4,
            memory_gb=16,
            instance_count=1,
            storage_capacity_gb=2000,
            storage_type="HDD",
        )

        # Expected: (4*100 + 16*10) * 1 + 2000*0.05
        # = 560 + 100 = 660
        assert cost == Decimal("660")

    def test_hardware_cost_with_nvme_storage(self):
        """Test hardware cost with NVME storage type."""
        cost = on_prem_costs.calculate_hardware_costs(
            cpu_cores=16,
            memory_gb=64,
            instance_count=1,
            storage_capacity_gb=500,
            storage_type="NVME",
        )

        # Expected: (16*100 + 64*10) * 1 + 500*0.50
        # = 2240 + 250 = 2490
        assert cost == Decimal("2490")

    def test_hardware_cost_multiple_instances(self):
        """Test hardware cost scales with instance count."""
        cost = on_prem_costs.calculate_hardware_costs(
            cpu_cores=4,
            memory_gb=8,
            instance_count=5,
            storage_capacity_gb=100,
            storage_type="SSD",
        )

        # Expected: (4*100 + 8*10) * 5 + 100*0.30
        # = 480 * 5 + 30 = 2430
        assert cost == Decimal("2430")


class TestCalculatePowerCosts:
    """Tests for calculate_power_costs function."""

    def test_basic_power_cost_calculation(self):
        """Test power cost with typical values."""
        cost = on_prem_costs.calculate_power_costs(
            cpu_cores=8,
            instance_count=2,
            utilization_percentage=50,
            operating_hours_per_month=730,
            years=1,
        )

        # Expected: 50W * 16 cores * 0.5 utilization * 730 hours / 1000 * $0.12 * 12 months
        # = 400W * 730 / 1000 * 0.12 * 12
        # = 292 kWh * 0.12 * 12 = 420.48
        assert cost == Decimal("420.48")

    def test_power_cost_scales_with_years(self):
        """Test power cost scales linearly with years."""
        cost_1_year = on_prem_costs.calculate_power_costs(
            cpu_cores=4, instance_count=1, utilization_percentage=100, operating_hours_per_month=744, years=1
        )
        cost_3_years = on_prem_costs.calculate_power_costs(
            cpu_cores=4, instance_count=1, utilization_percentage=100, operating_hours_per_month=744, years=3
        )

        assert cost_3_years == cost_1_year * 3

    def test_power_cost_with_low_utilization(self):
        """Test power cost with low utilization percentage."""
        cost = on_prem_costs.calculate_power_costs(
            cpu_cores=8,
            instance_count=1,
            utilization_percentage=10,
            operating_hours_per_month=730,
            years=1,
        )

        # Should be 1/5 of 50% utilization
        cost_50_percent = on_prem_costs.calculate_power_costs(
            cpu_cores=8,
            instance_count=1,
            utilization_percentage=50,
            operating_hours_per_month=730,
            years=1,
        )

        assert cost == cost_50_percent / 5


class TestCalculateCoolingCosts:
    """Tests for calculate_cooling_costs function."""

    def test_cooling_cost_is_40_percent_of_power(self):
        """Test cooling cost is 40% of power cost."""
        power_cost = on_prem_costs.calculate_power_costs(
            cpu_cores=8,
            instance_count=2,
            utilization_percentage=75,
            operating_hours_per_month=730,
            years=1,
        )

        cooling_cost = on_prem_costs.calculate_cooling_costs(
            cpu_cores=8,
            instance_count=2,
            utilization_percentage=75,
            operating_hours_per_month=730,
            years=1,
        )

        assert cooling_cost == power_cost * Decimal("0.40")

    def test_cooling_cost_scales_with_years(self):
        """Test cooling cost scales linearly with years."""
        cost_1_year = on_prem_costs.calculate_cooling_costs(
            cpu_cores=4, instance_count=1, utilization_percentage=100, operating_hours_per_month=744, years=1
        )
        cost_5_years = on_prem_costs.calculate_cooling_costs(
            cpu_cores=4, instance_count=1, utilization_percentage=100, operating_hours_per_month=744, years=5
        )

        assert cost_5_years == cost_1_year * 5


class TestCalculateMaintenanceCosts:
    """Tests for calculate_maintenance_costs function."""

    def test_maintenance_cost_is_17_5_percent_annually(self):
        """Test maintenance cost is 17.5% of hardware cost annually."""
        hardware_cost = on_prem_costs.calculate_hardware_costs(
            cpu_cores=8,
            memory_gb=32,
            instance_count=2,
            storage_capacity_gb=1000,
            storage_type="SSD",
        )

        maintenance_cost = on_prem_costs.calculate_maintenance_costs(
            cpu_cores=8,
            memory_gb=32,
            instance_count=2,
            storage_capacity_gb=1000,
            storage_type="SSD",
            years=1,
        )

        assert maintenance_cost == hardware_cost * Decimal("0.175")

    def test_maintenance_cost_scales_with_years(self):
        """Test maintenance cost scales linearly with years."""
        cost_1_year = on_prem_costs.calculate_maintenance_costs(
            cpu_cores=4, memory_gb=16, instance_count=1, storage_capacity_gb=500, storage_type="HDD", years=1
        )
        cost_3_years = on_prem_costs.calculate_maintenance_costs(
            cpu_cores=4, memory_gb=16, instance_count=1, storage_capacity_gb=500, storage_type="HDD", years=3
        )

        assert cost_3_years == cost_1_year * 3


class TestCalculateDataTransferCosts:
    """Tests for calculate_data_transfer_costs function."""

    def test_basic_data_transfer_cost(self):
        """Test data transfer cost with typical values."""
        cost = on_prem_costs.calculate_data_transfer_costs(
            monthly_data_transfer_gb=500,
            bandwidth_mbps=100,
            years=1,
        )

        # Expected: (100 Mbps * $3) * 12 months
        # Included: 100 * 10 = 1000 GB, so no overage
        # = 300 * 12 = 3600
        assert cost == Decimal("3600")

    def test_data_transfer_with_overage(self):
        """Test data transfer cost with overage charges."""
        cost = on_prem_costs.calculate_data_transfer_costs(
            monthly_data_transfer_gb=2000,
            bandwidth_mbps=100,
            years=1,
        )

        # Expected: (100 * $3 + (2000 - 1000) * $0.02) * 12
        # = (300 + 20) * 12 = 3840
        assert cost == Decimal("3840")

    def test_data_transfer_scales_with_years(self):
        """Test data transfer cost scales linearly with years."""
        cost_1_year = on_prem_costs.calculate_data_transfer_costs(
            monthly_data_transfer_gb=1000, bandwidth_mbps=100, years=1
        )
        cost_5_years = on_prem_costs.calculate_data_transfer_costs(
            monthly_data_transfer_gb=1000, bandwidth_mbps=100, years=5
        )

        assert cost_5_years == cost_1_year * 5

    def test_data_transfer_no_overage_when_within_limit(self):
        """Test no overage charges when transfer is within included bandwidth."""
        # 100 Mbps includes 1000 GB
        cost_500gb = on_prem_costs.calculate_data_transfer_costs(
            monthly_data_transfer_gb=500, bandwidth_mbps=100, years=1
        )
        cost_1000gb = on_prem_costs.calculate_data_transfer_costs(
            monthly_data_transfer_gb=1000, bandwidth_mbps=100, years=1
        )

        # Both should have same cost (no overage)
        assert cost_500gb == cost_1000gb
