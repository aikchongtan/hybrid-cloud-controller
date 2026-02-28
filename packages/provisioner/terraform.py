"""Terraform orchestrator for infrastructure provisioning.

This module provides functions to generate, apply, and destroy Terraform
configurations for AWS (via LocalStack) and on-premises cloud paths.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from python_terraform import Terraform
from sqlalchemy.orm import Session

from packages.database import models


class CloudPath(Enum):
    """Cloud path options for provisioning."""

    AWS = "aws"
    ON_PREM_IAAS = "on_prem_iaas"
    ON_PREM_CAAS = "on_prem_caas"


@dataclass
class TerraformFiles:
    """Container for generated Terraform configuration files."""

    main_tf: str
    variables_tf: str
    outputs_tf: str
    provider_tf: str


@dataclass
class TerraformResult:
    """Result of Terraform operation."""

    success: bool
    output: dict[str, str]
    error: Optional[str] = None
    state_file: Optional[str] = None


def generate_terraform(
    config: models.ConfigurationModel, cloud_path: CloudPath
) -> TerraformFiles:
    """Generate Terraform configuration files for the specified cloud path.

    Args:
        config: Configuration model with compute, storage, and network specs
        cloud_path: Target cloud path (AWS, on-prem IaaS, or on-prem CaaS)

    Returns:
        TerraformFiles containing generated .tf file contents
    """
    if cloud_path == CloudPath.AWS:
        return _generate_aws_terraform(config)
    elif cloud_path == CloudPath.ON_PREM_IAAS:
        return _generate_onprem_iaas_terraform(config)
    elif cloud_path == CloudPath.ON_PREM_CAAS:
        return _generate_onprem_caas_terraform(config)
    else:
        raise ValueError(f"Unsupported cloud path: {cloud_path}")


def _generate_aws_terraform(config: models.ConfigurationModel) -> TerraformFiles:
    """Generate Terraform configuration for AWS via LocalStack."""
    # Provider configuration for LocalStack
    provider_tf = """
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    ec2 = var.localstack_endpoint
    ebs = var.localstack_endpoint
    s3  = var.localstack_endpoint
  }
}
"""

    # Variables
    variables_tf = f"""
variable "aws_region" {{
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}}

variable "localstack_endpoint" {{
  description = "LocalStack endpoint URL"
  type        = string
  default     = "http://localhost:4566"
}}

variable "instance_count" {{
  description = "Number of EC2 instances"
  type        = number
  default     = {config.instance_count}
}}

variable "cpu_cores" {{
  description = "Number of CPU cores"
  type        = number
  default     = {config.cpu_cores}
}}

variable "memory_gb" {{
  description = "Memory in GB"
  type        = number
  default     = {config.memory_gb}
}}

variable "storage_capacity_gb" {{
  description = "Storage capacity in GB"
  type        = number
  default     = {config.storage_capacity_gb}
}}
"""

    # Main resources
    main_tf = """
# EC2 instances
resource "aws_instance" "app_server" {
  count         = var.instance_count
  ami           = "ami-0c55b159cbfafe1f0"  # Placeholder AMI for LocalStack
  instance_type = "t2.micro"

  tags = {
    Name = "hybrid-cloud-app-${count.index}"
  }
}

# EBS volumes
resource "aws_ebs_volume" "app_storage" {
  count             = var.instance_count
  availability_zone = "us-east-1a"
  size              = var.storage_capacity_gb

  tags = {
    Name = "hybrid-cloud-storage-${count.index}"
  }
}

# Attach EBS volumes to instances
resource "aws_volume_attachment" "app_storage_attachment" {
  count       = var.instance_count
  device_name = "/dev/sdh"
  volume_id   = aws_ebs_volume.app_storage[count.index].id
  instance_id = aws_instance.app_server[count.index].id
}
"""

    # Outputs
    outputs_tf = """
output "instance_ids" {
  description = "IDs of created EC2 instances"
  value       = aws_instance.app_server[*].id
}

output "instance_public_ips" {
  description = "Public IPs of EC2 instances"
  value       = aws_instance.app_server[*].public_ip
}

output "volume_ids" {
  description = "IDs of created EBS volumes"
  value       = aws_ebs_volume.app_storage[*].id
}
"""

    return TerraformFiles(
        main_tf=main_tf,
        variables_tf=variables_tf,
        outputs_tf=outputs_tf,
        provider_tf=provider_tf,
    )


def _generate_onprem_iaas_terraform(config: models.ConfigurationModel) -> TerraformFiles:
    """Generate Terraform configuration for on-premises IaaS (libvirt)."""
    # Provider configuration for libvirt
    provider_tf = """
terraform {
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "~> 0.7"
    }
  }
}

provider "libvirt" {
  uri = var.libvirt_uri
}
"""

    # Variables
    variables_tf = f"""
variable "libvirt_uri" {{
  description = "Libvirt connection URI"
  type        = string
  default     = "qemu:///system"
}}

variable "instance_count" {{
  description = "Number of VMs"
  type        = number
  default     = {config.instance_count}
}}

variable "cpu_cores" {{
  description = "Number of CPU cores per VM"
  type        = number
  default     = {config.cpu_cores}
}}

variable "memory_mb" {{
  description = "Memory in MB per VM"
  type        = number
  default     = {config.memory_gb * 1024}
}}

variable "storage_capacity_gb" {{
  description = "Storage capacity in GB per VM"
  type        = number
  default     = {config.storage_capacity_gb}
}}
"""

    # Main resources
    main_tf = """
# Create storage pool
resource "libvirt_pool" "hybrid_cloud_pool" {
  name = "hybrid_cloud_pool"
  type = "dir"
  path = "/var/lib/libvirt/images/hybrid_cloud"
}

# Create base volume
resource "libvirt_volume" "base_volume" {
  name   = "base_volume.qcow2"
  pool   = libvirt_pool.hybrid_cloud_pool.name
  format = "qcow2"
  size   = var.storage_capacity_gb * 1024 * 1024 * 1024
}

# Create VM volumes
resource "libvirt_volume" "vm_volume" {
  count          = var.instance_count
  name           = "vm_volume_${count.index}.qcow2"
  pool           = libvirt_pool.hybrid_cloud_pool.name
  base_volume_id = libvirt_volume.base_volume.id
  format         = "qcow2"
}

# Create VMs
resource "libvirt_domain" "vm" {
  count  = var.instance_count
  name   = "hybrid-cloud-vm-${count.index}"
  memory = var.memory_mb
  vcpu   = var.cpu_cores

  disk {
    volume_id = libvirt_volume.vm_volume[count.index].id
  }

  network_interface {
    network_name = "default"
  }

  console {
    type        = "pty"
    target_type = "serial"
    target_port = "0"
  }
}
"""

    # Outputs
    outputs_tf = """
output "vm_ids" {
  description = "IDs of created VMs"
  value       = libvirt_domain.vm[*].id
}

output "vm_names" {
  description = "Names of created VMs"
  value       = libvirt_domain.vm[*].name
}
"""

    return TerraformFiles(
        main_tf=main_tf,
        variables_tf=variables_tf,
        outputs_tf=outputs_tf,
        provider_tf=provider_tf,
    )


def _generate_onprem_caas_terraform(config: models.ConfigurationModel) -> TerraformFiles:
    """Generate Terraform configuration for on-premises CaaS (Docker)."""
    # Provider configuration for Docker
    provider_tf = """
terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  host = var.docker_host
}
"""

    # Variables
    variables_tf = f"""
variable "docker_host" {{
  description = "Docker daemon host"
  type        = string
  default     = "unix:///var/run/docker.sock"
}}

variable "instance_count" {{
  description = "Number of containers"
  type        = number
  default     = {config.instance_count}
}}

variable "cpu_cores" {{
  description = "CPU cores per container"
  type        = number
  default     = {config.cpu_cores}
}}

variable "memory_mb" {{
  description = "Memory in MB per container"
  type        = number
  default     = {config.memory_gb * 1024}
}}

variable "container_image" {{
  description = "Container image to deploy"
  type        = string
  default     = "nginx:latest"
}}
"""

    # Main resources
    main_tf = """
# Pull container image
resource "docker_image" "app_image" {
  name = var.container_image
}

# Create containers
resource "docker_container" "app_container" {
  count = var.instance_count
  name  = "hybrid-cloud-container-${count.index}"
  image = docker_image.app_image.image_id

  # Resource limits
  memory = var.memory_mb
  cpus   = var.cpu_cores

  # Port mapping
  ports {
    internal = 80
    external = 8080 + count.index
  }

  # Restart policy
  restart = "unless-stopped"
}
"""

    # Outputs
    outputs_tf = """
output "container_ids" {
  description = "IDs of created containers"
  value       = docker_container.app_container[*].id
}

output "container_names" {
  description = "Names of created containers"
  value       = docker_container.app_container[*].name
}

output "container_ports" {
  description = "Exposed ports of containers"
  value       = [for i in range(var.instance_count) : 8080 + i]
}
"""

    return TerraformFiles(
        main_tf=main_tf,
        variables_tf=variables_tf,
        outputs_tf=outputs_tf,
        provider_tf=provider_tf,
    )


async def apply_terraform(
    terraform_files: TerraformFiles,
    provision_id: str,
    db_session: Session,
    working_dir: Optional[Path] = None,
) -> TerraformResult:
    """Apply Terraform configuration and store state in database.

    Args:
        terraform_files: Generated Terraform configuration files
        provision_id: ID of the provision record
        db_session: Database session for storing state
        working_dir: Directory to write Terraform files (defaults to temp dir)

    Returns:
        TerraformResult with success status, outputs, and state file
    """
    # Create working directory if not provided
    if working_dir is None:
        working_dir = Path(f"/tmp/terraform_{provision_id}")
    working_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Write Terraform files to disk
        (working_dir / "main.tf").write_text(terraform_files.main_tf)
        (working_dir / "variables.tf").write_text(terraform_files.variables_tf)
        (working_dir / "outputs.tf").write_text(terraform_files.outputs_tf)
        (working_dir / "provider.tf").write_text(terraform_files.provider_tf)

        # Store generated Terraform files in database
        terraform_files_json = json.dumps(
            {
                "main.tf": terraform_files.main_tf,
                "variables.tf": terraform_files.variables_tf,
                "outputs.tf": terraform_files.outputs_tf,
                "provider.tf": terraform_files.provider_tf,
            }
        )

        # Initialize Terraform
        tf = Terraform(working_dir=str(working_dir))
        return_code, stdout, stderr = tf.init()

        if return_code != 0:
            return TerraformResult(
                success=False, output={}, error=f"Terraform init failed: {stderr}"
            )

        # Apply Terraform configuration
        return_code, stdout, stderr = tf.apply(skip_plan=True)

        if return_code != 0:
            return TerraformResult(
                success=False, output={}, error=f"Terraform apply failed: {stderr}"
            )

        # Get outputs
        return_code, outputs, stderr = tf.output(json=True)
        output_dict = json.loads(outputs) if outputs else {}

        # Read state file
        state_file_path = working_dir / "terraform.tfstate"
        state_file_content = ""
        if state_file_path.exists():
            state_file_content = state_file_path.read_text()

        # Store Terraform state in database
        terraform_state = models.TerraformStateModel(
            id=str(uuid.uuid4()),
            provision_id=provision_id,
            terraform_files=terraform_files_json,
            state_file=state_file_content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db_session.add(terraform_state)
        db_session.commit()

        return TerraformResult(
            success=True,
            output=output_dict,
            state_file=state_file_content,
        )

    except Exception as e:
        return TerraformResult(success=False, output={}, error=str(e))


async def destroy_terraform(
    provision_id: str, db_session: Session, working_dir: Optional[Path] = None
) -> TerraformResult:
    """Destroy Terraform-managed infrastructure.

    Args:
        provision_id: ID of the provision record
        db_session: Database session for retrieving state
        working_dir: Directory containing Terraform files (defaults to temp dir)

    Returns:
        TerraformResult with success status
    """
    # Retrieve Terraform state from database
    terraform_state = (
        db_session.query(models.TerraformStateModel)
        .filter_by(provision_id=provision_id)
        .first()
    )

    if not terraform_state:
        return TerraformResult(
            success=False, output={}, error="Terraform state not found in database"
        )

    # Create working directory if not provided
    if working_dir is None:
        working_dir = Path(f"/tmp/terraform_{provision_id}")
    working_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Restore Terraform files from database
        terraform_files_dict = json.loads(terraform_state.terraform_files)
        for filename, content in terraform_files_dict.items():
            (working_dir / filename).write_text(content)

        # Restore state file
        state_file_path = working_dir / "terraform.tfstate"
        state_file_path.write_text(terraform_state.state_file)

        # Initialize Terraform
        tf = Terraform(working_dir=str(working_dir))
        return_code, stdout, stderr = tf.init()

        if return_code != 0:
            return TerraformResult(
                success=False, output={}, error=f"Terraform init failed: {stderr}"
            )

        # Destroy infrastructure
        return_code, stdout, stderr = tf.destroy(auto_approve=True)

        if return_code != 0:
            return TerraformResult(
                success=False, output={}, error=f"Terraform destroy failed: {stderr}"
            )

        return TerraformResult(success=True, output={})

    except Exception as e:
        return TerraformResult(success=False, output={}, error=str(e))
