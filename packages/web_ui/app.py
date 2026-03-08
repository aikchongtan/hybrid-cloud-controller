"""Flask application for Web UI."""

from flask import Flask, redirect, request


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configure secret key for sessions (should be from environment in production)
    app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"

    # Configure HTTPS-only serving (Requirement 12.10)
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Force HTTPS redirect middleware
    @app.before_request
    def force_https():
        """Redirect HTTP requests to HTTPS."""
        if not request.is_secure and not app.debug:
            url = request.url.replace("http://", "https://", 1)
            return redirect(url, code=301)

    # Register routes
    from packages.web_ui import routes

    routes.register_routes(app)

    return app


if __name__ == "__main__":
    app = create_app()
    # Development server on port 10000 or higher
    # In production, use a proper WSGI server with SSL certificates
    app.run(host="0.0.0.0", port=10000, debug=True, ssl_context="adhoc")
