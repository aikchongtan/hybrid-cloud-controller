"""Unit tests for Terraform orchestrator."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from packages.database import models
from packages.provisioner.terraform import (
    CloudPath,
    TerraformFiles,
    TerraformResult,
    apply_terraform,
    destroy_terraform,
    generate_terraform,
)


@pytest.fixture
def mock_config():
    """Create a mock configuration model."""
    config = Mock(spec=models.ConfigurationModel)
    config.id = str(uuid.uuid4())
    config.cpu_cores = 4
    config.memory_gb = 16
    config.instance_count = 2
    config.storage_type = "SSD"
    config.storage_capacity_gb = 500
    config.storage_iops = 3000
    config.bandwidth_mbps = 1000
    config.monthly_data_transfer_gb = 1000
    return config


def test_generate_terraform_aws(mock_config):
    """Test Terraform generation for AWS cloud path."""
    result = generate_terraform(mock_config, CloudPath.AWS)

    assert isinstance(result, TerraformFiles)
    assert "provider \"aws\"" in result.provider_tf
    assert "localstack_endpoint" in result.variables_tf
    assert "aws_instance" in result.main_tf
    assert "aws_ebs_volume" in result.main_tf
    assert "instance_ids" in result.outputs_tf
    assert str(mock_config.instance_count) in result.variables_tf
    assert str(mock_config.cpu_cores) in result.variables_tf
    assert str(mock_config.memory_gb) in result.variables_tf
    assert str(mock_config.storage_capacity_gb) in result.variables_tf


def test_generate_terraform_onprem_iaas(mock_config):
    """Test Terraform generation for on-premises IaaS cloud path."""
    result = generate_terraform(mock_config, CloudPath.ON_PREM_IAAS)

    assert isinstance(result, TerraformFiles)
    assert "provider \"libvirt\"" in result.provider_tf
    assert "libvirt_uri" in result.variables_tf
    assert "libvirt_domain" in result.main_tf
    assert "libvirt_volume" in result.main_tf
    assert "vm_ids" in result.outputs_tf
    assert str(mock_config.instance_count) in result.variables_tf
    assert str(mock_config.cpu_cores) in result.variables_tf
    # Memory should be converted to MB
    assert str(mock_config.memory_gb * 1024) in result.variables_tf
    assert str(mock_config.storage_capacity_gb) in result.variables_tf


def test_generate_terraform_onprem_caas(mock_config):
    """Test Terraform generation for on-premises CaaS cloud path."""
    result = generate_terraform(mock_config, CloudPath.ON_PREM_CAAS)

    assert isinstance(result, TerraformFiles)
    assert "provider \"docker\"" in result.provider_tf
    assert "docker_host" in result.variables_tf
    assert "docker_container" in result.main_tf
    assert "docker_image" in result.main_tf
    assert "container_ids" in result.outputs_tf
    assert str(mock_config.instance_count) in result.variables_tf
    assert str(mock_config.cpu_cores) in result.variables_tf
    # Memory should be converted to MB
    assert str(mock_config.memory_gb * 1024) in result.variables_tf


def test_generate_terraform_invalid_cloud_path(mock_config):
    """Test that invalid cloud path raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported cloud path"):
        generate_terraform(mock_config, "invalid_path")


@pytest.mark.asyncio
async def test_apply_terraform_success(mock_config, tmp_path):
    """Test successful Terraform apply operation."""
    provision_id = str(uuid.uuid4())
    terraform_files = TerraformFiles(
        main_tf="resource \"null_resource\" \"test\" {}",
        variables_tf="",
        outputs_tf='output "test" { value = "success" }',
        provider_tf="terraform { required_providers {} }",
    )

    # Mock database session
    mock_session = MagicMock()

    # Mock Terraform operations
    with patch("packages.provisioner.terraform.Terraform") as mock_tf_class:
        mock_tf = mock_tf_class.return_value
        mock_tf.init.return_value = (0, "Success", "")
        mock_tf.apply.return_value = (0, "Success", "")
        mock_tf.output.return_value = (0, '{"test": {"value": "success"}}', "")

        # Create a mock state file
        state_file_content = '{"version": 4, "terraform_version": "1.0.0"}'
        (tmp_path / "terraform.tfstate").write_text(state_file_content)

        result = await apply_terraform(
            terraform_files, provision_id, mock_session, working_dir=tmp_path
        )

    assert result.success is True
    assert result.error is None
    assert "test" in result.output
    assert result.state_file == state_file_content

    # Verify files were written
    assert (tmp_path / "main.tf").exists()
    assert (tmp_path / "variables.tf").exists()
    assert (tmp_path / "outputs.tf").exists()
    assert (tmp_path / "provider.tf").exists()

    # Verify database operations
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_apply_terraform_init_failure(mock_config, tmp_path):
    """Test Terraform apply when init fails."""
    provision_id = str(uuid.uuid4())
    terraform_files = TerraformFiles(
        main_tf="", variables_tf="", outputs_tf="", provider_tf=""
    )

    mock_session = MagicMock()

    with patch("packages.provisioner.terraform.Terraform") as mock_tf_class:
        mock_tf = mock_tf_class.return_value
        mock_tf.init.return_value = (1, "", "Init failed")

        result = await apply_terraform(
            terraform_files, provision_id, mock_session, working_dir=tmp_path
        )

    assert result.success is False
    assert "Terraform init failed" in result.error
    assert result.state_file is None


@pytest.mark.asyncio
async def test_apply_terraform_apply_failure(mock_config, tmp_path):
    """Test Terraform apply when apply fails."""
    provision_id = str(uuid.uuid4())
    terraform_files = TerraformFiles(
        main_tf="", variables_tf="", outputs_tf="", provider_tf=""
    )

    mock_session = MagicMock()

    with patch("packages.provisioner.terraform.Terraform") as mock_tf_class:
        mock_tf = mock_tf_class.return_value
        mock_tf.init.return_value = (0, "Success", "")
        mock_tf.apply.return_value = (1, "", "Apply failed")

        result = await apply_terraform(
            terraform_files, provision_id, mock_session, working_dir=tmp_path
        )

    assert result.success is False
    assert "Terraform apply failed" in result.error


@pytest.mark.asyncio
async def test_destroy_terraform_success(tmp_path):
    """Test successful Terraform destroy operation."""
    provision_id = str(uuid.uuid4())

    # Mock database session with Terraform state
    mock_session = MagicMock()
    mock_state = Mock(spec=models.TerraformStateModel)
    mock_state.provision_id = provision_id
    mock_state.terraform_files = json.dumps(
        {
            "main.tf": "resource \"null_resource\" \"test\" {}",
            "variables.tf": "",
            "outputs.tf": "",
            "provider.tf": "",
        }
    )
    mock_state.state_file = '{"version": 4}'

    mock_query = mock_session.query.return_value
    mock_query.filter_by.return_value.first.return_value = mock_state

    with patch("packages.provisioner.terraform.Terraform") as mock_tf_class:
        mock_tf = mock_tf_class.return_value
        mock_tf.init.return_value = (0, "Success", "")
        mock_tf.destroy.return_value = (0, "Success", "")

        result = await destroy_terraform(provision_id, mock_session, working_dir=tmp_path)

    assert result.success is True
    assert result.error is None

    # Verify files were restored
    assert (tmp_path / "main.tf").exists()
    assert (tmp_path / "terraform.tfstate").exists()


@pytest.mark.asyncio
async def test_destroy_terraform_state_not_found():
    """Test Terraform destroy when state is not found in database."""
    provision_id = str(uuid.uuid4())

    mock_session = MagicMock()
    mock_query = mock_session.query.return_value
    mock_query.filter_by.return_value.first.return_value = None

    result = await destroy_terraform(provision_id, mock_session)

    assert result.success is False
    assert "Terraform state not found" in result.error


@pytest.mark.asyncio
async def test_destroy_terraform_destroy_failure(tmp_path):
    """Test Terraform destroy when destroy command fails."""
    provision_id = str(uuid.uuid4())

    mock_session = MagicMock()
    mock_state = Mock(spec=models.TerraformStateModel)
    mock_state.provision_id = provision_id
    mock_state.terraform_files = json.dumps(
        {"main.tf": "", "variables.tf": "", "outputs.tf": "", "provider.tf": ""}
    )
    mock_state.state_file = "{}"

    mock_query = mock_session.query.return_value
    mock_query.filter_by.return_value.first.return_value = mock_state

    with patch("packages.provisioner.terraform.Terraform") as mock_tf_class:
        mock_tf = mock_tf_class.return_value
        mock_tf.init.return_value = (0, "Success", "")
        mock_tf.destroy.return_value = (1, "", "Destroy failed")

        result = await destroy_terraform(provision_id, mock_session, working_dir=tmp_path)

    assert result.success is False
    assert "Terraform destroy failed" in result.error


def test_terraform_files_dataclass():
    """Test TerraformFiles dataclass creation."""
    files = TerraformFiles(
        main_tf="main content",
        variables_tf="variables content",
        outputs_tf="outputs content",
        provider_tf="provider content",
    )

    assert files.main_tf == "main content"
    assert files.variables_tf == "variables content"
    assert files.outputs_tf == "outputs content"
    assert files.provider_tf == "provider content"


def test_terraform_result_dataclass():
    """Test TerraformResult dataclass creation."""
    result = TerraformResult(
        success=True, output={"key": "value"}, error=None, state_file="state content"
    )

    assert result.success is True
    assert result.output == {"key": "value"}
    assert result.error is None
    assert result.state_file == "state content"


def test_cloud_path_enum():
    """Test CloudPath enum values."""
    assert CloudPath.AWS.value == "aws"
    assert CloudPath.ON_PREM_IAAS.value == "on_prem_iaas"
    assert CloudPath.ON_PREM_CAAS.value == "on_prem_caas"
