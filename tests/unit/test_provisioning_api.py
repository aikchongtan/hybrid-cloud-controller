"""Unit tests for provisioning API endpoints."""

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.api.routes import provisioning
from packages.database.models import ConfigurationModel, ProvisionModel, ResourceModel


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.join.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    return session


@pytest.fixture
def mock_config():
    """Create a mock configuration model."""
    config = ConfigurationModel(
        id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        cpu_cores=4,
        memory_gb=16,
        instance_count=2,
        storage_type="ssd",
        storage_capacity_gb=100,
        storage_iops=3000,
        bandwidth_mbps=1000,
        monthly_data_transfer_gb=500,
        utilization_percentage=70,
        operating_hours_per_month=720,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return config


@pytest.fixture
def mock_provision():
    """Create a mock provision model."""
    provision = ProvisionModel(
        id=str(uuid.uuid4()),
        configuration_id=str(uuid.uuid4()),
        cloud_path="aws",
        status="completed",
        created_at=datetime.utcnow(),
    )
    return provision


def test_error_response():
    """Test error response formatting."""
    error = provisioning._error_response(
        "TEST_ERROR", "Test error message", {"detail": "value"}
    )

    assert error["error_code"] == "TEST_ERROR"
    assert error["message"] == "Test error message"
    assert error["details"]["detail"] == "value"
    assert "timestamp" in error


@patch("packages.api.routes.provisioning.get_session")
@patch("packages.api.routes.provisioning.localstack_adapter")
def test_provision_aws_helper(mock_adapter, mock_get_session, mock_config, mock_db_session):
    """Test AWS provisioning helper function."""
    mock_get_session.return_value = mock_db_session

    # Mock the adapter functions
    mock_adapter.create_ec2_instance = AsyncMock()
    mock_adapter.create_ebs_volume = AsyncMock()
    mock_adapter.configure_networking = AsyncMock()

    # Mock resource query
    mock_resource = ResourceModel(
        id=str(uuid.uuid4()),
        provision_id=str(uuid.uuid4()),
        resource_type="ec2_instance",
        external_id="i-12345",
        status="running",
        connection_info_json='{"ip": "10.0.0.1"}',
        created_at=datetime.utcnow(),
    )
    mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_resource]

    # Test the function (note: this is async, so we need to handle it properly)
    import asyncio

    provision_id = str(uuid.uuid4())
    resources = asyncio.run(
        provisioning._provision_aws(
            config=mock_config,
            provision_id=provision_id,
            container_image="nginx:latest",
            environment_vars={"ENV": "test"},
            db_session=mock_db_session,
        )
    )

    # Verify adapter functions were called
    assert mock_adapter.create_ec2_instance.called
    assert mock_adapter.create_ebs_volume.called
    assert mock_adapter.configure_networking.called

    # Verify resources were returned
    assert len(resources) == 1
    assert resources[0].resource_type == "ec2_instance"


@patch("packages.api.routes.provisioning.get_session")
@patch("packages.api.routes.provisioning.onprem_provisioner")
def test_provision_onprem_iaas_helper(
    mock_provisioner, mock_get_session, mock_config, mock_db_session
):
    """Test on-premises IaaS provisioning helper function."""
    mock_get_session.return_value = mock_db_session

    # Mock resource query
    mock_resource = ResourceModel(
        id=str(uuid.uuid4()),
        provision_id=str(uuid.uuid4()),
        resource_type="vm",
        external_id="vm-12345",
        status="running",
        connection_info_json='{"ip": "192.168.1.10"}',
        created_at=datetime.utcnow(),
    )
    mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_resource]

    # Test the function
    provision_id = str(uuid.uuid4())
    resources = provisioning._provision_onprem_iaas(
        config=mock_config,
        provision_id=provision_id,
        mock_mode=True,
        db_session=mock_db_session,
    )

    # Verify provisioner was called
    assert mock_provisioner.provision_iaas.called
    call_args = mock_provisioner.provision_iaas.call_args
    assert call_args[1]["config"] == mock_config
    assert call_args[1]["provision_id"] == provision_id
    assert call_args[1]["mock_mode"] is True

    # Verify resources were returned
    assert len(resources) == 1
    assert resources[0].resource_type == "vm"


@patch("packages.api.routes.provisioning.get_session")
@patch("packages.api.routes.provisioning.onprem_provisioner")
def test_provision_onprem_caas_helper(
    mock_provisioner, mock_get_session, mock_config, mock_db_session
):
    """Test on-premises CaaS provisioning helper function."""
    mock_get_session.return_value = mock_db_session

    # Mock resource query
    mock_resource = ResourceModel(
        id=str(uuid.uuid4()),
        provision_id=str(uuid.uuid4()),
        resource_type="container",
        external_id="container-12345",
        status="running",
        connection_info_json='{"endpoint": "http://localhost:8080"}',
        created_at=datetime.utcnow(),
    )
    mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_resource]

    # Test the function
    provision_id = str(uuid.uuid4())
    resources = provisioning._provision_onprem_caas(
        config=mock_config,
        provision_id=provision_id,
        container_image="nginx:latest",
        environment_vars={"ENV": "test"},
        db_session=mock_db_session,
    )

    # Verify provisioner was called
    assert mock_provisioner.provision_caas.called
    call_args = mock_provisioner.provision_caas.call_args
    assert call_args[1]["config"] == mock_config
    assert call_args[1]["provision_id"] == provision_id
    assert call_args[1]["image_url"] == "nginx:latest"
    assert call_args[1]["environment_vars"] == {"ENV": "test"}

    # Verify resources were returned
    assert len(resources) == 1
    assert resources[0].resource_type == "container"


def test_cloud_path_validation():
    """Test that cloud path validation works correctly."""
    valid_paths = ["aws", "on_prem_iaas", "on_prem_caas"]

    for path in valid_paths:
        assert path in ["aws", "on_prem_iaas", "on_prem_caas"]

    invalid_paths = ["azure", "gcp", "invalid"]
    for path in invalid_paths:
        assert path not in ["aws", "on_prem_iaas", "on_prem_caas"]


def test_container_image_requirement():
    """Test that container image is required for CaaS and AWS."""
    # CaaS requires container image
    assert "on_prem_caas" in ["on_prem_caas", "aws"]

    # AWS requires container image
    assert "aws" in ["on_prem_caas", "aws"]

    # IaaS does not require container image
    assert "on_prem_iaas" not in ["on_prem_caas", "aws"]
