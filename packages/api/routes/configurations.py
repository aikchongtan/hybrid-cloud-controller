"""Configuration API routes for creating, retrieving, and validating configurations."""

import logging
import uuid
from datetime import datetime

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from packages.database import get_session
from packages.database.models import ConfigurationModel
from packages.tco_engine.validation import ValidationError, validate_configuration

logger = logging.getLogger("hybrid_cloud.api.routes.configurations")

# Create blueprint for configuration routes
bp = Blueprint("configurations", __name__, url_prefix="/api/configurations")


@bp.route("", methods=["POST"])
def create_configuration():
    """
    Create and store a new configuration.

    Validates: Requirements 1.5, 1.6, 9.2

    Request Body:
        {
            "cpu_cores": int,
            "memory_gb": int,
            "instance_count": int,
            "storage_type": str (SSD, HDD, or NVME),
            "storage_capacity_gb": int,
            "storage_iops": int (optional),
            "bandwidth_mbps": int,
            "monthly_data_transfer_gb": int,
            "utilization_percentage": int (0-100),
            "operating_hours_per_month": int (0-744)
        }

    Returns:
        201: Configuration created successfully
        {
            "id": str,
            "user_id": str,
            "cpu_cores": int,
            "memory_gb": int,
            "instance_count": int,
            "storage_type": str,
            "storage_capacity_gb": int,
            "storage_iops": int | null,
            "bandwidth_mbps": int,
            "monthly_data_transfer_gb": int,
            "utilization_percentage": int,
            "operating_hours_per_month": int,
            "created_at": str (ISO format),
            "updated_at": str (ISO format)
        }

        400: Validation error
        {
            "error_code": "VALIDATION_ERROR",
            "message": str,
            "details": dict[str, str],
            "timestamp": str (ISO format)
        }

        401: Authentication required
        {
            "error_code": "AUTHENTICATION_REQUIRED",
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
        # Parse request body
        data = request.get_json(silent=True)
        if not data:
            return _error_response("VALIDATION_ERROR", "Request body is required"), 400

        # Extract fields
        cpu_cores = data.get("cpu_cores")
        memory_gb = data.get("memory_gb")
        instance_count = data.get("instance_count")
        storage_type = data.get("storage_type")
        storage_capacity_gb = data.get("storage_capacity_gb")
        storage_iops = data.get("storage_iops")
        bandwidth_mbps = data.get("bandwidth_mbps")
        monthly_data_transfer_gb = data.get("monthly_data_transfer_gb")
        utilization_percentage = data.get("utilization_percentage")
        operating_hours_per_month = data.get("operating_hours_per_month")

        # Validate configuration
        try:
            validate_configuration(
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                instance_count=instance_count,
                storage_type=storage_type,
                storage_capacity_gb=storage_capacity_gb,
                storage_iops=storage_iops,
                bandwidth_mbps=bandwidth_mbps,
                monthly_data_transfer_gb=monthly_data_transfer_gb,
                utilization_percentage=utilization_percentage,
                operating_hours_per_month=operating_hours_per_month,
            )
        except ValidationError as e:
            logger.warning(f"Configuration validation failed: {e.errors}")
            return (
                _error_response(
                    "VALIDATION_ERROR",
                    "Configuration validation failed",
                    details=e.errors,
                ),
                400,
            )

        # Get user_id from Flask's g object (set by auth middleware)
        user_id = getattr(g, "user_id", None)
        if not user_id:
            return (
                _error_response(
                    "AUTHENTICATION_REQUIRED", "Authentication required to create configuration"
                ),
                401,
            )

        # Get database session
        db = get_session()

        try:
            # Create configuration model
            config_id = str(uuid.uuid4())
            now = datetime.utcnow()

            config = ConfigurationModel(
                id=config_id,
                user_id=user_id,
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                instance_count=instance_count,
                storage_type=storage_type,
                storage_capacity_gb=storage_capacity_gb,
                storage_iops=storage_iops,
                bandwidth_mbps=bandwidth_mbps,
                monthly_data_transfer_gb=monthly_data_transfer_gb,
                utilization_percentage=utilization_percentage,
                operating_hours_per_month=operating_hours_per_month,
                created_at=now,
                updated_at=now,
            )

            # Store in database
            db.add(config)
            db.commit()

            logger.info(f"Configuration created successfully: {config_id}")

            return (
                jsonify(
                    {
                        "id": config.id,
                        "user_id": config.user_id,
                        "cpu_cores": config.cpu_cores,
                        "memory_gb": config.memory_gb,
                        "instance_count": config.instance_count,
                        "storage_type": config.storage_type,
                        "storage_capacity_gb": config.storage_capacity_gb,
                        "storage_iops": config.storage_iops,
                        "bandwidth_mbps": config.bandwidth_mbps,
                        "monthly_data_transfer_gb": config.monthly_data_transfer_gb,
                        "utilization_percentage": config.utilization_percentage,
                        "operating_hours_per_month": config.operating_hours_per_month,
                        "created_at": config.created_at.isoformat(),
                        "updated_at": config.updated_at.isoformat(),
                    }
                ),
                201,
            )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during configuration creation: {e}")
        return _error_response("DATABASE_ERROR", "Failed to create configuration"), 500

    except Exception as e:
        logger.error(f"Unexpected error during configuration creation: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


@bp.route("/<config_id>", methods=["GET"])
def get_configuration(config_id: str):
    """
    Retrieve a configuration by ID.

    Validates: Requirements 9.2

    Path Parameters:
        config_id: Configuration UUID

    Returns:
        200: Configuration retrieved successfully
        {
            "id": str,
            "user_id": str,
            "cpu_cores": int,
            "memory_gb": int,
            "instance_count": int,
            "storage_type": str,
            "storage_capacity_gb": int,
            "storage_iops": int | null,
            "bandwidth_mbps": int,
            "monthly_data_transfer_gb": int,
            "utilization_percentage": int,
            "operating_hours_per_month": int,
            "created_at": str (ISO format),
            "updated_at": str (ISO format)
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
                    "AUTHENTICATION_REQUIRED", "Authentication required to retrieve configuration"
                ),
                401,
            )

        # Get database session
        db = get_session()

        try:
            # Query configuration
            config = (
                db.query(ConfigurationModel)
                .filter(ConfigurationModel.id == config_id, ConfigurationModel.user_id == user_id)
                .first()
            )

            if not config:
                logger.warning(f"Configuration not found: {config_id}")
                return _error_response("NOT_FOUND", "Configuration not found"), 404

            logger.info(f"Configuration retrieved successfully: {config_id}")

            return jsonify(
                {
                    "id": config.id,
                    "user_id": config.user_id,
                    "cpu_cores": config.cpu_cores,
                    "memory_gb": config.memory_gb,
                    "instance_count": config.instance_count,
                    "storage_type": config.storage_type,
                    "storage_capacity_gb": config.storage_capacity_gb,
                    "storage_iops": config.storage_iops,
                    "bandwidth_mbps": config.bandwidth_mbps,
                    "monthly_data_transfer_gb": config.monthly_data_transfer_gb,
                    "utilization_percentage": config.utilization_percentage,
                    "operating_hours_per_month": config.operating_hours_per_month,
                    "created_at": config.created_at.isoformat(),
                    "updated_at": config.updated_at.isoformat(),
                }
            )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during configuration retrieval: {e}")
        return _error_response("DATABASE_ERROR", "Failed to retrieve configuration"), 500

    except Exception as e:
        logger.error(f"Unexpected error during configuration retrieval: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


@bp.route("/validate", methods=["POST"])
def validate_configuration_endpoint():
    """
    Validate a configuration without saving it.

    Validates: Requirements 1.5, 1.6

    Request Body:
        {
            "cpu_cores": int,
            "memory_gb": int,
            "instance_count": int,
            "storage_type": str (SSD, HDD, or NVME),
            "storage_capacity_gb": int,
            "storage_iops": int (optional),
            "bandwidth_mbps": int,
            "monthly_data_transfer_gb": int,
            "utilization_percentage": int (0-100),
            "operating_hours_per_month": int (0-744)
        }

    Returns:
        200: Configuration is valid
        {
            "valid": true,
            "message": "Configuration is valid"
        }

        400: Validation error
        {
            "valid": false,
            "error_code": "VALIDATION_ERROR",
            "message": str,
            "details": dict[str, str],
            "timestamp": str (ISO format)
        }
    """
    try:
        # Parse request body
        data = request.get_json(silent=True)
        if not data:
            return _error_response("VALIDATION_ERROR", "Request body is required"), 400

        # Extract fields
        cpu_cores = data.get("cpu_cores")
        memory_gb = data.get("memory_gb")
        instance_count = data.get("instance_count")
        storage_type = data.get("storage_type")
        storage_capacity_gb = data.get("storage_capacity_gb")
        storage_iops = data.get("storage_iops")
        bandwidth_mbps = data.get("bandwidth_mbps")
        monthly_data_transfer_gb = data.get("monthly_data_transfer_gb")
        utilization_percentage = data.get("utilization_percentage")
        operating_hours_per_month = data.get("operating_hours_per_month")

        # Validate configuration
        try:
            validate_configuration(
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                instance_count=instance_count,
                storage_type=storage_type,
                storage_capacity_gb=storage_capacity_gb,
                storage_iops=storage_iops,
                bandwidth_mbps=bandwidth_mbps,
                monthly_data_transfer_gb=monthly_data_transfer_gb,
                utilization_percentage=utilization_percentage,
                operating_hours_per_month=operating_hours_per_month,
            )

            logger.info("Configuration validation successful")

            return jsonify({"valid": True, "message": "Configuration is valid"})

        except ValidationError as e:
            logger.warning(f"Configuration validation failed: {e.errors}")
            return (
                jsonify(
                    {
                        "valid": False,
                        "error_code": "VALIDATION_ERROR",
                        "message": "Configuration validation failed",
                        "details": e.errors,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ),
                400,
            )

    except Exception as e:
        logger.error(f"Unexpected error during configuration validation: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


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
