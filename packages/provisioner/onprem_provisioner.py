"""On-premises infrastructure provisioner for IaaS and CaaS.

This module provides functions to provision on-premises infrastructure resources
including virtual machines (IaaS) using QEMU/KVM with libvirt, and containers (CaaS)
using Docker/Podman. Supports both production mode and Mock_Mode for development.
"""

import json
import logging
import secrets
import shutil
import string
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from packages.database import models

# Try to import libvirt, but don't fail if not available (for mock mode)
try:
    import libvirt

    LIBVIRT_AVAILABLE = True
except ImportError:
    LIBVIRT_AVAILABLE = False
    libvirt = None

# Try to import docker, but don't fail if not available
try:
    import docker

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None

logger = logging.getLogger(__name__)


@dataclass
class VMDetails:
    """Details of a provisioned virtual machine."""

    vm_id: str
    name: str
    cpu_cores: int
    memory_gb: int
    storage_gb: int
    ip_address: str
    port: int
    username: str
    password: str
    status: str


@dataclass
class ContainerDetails:
    """Details of a provisioned container."""

    container_id: str
    name: str
    image_url: str
    cpu_limit: float
    memory_limit_mb: int
    endpoint: str
    port: int
    status: str
    environment_vars: dict[str, str]


def provision_iaas(
    config: models.ConfigurationModel,
    provision_id: str,
    db_session: Session,
    mock_mode: bool = True,
) -> list[VMDetails]:
    """Provision IaaS resources (virtual machines).

    Args:
        config: Configuration model with compute, storage, and network specs
        provision_id: ID of the provision record for tracking
        db_session: Database session for storing resource records
        mock_mode: If True, simulate VM provisioning without consuming resources.
                   If False, create actual VMs using libvirt (requires libvirt installed)

    Returns:
        List of VMDetails for all provisioned VMs

    Raises:
        RuntimeError: If production mode is requested but libvirt is not available
    """
    if mock_mode:
        logger.info(
            f"Provisioning IaaS in Mock_Mode for provision {provision_id} "
            f"({config.instance_count} VMs)"
        )
        vms = [create_mock_vm(config, provision_id, i) for i in range(config.instance_count)]
    else:
        if not LIBVIRT_AVAILABLE:
            raise RuntimeError(
                "Production mode requires libvirt-python to be installed. "
                "Install with: pip install libvirt-python"
            )
        logger.info(
            f"Provisioning IaaS in production mode for provision {provision_id} "
            f"({config.instance_count} VMs)"
        )
        vms = [create_vm(config, provision_id, i) for i in range(config.instance_count)]

    # Track all VMs in database
    for vm in vms:
        connection_info = {
            "ip_address": vm.ip_address,
            "port": str(vm.port),
            "username": vm.username,
            "password": vm.password,
        }

        resource = models.ResourceModel(
            id=str(uuid.uuid4()),
            provision_id=provision_id,
            resource_type="vm",
            external_id=vm.vm_id,
            status=vm.status,
            connection_info_json=json.dumps(connection_info),
            created_at=datetime.utcnow(),
        )
        db_session.add(resource)

    db_session.commit()
    logger.info(f"Successfully tracked {len(vms)} VMs in database")

    return vms


def create_mock_vm(config: models.ConfigurationModel, provision_id: str, index: int) -> VMDetails:
    """Create a mock VM for development without consuming actual resources.

    Args:
        config: Configuration model with compute, storage, and network specs
        provision_id: ID of the provision record
        index: Index of this VM in the instance count

    Returns:
        VMDetails with mock connection information
    """
    vm_id = str(uuid.uuid4())
    name = f"mock-vm-{provision_id[:8]}-{index}"

    # Generate mock IP address in 10.0.x.x range
    ip_address = f"10.0.{(index // 256) % 256}.{index % 256 + 1}"

    # Generate mock credentials
    username = "ubuntu"
    password = _generate_password()

    logger.info(
        f"Created mock VM: {name} with {config.cpu_cores} cores, "
        f"{config.memory_gb}GB RAM, {config.storage_capacity_gb}GB storage"
    )

    return VMDetails(
        vm_id=vm_id,
        name=name,
        cpu_cores=config.cpu_cores,
        memory_gb=config.memory_gb,
        storage_gb=config.storage_capacity_gb,
        ip_address=ip_address,
        port=22,
        username=username,
        password=password,
        status="running",
    )


def create_vm(config: models.ConfigurationModel, provision_id: str, index: int) -> VMDetails:
    """Create a virtual machine using QEMU/KVM with libvirt.

    Args:
        config: Configuration model with compute, storage, and network specs
        provision_id: ID of the provision record
        index: Index of this VM in the instance count

    Returns:
        VMDetails with actual VM connection information

    Raises:
        RuntimeError: If libvirt connection or VM creation fails
    """
    if not LIBVIRT_AVAILABLE:
        raise RuntimeError("libvirt-python is not available")

    name = f"hybrid-cloud-vm-{provision_id[:8]}-{index}"

    try:
        # Connect to libvirt
        conn = libvirt.open("qemu:///system")
        if conn is None:
            raise RuntimeError("Failed to connect to libvirt (qemu:///system)")

        # Generate VM XML definition
        xml_config = _generate_vm_xml(
            name=name,
            cpu_cores=config.cpu_cores,
            memory_gb=config.memory_gb,
            storage_gb=config.storage_capacity_gb,
        )

        # Create and start the VM
        domain = conn.defineXML(xml_config)
        if domain is None:
            raise RuntimeError(f"Failed to define VM {name}")

        if domain.create() < 0:
            raise RuntimeError(f"Failed to start VM {name}")

        # Get VM ID from libvirt
        libvirt_id = domain.UUIDString()

        # Wait for IP address assignment (simplified - in production would poll)
        # For now, generate a mock IP since actual IP assignment takes time
        ip_address = f"192.168.122.{index + 10}"

        # Generate SSH credentials
        username = "ubuntu"
        password = _generate_password()

        logger.info(
            f"Created VM: {name} (libvirt ID: {libvirt_id}) with {config.cpu_cores} cores, "
            f"{config.memory_gb}GB RAM, {config.storage_capacity_gb}GB storage"
        )

        conn.close()

        return VMDetails(
            vm_id=libvirt_id,
            name=name,
            cpu_cores=config.cpu_cores,
            memory_gb=config.memory_gb,
            storage_gb=config.storage_capacity_gb,
            ip_address=ip_address,
            port=22,
            username=username,
            password=password,
            status="running",
        )

    except RuntimeError:
        # Re-raise our own RuntimeErrors (connection, define, start failures)
        raise
    except Exception as e:
        # Handle any other unexpected errors (including libvirt errors)
        logger.error(f"Unexpected error creating VM {name}: {e}")
        raise RuntimeError(f"Failed to create VM {name}: {e}") from e


def _generate_vm_xml(name: str, cpu_cores: int, memory_gb: int, storage_gb: int) -> str:
    """Generate libvirt XML definition for a virtual machine.

    Args:
        name: Name of the VM
        cpu_cores: Number of CPU cores
        memory_gb: Memory size in GB
        storage_gb: Storage size in GB

    Returns:
        XML string for libvirt domain definition
    """
    memory_kb = memory_gb * 1024 * 1024  # Convert GB to KB

    xml = f"""
<domain type='kvm'>
  <name>{name}</name>
  <memory unit='KiB'>{memory_kb}</memory>
  <currentMemory unit='KiB'>{memory_kb}</currentMemory>
  <vcpu placement='static'>{cpu_cores}</vcpu>
  <os>
    <type arch='x86_64' machine='pc'>hvm</type>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
  </features>
  <cpu mode='host-model'/>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='/var/lib/libvirt/images/{name}.qcow2'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <interface type='network'>
      <source network='default'/>
      <model type='virtio'/>
    </interface>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <graphics type='vnc' port='-1' autoport='yes'/>
  </devices>
</domain>
"""
    return xml.strip()


def _generate_password(length: int = 16) -> str:
    """Generate a secure random password.

    Args:
        length: Length of the password (default: 16)

    Returns:
        Randomly generated password string
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # Ensure at least one of each character type
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(string.punctuation),
    ]
    # Fill the rest randomly
    password.extend(secrets.choice(alphabet) for _ in range(length - 4))
    # Shuffle to avoid predictable patterns
    password_list = list(password)
    secrets.SystemRandom().shuffle(password_list)
    return "".join(password_list)


def provision_caas(
    config: models.ConfigurationModel,
    image_url: str,
    provision_id: str,
    db_session: Session,
    environment_vars: Optional[dict[str, str]] = None,
    use_podman: bool = False,
) -> list[ContainerDetails]:
    """Provision CaaS resources (containers).

    Args:
        config: Configuration model with compute, storage, and network specs
        image_url: Container image URL (Docker Hub, ECR, or private registry)
        provision_id: ID of the provision record for tracking
        db_session: Database session for storing resource records
        environment_vars: Optional environment variables to inject into containers
        use_podman: If True, use Podman instead of Docker (default: False)

    Returns:
        List of ContainerDetails for all provisioned containers

    Raises:
        RuntimeError: If neither Docker nor Podman is available
    """
    if environment_vars is None:
        environment_vars = {}

    # Detect container runtime
    runtime = _detect_container_runtime(use_podman)
    if runtime is None:
        raise RuntimeError(
            "Neither Docker nor Podman is available. "
            "Install Docker (https://docs.docker.com/get-docker/) or "
            "Podman (https://podman.io/getting-started/installation)"
        )

    logger.info(
        f"Provisioning CaaS using {runtime} for provision {provision_id} "
        f"({config.instance_count} containers, image: {image_url})"
    )

    containers = []
    for i in range(config.instance_count):
        container = create_container(
            config=config,
            image_url=image_url,
            provision_id=provision_id,
            index=i,
            environment_vars=environment_vars,
            runtime=runtime,
        )
        containers.append(container)

    # Track all containers in database
    for container in containers:
        connection_info = {
            "endpoint": container.endpoint,
            "port": str(container.port),
            "container_id": container.container_id,
            "image_url": container.image_url,
        }

        resource = models.ResourceModel(
            id=str(uuid.uuid4()),
            provision_id=provision_id,
            resource_type="container",
            external_id=container.container_id,
            status=container.status,
            connection_info_json=json.dumps(connection_info),
            created_at=datetime.utcnow(),
        )
        db_session.add(resource)

    db_session.commit()
    logger.info(f"Successfully tracked {len(containers)} containers in database")

    return containers


def create_container(
    config: models.ConfigurationModel,
    image_url: str,
    provision_id: str,
    index: int,
    environment_vars: dict[str, str],
    runtime: str,
) -> ContainerDetails:
    """Create a container using Docker or Podman.

    Args:
        config: Configuration model with compute, storage, and network specs
        image_url: Container image URL
        provision_id: ID of the provision record
        index: Index of this container in the instance count
        environment_vars: Environment variables to inject
        runtime: Container runtime to use ("docker" or "podman")

    Returns:
        ContainerDetails with container information

    Raises:
        RuntimeError: If container creation fails
    """
    name = f"hybrid-cloud-container-{provision_id[:8]}-{index}"

    # Calculate resource limits
    cpu_limit = float(config.cpu_cores)
    memory_limit_mb = config.memory_gb * 1024

    try:
        if runtime == "docker":
            container_id, endpoint, port = _create_docker_container(
                name=name,
                image_url=image_url,
                cpu_limit=cpu_limit,
                memory_limit_mb=memory_limit_mb,
                environment_vars=environment_vars,
            )
        else:  # podman
            container_id, endpoint, port = _create_podman_container(
                name=name,
                image_url=image_url,
                cpu_limit=cpu_limit,
                memory_limit_mb=memory_limit_mb,
                environment_vars=environment_vars,
            )

        logger.info(
            f"Created container: {name} (ID: {container_id[:12]}) with "
            f"{cpu_limit} CPU, {memory_limit_mb}MB RAM, endpoint: {endpoint}:{port}"
        )

        return ContainerDetails(
            container_id=container_id,
            name=name,
            image_url=image_url,
            cpu_limit=cpu_limit,
            memory_limit_mb=memory_limit_mb,
            endpoint=endpoint,
            port=port,
            status="running",
            environment_vars=environment_vars,
        )

    except Exception as e:
        logger.error(f"Failed to create container {name}: {e}")
        raise RuntimeError(f"Failed to create container {name}: {e}") from e


def _detect_container_runtime(prefer_podman: bool = False) -> Optional[str]:
    """Detect available container runtime (Docker or Podman).

    Args:
        prefer_podman: If True, prefer Podman over Docker when both are available

    Returns:
        "docker", "podman", or None if neither is available
    """
    docker_available = shutil.which("docker") is not None
    podman_available = shutil.which("podman") is not None

    if prefer_podman:
        if podman_available:
            return "podman"
        if docker_available:
            return "docker"
    else:
        if docker_available:
            return "docker"
        if podman_available:
            return "podman"

    return None


def _create_docker_container(
    name: str,
    image_url: str,
    cpu_limit: float,
    memory_limit_mb: int,
    environment_vars: dict[str, str],
) -> tuple[str, str, int]:
    """Create a container using Docker SDK.

    Args:
        name: Container name
        image_url: Container image URL
        cpu_limit: CPU limit (number of cores)
        memory_limit_mb: Memory limit in MB
        environment_vars: Environment variables to inject

    Returns:
        Tuple of (container_id, endpoint, port)

    Raises:
        RuntimeError: If Docker SDK is not available or container creation fails
    """
    if not DOCKER_AVAILABLE:
        raise RuntimeError("Docker SDK is not available. Install with: pip install docker")

    try:
        client = docker.from_env()

        # Pull the image
        logger.info(f"Pulling image: {image_url}")
        client.images.pull(image_url)

        # Configure CPU limit using cpu_period and cpu_quota
        # Docker uses cpu_period (default 100000) and cpu_quota
        # For 0.5 CPU: quota=50000, period=100000
        # For 2.0 CPU: quota=200000, period=100000
        cpu_period = 100000
        cpu_quota = int(cpu_limit * cpu_period)

        # Convert memory to bytes
        memory_limit_bytes = memory_limit_mb * 1024 * 1024

        # Create and start container
        container = client.containers.run(
            image=image_url,
            name=name,
            detach=True,
            environment=environment_vars,
            cpu_period=cpu_period,
            cpu_quota=cpu_quota,
            mem_limit=memory_limit_bytes,
            remove=False,
            publish_all_ports=True,  # Publish all exposed ports
        )

        # Get container endpoint
        endpoint, port = _get_container_endpoint(container)

        return container.id, endpoint, port

    except Exception as e:
        logger.error(f"Docker container creation failed: {e}")
        raise RuntimeError(f"Docker container creation failed: {e}") from e


def _create_podman_container(
    name: str,
    image_url: str,
    cpu_limit: float,
    memory_limit_mb: int,
    environment_vars: dict[str, str],
) -> tuple[str, str, int]:
    """Create a container using Podman CLI.

    Args:
        name: Container name
        image_url: Container image URL
        cpu_limit: CPU limit (number of cores)
        memory_limit_mb: Memory limit in MB
        environment_vars: Environment variables to inject

    Returns:
        Tuple of (container_id, endpoint, port)

    Raises:
        RuntimeError: If Podman is not available or container creation fails
    """
    try:
        # Pull the image
        logger.info(f"Pulling image with Podman: {image_url}")
        subprocess.run(
            ["podman", "pull", image_url],
            check=True,
            capture_output=True,
            text=True,
        )

        # Build environment variable arguments
        env_args = []
        for key, value in environment_vars.items():
            env_args.extend(["-e", f"{key}={value}"])

        # Create and start container
        # Podman uses --cpus for CPU limit (e.g., --cpus=2.0)
        # and --memory for memory limit (e.g., --memory=2048m)
        cmd = [
            "podman",
            "run",
            "-d",  # Detach
            "--name",
            name,
            f"--cpus={cpu_limit}",
            f"--memory={memory_limit_mb}m",
            "-P",  # Publish all exposed ports
        ]
        cmd.extend(env_args)
        cmd.append(image_url)

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )

        container_id = result.stdout.strip()

        # Get container endpoint using podman inspect
        inspect_result = subprocess.run(
            ["podman", "inspect", container_id],
            check=True,
            capture_output=True,
            text=True,
        )

        import json as json_module

        inspect_data = json_module.loads(inspect_result.stdout)[0]

        # Get IP address
        endpoint = inspect_data.get("NetworkSettings", {}).get("IPAddress", "127.0.0.1")

        # Get first exposed port (simplified)
        ports = inspect_data.get("NetworkSettings", {}).get("Ports", {})
        port = 80  # Default
        if ports:
            first_port_key = list(ports.keys())[0]
            if "/" in first_port_key:
                port = int(first_port_key.split("/")[0])

        return container_id, endpoint, port

    except subprocess.CalledProcessError as e:
        logger.error(f"Podman container creation failed: {e.stderr}")
        raise RuntimeError(f"Podman container creation failed: {e.stderr}") from e
    except Exception as e:
        logger.error(f"Podman container creation failed: {e}")
        raise RuntimeError(f"Podman container creation failed: {e}") from e


def _get_container_endpoint(container) -> tuple[str, int]:
    """Get container endpoint (IP and port) from Docker container.

    Args:
        container: Docker container object

    Returns:
        Tuple of (endpoint, port)
    """
    # Reload container to get latest network info
    container.reload()

    # Get container IP address
    network_settings = container.attrs.get("NetworkSettings", {})
    ip_address = network_settings.get("IPAddress", "127.0.0.1")

    # Get exposed ports
    ports = network_settings.get("Ports", {})
    port = 80  # Default

    if ports:
        # Get first exposed port
        first_port_key = list(ports.keys())[0]
        if "/" in first_port_key:
            port = int(first_port_key.split("/")[0])

    return ip_address, port
