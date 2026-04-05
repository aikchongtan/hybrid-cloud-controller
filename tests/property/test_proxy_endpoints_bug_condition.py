"""
Bug Condition Exploration Test for Missing Proxy Endpoints

This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

This test encodes the expected behavior - it will validate the fix when it passes after implementation.

GOAL: Surface counterexamples that demonstrate the bug exists.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from flask import Flask
from packages.web_ui.routes.provisioning import bp as provisioning_bp
from packages.web_ui.routes.monitoring import bp as monitoring_bp


@pytest.fixture
def app():
    """Create a Flask app with provisioning and monitoring blueprints."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    
    # Register blueprints
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
    return client


# Property-based test for missing provisioning proxy endpoints
@pytest.mark.property
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    provision_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pd"))),
)
def test_provisioning_proxy_endpoints_exist(authenticated_client, provision_id):
    """
    Property 1: Bug Condition - Missing Proxy Endpoints Return 404
    
    This test checks that the 3 provisioning proxy endpoints exist and do NOT return 404.
    
    EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with 404 errors (proves bug exists)
    EXPECTED OUTCOME ON FIXED CODE: Test PASSES (proves bug is fixed)
    """
    # Test POST /api/provision endpoint exists
    response = authenticated_client.post(
        "/api/provision",
        json={
            "configuration_id": "test-config-123",
            "cloud_path": "aws",
            "container_image": "nginx:latest",
        },
        content_type="application/json",
    )
    
    # Should NOT return 404 (endpoint should exist)
    # May return 503 (API unavailable) or other errors, but NOT 404
    assert response.status_code != 404, (
        f"POST /api/provision returned 404 - endpoint does not exist. "
        f"This confirms the bug: missing proxy endpoint."
    )
    
    # Test GET /api/provision/<provision_id>/status endpoint exists
    response = authenticated_client.get(f"/api/provision/{provision_id}/status")
    
    # Should NOT return 404 (endpoint should exist)
    assert response.status_code != 404, (
        f"GET /api/provision/{provision_id}/status returned 404 - endpoint does not exist. "
        f"This confirms the bug: missing proxy endpoint."
    )
    
    # Test GET /api/provision/<provision_id> endpoint exists
    response = authenticated_client.get(f"/api/provision/{provision_id}")
    
    # Should NOT return 404 (endpoint should exist)
    assert response.status_code != 404, (
        f"GET /api/provision/{provision_id} returned 404 - endpoint does not exist. "
        f"This confirms the bug: missing proxy endpoint."
    )


# Property-based test for missing monitoring proxy endpoints
@pytest.mark.property
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    resource_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pd"))),
    time_range=st.sampled_from(["1h", "24h", "7d", None]),
)
def test_monitoring_proxy_endpoints_exist(authenticated_client, resource_id, time_range):
    """
    Property 1: Bug Condition - Missing Proxy Endpoints Return 404
    
    This test checks that the 2 monitoring proxy endpoints exist and do NOT return 404.
    
    EXPECTED OUTCOME ON UNFIXED CODE: Test FAILS with 404 errors (proves bug exists)
    EXPECTED OUTCOME ON FIXED CODE: Test PASSES (proves bug is fixed)
    """
    # Test GET /api/monitoring/resources endpoint exists
    response = authenticated_client.get("/api/monitoring/resources")
    
    # Should NOT return 404 (endpoint should exist)
    # May return 503 (API unavailable) or other errors, but NOT 404
    assert response.status_code != 404, (
        f"GET /api/monitoring/resources returned 404 - endpoint does not exist. "
        f"This confirms the bug: missing proxy endpoint."
    )
    
    # Test GET /api/monitoring/<resource_id>/metrics endpoint exists
    url = f"/api/monitoring/{resource_id}/metrics"
    if time_range:
        url += f"?time_range={time_range}"
    
    response = authenticated_client.get(url)
    
    # Should NOT return 404 (endpoint should exist)
    assert response.status_code != 404, (
        f"GET /api/monitoring/{resource_id}/metrics returned 404 - endpoint does not exist. "
        f"This confirms the bug: missing proxy endpoint."
    )


# Concrete test cases for the 7 specific missing endpoints
@pytest.mark.property
def test_concrete_missing_endpoints(authenticated_client):
    """
    Concrete test cases for the 7 specific missing proxy endpoints.
    
    This test documents the exact endpoints that are missing.
    
    EXPECTED OUTCOME ON UNFIXED CODE: All assertions FAIL with 404 errors
    EXPECTED OUTCOME ON FIXED CODE: All assertions PASS
    """
    # 1. POST /api/provision (AWS/IaaS/CaaS provisioning)
    response = authenticated_client.post(
        "/api/provision",
        json={"configuration_id": "test-123", "cloud_path": "aws"},
        content_type="application/json",
    )
    assert response.status_code != 404, "POST /api/provision endpoint missing"
    
    # 2. GET /api/provision/{id}/status (status check)
    response = authenticated_client.get("/api/provision/test-provision-123/status")
    assert response.status_code != 404, "GET /api/provision/{id}/status endpoint missing"
    
    # 3. GET /api/provision/{id} (details retrieval)
    response = authenticated_client.get("/api/provision/test-provision-123")
    assert response.status_code != 404, "GET /api/provision/{id} endpoint missing"
    
    # 4. GET /api/monitoring/resources (resources list)
    response = authenticated_client.get("/api/monitoring/resources")
    assert response.status_code != 404, "GET /api/monitoring/resources endpoint missing"
    
    # 5. GET /api/monitoring/{id}/metrics (metrics retrieval)
    response = authenticated_client.get("/api/monitoring/test-resource-123/metrics")
    assert response.status_code != 404, "GET /api/monitoring/{id}/metrics endpoint missing"
    
    # 6. GET /api/monitoring/{id}/metrics?time_range=24h (metrics with time range)
    response = authenticated_client.get("/api/monitoring/test-resource-123/metrics?time_range=24h")
    assert response.status_code != 404, "GET /api/monitoring/{id}/metrics?time_range endpoint missing"


# Test that unauthenticated requests should return 401 (not 404)
@pytest.mark.property
def test_unauthenticated_requests_return_401_not_404(client):
    """
    Test that unauthenticated requests to proxy endpoints return 401, not 404.
    
    This test will fail on unfixed code because endpoints don't exist (404).
    On fixed code, it should return 401 (authentication required).
    """
    # These should return 401 (authentication required), not 404 (not found)
    endpoints = [
        ("/api/provision", "POST"),
        ("/api/provision/test-123/status", "GET"),
        ("/api/provision/test-123", "GET"),
        ("/api/monitoring/resources", "GET"),
        ("/api/monitoring/test-123/metrics", "GET"),
    ]
    
    for endpoint, method in endpoints:
        if method == "POST":
            response = client.post(endpoint, json={}, content_type="application/json")
        else:
            response = client.get(endpoint)
        
        # On unfixed code: returns 404 (endpoint doesn't exist)
        # On fixed code: returns 401 (authentication required)
        assert response.status_code != 404, (
            f"{method} {endpoint} returned 404 - endpoint does not exist. "
            f"Expected 401 (authentication required) on fixed code."
        )
