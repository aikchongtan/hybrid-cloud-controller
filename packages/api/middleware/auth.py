"""Authentication middleware for API request validation."""

import logging

from flask import g, request
from werkzeug.exceptions import Unauthorized

logger = logging.getLogger("hybrid_cloud.api.middleware.auth")

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = [
    "/api/auth/login",
    "/api/auth/register",
    "/health",
    "/",
]


def authenticate_request() -> None:
    """
    Authenticate API requests using session tokens.

    Validates: Requirements 12.3, 12.4, 12.5

    This middleware:
    - Skips authentication for public endpoints
    - Validates session tokens from Authorization header
    - Checks session timeout (30 minutes inactivity)
    - Updates last_activity timestamp
    - Stores user_id in Flask's g object for route handlers

    Raises:
        Unauthorized: If authentication fails or session is invalid
    """
    # Skip authentication for public endpoints
    if _is_public_endpoint(request.path):
        logger.debug(f"Skipping auth for public endpoint: {request.path}")
        return

    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.warning(f"Missing Authorization header for {request.path}")
        raise Unauthorized("Authentication required")

    # Expect format: "Bearer <token>"
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid Authorization header format for {request.path}")
        raise Unauthorized("Invalid authentication format")

    token = parts[1]

    # Validate session token
    # Note: Actual validation will be implemented when database integration is added
    # For now, this is a placeholder that will be completed in future tasks
    try:
        session = _validate_session_token(token)
        if not session:
            raise Unauthorized("Invalid or expired session")

        # Store user_id in Flask's g object for route handlers
        g.user_id = session.get("user_id")
        g.session_id = session.get("session_id")

        logger.debug(f"Authentication successful for user {g.user_id} on {request.path}")

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise Unauthorized("Authentication failed") from e


def _is_public_endpoint(path: str) -> bool:
    """Check if the endpoint is public (doesn't require authentication)."""
    return any(path.startswith(endpoint) for endpoint in PUBLIC_ENDPOINTS)


def _validate_session_token(token: str) -> dict[str, str] | None:
    """
    Validate session token and check timeout.

    This is a placeholder implementation. The actual implementation will:
    1. Query the database for the session by token
    2. Check if session is_valid is True
    3. Check if last_activity is within 30 minutes
    4. Update last_activity timestamp
    5. Return session data or None

    Args:
        token: Session token from Authorization header

    Returns:
        Session data dict with user_id and session_id, or None if invalid
    """
    # TODO: Implement actual database query in future task
    # from packages.database import models
    # from packages.security import auth as auth_service
    #
    # session = auth_service.validate_session(token)
    # if not session:
    #     return None
    #
    # # Check timeout (30 minutes)
    # timeout_minutes = current_app.config.get("SESSION_TIMEOUT_MINUTES", 30)
    # timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    # if session.last_activity < timeout_threshold:
    #     auth_service.invalidate_session(token)
    #     return None
    #
    # # Update last_activity
    # auth_service.update_session_activity(token)
    #
    # return {
    #     "user_id": session.user_id,
    #     "session_id": session.id
    # }

    # Placeholder: return None to indicate authentication not yet implemented
    logger.warning("Session validation not yet implemented - using placeholder")
    return None
