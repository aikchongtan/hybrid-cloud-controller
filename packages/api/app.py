"""Flask application setup for Hybrid Cloud Controller API."""

import logging
from typing import Any

from flask import Flask, request
from werkzeug.exceptions import HTTPException

from packages.api.middleware import auth, error_handler, https_enforcement

# Configure logging
logger = logging.getLogger("hybrid_cloud.api")


def create_app(config: dict[str, Any] | None = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Default configuration
    app.config.update(
        {
            "SECRET_KEY": "dev-secret-key-change-in-production",
            "REQUIRE_HTTPS": True,
            "SESSION_TIMEOUT_MINUTES": 30,
        }
    )

    # Apply custom configuration if provided
    if config:
        app.config.update(config)

    # Register middleware
    _register_middleware(app)

    # Register error handlers
    _register_error_handlers(app)

    # Register blueprints
    from packages.api.routes import auth as auth_routes

    app.register_blueprint(auth_routes.bp)
    # Additional routes will be added in future tasks:
    # from packages.api.routes import configuration, tco, provisioning, qa, monitoring
    # app.register_blueprint(configuration.bp)
    # app.register_blueprint(tco.bp)
    # app.register_blueprint(provisioning.bp)
    # app.register_blueprint(qa.bp)
    # app.register_blueprint(monitoring.bp)

    logger.info("Flask application created successfully")
    return app


def _register_middleware(app: Flask) -> None:
    """Register middleware functions."""
    # HTTPS enforcement (must be first)
    if app.config.get("REQUIRE_HTTPS", True):
        app.before_request(https_enforcement.enforce_https)

    # Authentication middleware (checks session tokens)
    app.before_request(auth.authenticate_request)

    # Request logging
    @app.before_request
    def log_request() -> None:
        logger.info(
            f"Request: {request.method} {request.path}",
            extra={"remote_addr": request.remote_addr},
        )


def _register_error_handlers(app: Flask) -> None:
    """Register error handlers for consistent error responses."""

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException) -> tuple[dict[str, Any], int]:
        """Handle HTTP exceptions."""
        return error_handler.handle_http_error(e)

    @app.errorhandler(Exception)
    def handle_generic_exception(e: Exception) -> tuple[dict[str, Any], int]:
        """Handle all other exceptions."""
        return error_handler.handle_generic_error(e)


if __name__ == "__main__":
    # Development server (not for production)
    app = create_app({"REQUIRE_HTTPS": False})  # Disable HTTPS for local dev
    app.run(host="0.0.0.0", port=10000, debug=True)
