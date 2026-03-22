"""Configuration routes for TCO analysis input."""

import logging

import requests
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

logger = logging.getLogger("hybrid_cloud.web_ui.routes.configuration")

# Create blueprint for configuration routes
bp = Blueprint("configuration", __name__)

# API base URL (should be from environment in production)
# Use 'api' hostname for Docker, 'localhost' for local development
import os
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")


@bp.route("/configuration", methods=["GET"])
def configuration_input():
    """
    Render the configuration input page.

    GET: Display configuration form with all required fields

    Validates: Requirements 1.1, 1.2, 1.3, 1.4
    """
    return render_template("configuration.html")


@bp.route("/configuration", methods=["POST"])
def submit_configuration():
    """
    Handle configuration form submission.

    POST: Validate and submit configuration to API, then redirect to TCO results

    Validates: Requirements 1.5, 1.6
    """
    # Get authentication token
    token = session.get("token")
    if not token:
        flash("Please log in to submit a configuration", "danger")
        return redirect(url_for("auth.login"))

    # Extract form data
    try:
        cpu_cores = int(request.form.get("cpu_cores", 0))
    except (ValueError, TypeError):
        cpu_cores = None

    try:
        memory_gb = int(request.form.get("memory_gb", 0))
    except (ValueError, TypeError):
        memory_gb = None

    try:
        instance_count = int(request.form.get("instance_count", 0))
    except (ValueError, TypeError):
        instance_count = None

    storage_type = request.form.get("storage_type", "").upper()

    try:
        storage_capacity_gb = int(request.form.get("storage_capacity_gb", 0))
    except (ValueError, TypeError):
        storage_capacity_gb = None

    storage_iops_str = request.form.get("storage_iops", "").strip()
    if storage_iops_str:
        try:
            storage_iops = int(storage_iops_str)
        except (ValueError, TypeError):
            storage_iops = None
    else:
        storage_iops = None

    try:
        bandwidth_mbps = int(request.form.get("bandwidth_mbps", 0))
    except (ValueError, TypeError):
        bandwidth_mbps = None

    try:
        monthly_data_transfer_gb = int(request.form.get("monthly_data_transfer_gb", 0))
    except (ValueError, TypeError):
        monthly_data_transfer_gb = None

    try:
        utilization_percentage = int(request.form.get("utilization_percentage", 0))
    except (ValueError, TypeError):
        utilization_percentage = None

    try:
        operating_hours_per_month = int(request.form.get("operating_hours_per_month", 0))
    except (ValueError, TypeError):
        operating_hours_per_month = None

    # Build configuration payload
    config_data = {
        "cpu_cores": cpu_cores,
        "memory_gb": memory_gb,
        "instance_count": instance_count,
        "storage_type": storage_type,
        "storage_capacity_gb": storage_capacity_gb,
        "storage_iops": storage_iops,
        "bandwidth_mbps": bandwidth_mbps,
        "monthly_data_transfer_gb": monthly_data_transfer_gb,
        "utilization_percentage": utilization_percentage,
        "operating_hours_per_month": operating_hours_per_month,
    }

    try:
        # Call API to create configuration
        response = requests.post(
            f"{API_BASE_URL}/api/configurations",
            json=config_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        if response.status_code == 201:
            # Configuration created successfully
            data = response.json()
            config_id = data["id"]

            logger.info(f"Configuration created successfully: {config_id}")
            flash("Configuration saved successfully!", "success")

            # Store config_id in session for later use
            session["config_id"] = config_id

            # Redirect to TCO results page
            return redirect(url_for("configuration.tco_results", config_id=config_id))

        elif response.status_code == 400:
            # Validation error
            error_data = response.json()
            details = error_data.get("details", {})

            # Display field-specific errors
            if details:
                for field, error_msg in details.items():
                    flash(f"{field.replace('_', ' ').title()}: {error_msg}", "danger")
            else:
                flash(error_data.get("message", "Validation failed"), "danger")

            # Re-render form with submitted data
            return render_template("configuration.html", form_data=request.form)

        elif response.status_code == 401:
            # Authentication required
            flash("Your session has expired. Please log in again.", "danger")
            return redirect(url_for("auth.login"))

        else:
            # Other error
            error_data = response.json()
            error_msg = error_data.get("message", "Failed to save configuration")
            flash(f"Error: {error_msg}", "danger")
            return render_template("configuration.html", form_data=request.form)

    except requests.exceptions.Timeout:
        logger.error("API request timeout during configuration submission")
        flash("Request timeout. Please try again.", "danger")
        return render_template("configuration.html", form_data=request.form)

    except requests.exceptions.ConnectionError:
        logger.error("API connection error during configuration submission")
        flash("Unable to connect to the service. Please try again later.", "danger")
        return render_template("configuration.html", form_data=request.form)

    except Exception as e:
        logger.error(f"Unexpected error during configuration submission: {e}")
        flash("An unexpected error occurred. Please try again.", "danger")
        return render_template("configuration.html", form_data=request.form)


@bp.route("/tco/results/<config_id>", methods=["GET"])
def tco_results(config_id: str):
    """
    Display TCO results for a configuration.

    GET: Display side-by-side comparison of on-premises vs AWS costs

    Validates: Requirements 2.4, 2.5
    """
    # Get authentication token
    token = session.get("token")
    if not token:
        flash("Please log in to view TCO results", "danger")
        return redirect(url_for("auth.login"))

    try:
        # First, try to get existing TCO results
        response = requests.get(
            f"{API_BASE_URL}/api/tco/{config_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        tco_data = None
        if response.status_code == 200:
            # TCO results exist
            data = response.json()
            tco_data = {
                "id": data["id"],
                "configuration_id": data["configuration_id"],
                "on_prem_costs": data["on_prem_costs"],
                "aws_costs": data["aws_costs"],
                "recommendation": data.get("recommendation"),
                "calculated_at": data["calculated_at"],
            }
            logger.info(f"TCO results retrieved for config: {config_id}")

        elif response.status_code == 404:
            # TCO not calculated yet - trigger calculation
            logger.info(f"TCO not found for config {config_id}, triggering calculation")

            calc_response = requests.post(
                f"{API_BASE_URL}/api/tco/{config_id}/calculate",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )

            if calc_response.status_code == 200:
                # Calculation successful
                data = calc_response.json()
                tco_data = {
                    "id": data["id"],
                    "configuration_id": data["configuration_id"],
                    "on_prem_costs": data["on_prem_costs"],
                    "aws_costs": data["aws_costs"],
                    "recommendation": data.get("recommendation"),
                    "calculated_at": data["calculated_at"],
                }
                logger.info(f"TCO calculated successfully for config: {config_id}")
                flash("TCO calculation completed successfully!", "success")

            elif calc_response.status_code == 401:
                flash("Your session has expired. Please log in again.", "danger")
                return redirect(url_for("auth.login"))

            else:
                error_data = calc_response.json()
                error_msg = error_data.get("message", "Failed to calculate TCO")
                flash(f"Error: {error_msg}", "danger")
                logger.error(f"TCO calculation failed: {error_msg}")

        elif response.status_code == 401:
            flash("Your session has expired. Please log in again.", "danger")
            return redirect(url_for("auth.login"))

        else:
            error_data = response.json()
            error_msg = error_data.get("message", "Failed to retrieve TCO results")
            flash(f"Error: {error_msg}", "danger")
            logger.error(f"Failed to retrieve TCO results: {error_msg}")

        # Render TCO results page
        return render_template("tco_results.html", tco_data=tco_data, config_id=config_id)

    except requests.exceptions.Timeout:
        logger.error("API request timeout during TCO retrieval")
        flash("Request timeout. Please try again.", "danger")
        return render_template("tco_results.html", tco_data=None, config_id=config_id)

    except requests.exceptions.ConnectionError:
        logger.error("API connection error during TCO retrieval")
        flash("Unable to connect to the service. Please try again later.", "danger")
        return render_template("tco_results.html", tco_data=None, config_id=config_id)

    except Exception as e:
        logger.error(f"Unexpected error during TCO retrieval: {e}")
        flash("An unexpected error occurred. Please try again.", "danger")
        return render_template("tco_results.html", tco_data=None, config_id=config_id)
