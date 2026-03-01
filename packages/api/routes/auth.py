"""Authentication API routes for user registration, login, and logout."""

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from packages.database import get_session
from packages.security import auth as auth_service

logger = logging.getLogger("hybrid_cloud.api.routes.auth")

# Create blueprint for authentication routes
bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user account.

    Validates: Requirements 12.1, 12.2

    Request Body:
        {
            "username": str,
            "password": str
        }

    Returns:
        201: User created successfully
        {
            "user_id": str,
            "username": str,
            "created_at": str (ISO format)
        }

        400: Validation error
        {
            "error_code": "VALIDATION_ERROR",
            "message": str,
            "timestamp": str (ISO format)
        }

        409: Username already exists
        {
            "error_code": "CONFLICT",
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

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                _error_response("VALIDATION_ERROR", "Username and password are required"),
                400,
            )

        # Get database session
        db = get_session()

        try:
            # Register user
            user = auth_service.register_user(db, username, password)

            logger.info(f"User registered successfully: {username}")

            return (
                jsonify(
                    {
                        "id": user.id,
                        "username": user.username,
                        "created_at": user.created_at.isoformat(),
                    }
                ),
                201,
            )

        except ValueError as e:
            # Username already exists or validation error
            error_msg = str(e)
            if "already exists" in error_msg:
                return _error_response("CONFLICT", error_msg), 409
            return _error_response("VALIDATION_ERROR", error_msg), 400

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during registration: {e}")
        return _error_response("DATABASE_ERROR", "Failed to register user"), 500

    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


@bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user and create session.

    Validates: Requirements 12.3

    Request Body:
        {
            "username": str,
            "password": str
        }

    Returns:
        200: Login successful
        {
            "session_token": str,
            "user_id": str,
            "created_at": str (ISO format)
        }

        400: Validation error
        {
            "error_code": "VALIDATION_ERROR",
            "message": str,
            "timestamp": str (ISO format)
        }

        401: Invalid credentials
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

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return (
                _error_response("VALIDATION_ERROR", "Username and password are required"),
                400,
            )

        # Get database session
        db = get_session()

        try:
            # Authenticate user and create session
            session = auth_service.authenticate(db, username, password)

            logger.info(f"User logged in successfully: {username}")

            return jsonify(
                {
                    "token": session.token,
                    "user_id": session.user_id,
                    "created_at": session.created_at.isoformat(),
                }
            )

        except ValueError:
            # Invalid credentials
            logger.warning(f"Login failed for username: {username}")
            return (
                _error_response("AUTHENTICATION_REQUIRED", "Invalid credentials"),
                401,
            )

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during login: {e}")
        return _error_response("DATABASE_ERROR", "Failed to authenticate user"), 500

    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


@bp.route("/logout", methods=["POST"])
def logout():
    """
    Invalidate user session (logout).

    Validates: Requirements 12.4

    Headers:
        Authorization: Bearer <session_token>

    Returns:
        200: Logout successful
        {
            "message": "Logged out successfully"
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
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return (
                _error_response("AUTHENTICATION_REQUIRED", "Missing authorization header"),
                401,
            )

        # Expect format: "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return (
                _error_response("AUTHENTICATION_REQUIRED", "Invalid authorization header format"),
                401,
            )

        token = parts[1]

        # Get database session
        db = get_session()

        try:
            # Invalidate session
            auth_service.invalidate_session(db, token)

            logger.info("User logged out successfully")

            return jsonify({"message": "Logged out successfully"})

        finally:
            db.close()

    except SQLAlchemyError as e:
        logger.error(f"Database error during logout: {e}")
        return _error_response("DATABASE_ERROR", "Failed to logout"), 500

    except Exception as e:
        logger.error(f"Unexpected error during logout: {e}")
        return _error_response("DATABASE_ERROR", "An unexpected error occurred"), 500


def _error_response(error_code: str, message: str) -> dict:
    """
    Create a consistent error response.

    Args:
        error_code: Machine-readable error code
        message: Human-readable error message

    Returns:
        Error response dictionary
    """
    return {
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
