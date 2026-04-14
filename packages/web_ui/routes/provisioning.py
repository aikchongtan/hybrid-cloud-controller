"""Provisioning routes for cloud path selection and resource provisioning."""

import logging
import os

import requests
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

logger = logging.getLogger("hybrid_cloud.web_ui.routes.provisioning")

# Create blueprint for provisioning routes
bp = Blueprint("provisioning", __name__)

# API base URL (should be from environment in production)
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")


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


@bp.route("/api/provision", methods=["POST"])
def provision():
    """
    Proxy endpoint for starting provisioning (AWS, IaaS, or CaaS).

    POST: Forward provisioning request to API
    """
    token = session.get("token")
    if not token:
        return jsonify({"error": "Authentication required"}), 401

    try:
        data = request.get_json()

        response = requests.post(
            f"{API_BASE_URL}/api/provision",
            json=data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

        return jsonify(response.json()), response.status_code

    except requests.exceptions.Timeout:
        logger.error("API request timeout during provisioning")
        return jsonify({"error": "Request timeout"}), 504

    except requests.exceptions.ConnectionError:
        logger.error("API connection error during provisioning")
        return jsonify({"error": "Unable to connect to service"}), 503

    except Exception as e:
        logger.error(f"Unexpected error during provisioning: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@bp.route("/api/provision/<provision_id>/status", methods=["GET"])
def provision_status(provision_id: str):
    """
    Proxy endpoint for checking provisioning status.

    GET: Forward status request to API
    """
    token = session.get("token")
    if not token:
        return jsonify({"error": "Authentication required"}), 401

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/provision/{provision_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        return jsonify(response.json()), response.status_code

    except requests.exceptions.Timeout:
        logger.error("API request timeout during status check")
        return jsonify({"error": "Request timeout"}), 504

    except requests.exceptions.ConnectionError:
        logger.error("API connection error during status check")
        return jsonify({"error": "Unable to connect to service"}), 503

    except Exception as e:
        logger.error(f"Unexpected error during status check: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@bp.route("/api/provision/<provision_id>", methods=["GET"])
def provision_details(provision_id: str):
    """
    Proxy endpoint for getting provisioning details.

    GET: Forward details request to API
    """
    token = session.get("token")
    if not token:
        return jsonify({"error": "Authentication required"}), 401

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/provision/{provision_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        return jsonify(response.json()), response.status_code

    except requests.exceptions.Timeout:
        logger.error("API request timeout during details retrieval")
        return jsonify({"error": "Request timeout"}), 504

    except requests.exceptions.ConnectionError:
        logger.error("API connection error during details retrieval")
        return jsonify({"error": "Unable to connect to service"}), 503

    except Exception as e:
        logger.error(f"Unexpected error during details retrieval: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500
