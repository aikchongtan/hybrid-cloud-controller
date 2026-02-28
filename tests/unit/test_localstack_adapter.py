"""Unit tests for LocalStack adapter."""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from packages.provisioner.localstack_adapter import (
    ComputeSpec,
    EBSVolume,
    EC2Instance,
    ECSDeployment,
    NetworkConfig,
    NetworkSpec,
    ResourceStatus,
    StorageSpec,
    _get_boto3_client,
    _select_instance_type,
    _select_volume_type,
    configure_networking,
    create_ebs_volume,
    create_ec2_instance,
    deploy_to_ecs,
)


def test_select_instance_type_small():
    """Test instance type selection for small requirements."""
    instance_type = _select_instance_type(cpu_cores=2, memory_gb=4)
    assert instance_type == "t2.small"


def test_select_instance_type_medium():
    """Test instance type selection for medium requirements."""
    instance_type = _select_instance_type(cpu_cores=2, memory_gb=8)
    assert instance_type == "t2.medium"


def test_select_instance_type_xlarge():
    """Test instance type selection for xlarge requirements."""
    instance_type = _select_instance_type(cpu_cores=4, memory_gb=16)
    assert instance_type == "t2.xlarge"


def test_select_instance_type_2xlarge():
    """Test instance type selection for 2xlarge requirements."""
    instance_type = _select_instance_type(cpu_cores=8, memory_gb=32)
    assert instance_type == "m5.2xlarge"


def test_select_instance_type_4xlarge():
    """Test instance type selection for 4xlarge requirements."""
    instance_type = _select_instance_type(cpu_cores=16, memory_gb=64)
    assert instance_type == "m5.4xlarge"


def test_select_instance_type_8xlarge():
    """Test instance type selection for large requirements."""
    instance_type = _select_instance_type(cpu_cores=32, memory_gb=128)
    assert instance_type == "m5.8xlarge"


def test_select_volume_type_nvme():
    """Test volume type selection for NVMe storage."""
    volume_type = _select_volume_type(storage_type="nvme", iops=None)
    assert volume_type == "io2"


def test_select_volume_type_high_iops():
    """Test volume type selection for high IOPS requirements."""
    volume_type = _select_volume_type(storage_type="ssd", iops=20000)
    assert volume_type == "io2"


def test_select_volume_type_ssd():
    """Test volume type selection for SSD storage."""
    volume_type = _select_volume_type(storage_type="ssd", iops=None)
    assert volume_type == "gp3"


def test_select_volume_type_hdd():
    """Test volume type selection for HDD storage."""
    volume_type = _select_volume_type(storage_type="hdd", iops=None)
    assert volume_type == "st1"


@patch("packages.provisioner.localstack_adapter.boto3.client")
def test_get_boto3_client(mock_boto3_client):
    """Test boto3 client creation for LocalStack."""
    _get_boto3_client("ec2", "http://localhost:4566")

    mock_boto3_client.assert_called_once_with(
        "ec2",
        endpoint_url="http://localhost:4566",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.mark.asyncio
@patch("packages.provisioner.localstack_adapter._get_boto3_client")
async def test_create_ec2_instance_success(mock_get_client):
    """Test successful EC2 instance creation."""
    provision_id = str(uuid.uuid4())
    spec = ComputeSpec(cpu_cores=4, memory_gb=16, instance_count=2)

    # Mock EC2 client
    mock_ec2 = MagicMock()
    mock_get_client.return_value = mock_ec2

    mock_ec2.run_instances.return_value = {
        "Instances": [
            {
                "InstanceId": "i-12345",
                "State": {"Name": "running"},
                "PrivateIpAddress": "10.0.1.10",
                "PublicIpAddress": "54.1.2.3",
            },
            {
                "InstanceId": "i-67890",
                "State": {"Name": "running"},
                "PrivateIpAddress": "10.0.1.11",
                "PublicIpAddress": "54.1.2.4",
            },
        ]
    }

    # Mock database session
    mock_session = MagicMock()

    result = await create_ec2_instance(spec, provision_id, mock_session)

    assert len(result) == 2
    assert result[0].instance_id == "i-12345"
    assert result[0].instance_type == "t2.xlarge"
    assert result[0].state == "running"
    assert result[0].public_ip == "54.1.2.3"
    assert result[1].instance_id == "i-67890"

    # Verify database operations
    assert mock_session.add.call_count == 2
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("packages.provisioner.localstack_adapter._get_boto3_client")
async def test_create_ec2_instance_failure(mock_get_client):
    """Test EC2 instance creation failure."""
    provision_id = str(uuid.uuid4())
    spec = ComputeSpec(cpu_cores=4, memory_gb=16, instance_count=1)

    # Mock EC2 client to raise exception
    mock_ec2 = MagicMock()
    mock_get_client.return_value = mock_ec2
    mock_ec2.run_instances.side_effect = Exception("AWS API error")

    mock_session = MagicMock()

    with pytest.raises(RuntimeError, match="Failed to create EC2 instances"):
        await create_ec2_instance(spec, provision_id, mock_session)

    # Verify rollback was called
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
@patch("packages.provisioner.localstack_adapter._get_boto3_client")
async def test_create_ebs_volume_success(mock_get_client):
    """Test successful EBS volume creation."""
    provision_id = str(uuid.uuid4())
    spec = StorageSpec(storage_type="ssd", capacity_gb=100, iops=3000)

    # Mock EC2 client
    mock_ec2 = MagicMock()
    mock_get_client.return_value = mock_ec2

    mock_ec2.create_volume.side_effect = [
        {
            "VolumeId": "vol-12345",
            "Size": 100,
            "VolumeType": "gp3",
            "State": "available",
        },
        {
            "VolumeId": "vol-67890",
            "Size": 100,
            "VolumeType": "gp3",
            "State": "available",
        },
    ]

    mock_session = MagicMock()

    result = await create_ebs_volume(spec, 2, provision_id, mock_session)

    assert len(result) == 2
    assert result[0].volume_id == "vol-12345"
    assert result[0].size_gb == 100
    assert result[0].volume_type == "gp3"
    assert result[0].state == "available"
    assert result[0].iops == 3000

    # Verify database operations
    assert mock_session.add.call_count == 2
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("packages.provisioner.localstack_adapter._get_boto3_client")
async def test_create_ebs_volume_with_high_iops(mock_get_client):
    """Test EBS volume creation with high IOPS."""
    provision_id = str(uuid.uuid4())
    spec = StorageSpec(storage_type="nvme", capacity_gb=500, iops=20000)

    mock_ec2 = MagicMock()
    mock_get_client.return_value = mock_ec2

    mock_ec2.create_volume.return_value = {
        "VolumeId": "vol-12345",
        "Size": 500,
        "VolumeType": "io2",
        "State": "available",
        "Iops": 20000,
    }

    mock_session = MagicMock()

    result = await create_ebs_volume(spec, 1, provision_id, mock_session)

    assert len(result) == 1
    assert result[0].volume_type == "io2"
    assert result[0].iops == 20000

    # Verify IOPS was included in the create_volume call
    call_args = mock_ec2.create_volume.call_args[1]
    assert call_args["Iops"] == 20000


@pytest.mark.asyncio
@patch("packages.provisioner.localstack_adapter._get_boto3_client")
async def test_create_ebs_volume_failure(mock_get_client):
    """Test EBS volume creation failure."""
    provision_id = str(uuid.uuid4())
    spec = StorageSpec(storage_type="ssd", capacity_gb=100, iops=None)

    mock_ec2 = MagicMock()
    mock_get_client.return_value = mock_ec2
    mock_ec2.create_volume.side_effect = Exception("Volume creation failed")

    mock_session = MagicMock()

    with pytest.raises(RuntimeError, match="Failed to create EBS volumes"):
        await create_ebs_volume(spec, 1, provision_id, mock_session)

    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
@patch("packages.provisioner.localstack_adapter._get_boto3_client")
async def test_configure_networking_success(mock_get_client):
    """Test successful VPC and networking configuration."""
    provision_id = str(uuid.uuid4())
    spec = NetworkSpec(bandwidth_mbps=1000, monthly_data_transfer_gb=5000)

    # Mock EC2 client
    mock_ec2 = MagicMock()
    mock_get_client.return_value = mock_ec2

    mock_ec2.create_vpc.return_value = {"Vpc": {"VpcId": "vpc-12345"}}
    mock_ec2.create_subnet.return_value = {"Subnet": {"SubnetId": "subnet-12345"}}
    mock_ec2.create_security_group.return_value = {"GroupId": "sg-12345"}

    mock_session = MagicMock()

    result = await configure_networking(spec, provision_id, mock_session)

    assert result.vpc_id == "vpc-12345"
    assert result.subnet_id == "subnet-12345"
    assert result.security_group_id == "sg-12345"
    assert result.cidr_block == "10.0.0.0/16"

    # Verify security group ingress rules were added
    mock_ec2.authorize_security_group_ingress.assert_called_once()

    # Verify database operations (VPC, subnet, security group)
    assert mock_session.add.call_count == 3
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("packages.provisioner.localstack_adapter._get_boto3_client")
async def test_configure_networking_failure(mock_get_client):
    """Test networking configuration failure."""
    provision_id = str(uuid.uuid4())
    spec = NetworkSpec(bandwidth_mbps=1000, monthly_data_transfer_gb=5000)

    mock_ec2 = MagicMock()
    mock_get_client.return_value = mock_ec2
    mock_ec2.create_vpc.side_effect = Exception("VPC creation failed")

    mock_session = MagicMock()

    with pytest.raises(RuntimeError, match="Failed to configure networking"):
        await configure_networking(spec, provision_id, mock_session)

    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
@patch("packages.provisioner.localstack_adapter._get_boto3_client")
async def test_deploy_to_ecs_success(mock_get_client):
    """Test successful ECS deployment."""
    provision_id = str(uuid.uuid4())
    image_url = "nginx:latest"
    cpu_cores = 2
    memory_gb = 4
    env_vars = {"ENV": "production", "DEBUG": "false"}

    # Mock ECS client
    mock_ecs = MagicMock()
    mock_get_client.return_value = mock_ecs

    mock_ecs.create_cluster.return_value = {
        "cluster": {"clusterArn": "arn:aws:ecs:us-east-1:123456789:cluster/test"}
    }
    mock_ecs.register_task_definition.return_value = {
        "taskDefinition": {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789:task-definition/test:1"
        }
    }
    mock_ecs.create_service.return_value = {
        "service": {"serviceArn": "arn:aws:ecs:us-east-1:123456789:service/test"}
    }

    mock_session = MagicMock()

    result = await deploy_to_ecs(
        image_url, cpu_cores, memory_gb, provision_id, mock_session, env_vars
    )

    assert "cluster" in result.cluster_arn
    assert "service" in result.service_arn
    assert "task-definition" in result.task_definition_arn
    assert result.endpoint == "http://localhost:8080"

    # Verify task definition includes environment variables
    task_def_call = mock_ecs.register_task_definition.call_args[1]
    container_def = task_def_call["containerDefinitions"][0]
    assert len(container_def["environment"]) == 2
    assert {"name": "ENV", "value": "production"} in container_def["environment"]
    assert {"name": "DEBUG", "value": "false"} in container_def["environment"]

    # Verify CPU and memory are correctly converted
    assert task_def_call["cpu"] == "2048"  # 2 cores * 1024
    assert task_def_call["memory"] == "4096"  # 4 GB * 1024

    # Verify database operations (cluster and service)
    assert mock_session.add.call_count == 2
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("packages.provisioner.localstack_adapter._get_boto3_client")
async def test_deploy_to_ecs_without_env_vars(mock_get_client):
    """Test ECS deployment without environment variables."""
    provision_id = str(uuid.uuid4())
    image_url = "nginx:latest"

    mock_ecs = MagicMock()
    mock_get_client.return_value = mock_ecs

    mock_ecs.create_cluster.return_value = {
        "cluster": {"clusterArn": "arn:aws:ecs:us-east-1:123456789:cluster/test"}
    }
    mock_ecs.register_task_definition.return_value = {
        "taskDefinition": {
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789:task-definition/test:1"
        }
    }
    mock_ecs.create_service.return_value = {
        "service": {"serviceArn": "arn:aws:ecs:us-east-1:123456789:service/test"}
    }

    mock_session = MagicMock()

    result = await deploy_to_ecs(image_url, 1, 2, provision_id, mock_session)

    # Verify task definition has empty environment list
    task_def_call = mock_ecs.register_task_definition.call_args[1]
    container_def = task_def_call["containerDefinitions"][0]
    assert container_def["environment"] == []


@pytest.mark.asyncio
@patch("packages.provisioner.localstack_adapter._get_boto3_client")
async def test_deploy_to_ecs_failure(mock_get_client):
    """Test ECS deployment failure."""
    provision_id = str(uuid.uuid4())
    image_url = "nginx:latest"

    mock_ecs = MagicMock()
    mock_get_client.return_value = mock_ecs
    mock_ecs.create_cluster.side_effect = Exception("Cluster creation failed")

    mock_session = MagicMock()

    with pytest.raises(RuntimeError, match="Failed to deploy to ECS"):
        await deploy_to_ecs(image_url, 2, 4, provision_id, mock_session)

    mock_session.rollback.assert_called_once()


def test_resource_status_enum():
    """Test ResourceStatus enum values."""
    assert ResourceStatus.PENDING.value == "pending"
    assert ResourceStatus.RUNNING.value == "running"
    assert ResourceStatus.STOPPED.value == "stopped"
    assert ResourceStatus.TERMINATED.value == "terminated"
    assert ResourceStatus.ERROR.value == "error"


def test_ec2_instance_dataclass():
    """Test EC2Instance dataclass creation."""
    instance = EC2Instance(
        instance_id="i-12345",
        instance_type="t2.micro",
        state="running",
        public_ip="54.1.2.3",
        private_ip="10.0.1.10",
    )

    assert instance.instance_id == "i-12345"
    assert instance.instance_type == "t2.micro"
    assert instance.state == "running"
    assert instance.public_ip == "54.1.2.3"
    assert instance.private_ip == "10.0.1.10"


def test_ebs_volume_dataclass():
    """Test EBSVolume dataclass creation."""
    volume = EBSVolume(
        volume_id="vol-12345",
        size_gb=100,
        volume_type="gp3",
        state="available",
        iops=3000,
    )

    assert volume.volume_id == "vol-12345"
    assert volume.size_gb == 100
    assert volume.volume_type == "gp3"
    assert volume.state == "available"
    assert volume.iops == 3000


def test_network_config_dataclass():
    """Test NetworkConfig dataclass creation."""
    config = NetworkConfig(
        vpc_id="vpc-12345",
        subnet_id="subnet-12345",
        security_group_id="sg-12345",
        cidr_block="10.0.0.0/16",
    )

    assert config.vpc_id == "vpc-12345"
    assert config.subnet_id == "subnet-12345"
    assert config.security_group_id == "sg-12345"
    assert config.cidr_block == "10.0.0.0/16"


def test_ecs_deployment_dataclass():
    """Test ECSDeployment dataclass creation."""
    deployment = ECSDeployment(
        cluster_arn="arn:aws:ecs:us-east-1:123456789:cluster/test",
        service_arn="arn:aws:ecs:us-east-1:123456789:service/test",
        task_definition_arn="arn:aws:ecs:us-east-1:123456789:task-definition/test:1",
        endpoint="http://localhost:8080",
    )

    assert "cluster" in deployment.cluster_arn
    assert "service" in deployment.service_arn
    assert "task-definition" in deployment.task_definition_arn
    assert deployment.endpoint == "http://localhost:8080"
