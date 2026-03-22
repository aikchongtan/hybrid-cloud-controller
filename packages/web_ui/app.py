"""Flask application for Web UI."""

from flask import Flask, redirect, request


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configure secret key for sessions (should be from environment in production)
    app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"

    # Configure session cookies
    # For local development (HTTP), set SESSION_COOKIE_SECURE to False
    # In production with HTTPS, set to True
    app.config["SESSION_COOKIE_SECURE"] = False  # Changed for local development
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Force HTTPS redirect middleware (disabled for local development)
    @app.before_request
    def force_https():
        """Redirect HTTP requests to HTTPS."""
        # Disabled for local development - enable in production
        # if not request.is_secure and not app.debug:
        #     url = request.url.replace("http://", "https://", 1)
        #     return redirect(url, code=301)
        pass

    # Register routes
    from packages.web_ui import routes

    routes.register_routes(app)

    return app


if __name__ == "__main__":
    app = create_app()
    # Development server on port 10001 (API uses 10000)
    # For local testing, disable SSL (use ssl_context="adhoc" for HTTPS in production)
    app.run(host="0.0.0.0", port=10001, debug=True)
