"""Monitoring routes for resource metrics dashboard."""

import logging

from flask import Blueprint, flash, redirect, render_template, session, url_for

logger = logging.getLogger("hybrid_cloud.web_ui.routes.monitoring")

# Create blueprint for monitoring routes
bp = Blueprint("monitoring", __name__)


@bp.route("/monitoring", methods=["GET"])
def monitoring_dashboard():
    """
    Render monitoring dashboard page showing all resources.

    GET: Display monitoring dashboard with metrics for all provisioned resources

    Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 11.11
    """
    # Get authentication token
    token = session.get("token")
    if not token:
        flash("Please log in to access monitoring", "danger")
        return redirect(url_for("auth.login"))

    logger.info("Rendering monitoring dashboard")

    return render_template("monitoring.html")


@bp.route("/monitoring/<resource_id>", methods=["GET"])
def monitoring_resource(resource_id: str):
    """
    Render monitoring dashboard page for a specific resource.

    GET: Display monitoring dashboard with metrics for a single resource

    Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8
    """
    # Get authentication token
    token = session.get("token")
    if not token:
        flash("Please log in to access monitoring", "danger")
        return redirect(url_for("auth.login"))

    logger.info(f"Rendering monitoring dashboard for resource {resource_id}")

    return render_template("monitoring.html", resource_id=resource_id)
