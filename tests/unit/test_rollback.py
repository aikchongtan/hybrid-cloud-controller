"""Unit tests for rollback manager."""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from packages.database import models
from packages.provisioner.rollback import (
    RollbackResult,
    rollback_deployment,
    rollback_provisioning,
)
from packages.provisioner.terraform import TerraformResult


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def provision_id():
    """Generate a provision ID."""
    return str(uuid.uuid4())


@pytest.fixture
def deployment_id():
    """Generate a deployment ID."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_provision(provision_id):
    """Create a mock provision model."""
    provision = Mock(spec=models.ProvisionModel)
    provision.id = provision_id
    provision.configuration_id = str(uuid.uuid4())
    provision.cloud_path = "aws"
    provision.status = "failed"
    provision.created_at = datetime.utcnow()
    return provision


@pytest.fixture
def mock_terraform_state(provision_id):
    """Create a mock Terraform state model."""
    state = Mock(spec=models.TerraformStateModel)
    state.id = str(uuid.uuid4())
    state.provision_id = provision_id
    state.terraform_files = '{"main.tf": "content"}'
    state.state_file = '{"version": 4}'
    state.created_at = datetime.utcnow()
    state.updated_at = datetime.utcnow()
    return state


@pytest.mark.asyncio
async def test_rollback_provisioning_success(
    mock_db_session, provision_id, mock_provision, mock_terraform_state
):
    """Test successful provisioning rollback."""
    # Setup database mocks
    provision_query = mock_db_session.query.return_value
    provision_query.filter_by.return_value.first.side_effect = [
        mock_provision,  # First call for provision
        mock_terraform_state,  # Second call for terraform state
    ]

    # Mock resource count query
    resource_query = Mock()
    resource_query.filter_by.return_value.count.return_value = 3
    resource_query.filter_by.return_value.update.return_value = None
    mock_db_session.query.side_effect = [
        provision_query,  # First query for provision
        provision_query,  # Second query for terraform state
        resource_query,  # Third query for resource count
        resource_query,  # Fourth query for resource update
    ]

    # Mock terraform destroy
    with patch("packages.provisioner.rollback.terraform.destroy_terraform") as mock_destroy:
        mock_destroy.return_value = TerraformResult(success=True, output={})

        result = await rollback_provisioning(provision_id, mock_db_session)

    assert result.success is True
    assert result.provision_id == provision_id
    assert result.error is None
    assert result.resources_removed == 3
    assert mock_provision.status == "rolled_back"
    mock_db_session.commit.assert_called()


@pytest.mark.asyncio
async def test_rollback_provisioning_no_provision_record(mock_db_session, provision_id):
    """Test rollback when provision record is not found."""
    # Setup database mock to return None
    provision_query = mock_db_session.query.return_value
    provision_query.filter_by.return_value.first.return_value = None

    result = await rollback_provisioning(provision_id, mock_db_session)

    assert result.success is False
    assert result.provision_id == provision_id
    assert "Provision record not found" in result.error


@pytest.mark.asyncio
async def test_rollback_provisioning_no_terraform_state(
    mock_db_session, provision_id, mock_provision
):
    """Test rollback when no Terraform state exists (no resources created)."""
    # Setup database mocks
    provision_query = mock_db_session.query.return_value
    provision_query.filter_by.return_value.first.side_effect = [
        mock_provision,  # First call for provision
        None,  # Second call for terraform state (not found)
    ]

    result = await rollback_provisioning(provision_id, mock_db_session)

    assert result.success is True
    assert result.provision_id == provision_id
    assert result.error is None
    assert result.resources_removed == 0
    assert mock_provision.status == "rolled_back"
    mock_db_session.commit.assert_called()


@pytest.mark.asyncio
async def test_rollback_provisioning_terraform_destroy_failure(
    mock_db_session, provision_id, mock_provision, mock_terraform_state
):
    """Test rollback when Terraform destroy fails."""
    # Setup database mocks
    provision_query = mock_db_session.query.return_value
    provision_query.filter_by.return_value.first.side_effect = [
        mock_provision,
        mock_terraform_state,
    ]

    # Mock terraform destroy failure
    with patch("packages.provisioner.rollback.terraform.destroy_terraform") as mock_destroy:
        mock_destroy.return_value = TerraformResult(
            success=False, output={}, error="Destroy command failed"
        )

        result = await rollback_provisioning(provision_id, mock_db_session)

    assert result.success is False
    assert result.provision_id == provision_id
    assert "Terraform destroy failed" in result.error
    assert "Destroy command failed" in result.error


@pytest.mark.asyncio
async def test_rollback_provisioning_updates_resource_status(
    mock_db_session, provision_id, mock_provision, mock_terraform_state
):
    """Test that rollback updates all resource statuses to terminated."""
    # Setup database mocks
    provision_query = mock_db_session.query.return_value
    provision_query.filter_by.return_value.first.side_effect = [
        mock_provision,
        mock_terraform_state,
    ]

    # Mock resource queries
    resource_query = Mock()
    resource_query.filter_by.return_value.count.return_value = 2
    resource_update_query = Mock()
    resource_update_query.filter_by.return_value.update.return_value = None
    mock_db_session.query.side_effect = [
        provision_query,  # Provision query
        provision_query,  # Terraform state query
        resource_query,  # Resource count query
        resource_update_query,  # Resource update query
    ]

    # Mock terraform destroy
    with patch("packages.provisioner.rollback.terraform.destroy_terraform") as mock_destroy:
        mock_destroy.return_value = TerraformResult(success=True, output={})

        result = await rollback_provisioning(provision_id, mock_db_session)

    assert result.success is True
    # Verify resource update was called with correct status
    resource_update_query.filter_by.return_value.update.assert_called_once_with(
        {"status": "terminated"}
    )


@pytest.mark.asyncio
async def test_rollback_deployment_success(
    mock_db_session, deployment_id, provision_id, mock_provision, mock_terraform_state
):
    """Test successful deployment rollback."""
    # Setup database mocks
    provision_query = mock_db_session.query.return_value
    provision_query.filter_by.return_value.first.side_effect = [
        mock_provision,  # First call in rollback_deployment
        mock_provision,  # Second call in rollback_provisioning
        mock_terraform_state,  # Third call for terraform state
    ]

    # Mock resource queries
    resource_query = Mock()
    resource_query.filter_by.return_value.count.return_value = 2
    resource_query.filter_by.return_value.update.return_value = None
    mock_db_session.query.side_effect = [
        provision_query,  # Provision query in rollback_deployment
        provision_query,  # Provision query in rollback_provisioning
        provision_query,  # Terraform state query
        resource_query,  # Resource count query
        resource_query,  # Resource update query
    ]

    # Mock terraform destroy
    with patch("packages.provisioner.rollback.terraform.destroy_terraform") as mock_destroy:
        mock_destroy.return_value = TerraformResult(success=True, output={})

        result = await rollback_deployment(deployment_id, provision_id, mock_db_session)

    assert result.success is True
    assert result.provision_id == provision_id
    assert result.error is None
    assert result.resources_removed == 2


@pytest.mark.asyncio
async def test_rollback_deployment_no_provision_record(
    mock_db_session, deployment_id, provision_id
):
    """Test deployment rollback when provision record is not found."""
    # Setup database mock to return None
    provision_query = mock_db_session.query.return_value
    provision_query.filter_by.return_value.first.return_value = None

    result = await rollback_deployment(deployment_id, provision_id, mock_db_session)

    assert result.success is False
    assert result.provision_id == provision_id
    assert "Provision record not found" in result.error


@pytest.mark.asyncio
async def test_rollback_deployment_provisioning_rollback_failure(
    mock_db_session, deployment_id, provision_id, mock_provision, mock_terraform_state
):
    """Test deployment rollback when provisioning rollback fails."""
    # Setup database mocks
    provision_query = mock_db_session.query.return_value
    provision_query.filter_by.return_value.first.side_effect = [
        mock_provision,  # First call in rollback_deployment
        mock_provision,  # Second call in rollback_provisioning
        mock_terraform_state,  # Third call for terraform state
    ]

    # Mock terraform destroy failure
    with patch("packages.provisioner.rollback.terraform.destroy_terraform") as mock_destroy:
        mock_destroy.return_value = TerraformResult(
            success=False, output={}, error="Destroy failed"
        )

        result = await rollback_deployment(deployment_id, provision_id, mock_db_session)

    assert result.success is False
    assert result.provision_id == provision_id
    assert "Deployment rollback failed" in result.error


def test_rollback_result_dataclass():
    """Test RollbackResult dataclass creation."""
    result = RollbackResult(
        success=True,
        provision_id="test-id",
        error=None,
        resources_removed=5,
    )

    assert result.success is True
    assert result.provision_id == "test-id"
    assert result.error is None
    assert result.resources_removed == 5


def test_rollback_result_with_error():
    """Test RollbackResult dataclass with error."""
    result = RollbackResult(
        success=False,
        provision_id="test-id",
        error="Something went wrong",
        resources_removed=0,
    )

    assert result.success is False
    assert result.provision_id == "test-id"
    assert result.error == "Something went wrong"
    assert result.resources_removed == 0
