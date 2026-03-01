"""API package for Hybrid Cloud Controller REST endpoints."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

__all__ = ["ErrorResponse", "ERROR_STATUS_CODES"]


@dataclass
class ErrorResponse:
    """Consistent error response format for all API endpoints."""

    error_code: str  # Machine-readable error code
    message: str  # Human-readable error message
    details: Optional[dict[str, Any]] = None  # Additional context
    timestamp: datetime = field(default_factory=datetime.utcnow)


# HTTP Status Code Mapping
ERROR_STATUS_CODES = {
    "VALIDATION_ERROR": 400,
    "AUTHENTICATION_REQUIRED": 401,
    "ACCESS_DENIED": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "PROVISIONING_FAILED": 500,
    "DATABASE_ERROR": 500,
    "EXTERNAL_SERVICE_ERROR": 502,
    "SERVICE_UNAVAILABLE": 503,
}
