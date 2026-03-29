"""Q&A routes for conversational assistance."""

import logging

import requests
from flask import Blueprint, flash, jsonify, redirect, request, session, url_for

logger = logging.getLogger("hybrid_cloud.web_ui.routes.qa")

# Create blueprint for Q&A routes
bp = Blueprint("qa", __name__)

# API base URL (should be from environment in production)
import os
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")


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


@bp.route("/api/qa/<config_id>/ask", methods=["POST"])
def ask_question(config_id: str):
    """
    Proxy endpoint for asking questions to the API.

    POST: Forward question to API and return response
    """
    # Get authentication token
    token = session.get("token")
    if not token:
        return jsonify({"error": "Authentication required"}), 401

    try:
        # Get question from request
        data = request.get_json()
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"error": "Question is required"}), 400

        # Forward to API
        response = requests.post(
            f"{API_BASE_URL}/api/qa/{config_id}/ask",
            json={"question": question},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            error_data = response.json()
            return jsonify(error_data), response.status_code

    except requests.exceptions.Timeout:
        logger.error("API request timeout during Q&A")
        return jsonify({"error": "Request timeout. Please try again."}), 504

    except requests.exceptions.ConnectionError:
        logger.error("API connection error during Q&A")
        return jsonify({"error": "Unable to connect to service"}), 503

    except Exception as e:
        logger.error(f"Unexpected error during Q&A: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@bp.route("/api/qa/<config_id>/history", methods=["GET"])
def get_history(config_id: str):
    """
    Proxy endpoint for getting conversation history from the API.

    GET: Forward request to API and return conversation history
    """
    # Get authentication token
    token = session.get("token")
    if not token:
        return jsonify({"error": "Authentication required"}), 401

    try:
        # Forward to API
        response = requests.get(
            f"{API_BASE_URL}/api/qa/{config_id}/history",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        if response.status_code == 200:
            return jsonify(response.json()), 200
        elif response.status_code == 404:
            # No history yet - return empty
            return jsonify({"messages": []}), 200
        else:
            error_data = response.json()
            return jsonify(error_data), response.status_code

    except requests.exceptions.Timeout:
        logger.error("API request timeout during history retrieval")
        return jsonify({"error": "Request timeout"}), 504

    except requests.exceptions.ConnectionError:
        logger.error("API connection error during history retrieval")
        return jsonify({"error": "Unable to connect to service"}), 503

    except Exception as e:
        logger.error(f"Unexpected error during history retrieval: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500
