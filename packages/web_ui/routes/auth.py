"""Authentication routes for login and registration."""

import logging

import requests
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

logger = logging.getLogger("hybrid_cloud.web_ui.routes.auth")

# Create blueprint for authentication routes
bp = Blueprint("auth", __name__)

# API base URL (should be from environment in production)
API_BASE_URL = "http://localhost:8000"


@bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Handle login page and form submission.

    GET: Render login form
    POST: Submit credentials to API and create session

    Validates: Requirements 12.1, 12.3
    """
    if request.method == "GET":
        return render_template("auth/login.html")

    # Handle POST - form submission
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # Client-side validation
    if not username or not password:
        flash("Username and password are required", "danger")
        return render_template("auth/login.html")

    try:
        # Call API login endpoint
        response = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )

        if response.status_code == 200:
            # Login successful
            data = response.json()
            session["token"] = data["token"]
            session["user_id"] = data["user_id"]
            session.permanent = False  # Session expires when browser closes

            logger.info(f"User logged in successfully: {username}")
            flash("Login successful! Welcome back.", "success")

            # Redirect to home page
            return redirect(url_for("index"))

        elif response.status_code == 401:
            # Invalid credentials
            flash("Invalid username or password", "danger")
            return render_template("auth/login.html")

        else:
            # Other error
            error_data = response.json()
            error_msg = error_data.get("message", "Login failed")
            flash(f"Login failed: {error_msg}", "danger")
            return render_template("auth/login.html")

    except requests.exceptions.Timeout:
        logger.error("API request timeout during login")
        flash("Request timeout. Please try again.", "danger")
        return render_template("auth/login.html")

    except requests.exceptions.ConnectionError:
        logger.error("API connection error during login")
        flash("Unable to connect to authentication service", "danger")
        return render_template("auth/login.html")

    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        flash("An unexpected error occurred. Please try again.", "danger")
        return render_template("auth/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Handle registration page and form submission.

    GET: Render registration form
    POST: Submit credentials to API and create user account

    Validates: Requirements 12.1, 12.2
    """
    if request.method == "GET":
        return render_template("auth/register.html")

    # Handle POST - form submission
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Client-side validation
    if not username or not password or not confirm_password:
        flash("All fields are required", "danger")
        return render_template("auth/register.html")

    if len(password) < 8:
        flash("Password must be at least 8 characters long", "danger")
        return render_template("auth/register.html")

    if password != confirm_password:
        flash("Passwords do not match", "danger")
        return render_template("auth/register.html")

    try:
        # Call API register endpoint
        response = requests.post(
            f"{API_BASE_URL}/api/auth/register",
            json={"username": username, "password": password},
            timeout=10,
        )

        if response.status_code == 201:
            # Registration successful
            logger.info(f"User registered successfully: {username}")
            flash(
                "Registration successful! Please log in with your credentials.",
                "success",
            )

            # Redirect to login page
            return redirect(url_for("auth.login"))

        elif response.status_code == 409:
            # Username already exists
            flash("Username already exists. Please choose a different username.", "danger")
            return render_template("auth/register.html")

        else:
            # Other error
            error_data = response.json()
            error_msg = error_data.get("message", "Registration failed")
            flash(f"Registration failed: {error_msg}", "danger")
            return render_template("auth/register.html")

    except requests.exceptions.Timeout:
        logger.error("API request timeout during registration")
        flash("Request timeout. Please try again.", "danger")
        return render_template("auth/register.html")

    except requests.exceptions.ConnectionError:
        logger.error("API connection error during registration")
        flash("Unable to connect to authentication service", "danger")
        return render_template("auth/register.html")

    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        flash("An unexpected error occurred. Please try again.", "danger")
        return render_template("auth/register.html")


@bp.route("/logout", methods=["POST"])
def logout():
    """
    Handle logout request.

    POST: Invalidate session and redirect to home page

    Validates: Requirements 12.4
    """
    token = session.get("token")

    if token:
        try:
            # Call API logout endpoint
            requests.post(
                f"{API_BASE_URL}/api/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Error during logout API call: {e}")
            # Continue with local session cleanup even if API call fails

    # Clear session
    session.clear()

    flash("You have been logged out successfully.", "info")
    return redirect(url_for("index"))
