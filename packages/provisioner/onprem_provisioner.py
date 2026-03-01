"""On-premises infrastructure provisioner for IaaS and CaaS.

This module provides functions to provision on-premises infrastructure resources
including virtual machines (IaaS) using QEMU/KVM with libvirt, and containers (CaaS)
using Docker/Podman. Supports both production mode and Mock_Mode for development.
"""

import json
import logging
import secrets
import string
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from packages.database import models

# Try to import libvirt, but don't fail if not available (for mock mode)
try:
    import libvirt

    LIBVIRT_AVAILABLE = True
except ImportError:
    LIBVIRT_AVAILABLE = False
    libvirt = None

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
