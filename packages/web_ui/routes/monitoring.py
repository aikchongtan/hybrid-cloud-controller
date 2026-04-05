"""Monitoring routes for resource metrics dashboard."""

import logging
import os

import requests
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

logger = logging.getLogger("hybrid_cloud.web_ui.routes.monitoring")

# Create blueprint for monitoring routes
bp = Blueprint("monitoring", __name__)

# API base URL (should be from environment in production)
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")


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


@bp.route("/api/monitoring/resources", methods=["GET"])
def monitoring_resources():
    """
    Proxy endpoint for getting list of provisioned resources.
    
    GET: Forward resources request to API
    """
    token = session.get("token")
    if not token:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/monitoring/resources",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.Timeout:
        logger.error("API request timeout during resources retrieval")
        return jsonify({"error": "Request timeout"}), 504
    
    except requests.exceptions.ConnectionError:
        logger.error("API connection error during resources retrieval")
        return jsonify({"error": "Unable to connect to service"}), 503
    
    except Exception as e:
        logger.error(f"Unexpected error during resources retrieval: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@bp.route("/api/monitoring/<resource_id>/metrics", methods=["GET"])
def monitoring_metrics(resource_id: str):
    """
    Proxy endpoint for getting metrics for a specific resource.
    
    GET: Forward metrics request to API with optional time_range parameter
    """
    token = session.get("token")
    if not token:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        # Extract optional time_range query parameter
        time_range = request.args.get("time_range")
        
        # Build URL with time_range parameter if provided
        url = f"{API_BASE_URL}/api/monitoring/{resource_id}/metrics"
        if time_range:
            url += f"?time_range={time_range}"
        
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.Timeout:
        logger.error("API request timeout during metrics retrieval")
        return jsonify({"error": "Request timeout"}), 504
    
    except requests.exceptions.ConnectionError:
        logger.error("API connection error during metrics retrieval")
        return jsonify({"error": "Unable to connect to service"}), 503
    
    except Exception as e:
        logger.error(f"Unexpected error during metrics retrieval: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500
