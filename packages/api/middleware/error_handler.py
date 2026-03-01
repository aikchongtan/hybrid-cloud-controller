"""Error handling middleware for consistent API error responses."""

import logging
from typing import Any

from werkzeug.exceptions import HTTPException

from packages.api import ERROR_STATUS_CODES, ErrorResponse

logger = logging.getLogger("hybrid_cloud.api.middleware.error_handler")


def handle_http_error(error: HTTPException) -> tuple[dict[str, Any], int]:
    """
    Handle HTTP exceptions with consistent error response format.

    Args:
        error: HTTP exception from Flask/Werkzeug

    Returns:
        Tuple of (error response dict, status code)
    """
    # Map HTTP status codes to error codes
    status_to_error_code = {
        400: "VALIDATION_ERROR",
        401: "AUTHENTICATION_REQUIRED",
        403: "ACCESS_DENIED",
        404: "NOT_FOUND",
        409: "CONFLICT",
        500: "DATABASE_ERROR",
        502: "EXTERNAL_SERVICE_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }

    error_code = status_to_error_code.get(error.code, "UNKNOWN_ERROR")
    status_code = error.code or 500

    error_response = ErrorResponse(
        error_code=error_code,
        message=error.description or "An error occurred",
        details={"http_status": status_code},
    )

    logger.warning(
        f"HTTP error {status_code}: {error_code} - {error.description}",
        extra={"error_code": error_code, "status_code": status_code},
    )

    return _serialize_error_response(error_response), status_code


def handle_generic_error(error: Exception) -> tuple[dict[str, Any], int]:
    """
    Handle generic exceptions with consistent error response format.

    Args:
        error: Generic Python exception

    Returns:
        Tuple of (error response dict, status code)
    """
    # Determine error code based on exception type
    error_code = _determine_error_code(error)
    status_code = ERROR_STATUS_CODES.get(error_code, 500)

    error_response = ErrorResponse(
        error_code=error_code,
        message=str(error),
        details={"exception_type": type(error).__name__},
    )

    logger.error(
        f"Unhandled exception: {type(error).__name__} - {error}",
        extra={"error_code": error_code, "exception_type": type(error).__name__},
        exc_info=True,
    )

    return _serialize_error_response(error_response), status_code


def _determine_error_code(error: Exception) -> str:
    """
    Determine appropriate error code based on exception type.

    Args:
        error: Exception instance

    Returns:
        Error code string
    """
    exception_type = type(error).__name__

    # Map common exception types to error codes
    error_mapping = {
        "ValueError": "VALIDATION_ERROR",
        "TypeError": "VALIDATION_ERROR",
        "KeyError": "NOT_FOUND",
        "AttributeError": "NOT_FOUND",
        "PermissionError": "ACCESS_DENIED",
        "TimeoutError": "SERVICE_UNAVAILABLE",
        "ConnectionError": "EXTERNAL_SERVICE_ERROR",
        "DatabaseError": "DATABASE_ERROR",
        "IntegrityError": "CONFLICT",
    }

    return error_mapping.get(exception_type, "DATABASE_ERROR")


def _serialize_error_response(error_response: ErrorResponse) -> dict[str, Any]:
    """
    Serialize ErrorResponse dataclass to JSON-compatible dict.

    Args:
        error_response: ErrorResponse instance

    Returns:
        Dictionary representation of error response
    """
    return {
        "error_code": error_response.error_code,
        "message": error_response.message,
        "details": error_response.details,
        "timestamp": error_response.timestamp.isoformat(),
    }


def create_error_response(
    error_code: str, message: str, details: dict[str, Any] | None = None
) -> tuple[dict[str, Any], int]:
    """
    Create a standardized error response.

    This helper function can be used by route handlers to create
    consistent error responses.

    Args:
        error_code: Machine-readable error code (must be in ERROR_STATUS_CODES)
        message: Human-readable error message
        details: Optional additional context

    Returns:
        Tuple of (error response dict, status code)
    """
    if error_code not in ERROR_STATUS_CODES:
        logger.warning(f"Unknown error code: {error_code}, using DATABASE_ERROR")
        error_code = "DATABASE_ERROR"

    status_code = ERROR_STATUS_CODES[error_code]

    error_response = ErrorResponse(error_code=error_code, message=message, details=details)

    return _serialize_error_response(error_response), status_code
