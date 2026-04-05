# UAT Proxy Endpoints Fix - Bugfix Design

## Overview

This bugfix addresses missing proxy endpoints in the Web UI layer that prevent the frontend from communicating with the API service for provisioning and monitoring features. The application uses a two-tier architecture where the Web UI (port 10001) serves HTML pages and must forward API requests to the API service (port 10000). When proxy endpoints are missing, JavaScript API calls fail with authentication/CORS errors.

The fix involves adding 7 proxy endpoints across two Web UI route files:
- 5 endpoints in `packages/web_ui/routes/provisioning.py` (AWS, IaaS, CaaS provisioning + status + details)
- 2 endpoints in `packages/web_ui/routes/monitoring.py` (resources list + metrics)

This follows the same pattern as previously fixed Issues #10 (Q&A) and #11 (configuration validation), where proxy endpoints forward authenticated requests from the browser to the API service.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when JavaScript makes API calls for provisioning or monitoring operations
- **Property (P)**: The desired behavior - requests should be forwarded to the API service with authentication and responses returned to the browser
- **Preservation**: Existing proxy endpoints (Q&A, configuration validation, authentication) that must remain unchanged by the fix
- **Proxy Endpoint**: A Web UI route that forwards requests to the API service with authentication tokens
- **API Service**: The backend service running on port 10000 that handles business logic
- **Web UI Service**: The frontend service running on port 10001 that serves HTML and proxies API requests
- **LocalStack**: AWS emulator used for testing cloud provisioning features

## Bug Details

### Bug Condition

The bug manifests when JavaScript code in the browser attempts to make API calls for provisioning or monitoring operations. The Web UI service receives these requests but has no endpoints to handle them, resulting in 404 errors or authentication failures.

**Formal Specification:**
```
FUNCTION isBugCondition(request)
  INPUT: request of type HTTPRequest
  OUTPUT: boolean
  
  RETURN (request.path == "/api/provision" AND request.method == "POST")
         OR (request.path MATCHES "/api/provision/{id}/status" AND request.method == "GET")
         OR (request.path MATCHES "/api/provision/{id}" AND request.method == "GET")
         OR (request.path == "/api/monitoring/resources" AND request.method == "GET")
         OR (request.path MATCHES "/api/monitoring/{id}/metrics" AND request.method == "GET")
         AND NOT endpointExists(request.path, request.method)
END FUNCTION
```

### Examples

**Provisioning Examples:**
- User submits AWS provisioning request → JavaScript calls `POST /api/provision` → Web UI returns 404 (endpoint doesn't exist)
- User checks provisioning status → JavaScript calls `GET /api/provision/{id}/status` → Web UI returns 404
- User retrieves provisioning details → JavaScript calls `GET /api/provision/{id}` → Web UI returns 404

**Monitoring Examples:**
- Dashboard loads and requests resource list → JavaScript calls `GET /api/monitoring/resources` → Web UI returns 404
- Dashboard requests metrics for a resource → JavaScript calls `GET /api/monitoring/{id}/metrics` → Web UI returns 404
- Dashboard requests metrics with time range → JavaScript calls `GET /api/monitoring/{id}/metrics?time_range=24h` → Web UI returns 404 (time_range parameter not forwarded)

**Edge Cases:**
- User not authenticated → Should return 401 (authentication required)
- API service unavailable → Should return 503 (service unavailable)
- API request timeout → Should return 504 (gateway timeout)
- Invalid provision/resource ID → Should return 404 from API (forwarded correctly)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Existing proxy endpoints (Q&A, configuration validation) must continue to work exactly as before
- Authentication middleware must continue to protect all authenticated endpoints
- Error handling patterns (timeouts, connection errors) must remain consistent
- HTML page rendering endpoints must remain unchanged
- Session management and token handling must remain unchanged

**Scope:**
All requests that do NOT involve the 7 missing proxy endpoints should be completely unaffected by this fix. This includes:
- Authentication endpoints (login, logout, register)
- Configuration endpoints (create, validate, retrieve)
- TCO calculation endpoints
- Q&A endpoints (ask, history)
- Static file serving
- HTML page rendering

## Hypothesized Root Cause

Based on the bug description and codebase analysis, the root cause is clear:

1. **Incomplete Implementation**: The Web UI route files were created with only HTML rendering endpoints, but proxy endpoints for API forwarding were never added for provisioning and monitoring features.

2. **Architectural Pattern Not Applied**: The application follows a proxy pattern (demonstrated in Q&A and configuration routes), but this pattern was not applied to provisioning and monitoring routes.

3. **Development Oversight**: The provisioning and monitoring features were likely developed with focus on the API layer, but the Web UI proxy layer was not completed.

4. **No Fallback Mechanism**: JavaScript makes direct API calls expecting the Web UI to proxy them, but there's no fallback or error handling when endpoints are missing.

## Correctness Properties

Property 1: Bug Condition - Proxy Endpoints Forward Requests

_For any_ HTTP request where the bug condition holds (request targets a missing proxy endpoint), the fixed Web UI SHALL forward the request to the API service with the user's authentication token, handle the API response, and return the result to the browser with appropriate status codes and error handling.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8**

Property 2: Preservation - Existing Endpoints Unchanged

_For any_ HTTP request that does NOT target the 7 new proxy endpoints, the fixed Web UI SHALL produce exactly the same behavior as the original code, preserving all existing functionality for authentication, configuration, TCO, Q&A, and static file serving.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

## Fix Implementation

### Changes Required

**File 1**: `packages/web_ui/routes/provisioning.py`

**Current State**: Only has `GET /provision/<config_id>` endpoint for rendering HTML page

**Required Changes**: Add 5 proxy endpoints following the pattern from `qa.py` and `configuration.py`

**Specific Changes**:

1. **Add imports at top of file**:
   ```python
   import os
   import requests
   from flask import jsonify, request
   
   API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")
   ```

2. **Add POST /api/provision endpoint** (unified provisioning for all cloud paths):
   - Accepts JSON body with `configuration_id`, `cloud_path`, `container_image`, `environment_vars`, `mock_mode`
   - Validates authentication (session token required)
   - Forwards to `POST {API_BASE_URL}/api/provision` with Authorization header
   - Returns API response (201 on success, 400/401/404/500 on error)
   - Handles timeouts (504), connection errors (503), and unexpected errors (500)

3. **Add GET /api/provision/<provision_id>/status endpoint**:
   - Accepts provision_id path parameter
   - Validates authentication (session token required)
   - Forwards to `GET {API_BASE_URL}/api/provision/{provision_id}/status` with Authorization header
   - Returns API response (200 on success, 401/404/500 on error)
   - Handles timeouts (504), connection errors (503), and unexpected errors (500)

4. **Add GET /api/provision/<provision_id> endpoint**:
   - Accepts provision_id path parameter
   - Validates authentication (session token required)
   - Forwards to `GET {API_BASE_URL}/api/provision/{provision_id}` with Authorization header
   - Returns API response (200 on success, 401/404/500 on error)
   - Handles timeouts (504), connection errors (503), and unexpected errors (500)

**File 2**: `packages/web_ui/routes/monitoring.py`

**Current State**: Only has `GET /monitoring` and `GET /monitoring/<resource_id>` endpoints for rendering HTML pages

**Required Changes**: Add 2 proxy endpoints following the same pattern

**Specific Changes**:

1. **Add imports at top of file**:
   ```python
   import os
   import requests
   from flask import jsonify, request
   
   API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")
   ```

2. **Add GET /api/monitoring/resources endpoint**:
   - No path parameters
   - Validates authentication (session token required)
   - Forwards to `GET {API_BASE_URL}/api/monitoring/resources` with Authorization header
   - Returns API response with list of resources (200 on success, 401/500 on error)
   - Handles timeouts (504), connection errors (503), and unexpected errors (500)

3. **Add GET /api/monitoring/<resource_id>/metrics endpoint**:
   - Accepts resource_id path parameter
   - Accepts optional time_range query parameter (1h, 24h, 7d)
   - Validates authentication (session token required)
   - Forwards to `GET {API_BASE_URL}/api/monitoring/{resource_id}/metrics?time_range={time_range}` with Authorization header
   - CRITICAL: Must forward time_range query parameter to API
   - Returns API response with metrics data (200 on success, 400/401/404/500 on error)
   - Handles timeouts (504), connection errors (503), and unexpected errors (500)

### Error Handling Pattern

All proxy endpoints must follow this consistent error handling pattern (from existing proxy endpoints):

```python
try:
    # Forward request to API
    response = requests.post/get(
        f"{API_BASE_URL}/api/...",
        json=data,  # For POST requests
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,  # 30s for POST, 10s for GET
    )
    
    # Return API response as-is
    return jsonify(response.json()), response.status_code
    
except requests.exceptions.Timeout:
    logger.error("API request timeout during ...")
    return jsonify({"error": "Request timeout"}), 504

except requests.exceptions.ConnectionError:
    logger.error("API connection error during ...")
    return jsonify({"error": "Unable to connect to service"}), 503

except Exception as e:
    logger.error(f"Unexpected error during ...: {e}")
    return jsonify({"error": "An unexpected error occurred"}), 500
```

### Authentication Pattern

All proxy endpoints must validate authentication before forwarding:

```python
token = session.get("token")
if not token:
    return jsonify({"error": "Authentication required"}), 401
```

### Request Forwarding Pattern

**For POST requests** (provisioning):
```python
data = request.get_json()
response = requests.post(
    f"{API_BASE_URL}/api/provision",
    json=data,
    headers={"Authorization": f"Bearer {token}"},
    timeout=30,
)
```

**For GET requests** (status, details, resources):
```python
response = requests.get(
    f"{API_BASE_URL}/api/provision/{provision_id}/status",
    headers={"Authorization": f"Bearer {token}"},
    timeout=10,
)
```

**For GET requests with query parameters** (metrics with time_range):
```python
time_range = request.args.get("time_range")
url = f"{API_BASE_URL}/api/monitoring/{resource_id}/metrics"
if time_range:
    url += f"?time_range={time_range}"

response = requests.get(
    url,
    headers={"Authorization": f"Bearer {token}"},
    timeout=10,
)
```

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the missing endpoints cause failures.

**Test Plan**: Use browser developer tools or curl to make API calls to the missing endpoints. Run these tests on the UNFIXED code to observe 404 errors and understand the failure pattern.

**Test Cases**:
1. **AWS Provisioning Test**: POST to `/api/provision` with AWS configuration (will fail with 404 on unfixed code)
2. **Status Check Test**: GET `/api/provision/{id}/status` for any provision ID (will fail with 404 on unfixed code)
3. **Details Retrieval Test**: GET `/api/provision/{id}` for any provision ID (will fail with 404 on unfixed code)
4. **Resources List Test**: GET `/api/monitoring/resources` (will fail with 404 on unfixed code)
5. **Metrics Test**: GET `/api/monitoring/{id}/metrics` for any resource ID (will fail with 404 on unfixed code)
6. **Metrics with Time Range Test**: GET `/api/monitoring/{id}/metrics?time_range=24h` (will fail with 404 on unfixed code)

**Expected Counterexamples**:
- All requests return 404 Not Found from Web UI
- Browser console shows "Load failed" errors
- API logs show no incoming requests (requests never reach API)

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL request WHERE isBugCondition(request) DO
  response := handleRequest_fixed(request)
  ASSERT response.forwarded_to_api == true
  ASSERT response.status_code IN [200, 201, 400, 401, 404, 500, 503, 504]
  ASSERT response.has_authentication_header == true
END FOR
```

**Test Cases**:
1. **Successful Provisioning**: POST valid AWS provisioning request → Should return 201 with provision_id
2. **Status Check**: GET status for existing provision → Should return 200 with status data
3. **Details Retrieval**: GET details for existing provision → Should return 200 with full details
4. **Resources List**: GET resources list → Should return 200 with array of resources
5. **Metrics Retrieval**: GET metrics for existing resource → Should return 200 with metrics data
6. **Metrics with Time Range**: GET metrics with time_range=24h → Should return 200 with historical data
7. **Authentication Failure**: Request without session token → Should return 401
8. **API Timeout**: Request when API is slow → Should return 504
9. **API Unavailable**: Request when API is down → Should return 503
10. **Invalid ID**: Request with non-existent provision/resource ID → Should return 404 from API

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL request WHERE NOT isBugCondition(request) DO
  ASSERT handleRequest_original(request) = handleRequest_fixed(request)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Test all existing endpoints to ensure they continue working after adding new proxy endpoints.

**Test Cases**:
1. **Authentication Preservation**: Login, logout, register endpoints continue working
2. **Configuration Preservation**: Configuration create, validate, retrieve endpoints continue working
3. **TCO Preservation**: TCO calculation and results endpoints continue working
4. **Q&A Preservation**: Q&A ask and history endpoints continue working
5. **HTML Rendering Preservation**: All page rendering endpoints continue working
6. **Static Files Preservation**: CSS, JavaScript, images continue serving correctly

### Unit Tests

- Test each proxy endpoint with valid authentication token
- Test each proxy endpoint without authentication (should return 401)
- Test error handling for timeouts (mock slow API)
- Test error handling for connection errors (mock unavailable API)
- Test query parameter forwarding (time_range for metrics)
- Test request body forwarding (provisioning data)
- Test response status code forwarding (200, 201, 400, 401, 404, 500)

### Property-Based Tests

- Generate random provisioning configurations and verify they are forwarded correctly
- Generate random provision IDs and verify status/details requests are forwarded
- Generate random resource IDs and verify metrics requests are forwarded
- Generate random time_range values and verify they are forwarded correctly
- Test that all non-proxy endpoints continue working across many scenarios

### Integration Tests

- Test full provisioning flow: submit request → check status → retrieve details
- Test full monitoring flow: list resources → get metrics → get metrics with time range
- Test authentication flow: login → make proxy request → logout → verify 401
- Test error propagation: API returns 400 → Web UI forwards 400 to browser
- Test LocalStack integration: provision AWS resources → verify in LocalStack
- Test monitoring data collection: provision resources → wait for metrics → retrieve metrics
