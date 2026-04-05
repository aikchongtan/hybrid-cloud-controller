# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Missing Proxy Endpoints Return 404
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to the 7 concrete missing endpoints to ensure reproducibility
  - Test that requests to missing proxy endpoints return 404 errors:
    - POST /api/provision (AWS/IaaS/CaaS provisioning)
    - GET /api/provision/{id}/status (status check)
    - GET /api/provision/{id} (details retrieval)
    - GET /api/monitoring/resources (resources list)
    - GET /api/monitoring/{id}/metrics (metrics retrieval)
    - GET /api/monitoring/{id}/metrics?time_range=24h (metrics with time range)
  - Use property-based testing to generate random provision IDs and resource IDs
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with 404 errors (this is correct - it proves the bug exists)
  - Document counterexamples found (e.g., "POST /api/provision returns 404 instead of forwarding to API")
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Endpoints Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for existing endpoints:
    - Authentication endpoints (login, logout, register)
    - Configuration endpoints (create, validate, retrieve)
    - TCO calculation endpoints
    - Q&A endpoints (ask, history)
    - HTML page rendering (provisioning.html, monitoring.html)
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements:
    - For all requests to existing endpoints, behavior remains unchanged
    - Authentication continues to protect all endpoints
    - Error handling patterns (timeouts, connection errors) remain consistent
    - Session management and token handling remain unchanged
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 3. Add proxy endpoints to provisioning.py

  - [x] 3.1 Add imports and API_BASE_URL configuration
    - Add `import os` at top of file
    - Add `import requests` at top of file
    - Add `from flask import jsonify, request` to existing imports
    - Add `API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")` after imports
    - _Bug_Condition: isBugCondition(request) where request.path matches provisioning endpoints_
    - _Expected_Behavior: Proxy endpoints forward requests to API with authentication_
    - _Preservation: Existing HTML rendering endpoint remains unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.2 Implement POST /api/provision endpoint
    - Add route decorator: `@bp.route("/api/provision", methods=["POST"])`
    - Validate authentication (session token required, return 401 if missing)
    - Get JSON body from request
    - Forward to `POST {API_BASE_URL}/api/provision` with Authorization header
    - Use 30s timeout for POST requests
    - Handle timeouts (504), connection errors (503), and unexpected errors (500)
    - Return API response with status code (201 on success)
    - Add logging for request forwarding and errors
    - _Bug_Condition: POST /api/provision returns 404 on unfixed code_
    - _Expected_Behavior: Forward provisioning request to API and return provision_id_
    - _Preservation: Authentication and error handling patterns remain consistent_
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.3 Implement GET /api/provision/<provision_id>/status endpoint
    - Add route decorator: `@bp.route("/api/provision/<provision_id>/status", methods=["GET"])`
    - Validate authentication (session token required, return 401 if missing)
    - Forward to `GET {API_BASE_URL}/api/provision/{provision_id}/status` with Authorization header
    - Use 10s timeout for GET requests
    - Handle timeouts (504), connection errors (503), and unexpected errors (500)
    - Return API response with status code (200 on success)
    - Add logging for request forwarding and errors
    - _Bug_Condition: GET /api/provision/{id}/status returns 404 on unfixed code_
    - _Expected_Behavior: Forward status request to API and return status data_
    - _Preservation: Authentication and error handling patterns remain consistent_
    - _Requirements: 2.4_

  - [x] 3.4 Implement GET /api/provision/<provision_id> endpoint
    - Add route decorator: `@bp.route("/api/provision/<provision_id>", methods=["GET"])`
    - Validate authentication (session token required, return 401 if missing)
    - Forward to `GET {API_BASE_URL}/api/provision/{provision_id}` with Authorization header
    - Use 10s timeout for GET requests
    - Handle timeouts (504), connection errors (503), and unexpected errors (500)
    - Return API response with status code (200 on success)
    - Add logging for request forwarding and errors
    - _Bug_Condition: GET /api/provision/{id} returns 404 on unfixed code_
    - _Expected_Behavior: Forward details request to API and return full provisioning details_
    - _Preservation: Authentication and error handling patterns remain consistent_
    - _Requirements: 2.5_

  - [x] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Provisioning Endpoints Forward Requests
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1 for provisioning endpoints
    - **EXPECTED OUTCOME**: Test PASSES for provisioning endpoints (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Endpoints Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after adding provisioning proxy endpoints

- [x] 4. Add proxy endpoints to monitoring.py

  - [x] 4.1 Add imports and API_BASE_URL configuration
    - Add `import os` at top of file
    - Add `import requests` at top of file
    - Add `from flask import jsonify, request` to existing imports
    - Add `API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")` after imports
    - _Bug_Condition: isBugCondition(request) where request.path matches monitoring endpoints_
    - _Expected_Behavior: Proxy endpoints forward requests to API with authentication_
    - _Preservation: Existing HTML rendering endpoints remain unchanged_
    - _Requirements: 2.6, 2.7, 2.8_

  - [x] 4.2 Implement GET /api/monitoring/resources endpoint
    - Add route decorator: `@bp.route("/api/monitoring/resources", methods=["GET"])`
    - Validate authentication (session token required, return 401 if missing)
    - Forward to `GET {API_BASE_URL}/api/monitoring/resources` with Authorization header
    - Use 10s timeout for GET requests
    - Handle timeouts (504), connection errors (503), and unexpected errors (500)
    - Return API response with status code (200 on success)
    - Add logging for request forwarding and errors
    - _Bug_Condition: GET /api/monitoring/resources returns 404 on unfixed code_
    - _Expected_Behavior: Forward resources request to API and return list of resources_
    - _Preservation: Authentication and error handling patterns remain consistent_
    - _Requirements: 2.6_

  - [x] 4.3 Implement GET /api/monitoring/<resource_id>/metrics endpoint
    - Add route decorator: `@bp.route("/api/monitoring/<resource_id>/metrics", methods=["GET"])`
    - Validate authentication (session token required, return 401 if missing)
    - Extract optional time_range query parameter from request.args
    - Build URL with time_range parameter if provided: `{API_BASE_URL}/api/monitoring/{resource_id}/metrics?time_range={time_range}`
    - Forward to API with Authorization header
    - Use 10s timeout for GET requests
    - Handle timeouts (504), connection errors (503), and unexpected errors (500)
    - Return API response with status code (200 on success)
    - Add logging for request forwarding and errors
    - **CRITICAL**: Must forward time_range query parameter to API
    - _Bug_Condition: GET /api/monitoring/{id}/metrics returns 404 on unfixed code_
    - _Expected_Behavior: Forward metrics request to API with time_range parameter and return metrics data_
    - _Preservation: Authentication and error handling patterns remain consistent_
    - _Requirements: 2.7, 2.8_

  - [x] 4.4 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Monitoring Endpoints Forward Requests
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1 for monitoring endpoints
    - **EXPECTED OUTCOME**: Test PASSES for monitoring endpoints (confirms bug is fixed)
    - _Requirements: 2.6, 2.7, 2.8_

  - [x] 4.5 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Endpoints Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after adding monitoring proxy endpoints

- [x] 5. Integration testing with LocalStack and full application stack

  - [x] 5.1 Test AWS provisioning flow end-to-end
    - Start LocalStack and application stack (docker-compose up)
    - Login to Web UI
    - Create AWS configuration
    - Submit AWS provisioning request via Web UI
    - Verify provision_id is returned
    - Check provisioning status via Web UI
    - Retrieve provisioning details via Web UI
    - Verify resources exist in LocalStack (EC2, EBS, S3, networking)
    - _Requirements: 2.1, 2.4, 2.5_

  - [x] 5.2 Test On-Premises IaaS provisioning flow
    - Login to Web UI
    - Create On-Premises IaaS configuration
    - Submit IaaS provisioning request via Web UI
    - Verify provision_id and SSH details are returned
    - Check provisioning status via Web UI
    - Retrieve provisioning details via Web UI
    - _Requirements: 2.2, 2.4, 2.5_

  - [x] 5.3 Test On-Premises CaaS provisioning flow
    - Login to Web UI
    - Create On-Premises CaaS configuration
    - Submit CaaS provisioning request via Web UI
    - Verify provision_id and container details are returned
    - Check provisioning status via Web UI
    - Retrieve provisioning details via Web UI
    - _Requirements: 2.3, 2.4, 2.5_

  - [x] 5.4 Test monitoring dashboard with provisioned resources
    - Navigate to monitoring dashboard
    - Verify resources list loads correctly (GET /api/monitoring/resources)
    - Select a resource
    - Verify metrics load correctly (GET /api/monitoring/{id}/metrics)
    - Change time range to 24h
    - Verify metrics update with time_range parameter
    - _Requirements: 2.6, 2.7, 2.8_

  - [x] 5.5 Test error handling scenarios
    - Test authentication failure (no session token) → Verify 401 response
    - Test API timeout (mock slow API) → Verify 504 response
    - Test API unavailable (stop API service) → Verify 503 response
    - Test invalid provision ID → Verify 404 response from API
    - Test invalid resource ID → Verify 404 response from API
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 5.6 Test preservation of existing functionality
    - Test Q&A endpoints (ask question, get history) → Verify unchanged behavior
    - Test configuration endpoints (create, validate, retrieve) → Verify unchanged behavior
    - Test TCO calculation → Verify unchanged behavior
    - Test authentication flow (login, logout, register) → Verify unchanged behavior
    - Test HTML page rendering → Verify unchanged behavior
    - _Requirements: 3.6, 3.7, 3.8_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
