"""Q&A routes for conversational assistance."""

import logging

from flask import Blueprint, flash, redirect, session, url_for

logger = logging.getLogger("hybrid_cloud.web_ui.routes.qa")

# Create blueprint for Q&A routes
bp = Blueprint("qa", __name__)


@bp.route("/qa/<config_id>", methods=["GET"])
def qa_interface(config_id: str):
    """
    Render Q&A interface for a configuration.

    GET: Display Q&A chat interface

    Validates: Requirements 4.1, 4.5
    """
    from flask import render_template

    # Get authentication token
    token = session.get("token")
    if not token:
        flash("Please log in to access Q&A", "danger")
        return redirect(url_for("auth.login"))

    # Render Q&A chat interface
    return render_template("qa.html", config_id=config_id)
