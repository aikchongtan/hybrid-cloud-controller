"""Provisioning API routes for resource provisioning and deployment."""

import json
import logging
import uuid
from datetime import datetime

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from packages.database import get_session
from packages.database.models import ConfigurationModel, ProvisionModel, ResourceModel
from packages.provisioner import localstack_adapter, onprem_provisioner

logger = logging.getLogger("hybrid_cloud.api.routes.provisioning")

# Create blueprint for provisioning routes
bp = Blueprint("provisioning", __name__, url_prefix="/api/provision")


@bp.route("", methods=["POST"])
async def provision_resources():
    """
    Initiate provisioning for a configuration.

    Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6

    Request Body:
        {
            "configuration_id": str,
            "cloud_path": str,  # "aws", "on_prem_iaas", or "on_prem_caas"
            "container_image": str (optional, required for CaaS and AWS),
            "environment_vars": dict (optional, for container deployments),
            "mock_mode": bool (optional, default: true for IaaS)
        }

    Returns:
        201: Provisioning initiated successfully
        {
            "provision_id": str,
            "configuration_id": str,
            "cloud_path": str,
            "status": str,
            "resources": [
                {
                    "id": str,
                    "resource_type": str,
                    "external_id": str,
                    "status": str,
                    "connection_info": dict
                }
            ],
            "created_at": str (ISO format)
        }

        400: Invalid request
        {
            "error_code": "VALIDATION_ERROR",
            "message": str,
            "details": dict,
            "timestamp": str (ISO format)
        }

        401: Authentication required
        {
            "error_code": "AUTHENTICATION_REQUIRED",
            "message": str,
            "timestamp": str (ISO format)
        }

        404: Configuration not found
        {
            "error_code": "NOT_FOUND",
            "message": str,
            "timestamp": str (ISO format)
        }

        500: Provisioning failed
        {
            "error_code": "PROVISIONING_FAILED",
            "message": str,
            "details": dict,
            "timestamp": str (ISO format)
        }
    """
    try:
        # Get user_id from Flask's g object (set by auth middleware)
        user_id = getattr(g, "user_id", None)
        if not user_id:
            return (
                _error_response(
                    "AUTHENTICATION_REQUIRED", "Authentication required to provision resources"
                ),
                401,
            )

        # Parse request body
        data = request.get_json()
        if not data:
            return (
                _error_response("VALIDATION_ERROR", "Request body is required"),
                400,
            )

        # Validate required fields
        configuration_id = data.get("configuration_id")
        cloud_path = data.get("cloud_path")

        if not configuration_id:
            return (
                _error_response(
                    "VALIDATION_ERROR",
                    "configuration_id is required",
                    {"field": "configuration_id"},
                ),
                400,
            )

        if not cloud_path:
            return (
                _error_response(
                    "VALIDATION_ERROR", "cloud_path is required", {"field": "cloud_path"}
                ),
                400,
            )

        # Validate cloud_path value
        valid_cloud_paths = ["aws", "on_prem_iaas", "on_prem_caas"]
        if cloud_path not in valid_cloud_paths:
            return (
                _error_response(
                    "VALIDATION_ERROR",
                    f"cloud_path must be one of: {', '.join(valid_cloud_paths)}",
                    {"field": "cloud_path", "valid_values": valid_cloud_paths},
                ),
                400,
            )

        # Validate container_image for CaaS and AWS
        container_image = data.get("container_image")
        if cloud_path in ["on_prem_caas", "aws"] and not container_image:
            return (
                _error_response(
                    "VALIDATION_ERROR",
                    f"container_image is required for {cloud_path}",
                    {"field": "container_image"},
                ),
                400,
            )

        # Get optional parameters
        environment_vars = data.get("environment_vars", {})
        mock_mode = data.get("mock_mode", True)

        # Get database session
        db = get_session()

        try:
            # Query configuration and verify ownership
            config_model = (
                db.query(ConfigurationModel)
                .filter(
                    ConfigurationModel.id == configuration_id,
                    ConfigurationModel.user_id == user_id,
                )
                .first()
            )

            if not config_model:
                logger.warning(f"Configuration not found: {configuration_id}")
                return _error_response("NOT_FOUND", "Configuration not found"), 404

            # Create provision record
            provision_id = str(uuid.uuid4())
            now = datetime.utcnow()

            provision_model = ProvisionModel(
                id=provision_id,
                configuration_id=configuration_id,
                cloud_path=cloud_path,
                status="provisioning",
                created_at=now,
            )

            db.add(provision_model)
            db.commit()

            logger.info(
                f"Provisioning initiated: {provision_id} for configuration {configuration_id} "
                f"on {cloud_path}"
            )

            # Provision resources based on cloud path
            resources = []
            try:
                if cloud_path == "aws":
                    resources = await _provision_aws(
                        config_model, provision_id, container_image, environment_vars, db
                    )
                elif cloud_path == "on_prem_iaas":
                    resources = _provision_onprem_iaas(config_model, provision_id, mock_mode, db)
                elif cloud_path == "on_prem_caas":
                    resources = _provision_onprem_caas(
                        config_model, provision_id, container_image, environment_vars, db
                    )

                # Update provision status to completed
                provision_model.status = "completed"
                db.commit()

                logger.info(
                    f"Provisioning completed successfully: {provision_id} "
                    f"({len(resources)} resources created)"
                )

            except Exception as e:
                # Provisioning failed - update status
                provision_model.status = "failed"
                db.commit()

                logger.error(f"Provisioning failed for {provision_id}: {e}")
                return (
                    _error_response(
                        "PROVISIONING_FAILED",
                        f"Failed to provision resources: {str(e)}",
                        {"provision_id": provision_id},
                    ),
                    500,
                )

            # Format resources for response
            resources_response = []
            for resource in resources:
                connection_info = {}
                if resource.connection_info_json:
                    connection_info = json.loads(resource.connection_info_json)

                resources_response.append(
                    {
                        "id": resource.id,
                        "resource_type": resource.resource_type,
                        "external_id": resource.external_id,
                        "status": resource.status,
                        "connection_info": connection_info,
                    }
                )

            return (
                jsonify(
                    {
                        "provision_id": provision_id,
                        "configuration_id": configuration_id,
                        "cloud_path": cloud_path,
                        "status": provision_model.status,
                        "resources": resources_response,
                        "created_at": now.isoformat(),
                    }
                ),
                201,
            )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during provisioning: {e}")
        return _error_response("DATABASE_ERROR", "Failed to provision resources"), 500

    except Exception as e:
        logger.error(f"Unexpected error during provisioning: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


@bp.route("/<provision_id>/status", methods=["GET"])
def get_provisioning_status(provision_id: str):
    """
    Get provisioning status and resource details.

    Validates: Requirements 5.6

    Path Parameters:
        provision_id: Provision UUID

    Returns:
        200: Status retrieved successfully
        {
            "provision_id": str,
            "configuration_id": str,
            "cloud_path": str,
            "status": str,
            "resources": [
                {
                    "id": str,
                    "resource_type": str,
                    "external_id": str,
                    "status": str,
                    "connection_info": dict
                }
            ],
            "created_at": str (ISO format)
        }

        401: Authentication required
        {
            "error_code": "AUTHENTICATION_REQUIRED",
            "message": str,
            "timestamp": str (ISO format)
        }

        404: Provision not found
        {
            "error_code": "NOT_FOUND",
            "message": str,
            "timestamp": str (ISO format)
        }

        500: Database error
        {
            "error_code": "DATABASE_ERROR",
            "message": str,
            "timestamp": str (ISO format)
        }
    """
    try:
        # Get user_id from Flask's g object (set by auth middleware)
        user_id = getattr(g, "user_id", None)
        if not user_id:
            return (
                _error_response(
                    "AUTHENTICATION_REQUIRED",
                    "Authentication required to retrieve provisioning status",
                ),
                401,
            )

        # Get database session
        db = get_session()

        try:
            # Query provision with configuration to verify ownership
            provision_model = (
                db.query(ProvisionModel)
                .join(ConfigurationModel)
                .filter(
                    ProvisionModel.id == provision_id,
                    ConfigurationModel.user_id == user_id,
                )
                .first()
            )

            if not provision_model:
                logger.warning(f"Provision not found: {provision_id}")
                return _error_response("NOT_FOUND", "Provision not found"), 404

            # Query resources for this provision
            resources = (
                db.query(ResourceModel).filter(ResourceModel.provision_id == provision_id).all()
            )

            logger.info(
                f"Provisioning status retrieved: {provision_id} "
                f"(status: {provision_model.status}, {len(resources)} resources)"
            )

            # Format resources for response
            resources_response = []
            for resource in resources:
                connection_info = {}
                if resource.connection_info_json:
                    connection_info = json.loads(resource.connection_info_json)

                resources_response.append(
                    {
                        "id": resource.id,
                        "resource_type": resource.resource_type,
                        "external_id": resource.external_id,
                        "status": resource.status,
                        "connection_info": connection_info,
                    }
                )

            return jsonify(
                {
                    "provision_id": provision_model.id,
                    "configuration_id": provision_model.configuration_id,
                    "cloud_path": provision_model.cloud_path,
                    "status": provision_model.status,
                    "resources": resources_response,
                    "created_at": provision_model.created_at.isoformat(),
                }
            )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during status retrieval: {e}")
        return _error_response("DATABASE_ERROR", "Failed to retrieve status"), 500

    except Exception as e:
        logger.error(f"Unexpected error during status retrieval: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


@bp.route("/<provision_id>/deploy", methods=["POST"])
async def deploy_application(provision_id: str):
    """
    Deploy application to provisioned resources.

    Validates: Requirements 11.2, 11.3, 11.4, 11.8, 11.9

    Path Parameters:
        provision_id: Provision UUID

    Request Body:
        {
            "container_image": str (required for CaaS/AWS),
            "environment_vars": dict (optional)
        }

    Returns:
        200: Deployment successful
        {
            "provision_id": str,
            "deployment_status": str,
            "endpoint": str,
            "message": str
        }

        400: Invalid request
        {
            "error_code": "VALIDATION_ERROR",
            "message": str,
            "timestamp": str (ISO format)
        }

        401: Authentication required
        {
            "error_code": "AUTHENTICATION_REQUIRED",
            "message": str,
            "timestamp": str (ISO format)
        }

        404: Provision not found
        {
            "error_code": "NOT_FOUND",
            "message": str,
            "timestamp": str (ISO format)
        }

        500: Deployment failed
        {
            "error_code": "PROVISIONING_FAILED",
            "message": str,
            "timestamp": str (ISO format)
        }
    """
    try:
        # Get user_id from Flask's g object (set by auth middleware)
        user_id = getattr(g, "user_id", None)
        if not user_id:
            return (
                _error_response(
                    "AUTHENTICATION_REQUIRED", "Authentication required to deploy application"
                ),
                401,
            )

        # Parse request body
        data = request.get_json()
        if not data:
            return (
                _error_response("VALIDATION_ERROR", "Request body is required"),
                400,
            )

        container_image = data.get("container_image")
        environment_vars = data.get("environment_vars", {})

        # Get database session
        db = get_session()

        try:
            # Query provision with configuration to verify ownership
            provision_model = (
                db.query(ProvisionModel)
                .join(ConfigurationModel)
                .filter(
                    ProvisionModel.id == provision_id,
                    ConfigurationModel.user_id == user_id,
                )
                .first()
            )

            if not provision_model:
                logger.warning(f"Provision not found: {provision_id}")
                return _error_response("NOT_FOUND", "Provision not found"), 404

            # Check provision status
            if provision_model.status != "completed":
                return (
                    _error_response(
                        "VALIDATION_ERROR",
                        f"Cannot deploy to provision with status: {provision_model.status}",
                        {"current_status": provision_model.status},
                    ),
                    400,
                )

            # Get configuration
            config_model = (
                db.query(ConfigurationModel)
                .filter(ConfigurationModel.id == provision_model.configuration_id)
                .first()
            )

            # Deploy based on cloud path
            cloud_path = provision_model.cloud_path
            endpoint = None

            try:
                if cloud_path == "aws":
                    if not container_image:
                        return (
                            _error_response(
                                "VALIDATION_ERROR",
                                "container_image is required for AWS deployment",
                                {"field": "container_image"},
                            ),
                            400,
                        )

                    # Deploy to ECS in LocalStack
                    deployment = await localstack_adapter.deploy_to_ecs(
                        image_url=container_image,
                        cpu_cores=config_model.cpu_cores,
                        memory_gb=config_model.memory_gb,
                        provision_id=provision_id,
                        db_session=db,
                        environment_vars=environment_vars,
                    )
                    endpoint = deployment.endpoint
                    message = f"Application deployed to ECS. Endpoint: {endpoint}"

                elif cloud_path == "on_prem_caas":
                    # For CaaS, containers are already deployed during provisioning
                    # This endpoint could be used for redeployment or updates
                    resources = (
                        db.query(ResourceModel)
                        .filter(
                            ResourceModel.provision_id == provision_id,
                            ResourceModel.resource_type == "container",
                        )
                        .all()
                    )

                    if resources:
                        connection_info = json.loads(resources[0].connection_info_json)
                        endpoint = connection_info.get("endpoint", "")
                        message = f"Container already deployed. Endpoint: {endpoint}"
                    else:
                        message = "No containers found for this provision"

                elif cloud_path == "on_prem_iaas":
                    # For IaaS, return SSH connection details
                    resources = (
                        db.query(ResourceModel)
                        .filter(
                            ResourceModel.provision_id == provision_id,
                            ResourceModel.resource_type == "vm",
                        )
                        .all()
                    )

                    if resources:
                        connection_info = json.loads(resources[0].connection_info_json)
                        ip_address = connection_info.get("ip_address", "")
                        port = connection_info.get("port", "22")
                        username = connection_info.get("username", "")
                        message = (
                            f"VMs provisioned. Connect via SSH: "
                            f"ssh {username}@{ip_address} -p {port}"
                        )
                    else:
                        message = "No VMs found for this provision"

                else:
                    return (
                        _error_response(
                            "VALIDATION_ERROR",
                            f"Unsupported cloud path: {cloud_path}",
                        ),
                        400,
                    )

                logger.info(f"Deployment completed for provision {provision_id}")

                return jsonify(
                    {
                        "provision_id": provision_id,
                        "deployment_status": "deployed",
                        "endpoint": endpoint,
                        "message": message,
                    }
                )

            except Exception as e:
                logger.error(f"Deployment failed for {provision_id}: {e}")
                return (
                    _error_response(
                        "PROVISIONING_FAILED",
                        f"Failed to deploy application: {str(e)}",
                        {"provision_id": provision_id},
                    ),
                    500,
                )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during deployment: {e}")
        return _error_response("DATABASE_ERROR", "Failed to deploy application"), 500

    except Exception as e:
        logger.error(f"Unexpected error during deployment: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


# Helper functions for provisioning different cloud paths


async def _provision_aws(
    config: ConfigurationModel,
    provision_id: str,
    container_image: str,
    environment_vars: dict[str, str],
    db_session,
) -> list[ResourceModel]:
    """
    Provision AWS resources using LocalStack.

    Args:
        config: Configuration model
        provision_id: Provision ID
        container_image: Container image URL
        environment_vars: Environment variables for container
        db_session: Database session

    Returns:
        List of created ResourceModel objects
    """
    logger.info(f"Provisioning AWS resources for {provision_id}")

    # Create compute spec
    compute_spec = localstack_adapter.ComputeSpec(
        cpu_cores=config.cpu_cores,
        memory_gb=config.memory_gb,
        instance_count=config.instance_count,
    )

    # Create storage spec
    storage_spec = localstack_adapter.StorageSpec(
        storage_type=config.storage_type,
        capacity_gb=config.storage_capacity_gb,
        iops=config.storage_iops,
    )

    # Create network spec
    network_spec = localstack_adapter.NetworkSpec(
        bandwidth_mbps=config.bandwidth_mbps,
        monthly_data_transfer_gb=config.monthly_data_transfer_gb,
    )

    # Create EC2 instances
    await localstack_adapter.create_ec2_instance(
        spec=compute_spec,
        provision_id=provision_id,
        db_session=db_session,
    )

    # Create EBS volumes
    await localstack_adapter.create_ebs_volume(
        spec=storage_spec,
        instance_count=config.instance_count,
        provision_id=provision_id,
        db_session=db_session,
    )

    # Configure networking
    await localstack_adapter.configure_networking(
        spec=network_spec,
        provision_id=provision_id,
        db_session=db_session,
    )

    # Query all created resources
    resources = (
        db_session.query(ResourceModel).filter(ResourceModel.provision_id == provision_id).all()
    )

    return resources


def _provision_onprem_iaas(
    config: ConfigurationModel,
    provision_id: str,
    mock_mode: bool,
    db_session,
) -> list[ResourceModel]:
    """
    Provision on-premises IaaS resources.

    Args:
        config: Configuration model
        provision_id: Provision ID
        mock_mode: Whether to use mock mode
        db_session: Database session

    Returns:
        List of created ResourceModel objects
    """
    logger.info(f"Provisioning on-premises IaaS for {provision_id} (mock_mode={mock_mode})")

    # Provision VMs
    onprem_provisioner.provision_iaas(
        config=config,
        provision_id=provision_id,
        db_session=db_session,
        mock_mode=mock_mode,
    )

    # Query all created resources
    resources = (
        db_session.query(ResourceModel).filter(ResourceModel.provision_id == provision_id).all()
    )

    return resources


def _provision_onprem_caas(
    config: ConfigurationModel,
    provision_id: str,
    container_image: str,
    environment_vars: dict[str, str],
    db_session,
) -> list[ResourceModel]:
    """
    Provision on-premises CaaS resources.

    Args:
        config: Configuration model
        provision_id: Provision ID
        container_image: Container image URL
        environment_vars: Environment variables for containers
        db_session: Database session

    Returns:
        List of created ResourceModel objects
    """
    logger.info(f"Provisioning on-premises CaaS for {provision_id}")

    # Provision containers
    onprem_provisioner.provision_caas(
        config=config,
        image_url=container_image,
        provision_id=provision_id,
        db_session=db_session,
        environment_vars=environment_vars,
    )

    # Query all created resources
    resources = (
        db_session.query(ResourceModel).filter(ResourceModel.provision_id == provision_id).all()
    )

    return resources


def _error_response(error_code: str, message: str, details: dict | None = None) -> dict:
    """
    Create a consistent error response.

    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Optional additional error details

    Returns:
        Error response dictionary
    """
    response = {
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if details:
        response["details"] = details

    return response
