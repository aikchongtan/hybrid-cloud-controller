"""Q&A API routes for conversational assistance about TCO analysis."""

import json
import logging
from datetime import datetime

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from packages.database import get_session
from packages.database.models import ConfigurationModel, TCOResultModel
from packages.qa_service import context as qa_context
from packages.qa_service import processor

logger = logging.getLogger("hybrid_cloud.api.routes.qa")

# Create blueprint for Q&A routes
bp = Blueprint("qa", __name__, url_prefix="/api/qa")


@bp.route("/<config_id>/ask", methods=["POST"])
def ask_question(config_id: str):
    """
    Submit a question about TCO analysis.

    Validates: Requirements 4.1, 4.5

    Path Parameters:
        config_id: Configuration UUID

    Request Body:
        {
            "question": str
        }

    Returns:
        200: Question processed successfully
        {
            "question": str,
            "answer": str,
            "timestamp": str (ISO format)
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

        404: Configuration or TCO results not found
        {
            "error_code": "NOT_FOUND",
            "message": str,
            "timestamp": str (ISO format)
        }

        500: Database or processing error
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
                    "AUTHENTICATION_REQUIRED", "Authentication required to ask questions"
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

        question = data.get("question")
        if not question or not question.strip():
            return (
                _error_response(
                    "VALIDATION_ERROR",
                    "question is required and cannot be empty",
                    {"field": "question"},
                ),
                400,
            )

        # Get database session
        db = get_session()

        try:
            # Query configuration and verify ownership
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

            # Query TCO results for this configuration
            tco_model = (
                db.query(TCOResultModel)
                .filter(TCOResultModel.configuration_id == config_id)
                .order_by(TCOResultModel.calculated_at.desc())
                .first()
            )

            if not tco_model:
                logger.warning(f"TCO results not found for configuration: {config_id}")
                return (
                    _error_response(
                        "NOT_FOUND",
                        "TCO results not found. Please calculate TCO first.",
                    ),
                    404,
                )

            # Build TCO context for Q&A processing
            tco_context = _build_tco_context(config_model, tco_model)

            # Process the question
            logger.info(f"Processing Q&A question for configuration: {config_id}")
            answer = processor.process_question(question, tco_context)

            # Get session_id from Flask's g object (set by auth middleware)
            session_id = getattr(g, "session_id", None)

            # Store question and answer in conversation history
            if session_id:
                qa_context.add_message(
                    db_session=db,
                    session_id=session_id,
                    role="user",
                    content=question,
                    configuration_id=config_id,
                )

                qa_context.add_message(
                    db_session=db,
                    session_id=session_id,
                    role="assistant",
                    content=answer,
                    configuration_id=config_id,
                )

            logger.info(f"Q&A question processed successfully for configuration: {config_id}")

            now = datetime.utcnow()
            return jsonify(
                {
                    "question": question,
                    "answer": answer,
                    "timestamp": now.isoformat(),
                }
            )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during Q&A processing: {e}")
        return _error_response("DATABASE_ERROR", "Failed to process question"), 500

    except Exception as e:
        logger.error(f"Unexpected error during Q&A processing: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


@bp.route("/<config_id>/history", methods=["GET"])
def get_conversation_history(config_id: str):
    """
    Retrieve conversation history for a configuration.

    Validates: Requirements 4.5, 4.6

    Path Parameters:
        config_id: Configuration UUID

    Returns:
        200: History retrieved successfully
        {
            "configuration_id": str,
            "messages": [
                {
                    "id": str,
                    "role": str,
                    "content": str,
                    "timestamp": str (ISO format)
                }
            ]
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
                    "AUTHENTICATION_REQUIRED",
                    "Authentication required to retrieve conversation history",
                ),
                401,
            )

        # Get database session
        db = get_session()

        try:
            # Query configuration and verify ownership
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

            # Get session_id from Flask's g object (set by auth middleware)
            session_id = getattr(g, "session_id", None)

            # Retrieve conversation history
            messages = []
            if session_id:
                messages = qa_context.get_history(
                    db_session=db,
                    session_id=session_id,
                )

            logger.info(
                f"Conversation history retrieved for configuration: {config_id} "
                f"({len(messages)} messages)"
            )

            return jsonify(
                {
                    "configuration_id": config_id,
                    "messages": messages,
                }
            )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during history retrieval: {e}")
        return _error_response("DATABASE_ERROR", "Failed to retrieve history"), 500

    except Exception as e:
        logger.error(f"Unexpected error during history retrieval: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


def _build_tco_context(
    config_model: ConfigurationModel,
    tco_model: TCOResultModel,
) -> processor.TCOContext:
    """
    Build TCO context from database models for Q&A processing.

    Args:
        config_model: Configuration database model
        tco_model: TCO result database model

    Returns:
        TCOContext object for Q&A processor
    """
    # Build configuration
    config = processor.Configuration(
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

    # Deserialize cost breakdowns
    on_prem_costs = _deserialize_costs(tco_model.on_prem_costs_json)
    aws_costs = _deserialize_costs(tco_model.aws_costs_json)

    return processor.TCOContext(
        configuration=config,
        on_prem_costs=on_prem_costs,
        aws_costs=aws_costs,
    )


def _deserialize_costs(costs_json: str) -> dict[int, processor.CostBreakdown]:
    """
    Deserialize cost breakdowns from JSON string.

    Args:
        costs_json: JSON string representation

    Returns:
        Dictionary mapping years to CostBreakdown objects
    """
    from decimal import Decimal

    costs_dict = json.loads(costs_json)
    result = {}

    for year_str, breakdown_dict in costs_dict.items():
        items = [
            processor.CostLineItem(
                category=item["category"],
                description=item["description"],
                amount=Decimal(item["amount"]),
                unit=item["unit"],
            )
            for item in breakdown_dict["items"]
        ]

        result[int(year_str)] = processor.CostBreakdown(
            items=items,
            total=Decimal(breakdown_dict["total"]),
            currency=breakdown_dict["currency"],
        )

    return result


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
