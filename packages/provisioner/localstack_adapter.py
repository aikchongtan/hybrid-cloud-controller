"""LocalStack adapter for AWS resource emulation.

This module provides functions to create and manage AWS resources in LocalStack,
including EC2 instances, EBS volumes, VPC networking, and ECS deployments.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import boto3
from sqlalchemy.orm import Session

from packages.database import models


class ResourceStatus(Enum):
    """Status of provisioned resources."""

    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    TERMINATED = "terminated"
    ERROR = "error"


@dataclass
class EC2Instance:
    """EC2 instance details."""

    instance_id: str
    instance_type: str
    state: str
    public_ip: str | None = None
    private_ip: str | None = None


@dataclass
class EBSVolume:
    """EBS volume details."""

    volume_id: str
    size_gb: int
    volume_type: str
    state: str
    iops: int | None = None


@dataclass
class NetworkConfig:
    """Network configuration details."""

    vpc_id: str
    subnet_id: str
    security_group_id: str
    cidr_block: str


@dataclass
class ECSDeployment:
    """ECS deployment details."""

    cluster_arn: str
    service_arn: str
    task_definition_arn: str
    endpoint: str | None = None


@dataclass
class ResourceState:
    """Current state of a resource."""

    resource_id: str
    resource_type: str
    external_id: str
    status: str
    details: dict[str, str] | None = None


@dataclass
class ComputeSpec:
    """Compute specifications."""

    cpu_cores: int
    memory_gb: int
    instance_count: int


@dataclass
class StorageSpec:
    """Storage specifications."""

    storage_type: str
    capacity_gb: int
    iops: int | None = None


@dataclass
class NetworkSpec:
    """Network specifications."""

    bandwidth_mbps: int
    monthly_data_transfer_gb: int


def _get_boto3_client(service_name: str, endpoint_url: str = "http://localhost:4566"):
    """Create boto3 client configured for LocalStack.

    Args:
        service_name: AWS service name (ec2, ecs, etc.)
        endpoint_url: LocalStack endpoint URL

    Returns:
        Configured boto3 client
    """
    return boto3.client(
        service_name,
        endpoint_url=endpoint_url,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


def _select_instance_type(cpu_cores: int, memory_gb: int) -> str:
    """Select appropriate EC2 instance type based on CPU and memory requirements.

    Args:
        cpu_cores: Number of CPU cores required
        memory_gb: Memory in GB required

    Returns:
        EC2 instance type string
    """
    # Simple mapping based on requirements
    if cpu_cores <= 2 and memory_gb <= 4:
        return "t2.small"
    elif cpu_cores <= 2 and memory_gb <= 8:
        return "t2.medium"
    elif cpu_cores <= 4 and memory_gb <= 16:
        return "t2.xlarge"
    elif cpu_cores <= 8 and memory_gb <= 32:
        return "m5.2xlarge"
    elif cpu_cores <= 16 and memory_gb <= 64:
        return "m5.4xlarge"
    else:
        return "m5.8xlarge"


def _select_volume_type(storage_type: str, iops: int | None) -> str:
    """Select appropriate EBS volume type.

    Args:
        storage_type: Storage type from configuration (ssd, hdd, nvme)
        iops: IOPS requirement if specified

    Returns:
        EBS volume type string
    """
    if storage_type.lower() == "nvme" or (iops and iops > 16000):
        return "io2"
    elif storage_type.lower() == "ssd":
        return "gp3"
    else:
        return "st1"


async def create_ec2_instance(
    spec: ComputeSpec,
    provision_id: str,
    db_session: Session,
    endpoint_url: str = "http://localhost:4566",
) -> list[EC2Instance]:
    """Create EC2 instances in LocalStack matching compute specifications.

    Args:
        spec: Compute specifications (CPU, memory, instance count)
        provision_id: ID of the provision record
        db_session: Database session for recording resources
        endpoint_url: LocalStack endpoint URL

    Returns:
        List of created EC2Instance objects
    """
    ec2_client = _get_boto3_client("ec2", endpoint_url)

    # Select appropriate instance type
    instance_type = _select_instance_type(spec.cpu_cores, spec.memory_gb)

    # Create instances
    instances = []
    try:
        response = ec2_client.run_instances(
            ImageId="ami-0c55b159cbfafe1f0",  # Placeholder AMI for LocalStack
            InstanceType=instance_type,
            MinCount=spec.instance_count,
            MaxCount=spec.instance_count,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": f"hybrid-cloud-{provision_id}"},
                        {"Key": "ProvisionId", "Value": provision_id},
                    ],
                }
            ],
        )

        # Process created instances
        for instance_data in response["Instances"]:
            instance = EC2Instance(
                instance_id=instance_data["InstanceId"],
                instance_type=instance_type,
                state=instance_data["State"]["Name"],
                private_ip=instance_data.get("PrivateIpAddress"),
                public_ip=instance_data.get("PublicIpAddress"),
            )
            instances.append(instance)

            # Record resource in database
            resource_record = models.ResourceModel(
                id=str(uuid.uuid4()),
                provision_id=provision_id,
                resource_type="ec2_instance",
                external_id=instance.instance_id,
                status=instance.state,
                connection_info_json=f'{{"instance_type": "{instance_type}", "public_ip": "{instance.public_ip}", "private_ip": "{instance.private_ip}"}}',
                created_at=datetime.utcnow(),
            )
            db_session.add(resource_record)

        db_session.commit()
        return instances

    except Exception as e:
        db_session.rollback()
        raise RuntimeError(f"Failed to create EC2 instances: {e}") from e


async def create_ebs_volume(
    spec: StorageSpec,
    instance_count: int,
    provision_id: str,
    db_session: Session,
    endpoint_url: str = "http://localhost:4566",
) -> list[EBSVolume]:
    """Create EBS volumes in LocalStack matching storage specifications.

    Args:
        spec: Storage specifications (type, capacity, IOPS)
        instance_count: Number of volumes to create (one per instance)
        provision_id: ID of the provision record
        db_session: Database session for recording resources
        endpoint_url: LocalStack endpoint URL

    Returns:
        List of created EBSVolume objects
    """
    ec2_client = _get_boto3_client("ec2", endpoint_url)

    # Select appropriate volume type
    volume_type = _select_volume_type(spec.storage_type, spec.iops)

    # Create volumes
    volumes = []
    try:
        for i in range(instance_count):
            # Prepare volume parameters
            volume_params = {
                "AvailabilityZone": "us-east-1a",
                "Size": spec.capacity_gb,
                "VolumeType": volume_type,
                "TagSpecifications": [
                    {
                        "ResourceType": "volume",
                        "Tags": [
                            {"Key": "Name", "Value": f"hybrid-cloud-{provision_id}-{i}"},
                            {"Key": "ProvisionId", "Value": provision_id},
                        ],
                    }
                ],
            }

            # Add IOPS if specified and volume type supports it
            if spec.iops and volume_type in ["io1", "io2", "gp3"]:
                volume_params["Iops"] = spec.iops

            response = ec2_client.create_volume(**volume_params)

            volume = EBSVolume(
                volume_id=response["VolumeId"],
                size_gb=spec.capacity_gb,
                volume_type=volume_type,
                state=response["State"],
                iops=spec.iops,
            )
            volumes.append(volume)

            # Record resource in database
            resource_record = models.ResourceModel(
                id=str(uuid.uuid4()),
                provision_id=provision_id,
                resource_type="ebs_volume",
                external_id=volume.volume_id,
                status=volume.state,
                connection_info_json=f'{{"size_gb": {spec.capacity_gb}, "volume_type": "{volume_type}", "iops": {spec.iops}}}',
                created_at=datetime.utcnow(),
            )
            db_session.add(resource_record)

        db_session.commit()
        return volumes

    except Exception as e:
        db_session.rollback()
        raise RuntimeError(f"Failed to create EBS volumes: {e}") from e


async def configure_networking(
    spec: NetworkSpec,
    provision_id: str,
    db_session: Session,
    endpoint_url: str = "http://localhost:4566",
) -> NetworkConfig:
    """Configure VPC and networking in LocalStack matching network specifications.

    Args:
        spec: Network specifications (bandwidth, data transfer)
        provision_id: ID of the provision record
        db_session: Database session for recording resources
        endpoint_url: LocalStack endpoint URL

    Returns:
        NetworkConfig with VPC, subnet, and security group details
    """
    ec2_client = _get_boto3_client("ec2", endpoint_url)

    try:
        # Create VPC
        vpc_response = ec2_client.create_vpc(
            CidrBlock="10.0.0.0/16",
            TagSpecifications=[
                {
                    "ResourceType": "vpc",
                    "Tags": [
                        {"Key": "Name", "Value": f"hybrid-cloud-vpc-{provision_id}"},
                        {"Key": "ProvisionId", "Value": provision_id},
                    ],
                }
            ],
        )
        vpc_id = vpc_response["Vpc"]["VpcId"]

        # Create subnet
        subnet_response = ec2_client.create_subnet(
            VpcId=vpc_id,
            CidrBlock="10.0.1.0/24",
            AvailabilityZone="us-east-1a",
            TagSpecifications=[
                {
                    "ResourceType": "subnet",
                    "Tags": [
                        {"Key": "Name", "Value": f"hybrid-cloud-subnet-{provision_id}"},
                        {"Key": "ProvisionId", "Value": provision_id},
                    ],
                }
            ],
        )
        subnet_id = subnet_response["Subnet"]["SubnetId"]

        # Create security group
        sg_response = ec2_client.create_security_group(
            GroupName=f"hybrid-cloud-sg-{provision_id}",
            Description=f"Security group for hybrid cloud provision {provision_id}",
            VpcId=vpc_id,
            TagSpecifications=[
                {
                    "ResourceType": "security-group",
                    "Tags": [
                        {"Key": "Name", "Value": f"hybrid-cloud-sg-{provision_id}"},
                        {"Key": "ProvisionId", "Value": provision_id},
                    ],
                }
            ],
        )
        security_group_id = sg_response["GroupId"]

        # Add ingress rules to security group
        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 80,
                    "ToPort": 80,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 443,
                    "ToPort": 443,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
            ],
        )

        network_config = NetworkConfig(
            vpc_id=vpc_id,
            subnet_id=subnet_id,
            security_group_id=security_group_id,
            cidr_block="10.0.0.0/16",
        )

        # Record VPC resource in database
        vpc_record = models.ResourceModel(
            id=str(uuid.uuid4()),
            provision_id=provision_id,
            resource_type="vpc",
            external_id=vpc_id,
            status="available",
            connection_info_json=f'{{"cidr_block": "10.0.0.0/16", "subnet_id": "{subnet_id}", "security_group_id": "{security_group_id}"}}',
            created_at=datetime.utcnow(),
        )
        db_session.add(vpc_record)

        # Record subnet resource in database
        subnet_record = models.ResourceModel(
            id=str(uuid.uuid4()),
            provision_id=provision_id,
            resource_type="subnet",
            external_id=subnet_id,
            status="available",
            connection_info_json=f'{{"cidr_block": "10.0.1.0/24", "vpc_id": "{vpc_id}"}}',
            created_at=datetime.utcnow(),
        )
        db_session.add(subnet_record)

        # Record security group resource in database
        sg_record = models.ResourceModel(
            id=str(uuid.uuid4()),
            provision_id=provision_id,
            resource_type="security_group",
            external_id=security_group_id,
            status="available",
            connection_info_json=f'{{"vpc_id": "{vpc_id}"}}',
            created_at=datetime.utcnow(),
        )
        db_session.add(sg_record)

        db_session.commit()
        return network_config

    except Exception as e:
        db_session.rollback()
        raise RuntimeError(f"Failed to configure networking: {e}") from e


async def deploy_to_ecs(
    image_url: str,
    cpu_cores: int,
    memory_gb: int,
    provision_id: str,
    db_session: Session,
    environment_vars: dict[str, str] | None = None,
    endpoint_url: str = "http://localhost:4566",
) -> ECSDeployment:
    """Deploy container to emulated ECS in LocalStack.

    Args:
        image_url: Container image URL
        cpu_cores: CPU cores to allocate
        memory_gb: Memory in GB to allocate
        provision_id: ID of the provision record
        db_session: Database session for recording resources
        environment_vars: Optional environment variables for the container
        endpoint_url: LocalStack endpoint URL

    Returns:
        ECSDeployment with cluster, service, and task definition details
    """
    ecs_client = _get_boto3_client("ecs", endpoint_url)

    try:
        # Create ECS cluster
        cluster_response = ecs_client.create_cluster(
            clusterName=f"hybrid-cloud-cluster-{provision_id}",
            tags=[
                {"key": "Name", "value": f"hybrid-cloud-cluster-{provision_id}"},
                {"key": "ProvisionId", "value": provision_id},
            ],
        )
        cluster_arn = cluster_response["cluster"]["clusterArn"]

        # Prepare environment variables
        environment = []
        if environment_vars:
            environment = [{"name": key, "value": value} for key, value in environment_vars.items()]

        # Register task definition
        # ECS CPU units: 1 vCPU = 1024 units
        cpu_units = str(cpu_cores * 1024)
        memory_mb = str(memory_gb * 1024)

        task_def_response = ecs_client.register_task_definition(
            family=f"hybrid-cloud-task-{provision_id}",
            networkMode="awsvpc",
            requiresCompatibilities=["FARGATE"],
            cpu=cpu_units,
            memory=memory_mb,
            containerDefinitions=[
                {
                    "name": "app-container",
                    "image": image_url,
                    "cpu": int(cpu_units),
                    "memory": int(memory_mb),
                    "essential": True,
                    "environment": environment,
                    "portMappings": [
                        {
                            "containerPort": 80,
                            "protocol": "tcp",
                        }
                    ],
                }
            ],
            tags=[
                {"key": "Name", "value": f"hybrid-cloud-task-{provision_id}"},
                {"key": "ProvisionId", "value": provision_id},
            ],
        )
        task_definition_arn = task_def_response["taskDefinition"]["taskDefinitionArn"]

        # Create ECS service
        service_response = ecs_client.create_service(
            cluster=cluster_arn,
            serviceName=f"hybrid-cloud-service-{provision_id}",
            taskDefinition=task_definition_arn,
            desiredCount=1,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": ["subnet-12345"],  # Placeholder for LocalStack
                    "assignPublicIp": "ENABLED",
                }
            },
            tags=[
                {"key": "Name", "value": f"hybrid-cloud-service-{provision_id}"},
                {"key": "ProvisionId", "value": provision_id},
            ],
        )
        service_arn = service_response["service"]["serviceArn"]

        deployment = ECSDeployment(
            cluster_arn=cluster_arn,
            service_arn=service_arn,
            task_definition_arn=task_definition_arn,
            endpoint="http://localhost:8080",  # Placeholder endpoint
        )

        # Record ECS cluster in database
        cluster_record = models.ResourceModel(
            id=str(uuid.uuid4()),
            provision_id=provision_id,
            resource_type="ecs_cluster",
            external_id=cluster_arn,
            status="active",
            connection_info_json=f'{{"cluster_arn": "{cluster_arn}"}}',
            created_at=datetime.utcnow(),
        )
        db_session.add(cluster_record)

        # Record ECS service in database
        service_record = models.ResourceModel(
            id=str(uuid.uuid4()),
            provision_id=provision_id,
            resource_type="ecs_service",
            external_id=service_arn,
            status="active",
            connection_info_json=f'{{"service_arn": "{service_arn}", "task_definition_arn": "{task_definition_arn}", "endpoint": "http://localhost:8080"}}',
            created_at=datetime.utcnow(),
        )
        db_session.add(service_record)

        db_session.commit()
        return deployment

    except Exception as e:
        db_session.rollback()
        raise RuntimeError(f"Failed to deploy to ECS: {e}") from e


def start_resource(
    resource_id: str,
    db_session: Session,
    endpoint_url: str = "http://localhost:4566",
) -> ResourceState:
    """Start a stopped resource.

    Args:
        resource_id: Database ID of the resource to start
        db_session: Database session for querying and updating resources
        endpoint_url: LocalStack endpoint URL

    Returns:
        ResourceState with updated status

    Raises:
        ValueError: If resource not found in database
        RuntimeError: If AWS API call fails
    """
    # Query database to get resource type and external_id
    resource = db_session.query(models.ResourceModel).filter_by(id=resource_id).first()
    if not resource:
        raise ValueError(f"Resource {resource_id} not found in database")

    try:
        if resource.resource_type == "ec2_instance":
            # Start EC2 instance
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            ec2_client.start_instances(InstanceIds=[resource.external_id])
            new_status = "running"

        elif resource.resource_type == "ecs_service":
            # Update ECS service to desired count 1
            ecs_client = _get_boto3_client("ecs", endpoint_url)
            # Extract cluster name from service ARN or use a default
            cluster_name = (
                resource.external_id.split("/")[-2] if "/" in resource.external_id else "default"
            )
            ecs_client.update_service(
                cluster=cluster_name,
                service=resource.external_id,
                desiredCount=1,
            )
            new_status = "running"

        else:
            raise ValueError(
                f"Resource type {resource.resource_type} does not support start operation"
            )

        # Update resource status in database
        resource.status = new_status
        db_session.commit()

        return ResourceState(
            resource_id=resource.id,
            resource_type=resource.resource_type,
            external_id=resource.external_id,
            status=new_status,
        )

    except Exception as e:
        db_session.rollback()
        raise RuntimeError(f"Failed to start resource {resource_id}: {e}") from e


def stop_resource(
    resource_id: str,
    db_session: Session,
    endpoint_url: str = "http://localhost:4566",
) -> ResourceState:
    """Stop a running resource.

    Args:
        resource_id: Database ID of the resource to stop
        db_session: Database session for querying and updating resources
        endpoint_url: LocalStack endpoint URL

    Returns:
        ResourceState with updated status

    Raises:
        ValueError: If resource not found in database
        RuntimeError: If AWS API call fails
    """
    # Query database to get resource type and external_id
    resource = db_session.query(models.ResourceModel).filter_by(id=resource_id).first()
    if not resource:
        raise ValueError(f"Resource {resource_id} not found in database")

    try:
        if resource.resource_type == "ec2_instance":
            # Stop EC2 instance
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            ec2_client.stop_instances(InstanceIds=[resource.external_id])
            new_status = "stopped"

        elif resource.resource_type == "ecs_service":
            # Update ECS service to desired count 0
            ecs_client = _get_boto3_client("ecs", endpoint_url)
            cluster_name = (
                resource.external_id.split("/")[-2] if "/" in resource.external_id else "default"
            )
            ecs_client.update_service(
                cluster=cluster_name,
                service=resource.external_id,
                desiredCount=0,
            )
            new_status = "stopped"

        else:
            raise ValueError(
                f"Resource type {resource.resource_type} does not support stop operation"
            )

        # Update resource status in database
        resource.status = new_status
        db_session.commit()

        return ResourceState(
            resource_id=resource.id,
            resource_type=resource.resource_type,
            external_id=resource.external_id,
            status=new_status,
        )

    except Exception as e:
        db_session.rollback()
        raise RuntimeError(f"Failed to stop resource {resource_id}: {e}") from e


def terminate_resource(
    resource_id: str,
    db_session: Session,
    endpoint_url: str = "http://localhost:4566",
) -> ResourceState:
    """Terminate a resource.

    Args:
        resource_id: Database ID of the resource to terminate
        db_session: Database session for querying and updating resources
        endpoint_url: LocalStack endpoint URL

    Returns:
        ResourceState with updated status

    Raises:
        ValueError: If resource not found in database
        RuntimeError: If AWS API call fails
    """
    # Query database to get resource type and external_id
    resource = db_session.query(models.ResourceModel).filter_by(id=resource_id).first()
    if not resource:
        raise ValueError(f"Resource {resource_id} not found in database")

    try:
        if resource.resource_type == "ec2_instance":
            # Terminate EC2 instance
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            ec2_client.terminate_instances(InstanceIds=[resource.external_id])
            new_status = "terminated"

        elif resource.resource_type == "ecs_service":
            # Delete ECS service
            ecs_client = _get_boto3_client("ecs", endpoint_url)
            cluster_name = (
                resource.external_id.split("/")[-2] if "/" in resource.external_id else "default"
            )
            ecs_client.delete_service(
                cluster=cluster_name,
                service=resource.external_id,
                force=True,
            )
            new_status = "terminated"

        elif resource.resource_type == "ecs_cluster":
            # Delete ECS cluster
            ecs_client = _get_boto3_client("ecs", endpoint_url)
            ecs_client.delete_cluster(cluster=resource.external_id)
            new_status = "terminated"

        elif resource.resource_type == "ebs_volume":
            # Delete EBS volume
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            ec2_client.delete_volume(VolumeId=resource.external_id)
            new_status = "terminated"

        elif resource.resource_type == "security_group":
            # Delete security group
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            ec2_client.delete_security_group(GroupId=resource.external_id)
            new_status = "terminated"

        elif resource.resource_type == "subnet":
            # Delete subnet
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            ec2_client.delete_subnet(SubnetId=resource.external_id)
            new_status = "terminated"

        elif resource.resource_type == "vpc":
            # Delete VPC
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            ec2_client.delete_vpc(VpcId=resource.external_id)
            new_status = "terminated"

        else:
            raise ValueError(
                f"Resource type {resource.resource_type} does not support terminate operation"
            )

        # Update resource status in database
        resource.status = new_status
        db_session.commit()

        return ResourceState(
            resource_id=resource.id,
            resource_type=resource.resource_type,
            external_id=resource.external_id,
            status=new_status,
        )

    except Exception as e:
        db_session.rollback()
        raise RuntimeError(f"Failed to terminate resource {resource_id}: {e}") from e


def get_resource_status(
    resource_id: str,
    db_session: Session,
    endpoint_url: str = "http://localhost:4566",
) -> ResourceState:
    """Query current resource state from LocalStack.

    Args:
        resource_id: Database ID of the resource to query
        db_session: Database session for querying and updating resources
        endpoint_url: LocalStack endpoint URL

    Returns:
        ResourceState with current status

    Raises:
        ValueError: If resource not found in database
        RuntimeError: If AWS API call fails
    """
    # Query database to get resource type and external_id
    resource = db_session.query(models.ResourceModel).filter_by(id=resource_id).first()
    if not resource:
        raise ValueError(f"Resource {resource_id} not found in database")

    try:
        details = {}

        if resource.resource_type == "ec2_instance":
            # Query EC2 instance state
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            response = ec2_client.describe_instances(InstanceIds=[resource.external_id])
            if response["Reservations"] and response["Reservations"][0]["Instances"]:
                instance = response["Reservations"][0]["Instances"][0]
                current_status = instance["State"]["Name"]
                details = {
                    "state": current_status,
                    "instance_type": instance.get("InstanceType", ""),
                    "public_ip": instance.get("PublicIpAddress", ""),
                    "private_ip": instance.get("PrivateIpAddress", ""),
                }
            else:
                current_status = "terminated"

        elif resource.resource_type == "ecs_service":
            # Query ECS service status
            ecs_client = _get_boto3_client("ecs", endpoint_url)
            cluster_name = (
                resource.external_id.split("/")[-2] if "/" in resource.external_id else "default"
            )
            response = ecs_client.describe_services(
                cluster=cluster_name,
                services=[resource.external_id],
            )
            if response["services"]:
                service = response["services"][0]
                current_status = service["status"].lower()
                details = {
                    "status": service["status"],
                    "desired_count": str(service.get("desiredCount", 0)),
                    "running_count": str(service.get("runningCount", 0)),
                }
            else:
                current_status = "terminated"

        elif resource.resource_type == "ecs_cluster":
            # Query ECS cluster status
            ecs_client = _get_boto3_client("ecs", endpoint_url)
            response = ecs_client.describe_clusters(clusters=[resource.external_id])
            if response["clusters"]:
                cluster = response["clusters"][0]
                current_status = cluster["status"].lower()
                details = {
                    "status": cluster["status"],
                    "active_services": str(cluster.get("activeServicesCount", 0)),
                }
            else:
                current_status = "terminated"

        elif resource.resource_type == "ebs_volume":
            # Query EBS volume state
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            response = ec2_client.describe_volumes(VolumeIds=[resource.external_id])
            if response["Volumes"]:
                volume = response["Volumes"][0]
                current_status = volume["State"]
                details = {
                    "state": volume["State"],
                    "size": str(volume.get("Size", 0)),
                    "volume_type": volume.get("VolumeType", ""),
                }
            else:
                current_status = "terminated"

        elif resource.resource_type == "vpc":
            # Query VPC state
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            response = ec2_client.describe_vpcs(VpcIds=[resource.external_id])
            if response["Vpcs"]:
                vpc = response["Vpcs"][0]
                current_status = vpc["State"]
                details = {
                    "state": vpc["State"],
                    "cidr_block": vpc.get("CidrBlock", ""),
                }
            else:
                current_status = "terminated"

        elif resource.resource_type == "subnet":
            # Query subnet state
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            response = ec2_client.describe_subnets(SubnetIds=[resource.external_id])
            if response["Subnets"]:
                subnet = response["Subnets"][0]
                current_status = subnet["State"]
                details = {
                    "state": subnet["State"],
                    "cidr_block": subnet.get("CidrBlock", ""),
                }
            else:
                current_status = "terminated"

        elif resource.resource_type == "security_group":
            # Query security group state
            ec2_client = _get_boto3_client("ec2", endpoint_url)
            response = ec2_client.describe_security_groups(GroupIds=[resource.external_id])
            if response["SecurityGroups"]:
                sg = response["SecurityGroups"][0]
                current_status = "available"
                details = {
                    "group_name": sg.get("GroupName", ""),
                    "vpc_id": sg.get("VpcId", ""),
                }
            else:
                current_status = "terminated"

        else:
            raise ValueError(f"Resource type {resource.resource_type} is not supported")

        # Update resource status in database if changed
        if resource.status != current_status:
            resource.status = current_status
            db_session.commit()

        return ResourceState(
            resource_id=resource.id,
            resource_type=resource.resource_type,
            external_id=resource.external_id,
            status=current_status,
            details=details,
        )

    except Exception as e:
        db_session.rollback()
        raise RuntimeError(f"Failed to get resource status for {resource_id}: {e}") from e
