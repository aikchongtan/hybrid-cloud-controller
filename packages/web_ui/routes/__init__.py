"""Web UI routes package."""

from flask import Flask, render_template


def register_routes(app: Flask) -> None:
    """Register all web UI routes."""

    @app.route("/")
    def index():
        """Render the main landing page."""
        return render_template("index.html")

    # Register authentication blueprint
    from packages.web_ui.routes import auth

    app.register_blueprint(auth.bp)

    # Register configuration blueprint
    from packages.web_ui.routes import configuration

    app.register_blueprint(configuration.bp)

    # Register Q&A blueprint
    from packages.web_ui.routes import qa

    app.register_blueprint(qa.bp)

    # Register provisioning blueprint
    from packages.web_ui.routes import provisioning

    app.register_blueprint(provisioning.bp)

    # Register monitoring blueprint
    from packages.web_ui.routes import monitoring

    app.register_blueprint(monitoring.bp)
