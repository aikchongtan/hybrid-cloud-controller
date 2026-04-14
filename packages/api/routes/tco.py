"""TCO API routes for calculating and retrieving TCO results."""

import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from packages.database import get_session
from packages.database.models import ConfigurationModel, TCOResultModel
from packages.pricing_service import fetcher as pricing_fetcher
from packages.tco_engine import calculator

logger = logging.getLogger("hybrid_cloud.api.routes.tco")

# Create blueprint for TCO routes
bp = Blueprint("tco", __name__, url_prefix="/api/tco")


@bp.route("/<config_id>/calculate", methods=["POST"])
def calculate_tco(config_id: str):
    """
    Calculate TCO for a configuration.

    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 9.4

    Path Parameters:
        config_id: Configuration UUID

    Returns:
        200: TCO calculation successful
        {
            "id": str,
            "configuration_id": str,
            "on_prem_costs": {
                "1": {
                    "items": [
                        {
                            "category": str,
                            "description": str,
                            "amount": str,
                            "unit": str
                        }
                    ],
                    "total": str,
                    "currency": str
                },
                "3": {...},
                "5": {...}
            },
            "aws_costs": {
                "1": {...},
                "3": {...},
                "5": {...}
            },
            "recommendation": str | null,
            "calculated_at": str (ISO format)
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

        500: Database or calculation error
        {
            "error_code": "DATABASE_ERROR" | "EXTERNAL_SERVICE_ERROR",
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
                    "AUTHENTICATION_REQUIRED", "Authentication required to calculate TCO"
                ),
                401,
            )

        # Get database session
        db = get_session()

        try:
            # Query configuration
            config_model = (
                db.query(ConfigurationModel)
                .filter(
                    ConfigurationModel.id == config_id,
                    ConfigurationModel.user_id == user_id,
                )
                .first()
            )

            if not config_model:
                logger.warning(f"Configuration not found: {config_id}")
                return _error_response("NOT_FOUND", "Configuration not found"), 404

            # Convert ConfigurationModel to calculator.Configuration
            config = calculator.Configuration(
                cpu_cores=config_model.cpu_cores,
                memory_gb=config_model.memory_gb,
                instance_count=config_model.instance_count,
                storage_type=config_model.storage_type,
                storage_capacity_gb=config_model.storage_capacity_gb,
                storage_iops=config_model.storage_iops,
                bandwidth_mbps=config_model.bandwidth_mbps,
                monthly_data_transfer_gb=config_model.monthly_data_transfer_gb,
                utilization_percentage=config_model.utilization_percentage,
                operating_hours_per_month=config_model.operating_hours_per_month,
            )

            # Get current pricing data
            pricing_data = pricing_fetcher.get_current_pricing()
            if not pricing_data:
                logger.error("No pricing data available")
                return (
                    _error_response(
                        "EXTERNAL_SERVICE_ERROR",
                        "Pricing data unavailable. Please try again later.",
                    ),
                    500,
                )

            # Convert pricing data to calculator.AWSPricing
            pricing = calculator.AWSPricing(
                ec2_pricing=pricing_data["ec2_pricing"],
                ebs_pricing=pricing_data["ebs_pricing"],
                s3_pricing=pricing_data["s3_pricing"],
                data_transfer_pricing=pricing_data["data_transfer_pricing"],
            )

            # Calculate TCO
            logger.info(f"Calculating TCO for configuration: {config_id}")
            tco_result = calculator.calculate_tco(config, pricing)

            # Generate recommendation based on total costs
            recommendation = _generate_recommendation(tco_result)

            # Store TCO result in database
            tco_id = str(uuid.uuid4())
            now = datetime.utcnow()

            tco_model = TCOResultModel(
                id=tco_id,
                configuration_id=config_id,
                on_prem_costs_json=_serialize_costs(tco_result["on_prem"]),
                aws_costs_json=_serialize_costs(tco_result["aws"]),
                recommendation=recommendation,
                calculated_at=now,
            )

            db.add(tco_model)
            db.commit()

            logger.info(f"TCO calculation completed and stored: {tco_id}")

            # Return TCO result
            return jsonify(
                {
                    "id": tco_id,
                    "configuration_id": config_id,
                    "on_prem_costs": _format_costs_for_response(tco_result["on_prem"]),
                    "aws_costs": _format_costs_for_response(tco_result["aws"]),
                    "recommendation": recommendation,
                    "calculated_at": now.isoformat(),
                }
            )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during TCO calculation: {e}")
        return _error_response("DATABASE_ERROR", "Failed to calculate TCO"), 500

    except Exception as e:
        logger.error(f"Unexpected error during TCO calculation: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


@bp.route("/<config_id>", methods=["GET"])
def get_tco_results(config_id: str):
    """
    Retrieve TCO results for a configuration.

    Validates: Requirements 9.4

    Path Parameters:
        config_id: Configuration UUID

    Returns:
        200: TCO results retrieved successfully
        {
            "id": str,
            "configuration_id": str,
            "on_prem_costs": {
                "1": {...},
                "3": {...},
                "5": {...}
            },
            "aws_costs": {
                "1": {...},
                "3": {...},
                "5": {...}
            },
            "recommendation": str | null,
            "calculated_at": str (ISO format)
        }

        401: Authentication required
        {
            "error_code": "AUTHENTICATION_REQUIRED",
            "message": str,
            "timestamp": str (ISO format)
        }

        404: TCO results not found
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
                    "AUTHENTICATION_REQUIRED", "Authentication required to retrieve TCO results"
                ),
                401,
            )

        # Get database session
        db = get_session()

        try:
            # Query TCO result with configuration to verify ownership
            tco_model = (
                db.query(TCOResultModel)
                .join(ConfigurationModel)
                .filter(
                    TCOResultModel.configuration_id == config_id,
                    ConfigurationModel.user_id == user_id,
                )
                .order_by(TCOResultModel.calculated_at.desc())
                .first()
            )

            if not tco_model:
                logger.warning(f"TCO results not found for configuration: {config_id}")
                return (
                    _error_response(
                        "NOT_FOUND",
                        "TCO results not found for this configuration",
                    ),
                    404,
                )

            logger.info(f"TCO results retrieved successfully: {tco_model.id}")

            # Deserialize costs
            on_prem_costs = _deserialize_costs(tco_model.on_prem_costs_json)
            aws_costs = _deserialize_costs(tco_model.aws_costs_json)

            return jsonify(
                {
                    "id": tco_model.id,
                    "configuration_id": tco_model.configuration_id,
                    "on_prem_costs": _format_costs_for_response(on_prem_costs),
                    "aws_costs": _format_costs_for_response(aws_costs),
                    "recommendation": tco_model.recommendation,
                    "calculated_at": tco_model.calculated_at.isoformat(),
                }
            )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during TCO retrieval: {e}")
        return _error_response("DATABASE_ERROR", "Failed to retrieve TCO results"), 500

    except Exception as e:
        logger.error(f"Unexpected error during TCO retrieval: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


def _serialize_costs(costs: dict[int, calculator.CostBreakdown]) -> str:
    """
    Serialize cost breakdowns to JSON string.

    Args:
        costs: Dictionary mapping years to CostBreakdown objects

    Returns:
        JSON string representation
    """
    serializable = {}
    for year, breakdown in costs.items():
        serializable[str(year)] = {
            "items": [
                {
                    "category": item.category,
                    "description": item.description,
                    "amount": str(item.amount),
                    "unit": item.unit,
                }
                for item in breakdown.items
            ],
            "total": str(breakdown.total),
            "currency": breakdown.currency,
        }
    return json.dumps(serializable)


def _deserialize_costs(costs_json: str) -> dict[int, calculator.CostBreakdown]:
    """
    Deserialize cost breakdowns from JSON string.

    Args:
        costs_json: JSON string representation

    Returns:
        Dictionary mapping years to CostBreakdown objects
    """
    costs_dict = json.loads(costs_json)
    result = {}

    for year_str, breakdown_dict in costs_dict.items():
        items = [
            calculator.CostLineItem(
                category=item["category"],
                description=item["description"],
                amount=Decimal(item["amount"]),
                unit=item["unit"],
            )
            for item in breakdown_dict["items"]
        ]

        result[int(year_str)] = calculator.CostBreakdown(
            items=items,
            total=Decimal(breakdown_dict["total"]),
            currency=breakdown_dict["currency"],
        )

    return result


def _format_costs_for_response(costs: dict[int, calculator.CostBreakdown]) -> dict:
    """
    Format cost breakdowns for JSON response.

    Args:
        costs: Dictionary mapping years to CostBreakdown objects

    Returns:
        Dictionary suitable for JSON serialization
    """
    formatted = {}
    for year, breakdown in costs.items():
        formatted[str(year)] = {
            "items": [
                {
                    "category": item.category,
                    "description": item.description,
                    "amount": str(item.amount),
                    "unit": item.unit,
                }
                for item in breakdown.items
            ],
            "total": str(breakdown.total),
            "currency": breakdown.currency,
        }
    return formatted


def _generate_recommendation(tco_result: dict[str, dict[int, calculator.CostBreakdown]]) -> str:
    """
    Generate a recommendation based on TCO comparison.

    Args:
        tco_result: TCO calculation result with on_prem and aws costs

    Returns:
        Recommendation string
    """
    # Compare 3-year totals (most common planning horizon)
    on_prem_3yr = tco_result["on_prem"][3].total
    aws_3yr = tco_result["aws"][3].total

    savings = abs(on_prem_3yr - aws_3yr)
    savings_percent = (savings / max(on_prem_3yr, aws_3yr)) * 100

    if on_prem_3yr < aws_3yr:
        return (
            f"On-premises hosting is recommended. "
            f"Estimated 3-year savings: ${savings:,.2f} ({savings_percent:.1f}% lower cost). "
            f"On-premises is more cost-effective for this workload profile."
        )
    elif aws_3yr < on_prem_3yr:
        return (
            f"AWS cloud hosting is recommended. "
            f"Estimated 3-year savings: ${savings:,.2f} ({savings_percent:.1f}% lower cost). "
            f"AWS provides better cost efficiency and eliminates upfront hardware investment."
        )
    else:
        return (
            "Both options have similar 3-year costs. "
            "Consider operational factors like scalability, maintenance overhead, "
            "and team expertise when making your decision."
        )


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
