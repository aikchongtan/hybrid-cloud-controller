"""Flask application setup for Hybrid Cloud Controller API."""

import logging
import os
from typing import Any, Optional

from flask import Flask, request
from werkzeug.exceptions import HTTPException

from packages.api.middleware import auth, error_handler, https_enforcement
from packages.database import create_tables, get_session, init_database
from packages.database.models import ResourceModel
from packages.monitoring import collector

# Configure logging
logger = logging.getLogger("hybrid_cloud.api")

# Global variable to store the monitoring collection thread
_monitoring_thread = None


def _start_monitoring_collection() -> None:
    """
    Start background monitoring metrics collection for all resources.

    This function starts a daemon thread that collects metrics every 30 seconds
    for all provisioned resources in the database.
    """
    global _monitoring_thread

    try:
        # Get database session
        db = get_session()

        try:
            # Get all resource IDs
            resources = db.query(ResourceModel).all()
            resource_ids = [resource.id for resource in resources]

            if not resource_ids:
                logger.info("No resources found, skipping monitoring collection startup")
                return

            logger.info(f"Starting monitoring collection for {len(resource_ids)} resources...")

            # Start the collection thread (30 second interval)
            _monitoring_thread = collector.start_collection(
                resource_ids=resource_ids, db_session=db, interval_seconds=30
            )

            logger.info("Monitoring collection started successfully (30s interval)")

        finally:
            # Note: We don't close the session here because the collector thread needs it
            pass

    except Exception as e:
        logger.error(f"Failed to start monitoring collection: {e}", exc_info=True)
        # Don't fail app startup if monitoring collection fails
        logger.warning("Continuing without monitoring collection")


def create_app(config: Optional[dict[str, Any]] = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Default configuration - load from environment variables
    app.config.update(
        {
            "SECRET_KEY": os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
            "REQUIRE_HTTPS": os.getenv("REQUIRE_HTTPS", "true").lower() == "true",
            "SESSION_TIMEOUT_MINUTES": int(os.getenv("SESSION_TIMEOUT_MINUTES", "30")),
        }
    )

    # Apply custom configuration if provided
    if config:
        app.config.update(config)

    # Initialize database
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        logger.info("Initializing database...")
        init_database(database_url)
        create_tables()
        logger.info("Database initialized successfully")

        # Start monitoring metrics collection
        _start_monitoring_collection()

    # Register middleware
    _register_middleware(app)

    # Register error handlers
    _register_error_handlers(app)

    # Register blueprints
    from packages.api.routes import auth as auth_routes
    from packages.api.routes import configurations, monitoring, provisioning, qa, tco

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(configurations.bp)
    app.register_blueprint(tco.bp)
    app.register_blueprint(provisioning.bp)
    app.register_blueprint(qa.bp)
    app.register_blueprint(monitoring.bp)

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
