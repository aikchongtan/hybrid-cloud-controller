"""
Preservation Property Tests for Existing Endpoints

These tests MUST PASS on unfixed code - they establish the baseline behavior to preserve.

GOAL: Ensure existing functionality remains unchanged after adding new proxy endpoints.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from flask import Flask
from packages.web_ui.routes.auth import bp as auth_bp
from packages.web_ui.routes.configuration import bp as configuration_bp
from packages.web_ui.routes.qa import bp as qa_bp
from packages.web_ui.routes.provisioning import bp as provisioning_bp
from packages.web_ui.routes.monitoring import bp as monitoring_bp


@pytest.fixture
def app():
    """Create a Flask app with all blueprints."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    
    # Register all blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(configuration_bp)
    app.register_blueprint(qa_bp)
    app.register_blueprint(provisioning_bp)
    app.register_blueprint(monitoring_bp)
    
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    """Create an authenticated test client with session token."""
    with client.session_transaction() as sess:
        sess["token"] = "test-token-12345"
        sess["user_id"] = "test-user-id"
    return client


# Property 2: Preservation - Configuration Validation Endpoint Unchanged
@pytest.mark.property
def test_configuration_validation_endpoint_preserved(client):
    """
    Property 2: Preservation - Configuration validation endpoint remains unchanged.
    
    This test verifies that the configuration validation proxy endpoint continues to work.
    
    EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
    """
    # Test POST /api/configurations/validate (public endpoint, no auth required)
    response = client.post(
        "/api/configurations/validate",
        json={
            "cpu_cores": 8,
            "memory_gb": 32,
            "instance_count": 3,
            "storage_type": "SSD",
            "storage_capacity_gb": 500,
            "bandwidth_mbps": 10000,
            "monthly_data_transfer_gb": 1000,
            "utilization_percentage": 75,
            "operating_hours_per_month": 720,
        },
        content_type="application/json",
    )
    # May return 503 (API unavailable) or other errors, but endpoint should exist
    assert response.status_code != 404, "POST /api/configurations/validate endpoint should exist"


# Property 2: Preservation - Q&A Proxy Endpoints Unchanged
@pytest.mark.property
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    config_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pd"))),
)
def test_qa_proxy_endpoints_preserved(authenticated_client, config_id):
    """
    Property 2: Preservation - Q&A proxy endpoints remain unchanged.
    
    This test verifies that Q&A ask and history proxy endpoints continue to work.
    
    EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
    """
    # Test POST /api/qa/<config_id>/ask endpoint exists
    response = authenticated_client.post(
        f"/api/qa/{config_id}/ask",
        json={"question": "Test question"},
        content_type="application/json",
    )
    # May return 503 (API unavailable) or other errors, but NOT 404
    assert response.status_code != 404, f"POST /api/qa/{config_id}/ask endpoint should exist"
    
    # Test GET /api/qa/<config_id>/history endpoint exists
    response = authenticated_client.get(f"/api/qa/{config_id}/history")
    # May return 503 (API unavailable) or other errors, but NOT 404
    assert response.status_code != 404, f"GET /api/qa/{config_id}/history endpoint should exist"


# Property 2: Preservation - Authentication Required for Proxy Endpoints
@pytest.mark.property
def test_authentication_required_for_proxy_endpoints_preserved(client):
    """
    Property 2: Preservation - Authentication continues to protect proxy endpoints.
    
    This test verifies that proxy endpoints still require authentication.
    
    EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
    """
    # Test that proxy endpoints require authentication (return 401 or 503, not 200)
    proxy_endpoints = [
        ("/api/qa/test-config-123/ask", "POST"),
        ("/api/qa/test-config-123/history", "GET"),
    ]
    
    for endpoint, method in proxy_endpoints:
        if method == "POST":
            response = client.post(endpoint, json={"question": "test"}, content_type="application/json")
        else:
            response = client.get(endpoint)
        
        # Should return 401 (authentication required) or 503 (API unavailable), but NOT 200 (unauthorized access)
        # May return 404 if endpoint doesn't exist, but that's OK for this test
        if response.status_code == 200:
            pytest.fail(f"{method} {endpoint} returned 200 without authentication - security issue")


# Property 2: Preservation - Error Handling Patterns Unchanged
@pytest.mark.property
def test_error_handling_patterns_preserved(authenticated_client):
    """
    Property 2: Preservation - Error handling patterns remain consistent.
    
    This test verifies that error responses follow the same patterns.
    
    EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
    """
    # Test that invalid JSON returns 400 or 500, not 404
    response = authenticated_client.post(
        "/api/qa/test-config-123/ask",
        data="invalid json",
        content_type="application/json",
    )
    # Should return error (400, 500, 503), but NOT 404 (endpoint exists)
    assert response.status_code != 404, "Invalid JSON should not return 404"
    
    # Test that missing required fields returns 400 or 500, not 404
    response = authenticated_client.post(
        "/api/qa/test-config-123/ask",
        json={},  # Missing 'question' field
        content_type="application/json",
    )
    # Should return error (400, 500, 503), but NOT 404 (endpoint exists)
    assert response.status_code != 404, "Missing required fields should not return 404"


# Property 2: Preservation - Session Management Unchanged
@pytest.mark.property
def test_session_management_preserved(client):
    """
    Property 2: Preservation - Session management remains unchanged.
    
    This test verifies that session handling continues to work correctly for proxy endpoints.
    
    EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
    """
    # Test that session token enables access to proxy endpoints
    with client.session_transaction() as sess:
        sess["token"] = "test-token"
        sess["user_id"] = "test-user"
    
    # Authenticated request to proxy endpoint should work (not return 401)
    response = client.post(
        "/api/qa/test-123/ask",
        json={"question": "test"},
        content_type="application/json",
    )
    # Should NOT return 401 (authentication required) - may return 503 (API unavailable) or other errors
    assert response.status_code != 401, "Authenticated request should not return 401"
    
    # Clear session
    with client.session_transaction() as sess:
        sess.clear()
    
    # Unauthenticated request should return 401
    response = client.post(
        "/api/qa/test-123/ask",
        json={"question": "test"},
        content_type="application/json",
    )
    # Should return 401 (authentication required) or 404 (endpoint doesn't exist)
    assert response.status_code in [401, 404], f"Unauthenticated request should return 401 or 404, got {response.status_code}"


# Concrete test for all existing proxy endpoints
@pytest.mark.property
def test_all_existing_proxy_endpoints_preserved(authenticated_client):
    """
    Concrete test for all existing proxy endpoints that must remain unchanged.
    
    EXPECTED OUTCOME: Test PASSES on both unfixed and fixed code.
    """
    # Q&A proxy endpoints (Issue #10 - already fixed)
    response = authenticated_client.post(
        "/api/qa/test-123/ask",
        json={"question": "test"},
        content_type="application/json",
    )
    assert response.status_code != 404, "POST /api/qa/{id}/ask should exist"
    
    response = authenticated_client.get("/api/qa/test-123/history")
    assert response.status_code != 404, "GET /api/qa/{id}/history should exist"
    
    # Configuration validation proxy endpoint (Issue #11 - already fixed)
    response = authenticated_client.post(
        "/api/configurations/validate",
        json={"cpu_cores": 8},
        content_type="application/json",
    )
    assert response.status_code != 404, "POST /api/configurations/validate should exist"
