"""Unit tests for on-premises IaaS provisioner."""

import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.database import models
from packages.provisioner import onprem_provisioner


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    yield session
    session.close()


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    config = models.ConfigurationModel(
        id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        cpu_cores=4,
        memory_gb=8,
        instance_count=2,
        storage_type="ssd",
        storage_capacity_gb=100,
        storage_iops=3000,
        bandwidth_mbps=1000,
        monthly_data_transfer_gb=500,
        utilization_percentage=80,
        operating_hours_per_month=720,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return config


@pytest.fixture
def provision_id():
    """Generate a provision ID for testing."""
    return str(uuid.uuid4())


class TestProvisionIaaS:
    """Tests for provision_iaas function."""

    def test_provision_iaas_mock_mode_default(self, sample_config, provision_id, db_session):
        """Test that provision_iaas defaults to mock mode."""
        vms = onprem_provisioner.provision_iaas(
            config=sample_config,
            provision_id=provision_id,
            db_session=db_session,
        )

        # Should create 2 VMs (instance_count=2)
        assert len(vms) == 2

        # Verify VM details
        for vm in vms:
            assert vm.cpu_cores == 4
            assert vm.memory_gb == 8
            assert vm.storage_gb == 100
            assert vm.port == 22
            assert vm.username == "ubuntu"
            assert len(vm.password) > 0
            assert vm.status == "running"
            assert vm.ip_address.startswith("10.0.")

        # Verify database tracking
        resources = db_session.query(models.ResourceModel).all()
        assert len(resources) == 2

        for resource in resources:
            assert resource.provision_id == provision_id
            assert resource.resource_type == "vm"
            assert resource.status == "running"

            # Verify connection info
            conn_info = json.loads(resource.connection_info_json)
            assert "ip_address" in conn_info
            assert "port" in conn_info
            assert "username" in conn_info
            assert "password" in conn_info

    def test_provision_iaas_explicit_mock_mode(self, sample_config, provision_id, db_session):
        """Test provision_iaas with explicit mock_mode=True."""
        vms = onprem_provisioner.provision_iaas(
            config=sample_config,
            provision_id=provision_id,
            db_session=db_session,
            mock_mode=True,
        )

        assert len(vms) == 2
        assert all(vm.status == "running" for vm in vms)

    def test_provision_iaas_single_instance(self, provision_id, db_session):
        """Test provisioning a single VM."""
        config = models.ConfigurationModel(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            cpu_cores=2,
            memory_gb=4,
            instance_count=1,
            storage_type="ssd",
            storage_capacity_gb=50,
            storage_iops=1000,
            bandwidth_mbps=500,
            monthly_data_transfer_gb=100,
            utilization_percentage=50,
            operating_hours_per_month=360,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        vms = onprem_provisioner.provision_iaas(
            config=config,
            provision_id=provision_id,
            db_session=db_session,
            mock_mode=True,
        )

        assert len(vms) == 1
        assert vms[0].cpu_cores == 2
        assert vms[0].memory_gb == 4
        assert vms[0].storage_gb == 50

    def test_provision_iaas_multiple_instances(self, provision_id, db_session):
        """Test provisioning multiple VMs."""
        config = models.ConfigurationModel(
            id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            cpu_cores=8,
            memory_gb=16,
            instance_count=5,
            storage_type="nvme",
            storage_capacity_gb=200,
            storage_iops=5000,
            bandwidth_mbps=2000,
            monthly_data_transfer_gb=1000,
            utilization_percentage=90,
            operating_hours_per_month=744,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        vms = onprem_provisioner.provision_iaas(
            config=config,
            provision_id=provision_id,
            db_session=db_session,
            mock_mode=True,
        )

        assert len(vms) == 5

        # Verify each VM has unique ID and IP
        vm_ids = [vm.vm_id for vm in vms]
        assert len(set(vm_ids)) == 5  # All unique

        vm_ips = [vm.ip_address for vm in vms]
        assert len(set(vm_ips)) == 5  # All unique

    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", False)
    def test_provision_iaas_production_mode_no_libvirt(
        self, sample_config, provision_id, db_session
    ):
        """Test that production mode raises error when libvirt is not available."""
        with pytest.raises(RuntimeError, match="Production mode requires libvirt-python"):
            onprem_provisioner.provision_iaas(
                config=sample_config,
                provision_id=provision_id,
                db_session=db_session,
                mock_mode=False,
            )

    def test_provision_iaas_database_tracking(self, sample_config, provision_id, db_session):
        """Test that all VMs are properly tracked in database."""
        vms = onprem_provisioner.provision_iaas(
            config=sample_config,
            provision_id=provision_id,
            db_session=db_session,
            mock_mode=True,
        )

        # Query database for resources
        resources = (
            db_session.query(models.ResourceModel).filter_by(provision_id=provision_id).all()
        )

        assert len(resources) == len(vms)

        # Verify each VM is tracked
        for vm, resource in zip(vms, resources):
            assert resource.external_id == vm.vm_id
            assert resource.resource_type == "vm"
            assert resource.status == vm.status

            conn_info = json.loads(resource.connection_info_json)
            assert conn_info["ip_address"] == vm.ip_address
            assert conn_info["port"] == str(vm.port)
            assert conn_info["username"] == vm.username
            assert conn_info["password"] == vm.password


class TestCreateMockVM:
    """Tests for create_mock_vm function."""

    def test_create_mock_vm_basic(self, sample_config, provision_id):
        """Test creating a basic mock VM."""
        vm = onprem_provisioner.create_mock_vm(sample_config, provision_id, 0)

        assert vm.cpu_cores == sample_config.cpu_cores
        assert vm.memory_gb == sample_config.memory_gb
        assert vm.storage_gb == sample_config.storage_capacity_gb
        assert vm.port == 22
        assert vm.username == "ubuntu"
        assert vm.status == "running"

    def test_create_mock_vm_unique_ids(self, sample_config, provision_id):
        """Test that each mock VM gets a unique ID."""
        vm1 = onprem_provisioner.create_mock_vm(sample_config, provision_id, 0)
        vm2 = onprem_provisioner.create_mock_vm(sample_config, provision_id, 1)

        assert vm1.vm_id != vm2.vm_id

    def test_create_mock_vm_unique_ips(self, sample_config, provision_id):
        """Test that each mock VM gets a unique IP address."""
        vms = [onprem_provisioner.create_mock_vm(sample_config, provision_id, i) for i in range(10)]

        ips = [vm.ip_address for vm in vms]
        assert len(set(ips)) == 10  # All unique

        # Verify IP format
        for ip in ips:
            assert ip.startswith("10.0.")
            parts = ip.split(".")
            assert len(parts) == 4
            assert all(part.isdigit() for part in parts)

    def test_create_mock_vm_ip_range(self, sample_config, provision_id):
        """Test that mock VM IPs are in the correct range."""
        vm = onprem_provisioner.create_mock_vm(sample_config, provision_id, 0)

        parts = vm.ip_address.split(".")
        assert parts[0] == "10"
        assert parts[1] == "0"
        assert 0 <= int(parts[2]) <= 255
        assert 1 <= int(parts[3]) <= 256

    def test_create_mock_vm_password_generation(self, sample_config, provision_id):
        """Test that mock VMs get secure passwords."""
        vm1 = onprem_provisioner.create_mock_vm(sample_config, provision_id, 0)
        vm2 = onprem_provisioner.create_mock_vm(sample_config, provision_id, 1)

        # Passwords should be non-empty
        assert len(vm1.password) > 0
        assert len(vm2.password) > 0

        # Passwords should be unique
        assert vm1.password != vm2.password

    def test_create_mock_vm_name_format(self, sample_config, provision_id):
        """Test that mock VM names follow the expected format."""
        vm = onprem_provisioner.create_mock_vm(sample_config, provision_id, 3)

        assert vm.name.startswith("mock-vm-")
        assert provision_id[:8] in vm.name
        assert vm.name.endswith("-3")

    def test_create_mock_vm_no_resources_consumed(self, sample_config, provision_id):
        """Test that mock mode doesn't consume actual resources."""
        # This test verifies that create_mock_vm completes quickly
        # and doesn't make any system calls to create real VMs
        import time

        start = time.time()
        vm = onprem_provisioner.create_mock_vm(sample_config, provision_id, 0)
        elapsed = time.time() - start

        # Should complete in less than 1 second (no actual VM creation)
        assert elapsed < 1.0
        assert vm.status == "running"


class TestCreateVM:
    """Tests for create_vm function (production mode)."""

    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", False)
    def test_create_vm_no_libvirt(self, sample_config, provision_id):
        """Test that create_vm raises error when libvirt is not available."""
        with pytest.raises(RuntimeError, match="libvirt-python is not available"):
            onprem_provisioner.create_vm(sample_config, provision_id, 0)

    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", True)
    @patch("packages.provisioner.onprem_provisioner.libvirt")
    def test_create_vm_success(self, mock_libvirt, sample_config, provision_id):
        """Test successful VM creation with libvirt."""
        # Mock libvirt connection and domain
        mock_conn = MagicMock()
        mock_domain = MagicMock()
        mock_domain.UUIDString.return_value = "test-uuid-1234"
        mock_domain.create.return_value = 0  # Success

        mock_conn.defineXML.return_value = mock_domain
        mock_libvirt.open.return_value = mock_conn

        vm = onprem_provisioner.create_vm(sample_config, provision_id, 0)

        # Verify libvirt was called correctly
        mock_libvirt.open.assert_called_once_with("qemu:///system")
        mock_conn.defineXML.assert_called_once()
        mock_domain.create.assert_called_once()
        mock_conn.close.assert_called_once()

        # Verify VM details
        assert vm.vm_id == "test-uuid-1234"
        assert vm.cpu_cores == sample_config.cpu_cores
        assert vm.memory_gb == sample_config.memory_gb
        assert vm.storage_gb == sample_config.storage_capacity_gb
        assert vm.status == "running"

    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", True)
    @patch("packages.provisioner.onprem_provisioner.libvirt")
    def test_create_vm_connection_failure(self, mock_libvirt, sample_config, provision_id):
        """Test VM creation when libvirt connection fails."""
        mock_libvirt.open.return_value = None

        with pytest.raises(RuntimeError, match="Failed to connect to libvirt"):
            onprem_provisioner.create_vm(sample_config, provision_id, 0)

    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", True)
    @patch("packages.provisioner.onprem_provisioner.libvirt")
    def test_create_vm_define_failure(self, mock_libvirt, sample_config, provision_id):
        """Test VM creation when defineXML fails."""
        mock_conn = MagicMock()
        mock_conn.defineXML.return_value = None
        mock_libvirt.open.return_value = mock_conn

        with pytest.raises(RuntimeError, match="Failed to define VM"):
            onprem_provisioner.create_vm(sample_config, provision_id, 0)

    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", True)
    @patch("packages.provisioner.onprem_provisioner.libvirt")
    def test_create_vm_start_failure(self, mock_libvirt, sample_config, provision_id):
        """Test VM creation when domain.create() fails."""
        mock_conn = MagicMock()
        mock_domain = MagicMock()
        mock_domain.create.return_value = -1  # Failure

        mock_conn.defineXML.return_value = mock_domain
        mock_libvirt.open.return_value = mock_conn

        with pytest.raises(RuntimeError, match="Failed to start VM"):
            onprem_provisioner.create_vm(sample_config, provision_id, 0)

    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", True)
    @patch("packages.provisioner.onprem_provisioner.libvirt")
    def test_create_vm_libvirt_error(self, mock_libvirt, sample_config, provision_id):
        """Test VM creation when libvirt raises an error."""
        mock_conn = MagicMock()
        mock_libvirt.open.return_value = mock_conn
        mock_libvirt.libvirtError = Exception  # Mock the exception class

        # Make defineXML raise a libvirt error
        mock_conn.defineXML.side_effect = Exception("Libvirt error")

        with pytest.raises(RuntimeError, match="Failed to create VM"):
            onprem_provisioner.create_vm(sample_config, provision_id, 0)


class TestGenerateVMXML:
    """Tests for _generate_vm_xml helper function."""

    def test_generate_vm_xml_basic(self):
        """Test basic VM XML generation."""
        xml = onprem_provisioner._generate_vm_xml(
            name="test-vm", cpu_cores=4, memory_gb=8, storage_gb=100
        )

        assert "<name>test-vm</name>" in xml
        assert "<vcpu placement='static'>4</vcpu>" in xml
        assert "<memory unit='KiB'>8388608</memory>" in xml  # 8GB in KB
        assert "type='kvm'" in xml
        assert "qcow2" in xml

    def test_generate_vm_xml_memory_conversion(self):
        """Test that memory is correctly converted from GB to KB."""
        xml = onprem_provisioner._generate_vm_xml(
            name="test-vm", cpu_cores=2, memory_gb=16, storage_gb=50
        )

        # 16 GB = 16 * 1024 * 1024 KB = 16777216 KB
        assert "<memory unit='KiB'>16777216</memory>" in xml
        assert "<currentMemory unit='KiB'>16777216</currentMemory>" in xml

    def test_generate_vm_xml_cpu_cores(self):
        """Test that CPU cores are correctly set."""
        xml = onprem_provisioner._generate_vm_xml(
            name="test-vm", cpu_cores=16, memory_gb=32, storage_gb=200
        )

        assert "<vcpu placement='static'>16</vcpu>" in xml

    def test_generate_vm_xml_disk_path(self):
        """Test that disk path includes VM name."""
        xml = onprem_provisioner._generate_vm_xml(
            name="my-custom-vm", cpu_cores=2, memory_gb=4, storage_gb=50
        )

        assert "/var/lib/libvirt/images/my-custom-vm.qcow2" in xml

    def test_generate_vm_xml_network_interface(self):
        """Test that network interface is configured."""
        xml = onprem_provisioner._generate_vm_xml(
            name="test-vm", cpu_cores=2, memory_gb=4, storage_gb=50
        )

        assert "<interface type='network'>" in xml
        assert "<source network='default'/>" in xml
        assert "virtio" in xml


class TestGeneratePassword:
    """Tests for _generate_password helper function."""

    def test_generate_password_default_length(self):
        """Test password generation with default length."""
        password = onprem_provisioner._generate_password()

        assert len(password) == 16

    def test_generate_password_custom_length(self):
        """Test password generation with custom length."""
        password = onprem_provisioner._generate_password(length=24)

        assert len(password) == 24

    def test_generate_password_uniqueness(self):
        """Test that generated passwords are unique."""
        passwords = [onprem_provisioner._generate_password() for _ in range(100)]

        # All passwords should be unique
        assert len(set(passwords)) == 100

    def test_generate_password_complexity(self):
        """Test that generated passwords contain different character types."""
        password = onprem_provisioner._generate_password()

        has_lowercase = any(c.islower() for c in password)
        has_uppercase = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_punctuation = any(not c.isalnum() for c in password)

        assert has_lowercase, "Password should contain lowercase letters"
        assert has_uppercase, "Password should contain uppercase letters"
        assert has_digit, "Password should contain digits"
        assert has_punctuation, "Password should contain punctuation"

    def test_generate_password_no_spaces(self):
        """Test that generated passwords don't contain spaces."""
        passwords = [onprem_provisioner._generate_password() for _ in range(10)]

        for password in passwords:
            assert " " not in password


class TestVMDetails:
    """Tests for VMDetails dataclass."""

    def test_vm_details_creation(self):
        """Test creating a VMDetails instance."""
        vm = onprem_provisioner.VMDetails(
            vm_id="test-id",
            name="test-vm",
            cpu_cores=4,
            memory_gb=8,
            storage_gb=100,
            ip_address="10.0.0.1",
            port=22,
            username="ubuntu",
            password="test-password",
            status="running",
        )

        assert vm.vm_id == "test-id"
        assert vm.name == "test-vm"
        assert vm.cpu_cores == 4
        assert vm.memory_gb == 8
        assert vm.storage_gb == 100
        assert vm.ip_address == "10.0.0.1"
        assert vm.port == 22
        assert vm.username == "ubuntu"
        assert vm.password == "test-password"
        assert vm.status == "running"


class TestIntegration:
    """Integration tests for the provisioner."""

    def test_end_to_end_mock_provisioning(self, sample_config, provision_id, db_session):
        """Test complete provisioning workflow in mock mode."""
        # Provision VMs
        vms = onprem_provisioner.provision_iaas(
            config=sample_config,
            provision_id=provision_id,
            db_session=db_session,
            mock_mode=True,
        )

        # Verify VMs were created
        assert len(vms) == sample_config.instance_count

        # Verify database records
        resources = (
            db_session.query(models.ResourceModel).filter_by(provision_id=provision_id).all()
        )
        assert len(resources) == sample_config.instance_count

        # Verify connection details are retrievable
        for resource in resources:
            conn_info = json.loads(resource.connection_info_json)
            assert conn_info["ip_address"]
            assert conn_info["port"]
            assert conn_info["username"]
            assert conn_info["password"]

    def test_multiple_provisions_isolated(self, sample_config, db_session):
        """Test that multiple provisions are properly isolated."""
        provision_id_1 = str(uuid.uuid4())
        provision_id_2 = str(uuid.uuid4())

        # Provision first set
        onprem_provisioner.provision_iaas(
            config=sample_config,
            provision_id=provision_id_1,
            db_session=db_session,
            mock_mode=True,
        )

        # Provision second set
        onprem_provisioner.provision_iaas(
            config=sample_config,
            provision_id=provision_id_2,
            db_session=db_session,
            mock_mode=True,
        )

        # Verify both provisions exist
        resources1 = (
            db_session.query(models.ResourceModel).filter_by(provision_id=provision_id_1).all()
        )
        resources2 = (
            db_session.query(models.ResourceModel).filter_by(provision_id=provision_id_2).all()
        )

        assert len(resources1) == sample_config.instance_count
        assert len(resources2) == sample_config.instance_count

        # Verify they have different IDs
        ids1 = {r.id for r in resources1}
        ids2 = {r.id for r in resources2}
        assert ids1.isdisjoint(ids2)
