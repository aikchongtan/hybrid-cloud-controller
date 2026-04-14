"""Monitoring API routes for resource metrics and health status."""

import logging
from datetime import datetime
from typing import Optional

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from packages.database import get_session
from packages.database.models import ResourceModel
from packages.monitoring import dashboard

logger = logging.getLogger("hybrid_cloud.api.routes.monitoring")

# Create blueprint for monitoring routes
bp = Blueprint("monitoring", __name__, url_prefix="/api/monitoring")


@bp.route("/<resource_id>/metrics", methods=["GET"])
def get_metrics(resource_id: str):
    """
    Get metrics for a specific resource.

    Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.6

    Path Parameters:
        resource_id: Resource UUID

    Query Parameters:
        time_range: Optional time range for historical metrics (1h, 24h, 7d)
                   If not provided, returns current metrics only

    Returns:
        200: Metrics retrieved successfully
        {
            "resource_id": str,
            "current": {
                "cpu_percent": float,
                "memory_percent": float,
                "storage_percent": float,
                "network_mbps": float,
                "timestamp": str (ISO format)
            },
            "historical": {  # Only if time_range provided
                "time_range": str,
                "data_points": [
                    {
                        "timestamp": str (ISO format),
                        "cpu": float,
                        "memory": float,
                        "storage": float,
                        "network": float
                    }
                ]
            },
            "alerts": [
                {
                    "metric_type": str,
                    "current_value": float,
                    "threshold": float,
                    "severity": str,
                    "timestamp": str (ISO format)
                }
            ]
        }

        400: Invalid time range
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

        404: Resource not found
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
                    "AUTHENTICATION_REQUIRED", "Authentication required to view metrics"
                ),
                401,
            )

        # Get optional time_range query parameter
        time_range_str = request.args.get("time_range")
        time_range = None

        if time_range_str:
            try:
                time_range = dashboard.TimeRange(time_range_str)
            except ValueError:
                return (
                    _error_response(
                        "VALIDATION_ERROR",
                        "Invalid time_range. Must be one of: 1h, 24h, 7d",
                        {"field": "time_range", "value": time_range_str},
                    ),
                    400,
                )

        # Get database session
        db = get_session()

        try:
            # Verify resource exists and user has access
            resource = (
                db.query(ResourceModel)
                .join(ResourceModel.provision)
                .filter(
                    ResourceModel.id == resource_id,
                )
                .first()
            )

            if not resource:
                logger.warning(f"Resource not found: {resource_id}")
                return _error_response("NOT_FOUND", "Resource not found"), 404

            # Get current metrics
            try:
                current_metrics = dashboard.get_current_metrics(resource_id, db)
                current_data = {
                    "cpu_percent": current_metrics.cpu_percent,
                    "memory_percent": current_metrics.memory_percent,
                    "storage_percent": current_metrics.storage_percent,
                    "network_mbps": current_metrics.network_mbps,
                    "timestamp": current_metrics.timestamp.isoformat(),
                }
            except ValueError as e:
                logger.warning(f"No metrics available for resource {resource_id}: {e}")
                current_data = None

            # Get historical metrics if time_range provided
            historical_data = None
            if time_range and current_data:
                try:
                    historical_metrics = dashboard.get_historical_metrics(
                        resource_id, time_range, db
                    )
                    historical_data = {
                        "time_range": time_range.value,
                        "data_points": historical_metrics.data_points,
                    }
                except Exception as e:
                    logger.warning(f"Failed to retrieve historical metrics for {resource_id}: {e}")

            # Get alerts
            alerts_data = []
            if current_data:
                try:
                    alerts = dashboard.get_alerts(resource_id, db)
                    alerts_data = [
                        {
                            "metric_type": alert.metric_type,
                            "current_value": alert.current_value,
                            "threshold": alert.threshold,
                            "severity": alert.severity,
                            "timestamp": alert.timestamp.isoformat(),
                        }
                        for alert in alerts
                    ]
                except Exception as e:
                    logger.warning(f"Failed to retrieve alerts for {resource_id}: {e}")

            logger.info(f"Metrics retrieved for resource: {resource_id}")

            response = {
                "resource_id": resource_id,
                "current": current_data,
                "alerts": alerts_data,
            }

            if historical_data:
                response["historical"] = historical_data

            return jsonify(response)

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during metrics retrieval: {e}")
        return _error_response("DATABASE_ERROR", "Failed to retrieve metrics"), 500

    except Exception as e:
        logger.error(f"Unexpected error during metrics retrieval: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


@bp.route("/resources", methods=["GET"])
def get_all_resources_status():
    """
    Get status and health information for all resources.

    Validates: Requirements 8.6, 8.8

    Returns:
        200: Resources retrieved successfully
        {
            "resources": [
                {
                    "resource_id": str,
                    "resource_type": str,
                    "status": str,
                    "health": {
                        "is_reachable": bool,
                        "status": str,
                        "last_successful_collection": str (ISO format) or null
                    },
                    "current_metrics": {
                        "cpu_percent": float,
                        "memory_percent": float,
                        "storage_percent": float,
                        "network_mbps": float,
                        "timestamp": str (ISO format)
                    } or null
                }
            ],
            "total_count": int
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
        # Get user_id from Flask's g object (set by auth middleware)
        user_id = getattr(g, "user_id", None)
        if not user_id:
            return (
                _error_response(
                    "AUTHENTICATION_REQUIRED",
                    "Authentication required to view resources",
                ),
                401,
            )

        # Get database session
        db = get_session()

        try:
            # Query all resources (could be filtered by user in future)
            resources = db.query(ResourceModel).all()

            resources_data = []
            for resource in resources:
                # Get health status
                try:
                    health = dashboard.get_resource_health(resource.id, db)
                    health_data = {
                        "is_reachable": health.is_reachable,
                        "status": health.status,
                        "last_successful_collection": health.last_successful_collection.isoformat()
                        if health.last_successful_collection
                        else None,
                    }
                except Exception as e:
                    logger.warning(f"Failed to get health for resource {resource.id}: {e}")
                    health_data = {
                        "is_reachable": False,
                        "status": "unknown",
                        "last_successful_collection": None,
                    }

                # Get current metrics if resource is reachable
                current_metrics_data = None
                if health_data["is_reachable"]:
                    try:
                        current_metrics = dashboard.get_current_metrics(resource.id, db)
                        current_metrics_data = {
                            "cpu_percent": current_metrics.cpu_percent,
                            "memory_percent": current_metrics.memory_percent,
                            "storage_percent": current_metrics.storage_percent,
                            "network_mbps": current_metrics.network_mbps,
                            "timestamp": current_metrics.timestamp.isoformat(),
                        }
                    except Exception as e:
                        logger.warning(
                            f"Failed to get current metrics for resource {resource.id}: {e}"
                        )

                resources_data.append(
                    {
                        "resource_id": resource.id,
                        "resource_type": resource.resource_type,
                        "status": resource.status,
                        "health": health_data,
                        "current_metrics": current_metrics_data,
                    }
                )

            logger.info(f"Retrieved status for {len(resources_data)} resources")

            return jsonify(
                {
                    "resources": resources_data,
                    "total_count": len(resources_data),
                }
            )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during resources status retrieval: {e}")
        return _error_response("DATABASE_ERROR", "Failed to retrieve resources"), 500

    except Exception as e:
        logger.error(f"Unexpected error during resources status retrieval: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


def _error_response(error_code: str, message: str, details: Optional[dict] = None) -> dict:
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
