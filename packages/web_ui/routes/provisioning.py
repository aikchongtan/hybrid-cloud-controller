"""Provisioning routes for cloud path selection and resource provisioning."""

import logging

from flask import Blueprint, flash, redirect, render_template, session, url_for

logger = logging.getLogger("hybrid_cloud.web_ui.routes.provisioning")

# Create blueprint for provisioning routes
bp = Blueprint("provisioning", __name__)


@bp.route("/provision/<config_id>", methods=["GET"])
def provision_page(config_id: str):
    """
    Render provisioning page for cloud path selection.

    GET: Display cloud path selection and provisioning options

    Validates: Requirements 5.1, 5.2, 5.6, 11.1, 11.4, 11.5, 11.6, 11.8, 11.10
    """
    # Get authentication token
    token = session.get("token")
    if not token:
        flash("Please log in to access provisioning", "danger")
        return redirect(url_for("auth.login"))

    # Store config_id in session for easy access
    session["config_id"] = config_id

    logger.info(f"Rendering provisioning page for configuration {config_id}")

    return render_template("provisioning.html", config_id=config_id)
