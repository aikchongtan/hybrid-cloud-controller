"""Unit tests for AWS cost calculation functions."""

from decimal import Decimal

from packages.tco_engine import aws_costs


class TestCalculateEC2Costs:
    """Tests for calculate_ec2_costs function."""

    def test_basic_ec2_cost_calculation(self):
        """Test EC2 cost calculation with typical values."""
        ec2_pricing = {
            "t3.small": Decimal("0.0208"),
            "t3.medium": Decimal("0.0416"),
            "m5.large": Decimal("0.096"),
        }

        cost = aws_costs.calculate_ec2_costs(
            cpu_cores=2,
            memory_gb=4,
            instance_count=2,
            utilization_percentage=70,
            operating_hours_per_month=730,
            ec2_pricing=ec2_pricing,
            years=1,
        )

        # Should select t3.medium (2 vCPU, 4GB)
        # Cost = 0.0416 * 730 hours * 2 instances * 12 months
        expected = Decimal("0.0416") * 730 * 2 * 12
        assert cost == expected

    def test_ec2_cost_scales_with_years(self):
        """Test EC2 cost scales linearly with years."""
        ec2_pricing = {"m5.large": Decimal("0.096")}

        cost_1_year = aws_costs.calculate_ec2_costs(
            cpu_cores=2,
            memory_gb=8,
            instance_count=1,
            utilization_percentage=50,
            operating_hours_per_month=730,
            ec2_pricing=ec2_pricing,
            years=1,
        )

        cost_3_years = aws_costs.calculate_ec2_costs(
            cpu_cores=2,
            memory_gb=8,
            instance_count=1,
            utilization_percentage=50,
            operating_hours_per_month=730,
            ec2_pricing=ec2_pricing,
            years=3,
        )

        assert cost_3_years == cost_1_year * 3


class TestCalculateEBSCosts:
    """Tests for calculate_ebs_costs function."""

    def test_basic_ebs_cost_calculation(self):
        """Test EBS cost calculation for standard SSD."""
        ebs_pricing = {
            "gp3": Decimal("0.08"),
            "st1": Decimal("0.045"),
            "io2": Decimal("0.125"),
        }

        cost = aws_costs.calculate_ebs_costs(
            storage_capacity_gb=100,
            storage_type="SSD",
            storage_iops=None,
            ebs_pricing=ebs_pricing,
            years=1,
        )

        # Cost = 100 GB * 0.08 per GB/month * 12 months
        expected = Decimal("100") * Decimal("0.08") * 12
        assert cost == expected

    def test_ebs_cost_with_provisioned_iops(self):
        """Test EBS cost calculation with provisioned IOPS."""
        ebs_pricing = {
            "io2": Decimal("0.125"),
            "iops": Decimal("0.065"),
        }

        cost = aws_costs.calculate_ebs_costs(
            storage_capacity_gb=100,
            storage_type="NVME",
            storage_iops=1000,
            ebs_pricing=ebs_pricing,
            years=1,
        )

        # Cost = (100 * 0.125 + 1000 * 0.065) * 12
        expected = (Decimal("100") * Decimal("0.125") + Decimal("1000") * Decimal("0.065")) * 12
        assert cost == expected


class TestCalculateS3Costs:
    """Tests for calculate_s3_costs function."""

    def test_basic_s3_cost_calculation(self):
        """Test S3 cost calculation."""
        s3_pricing = {"standard": Decimal("0.023")}

        cost = aws_costs.calculate_s3_costs(
            storage_capacity_gb=500,
            s3_pricing=s3_pricing,
            years=1,
        )

        # Cost = 500 GB * 0.023 per GB/month * 12 months
        expected = Decimal("500") * Decimal("0.023") * 12
        assert cost == expected

    def test_s3_cost_scales_with_years(self):
        """Test S3 cost scales linearly with years."""
        s3_pricing = {"standard": Decimal("0.023")}

        cost_1_year = aws_costs.calculate_s3_costs(
            storage_capacity_gb=1000,
            s3_pricing=s3_pricing,
            years=1,
        )

        cost_5_years = aws_costs.calculate_s3_costs(
            storage_capacity_gb=1000,
            s3_pricing=s3_pricing,
            years=5,
        )

        assert cost_5_years == cost_1_year * 5


class TestCalculateDataTransferCosts:
    """Tests for calculate_data_transfer_costs function."""

    def test_data_transfer_with_free_tier(self):
        """Test data transfer cost with AWS free tier (100GB/month)."""
        data_transfer_pricing = {
            "internet_egress": Decimal("0.09"),
            "inter_az": Decimal("0.01"),
        }

        # 150 GB total: 50 GB billable egress + 15 GB inter-AZ
        cost = aws_costs.calculate_data_transfer_costs(
            monthly_data_transfer_gb=150,
            data_transfer_pricing=data_transfer_pricing,
            years=1,
        )

        # Egress: (150 - 100) * 0.09 = 4.5
        # Inter-AZ: 150 * 0.10 * 0.01 = 0.15
        # Monthly: 4.5 + 0.15 = 4.65
        # Yearly: 4.65 * 12 = 55.8
        expected = (Decimal("50") * Decimal("0.09") + Decimal("150") * Decimal("0.10") * Decimal("0.01")) * 12
        assert cost == expected

    def test_data_transfer_below_free_tier(self):
        """Test data transfer cost when below free tier."""
        data_transfer_pricing = {
            "internet_egress": Decimal("0.09"),
            "inter_az": Decimal("0.01"),
        }

        # 50 GB total: 0 GB billable egress (under 100GB free tier) + 5 GB inter-AZ
        cost = aws_costs.calculate_data_transfer_costs(
            monthly_data_transfer_gb=50,
            data_transfer_pricing=data_transfer_pricing,
            years=1,
        )

        # Egress: 0 (under free tier)
        # Inter-AZ: 50 * 0.10 * 0.01 = 0.05
        # Monthly: 0.05
        # Yearly: 0.05 * 12 = 0.6
        expected = Decimal("50") * Decimal("0.10") * Decimal("0.01") * 12
        assert cost == expected

    def test_data_transfer_scales_with_years(self):
        """Test data transfer cost scales linearly with years."""
        data_transfer_pricing = {
            "internet_egress": Decimal("0.09"),
            "inter_az": Decimal("0.01"),
        }

        cost_1_year = aws_costs.calculate_data_transfer_costs(
            monthly_data_transfer_gb=500,
            data_transfer_pricing=data_transfer_pricing,
            years=1,
        )

        cost_3_years = aws_costs.calculate_data_transfer_costs(
            monthly_data_transfer_gb=500,
            data_transfer_pricing=data_transfer_pricing,
            years=3,
        )

        assert cost_3_years == cost_1_year * 3


class TestInstanceTypeSelection:
    """Tests for _select_instance_type helper function."""

    def test_selects_smallest_matching_instance(self):
        """Test that smallest instance meeting requirements is selected."""
        ec2_pricing = {
            "t3.small": Decimal("0.0208"),
            "t3.medium": Decimal("0.0416"),
            "m5.large": Decimal("0.096"),
        }

        instance_type = aws_costs._select_instance_type(
            cpu_cores=2,
            memory_gb=2,
            ec2_pricing=ec2_pricing,
        )

        # Should select t3.small (2 vCPU, 2GB) as it's cheapest
        assert instance_type == "t3.small"

    def test_selects_cheapest_when_multiple_match(self):
        """Test that cheapest instance is selected when multiple match."""
        ec2_pricing = {
            "t3.medium": Decimal("0.0416"),
            "m5.large": Decimal("0.096"),
        }

        instance_type = aws_costs._select_instance_type(
            cpu_cores=2,
            memory_gb=4,
            ec2_pricing=ec2_pricing,
        )

        # Both match requirements, should select cheaper t3.medium
        assert instance_type == "t3.medium"


class TestStorageTypeMapping:
    """Tests for _map_storage_type_to_ebs helper function."""

    def test_maps_ssd_to_gp3(self):
        """Test SSD maps to gp3."""
        assert aws_costs._map_storage_type_to_ebs("SSD") == "gp3"

    def test_maps_hdd_to_st1(self):
        """Test HDD maps to st1."""
        assert aws_costs._map_storage_type_to_ebs("HDD") == "st1"

    def test_maps_nvme_to_io2(self):
        """Test NVME maps to io2."""
        assert aws_costs._map_storage_type_to_ebs("NVME") == "io2"

    def test_defaults_to_gp3_for_unknown(self):
        """Test unknown storage type defaults to gp3."""
        assert aws_costs._map_storage_type_to_ebs("UNKNOWN") == "gp3"
