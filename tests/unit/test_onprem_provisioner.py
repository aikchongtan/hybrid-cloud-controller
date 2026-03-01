"""Unit tests for on-premises IaaS provisioner."""

import json
import subprocess
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


class TestProvisionCaaS:
    """Tests for provision_caas function."""

    @patch("packages.provisioner.onprem_provisioner._detect_container_runtime")
    @patch("packages.provisioner.onprem_provisioner.create_container")
    def test_provision_caas_docker(
        self, mock_create_container, mock_detect_runtime, sample_config, provision_id, db_session
    ):
        """Test CaaS provisioning with Docker."""
        mock_detect_runtime.return_value = "docker"

        # Mock container creation
        mock_containers = [
            onprem_provisioner.ContainerDetails(
                container_id=f"container-{i}",
                name=f"test-container-{i}",
                image_url="nginx:latest",
                cpu_limit=4.0,
                memory_limit_mb=8192,
                endpoint=f"172.17.0.{i + 2}",
                port=80,
                status="running",
                environment_vars={"ENV": "test"},
            )
            for i in range(2)
        ]
        mock_create_container.side_effect = mock_containers

        containers = onprem_provisioner.provision_caas(
            config=sample_config,
            image_url="nginx:latest",
            provision_id=provision_id,
            db_session=db_session,
            environment_vars={"ENV": "test"},
        )

        # Verify containers were created
        assert len(containers) == 2
        assert mock_create_container.call_count == 2

        # Verify database tracking
        resources = db_session.query(models.ResourceModel).all()
        assert len(resources) == 2

        for resource in resources:
            assert resource.provision_id == provision_id
            assert resource.resource_type == "container"
            assert resource.status == "running"

            conn_info = json.loads(resource.connection_info_json)
            assert "endpoint" in conn_info
            assert "port" in conn_info
            assert "container_id" in conn_info
            assert "image_url" in conn_info

    @patch("packages.provisioner.onprem_provisioner._detect_container_runtime")
    @patch("packages.provisioner.onprem_provisioner.create_container")
    def test_provision_caas_podman(
        self, mock_create_container, mock_detect_runtime, sample_config, provision_id, db_session
    ):
        """Test CaaS provisioning with Podman."""
        mock_detect_runtime.return_value = "podman"

        mock_container = onprem_provisioner.ContainerDetails(
            container_id="podman-container-1",
            name="test-container",
            image_url="nginx:latest",
            cpu_limit=4.0,
            memory_limit_mb=8192,
            endpoint="10.88.0.2",
            port=80,
            status="running",
            environment_vars={},
        )
        mock_create_container.return_value = mock_container

        containers = onprem_provisioner.provision_caas(
            config=sample_config,
            image_url="nginx:latest",
            provision_id=provision_id,
            db_session=db_session,
            use_podman=True,
        )

        assert len(containers) == 2
        mock_detect_runtime.assert_called_once_with(True)

    @patch("packages.provisioner.onprem_provisioner._detect_container_runtime")
    def test_provision_caas_no_runtime(
        self, mock_detect_runtime, sample_config, provision_id, db_session
    ):
        """Test CaaS provisioning when neither Docker nor Podman is available."""
        mock_detect_runtime.return_value = None

        with pytest.raises(RuntimeError, match="Neither Docker nor Podman is available"):
            onprem_provisioner.provision_caas(
                config=sample_config,
                image_url="nginx:latest",
                provision_id=provision_id,
                db_session=db_session,
            )

    @patch("packages.provisioner.onprem_provisioner._detect_container_runtime")
    @patch("packages.provisioner.onprem_provisioner.create_container")
    def test_provision_caas_with_environment_vars(
        self, mock_create_container, mock_detect_runtime, sample_config, provision_id, db_session
    ):
        """Test CaaS provisioning with environment variables."""
        mock_detect_runtime.return_value = "docker"

        env_vars = {
            "DATABASE_URL": "postgresql://localhost/db",
            "API_KEY": "secret-key",
            "DEBUG": "true",
        }

        mock_container = onprem_provisioner.ContainerDetails(
            container_id="container-1",
            name="test-container",
            image_url="myapp:latest",
            cpu_limit=4.0,
            memory_limit_mb=8192,
            endpoint="172.17.0.2",
            port=8080,
            status="running",
            environment_vars=env_vars,
        )
        mock_create_container.return_value = mock_container

        onprem_provisioner.provision_caas(
            config=sample_config,
            image_url="myapp:latest",
            provision_id=provision_id,
            db_session=db_session,
            environment_vars=env_vars,
        )

        # Verify environment variables were passed
        call_args = mock_create_container.call_args_list[0]
        assert call_args[1]["environment_vars"] == env_vars

    @patch("packages.provisioner.onprem_provisioner._detect_container_runtime")
    @patch("packages.provisioner.onprem_provisioner.create_container")
    def test_provision_caas_single_container(
        self, mock_create_container, mock_detect_runtime, provision_id, db_session
    ):
        """Test provisioning a single container."""
        mock_detect_runtime.return_value = "docker"

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

        mock_container = onprem_provisioner.ContainerDetails(
            container_id="container-1",
            name="test-container",
            image_url="nginx:latest",
            cpu_limit=2.0,
            memory_limit_mb=4096,
            endpoint="172.17.0.2",
            port=80,
            status="running",
            environment_vars={},
        )
        mock_create_container.return_value = mock_container

        containers = onprem_provisioner.provision_caas(
            config=config,
            image_url="nginx:latest",
            provision_id=provision_id,
            db_session=db_session,
        )

        assert len(containers) == 1
        assert containers[0].cpu_limit == 2.0
        assert containers[0].memory_limit_mb == 4096


class TestCreateContainer:
    """Tests for create_container function."""

    @patch("packages.provisioner.onprem_provisioner._create_docker_container")
    def test_create_container_docker(self, mock_create_docker, sample_config, provision_id):
        """Test creating a container with Docker."""
        mock_create_docker.return_value = ("container-id-123", "172.17.0.2", 80)

        container = onprem_provisioner.create_container(
            config=sample_config,
            image_url="nginx:latest",
            provision_id=provision_id,
            index=0,
            environment_vars={"ENV": "test"},
            runtime="docker",
        )

        assert container.container_id == "container-id-123"
        assert container.endpoint == "172.17.0.2"
        assert container.port == 80
        assert container.cpu_limit == 4.0
        assert container.memory_limit_mb == 8192
        assert container.status == "running"
        assert container.environment_vars == {"ENV": "test"}

        mock_create_docker.assert_called_once()

    @patch("packages.provisioner.onprem_provisioner._create_podman_container")
    def test_create_container_podman(self, mock_create_podman, sample_config, provision_id):
        """Test creating a container with Podman."""
        mock_create_podman.return_value = ("podman-id-456", "10.88.0.2", 8080)

        container = onprem_provisioner.create_container(
            config=sample_config,
            image_url="myapp:v1",
            provision_id=provision_id,
            index=1,
            environment_vars={"DEBUG": "true"},
            runtime="podman",
        )

        assert container.container_id == "podman-id-456"
        assert container.endpoint == "10.88.0.2"
        assert container.port == 8080
        assert container.status == "running"

        mock_create_podman.assert_called_once()

    @patch("packages.provisioner.onprem_provisioner._create_docker_container")
    def test_create_container_failure(self, mock_create_docker, sample_config, provision_id):
        """Test container creation failure."""
        mock_create_docker.side_effect = Exception("Docker daemon not running")

        with pytest.raises(RuntimeError, match="Failed to create container"):
            onprem_provisioner.create_container(
                config=sample_config,
                image_url="nginx:latest",
                provision_id=provision_id,
                index=0,
                environment_vars={},
                runtime="docker",
            )

    def test_create_container_resource_limits(self, sample_config, provision_id):
        """Test that resource limits are calculated correctly."""
        with patch("packages.provisioner.onprem_provisioner._create_docker_container") as mock:
            mock.return_value = ("id", "172.17.0.2", 80)

            container = onprem_provisioner.create_container(
                config=sample_config,
                image_url="nginx:latest",
                provision_id=provision_id,
                index=0,
                environment_vars={},
                runtime="docker",
            )

            # Verify CPU and memory limits
            assert container.cpu_limit == float(sample_config.cpu_cores)
            assert container.memory_limit_mb == sample_config.memory_gb * 1024


class TestDetectContainerRuntime:
    """Tests for _detect_container_runtime function."""

    @patch("packages.provisioner.onprem_provisioner.shutil.which")
    def test_detect_docker_available(self, mock_which):
        """Test detection when only Docker is available."""
        mock_which.side_effect = lambda cmd: "/usr/bin/docker" if cmd == "docker" else None

        runtime = onprem_provisioner._detect_container_runtime()
        assert runtime == "docker"

    @patch("packages.provisioner.onprem_provisioner.shutil.which")
    def test_detect_podman_available(self, mock_which):
        """Test detection when only Podman is available."""
        mock_which.side_effect = lambda cmd: "/usr/bin/podman" if cmd == "podman" else None

        runtime = onprem_provisioner._detect_container_runtime()
        assert runtime == "podman"

    @patch("packages.provisioner.onprem_provisioner.shutil.which")
    def test_detect_both_available_prefer_docker(self, mock_which):
        """Test detection when both are available (default: prefer Docker)."""
        mock_which.return_value = "/usr/bin/something"

        runtime = onprem_provisioner._detect_container_runtime(prefer_podman=False)
        assert runtime == "docker"

    @patch("packages.provisioner.onprem_provisioner.shutil.which")
    def test_detect_both_available_prefer_podman(self, mock_which):
        """Test detection when both are available (prefer Podman)."""
        mock_which.return_value = "/usr/bin/something"

        runtime = onprem_provisioner._detect_container_runtime(prefer_podman=True)
        assert runtime == "podman"

    @patch("packages.provisioner.onprem_provisioner.shutil.which")
    def test_detect_neither_available(self, mock_which):
        """Test detection when neither is available."""
        mock_which.return_value = None

        runtime = onprem_provisioner._detect_container_runtime()
        assert runtime is None


class TestCreateDockerContainer:
    """Tests for _create_docker_container function."""

    @patch("packages.provisioner.onprem_provisioner.DOCKER_AVAILABLE", False)
    def test_create_docker_container_sdk_not_available(self):
        """Test Docker container creation when SDK is not available."""
        with pytest.raises(RuntimeError, match="Docker SDK is not available"):
            onprem_provisioner._create_docker_container(
                name="test",
                image_url="nginx:latest",
                cpu_limit=2.0,
                memory_limit_mb=4096,
                environment_vars={},
            )

    @patch("packages.provisioner.onprem_provisioner.DOCKER_AVAILABLE", True)
    @patch("packages.provisioner.onprem_provisioner.docker")
    def test_create_docker_container_success(self, mock_docker_module):
        """Test successful Docker container creation."""
        # Mock Docker client and container
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "abc123def456"

        mock_docker_module.from_env.return_value = mock_client
        mock_client.containers.run.return_value = mock_container

        # Mock container endpoint
        with patch(
            "packages.provisioner.onprem_provisioner._get_container_endpoint"
        ) as mock_endpoint:
            mock_endpoint.return_value = ("172.17.0.2", 80)

            container_id, endpoint, port = onprem_provisioner._create_docker_container(
                name="test-container",
                image_url="nginx:latest",
                cpu_limit=2.0,
                memory_limit_mb=4096,
                environment_vars={"ENV": "test"},
            )

            # Verify results
            assert container_id == "abc123def456"
            assert endpoint == "172.17.0.2"
            assert port == 80

            # Verify Docker API calls
            mock_client.images.pull.assert_called_once_with("nginx:latest")
            mock_client.containers.run.assert_called_once()

            # Verify resource limits
            call_kwargs = mock_client.containers.run.call_args[1]
            assert call_kwargs["cpu_period"] == 100000
            assert call_kwargs["cpu_quota"] == 200000  # 2.0 * 100000
            assert call_kwargs["mem_limit"] == 4096 * 1024 * 1024
            assert call_kwargs["environment"] == {"ENV": "test"}

    @patch("packages.provisioner.onprem_provisioner.DOCKER_AVAILABLE", True)
    @patch("packages.provisioner.onprem_provisioner.docker")
    def test_create_docker_container_pull_failure(self, mock_docker_module):
        """Test Docker container creation when image pull fails."""
        mock_client = MagicMock()
        mock_docker_module.from_env.return_value = mock_client
        mock_client.images.pull.side_effect = Exception("Image not found")

        with pytest.raises(RuntimeError, match="Docker container creation failed"):
            onprem_provisioner._create_docker_container(
                name="test",
                image_url="invalid:image",
                cpu_limit=1.0,
                memory_limit_mb=2048,
                environment_vars={},
            )

    @patch("packages.provisioner.onprem_provisioner.DOCKER_AVAILABLE", True)
    @patch("packages.provisioner.onprem_provisioner.docker")
    def test_create_docker_container_cpu_limits(self, mock_docker_module):
        """Test Docker CPU limit calculation."""
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "test-id"

        mock_docker_module.from_env.return_value = mock_client
        mock_client.containers.run.return_value = mock_container

        with patch(
            "packages.provisioner.onprem_provisioner._get_container_endpoint"
        ) as mock_endpoint:
            mock_endpoint.return_value = ("172.17.0.2", 80)

            # Test 0.5 CPU
            onprem_provisioner._create_docker_container(
                name="test",
                image_url="nginx:latest",
                cpu_limit=0.5,
                memory_limit_mb=1024,
                environment_vars={},
            )

            call_kwargs = mock_client.containers.run.call_args[1]
            assert call_kwargs["cpu_quota"] == 50000  # 0.5 * 100000


class TestCreatePodmanContainer:
    """Tests for _create_podman_container function."""

    @patch("packages.provisioner.onprem_provisioner.subprocess.run")
    def test_create_podman_container_success(self, mock_run):
        """Test successful Podman container creation."""
        # Mock subprocess calls
        mock_run.side_effect = [
            MagicMock(returncode=0),  # pull
            MagicMock(stdout="container-id-789\n", returncode=0),  # run
            MagicMock(
                stdout=json.dumps(
                    [
                        {
                            "NetworkSettings": {
                                "IPAddress": "10.88.0.2",
                                "Ports": {"8080/tcp": None},
                            }
                        }
                    ]
                ),
                returncode=0,
            ),  # inspect
        ]

        container_id, endpoint, port = onprem_provisioner._create_podman_container(
            name="test-container",
            image_url="nginx:latest",
            cpu_limit=2.0,
            memory_limit_mb=4096,
            environment_vars={"ENV": "test"},
        )

        assert container_id == "container-id-789"
        assert endpoint == "10.88.0.2"
        assert port == 8080

        # Verify subprocess calls
        assert mock_run.call_count == 3

    @patch("packages.provisioner.onprem_provisioner.subprocess.run")
    def test_create_podman_container_pull_failure(self, mock_run):
        """Test Podman container creation when image pull fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["podman", "pull"], stderr="Image not found"
        )

        with pytest.raises(RuntimeError, match="Podman container creation failed"):
            onprem_provisioner._create_podman_container(
                name="test",
                image_url="invalid:image",
                cpu_limit=1.0,
                memory_limit_mb=2048,
                environment_vars={},
            )

    @patch("packages.provisioner.onprem_provisioner.subprocess.run")
    def test_create_podman_container_with_env_vars(self, mock_run):
        """Test Podman container creation with environment variables."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # pull
            MagicMock(stdout="container-id\n", returncode=0),  # run
            MagicMock(
                stdout=json.dumps([{"NetworkSettings": {"IPAddress": "10.88.0.2", "Ports": {}}}]),
                returncode=0,
            ),  # inspect
        ]

        env_vars = {"KEY1": "value1", "KEY2": "value2"}

        onprem_provisioner._create_podman_container(
            name="test",
            image_url="nginx:latest",
            cpu_limit=1.0,
            memory_limit_mb=2048,
            environment_vars=env_vars,
        )

        # Verify environment variables were passed
        run_call = mock_run.call_args_list[1]
        run_cmd = run_call[0][0]
        assert "-e" in run_cmd
        assert "KEY1=value1" in run_cmd
        assert "KEY2=value2" in run_cmd


class TestGetContainerEndpoint:
    """Tests for _get_container_endpoint function."""

    def test_get_container_endpoint_with_ip_and_port(self):
        """Test getting endpoint when container has IP and exposed ports."""
        mock_container = MagicMock()
        mock_container.attrs = {
            "NetworkSettings": {
                "IPAddress": "172.17.0.5",
                "Ports": {"8080/tcp": None, "9090/tcp": None},
            }
        }

        endpoint, port = onprem_provisioner._get_container_endpoint(mock_container)

        assert endpoint == "172.17.0.5"
        assert port == 8080  # First port

    def test_get_container_endpoint_no_ip(self):
        """Test getting endpoint when container has no IP (uses default)."""
        mock_container = MagicMock()
        mock_container.attrs = {"NetworkSettings": {"Ports": {"80/tcp": None}}}

        endpoint, port = onprem_provisioner._get_container_endpoint(mock_container)

        assert endpoint == "127.0.0.1"  # Default
        assert port == 80

    def test_get_container_endpoint_no_ports(self):
        """Test getting endpoint when container has no exposed ports."""
        mock_container = MagicMock()
        mock_container.attrs = {"NetworkSettings": {"IPAddress": "172.17.0.3", "Ports": {}}}

        endpoint, port = onprem_provisioner._get_container_endpoint(mock_container)

        assert endpoint == "172.17.0.3"
        assert port == 80  # Default


class TestContainerDetails:
    """Tests for ContainerDetails dataclass."""

    def test_container_details_creation(self):
        """Test creating a ContainerDetails instance."""
        container = onprem_provisioner.ContainerDetails(
            container_id="abc123",
            name="test-container",
            image_url="nginx:latest",
            cpu_limit=2.0,
            memory_limit_mb=4096,
            endpoint="172.17.0.2",
            port=80,
            status="running",
            environment_vars={"ENV": "test"},
        )

        assert container.container_id == "abc123"
        assert container.name == "test-container"
        assert container.image_url == "nginx:latest"
        assert container.cpu_limit == 2.0
        assert container.memory_limit_mb == 4096
        assert container.endpoint == "172.17.0.2"
        assert container.port == 80
        assert container.status == "running"
        assert container.environment_vars == {"ENV": "test"}


class TestCaaSIntegration:
    """Integration tests for CaaS provisioning."""

    @patch("packages.provisioner.onprem_provisioner._detect_container_runtime")
    @patch("packages.provisioner.onprem_provisioner._create_docker_container")
    def test_end_to_end_caas_provisioning(
        self, mock_create_docker, mock_detect_runtime, sample_config, provision_id, db_session
    ):
        """Test complete CaaS provisioning workflow."""
        mock_detect_runtime.return_value = "docker"
        mock_create_docker.side_effect = [
            ("container-1", "172.17.0.2", 80),
            ("container-2", "172.17.0.3", 80),
        ]

        # Provision containers
        containers = onprem_provisioner.provision_caas(
            config=sample_config,
            image_url="nginx:latest",
            provision_id=provision_id,
            db_session=db_session,
            environment_vars={"ENV": "production"},
        )

        # Verify containers were created
        assert len(containers) == sample_config.instance_count

        # Verify database records
        resources = (
            db_session.query(models.ResourceModel).filter_by(provision_id=provision_id).all()
        )
        assert len(resources) == sample_config.instance_count

        # Verify connection details are retrievable
        for resource in resources:
            conn_info = json.loads(resource.connection_info_json)
            assert conn_info["endpoint"]
            assert conn_info["port"]
            assert conn_info["container_id"]
            assert conn_info["image_url"] == "nginx:latest"


class TestConfigureNetworking:
    """Tests for configure_networking function."""

    def test_configure_networking_mock_mode_default(self, provision_id, db_session):
        """Test that configure_networking defaults to mock mode."""
        network_config = onprem_provisioner.configure_networking(
            provision_id=provision_id,
            db_session=db_session,
        )

        # Verify network configuration
        assert network_config.network_id
        assert network_config.network_name.startswith("mock-network-")
        assert network_config.subnet == "10.0.0.0/24"
        assert network_config.gateway == "10.0.0.1"
        assert network_config.dns_servers == ["8.8.8.8", "8.8.4.4"]
        assert network_config.status == "active"

        # Verify database tracking
        resources = db_session.query(models.ResourceModel).filter_by(resource_type="network").all()
        assert len(resources) == 1

        resource = resources[0]
        assert resource.provision_id == provision_id
        assert resource.resource_type == "network"
        assert resource.status == "active"

        # Verify connection info
        conn_info = json.loads(resource.connection_info_json)
        assert conn_info["network_id"] == network_config.network_id
        assert conn_info["network_name"] == network_config.network_name
        assert conn_info["subnet"] == "10.0.0.0/24"
        assert conn_info["gateway"] == "10.0.0.1"
        assert conn_info["dns_servers"] == "8.8.8.8,8.8.4.4"

    def test_configure_networking_custom_subnet(self, provision_id, db_session):
        """Test configure_networking with custom subnet."""
        network_config = onprem_provisioner.configure_networking(
            provision_id=provision_id,
            db_session=db_session,
            subnet="192.168.1.0/24",
        )

        # Verify network configuration with custom subnet
        assert network_config.subnet == "192.168.1.0/24"
        assert network_config.gateway == "192.168.1.1"
        assert network_config.status == "active"

    def test_configure_networking_libvirt_unavailable(self, provision_id, db_session):
        """Test that configure_networking raises error when libvirt is requested but unavailable."""
        # Only test if libvirt is not available
        if not onprem_provisioner.LIBVIRT_AVAILABLE:
            with pytest.raises(RuntimeError, match="libvirt-python"):
                onprem_provisioner.configure_networking(
                    provision_id=provision_id,
                    db_session=db_session,
                    use_libvirt=True,
                )

    @patch("packages.provisioner.onprem_provisioner.libvirt")
    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", True)
    def test_configure_networking_with_libvirt(self, mock_libvirt, provision_id, db_session):
        """Test configure_networking with libvirt mode (mocked)."""
        # Mock libvirt connection and network
        mock_conn = MagicMock()
        mock_network = MagicMock()
        mock_network.UUIDString.return_value = "test-network-uuid"
        mock_network.create.return_value = 0

        mock_conn.networkDefineXML.return_value = mock_network
        mock_libvirt.open.return_value = mock_conn

        network_config = onprem_provisioner.configure_networking(
            provision_id=provision_id,
            db_session=db_session,
            subnet="10.0.0.0/24",
            use_libvirt=True,
        )

        # Verify libvirt was called
        mock_libvirt.open.assert_called_once_with("qemu:///system")
        mock_conn.networkDefineXML.assert_called_once()
        mock_network.create.assert_called_once()

        # Verify network configuration
        assert network_config.network_id == "test-network-uuid"
        assert network_config.network_name.startswith("hybrid-cloud-net-")
        assert network_config.subnet == "10.0.0.0/24"
        assert network_config.gateway == "10.0.0.1"
        assert network_config.status == "active"

        # Verify database tracking
        resources = db_session.query(models.ResourceModel).filter_by(resource_type="network").all()
        assert len(resources) == 1


class TestCreateMockNetwork:
    """Tests for _create_mock_network function."""

    def test_create_mock_network_default_subnet(self, provision_id):
        """Test creating a mock network with default subnet."""
        network_config = onprem_provisioner._create_mock_network(
            provision_id=provision_id,
            subnet="10.0.0.0/24",
        )

        assert network_config.network_id
        assert network_config.network_name.startswith("mock-network-")
        assert network_config.subnet == "10.0.0.0/24"
        assert network_config.gateway == "10.0.0.1"
        assert network_config.dns_servers == ["8.8.8.8", "8.8.4.4"]
        assert network_config.status == "active"

    def test_create_mock_network_custom_subnet(self, provision_id):
        """Test creating a mock network with custom subnet."""
        network_config = onprem_provisioner._create_mock_network(
            provision_id=provision_id,
            subnet="192.168.100.0/24",
        )

        assert network_config.subnet == "192.168.100.0/24"
        assert network_config.gateway == "192.168.100.1"

    def test_create_mock_network_different_class_c(self, provision_id):
        """Test creating a mock network with different Class C subnet."""
        network_config = onprem_provisioner._create_mock_network(
            provision_id=provision_id,
            subnet="172.16.50.0/24",
        )

        assert network_config.subnet == "172.16.50.0/24"
        assert network_config.gateway == "172.16.50.1"


class TestCreateLibvirtNetwork:
    """Tests for _create_libvirt_network function."""

    @patch("packages.provisioner.onprem_provisioner.libvirt")
    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", True)
    def test_create_libvirt_network_success(self, mock_libvirt, provision_id):
        """Test successful libvirt network creation."""
        # Mock libvirt connection and network
        mock_conn = MagicMock()
        mock_network = MagicMock()
        mock_network.UUIDString.return_value = "test-uuid-1234"
        mock_network.create.return_value = 0

        mock_conn.networkDefineXML.return_value = mock_network
        mock_libvirt.open.return_value = mock_conn

        network_config = onprem_provisioner._create_libvirt_network(
            provision_id=provision_id,
            subnet="10.0.0.0/24",
        )

        # Verify libvirt calls
        mock_libvirt.open.assert_called_once_with("qemu:///system")
        mock_conn.networkDefineXML.assert_called_once()
        mock_network.create.assert_called_once()
        mock_conn.close.assert_called_once()

        # Verify network configuration
        assert network_config.network_id == "test-uuid-1234"
        assert network_config.network_name.startswith("hybrid-cloud-net-")
        assert network_config.subnet == "10.0.0.0/24"
        assert network_config.gateway == "10.0.0.1"
        assert network_config.dns_servers == ["8.8.8.8", "8.8.4.4"]
        assert network_config.status == "active"

    @patch("packages.provisioner.onprem_provisioner.libvirt")
    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", True)
    def test_create_libvirt_network_connection_failure(self, mock_libvirt, provision_id):
        """Test libvirt network creation with connection failure."""
        mock_libvirt.open.return_value = None

        with pytest.raises(RuntimeError, match="Failed to connect to libvirt"):
            onprem_provisioner._create_libvirt_network(
                provision_id=provision_id,
                subnet="10.0.0.0/24",
            )

    @patch("packages.provisioner.onprem_provisioner.libvirt")
    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", True)
    def test_create_libvirt_network_define_failure(self, mock_libvirt, provision_id):
        """Test libvirt network creation with define failure."""
        mock_conn = MagicMock()
        mock_conn.networkDefineXML.return_value = None
        mock_libvirt.open.return_value = mock_conn

        with pytest.raises(RuntimeError, match="Failed to define network"):
            onprem_provisioner._create_libvirt_network(
                provision_id=provision_id,
                subnet="10.0.0.0/24",
            )

    @patch("packages.provisioner.onprem_provisioner.libvirt")
    @patch("packages.provisioner.onprem_provisioner.LIBVIRT_AVAILABLE", True)
    def test_create_libvirt_network_start_failure(self, mock_libvirt, provision_id):
        """Test libvirt network creation with start failure."""
        mock_conn = MagicMock()
        mock_network = MagicMock()
        mock_network.create.return_value = -1

        mock_conn.networkDefineXML.return_value = mock_network
        mock_libvirt.open.return_value = mock_conn

        with pytest.raises(RuntimeError, match="Failed to start network"):
            onprem_provisioner._create_libvirt_network(
                provision_id=provision_id,
                subnet="10.0.0.0/24",
            )

    def test_create_libvirt_network_unavailable(self, provision_id):
        """Test that _create_libvirt_network raises error when libvirt is unavailable."""
        # Only test if libvirt is not available
        if not onprem_provisioner.LIBVIRT_AVAILABLE:
            with pytest.raises(RuntimeError, match="libvirt-python is not available"):
                onprem_provisioner._create_libvirt_network(
                    provision_id=provision_id,
                    subnet="10.0.0.0/24",
                )


class TestGenerateNetworkXML:
    """Tests for _generate_network_xml helper function."""

    def test_generate_network_xml_default_subnet(self):
        """Test generating network XML with default subnet."""
        xml = onprem_provisioner._generate_network_xml(
            name="test-network",
            subnet="10.0.0.0/24",
            gateway="10.0.0.1",
            dns_servers=["8.8.8.8", "8.8.4.4"],
        )

        # Verify XML contains expected elements
        assert "<name>test-network</name>" in xml
        assert "<forward mode='nat'>" in xml
        assert "address='10.0.0.1'" in xml
        assert "netmask='255.255.255.0'" in xml
        assert "start='10.0.0.10'" in xml
        assert "end='10.0.0.254'" in xml
        assert '<forwarder addr="8.8.8.8"/>' in xml
        assert '<forwarder addr="8.8.4.4"/>' in xml

    def test_generate_network_xml_custom_subnet(self):
        """Test generating network XML with custom subnet."""
        xml = onprem_provisioner._generate_network_xml(
            name="custom-network",
            subnet="192.168.1.0/24",
            gateway="192.168.1.1",
            dns_servers=["1.1.1.1"],
        )

        # Verify XML contains custom subnet elements
        assert "<name>custom-network</name>" in xml
        assert "address='192.168.1.1'" in xml
        assert "netmask='255.255.255.0'" in xml
        assert "start='192.168.1.10'" in xml
        assert "end='192.168.1.254'" in xml
        assert '<forwarder addr="1.1.1.1"/>' in xml

    def test_generate_network_xml_different_prefix(self):
        """Test generating network XML with different prefix length."""
        xml = onprem_provisioner._generate_network_xml(
            name="test-network",
            subnet="172.16.0.0/16",
            gateway="172.16.0.1",
            dns_servers=["8.8.8.8"],
        )

        # Verify XML contains correct netmask for /16
        assert "netmask='255.255.0.0'" in xml
        assert "address='172.16.0.1'" in xml


class TestNetworkConfig:
    """Tests for NetworkConfig dataclass."""

    def test_network_config_creation(self):
        """Test creating a NetworkConfig instance."""
        network_config = onprem_provisioner.NetworkConfig(
            network_id="test-id",
            network_name="test-network",
            subnet="10.0.0.0/24",
            gateway="10.0.0.1",
            dns_servers=["8.8.8.8", "8.8.4.4"],
            status="active",
        )

        assert network_config.network_id == "test-id"
        assert network_config.network_name == "test-network"
        assert network_config.subnet == "10.0.0.0/24"
        assert network_config.gateway == "10.0.0.1"
        assert network_config.dns_servers == ["8.8.8.8", "8.8.4.4"]
        assert network_config.status == "active"

    def test_network_config_with_custom_dns(self):
        """Test NetworkConfig with custom DNS servers."""
        network_config = onprem_provisioner.NetworkConfig(
            network_id="test-id",
            network_name="test-network",
            subnet="192.168.1.0/24",
            gateway="192.168.1.1",
            dns_servers=["1.1.1.1", "1.0.0.1"],
            status="active",
        )

        assert network_config.dns_servers == ["1.1.1.1", "1.0.0.1"]


class TestNetworkingIntegration:
    """Integration tests for networking configuration."""

    def test_end_to_end_network_provisioning(self, provision_id, db_session):
        """Test complete network provisioning workflow in mock mode."""
        # Configure network
        network_config = onprem_provisioner.configure_networking(
            provision_id=provision_id,
            db_session=db_session,
            subnet="10.0.0.0/24",
        )

        # Verify network was created
        assert network_config.network_id
        assert network_config.status == "active"

        # Verify database record
        resources = (
            db_session.query(models.ResourceModel)
            .filter_by(provision_id=provision_id, resource_type="network")
            .all()
        )
        assert len(resources) == 1

        # Verify connection details are retrievable
        resource = resources[0]
        conn_info = json.loads(resource.connection_info_json)
        assert conn_info["network_id"] == network_config.network_id
        assert conn_info["subnet"] == "10.0.0.0/24"
        assert conn_info["gateway"] == "10.0.0.1"
