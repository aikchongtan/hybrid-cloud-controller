# UAT Issues & Observations
**Session Date**: 2026-03-09  
**Tester**: User  
**Status**: In Progress

---

## UI/UX Issues

### Issue #1: Inconsistent Card Heights on Home Page
**Priority**: Low  
**Severity**: Minor (Cosmetic)  
**Status**: Open

**Description**:
The "TCO Analysis" card/banner is taller than the "Provisioning" and "Monitoring" cards on the home page, creating visual inconsistency.

**Location**: Home page (http://localhost:10001)

**Expected**:
All three feature cards should have equal height for visual consistency.

**Actual**:
"TCO Analysis" card is noticeably taller than the other two cards.

**Screenshot**: Provided

**Suggested Fix**:
- Add CSS to ensure equal card heights (e.g., `min-height` or flexbox `align-items: stretch`)
- Or adjust text content to be similar length across all cards

**Workaround**: None needed - purely cosmetic

---

### Issue #6: Low Contrast Instruction Text on Configuration Form
**Priority**: Low  
**Severity**: Minor (Cosmetic/Accessibility)  
**Status**: Open

**Description**:
The instruction text below each input field on the configuration form has very low contrast (pale gray text on light background), making it difficult to read.

**Location**: Configuration input page (http://localhost:10001/configuration)

**Affected Text**:
- "Number of CPU cores (positive integer)"
- "Memory size in gigabytes (positive number)"
- "Number of instances (positive integer)"
- "Type of storage (SSD, HDD, or NVMe)"
- "Storage capacity in gigabytes (positive number)"
- "Input/Output operations per second (optional)"
- "Network bandwidth in megabits per second (positive number)"
- "Monthly data transfer in gigabytes (positive number)"
- "Expected resource utilization (0-100%)"
- "Hours of operation per month (0-744)"

**Expected**:
Instruction text should have sufficient contrast for readability (WCAG AA standard: 4.5:1 contrast ratio for normal text)

**Actual**:
Text appears to be very light gray on light background, making it hard to read

**Suggested Fix**:
- Increase text color darkness (e.g., use Bulma's `has-text-grey-dark` or `has-text-grey-darker` classes)
- Or add custom CSS with better contrast color

**Workaround**: None needed - text is still readable with effort

**Screenshot**: Provided

---

## Functional Issues

### Issue #2: Web UI Cannot Connect to API (Wrong Hostname)
**Priority**: Critical  
**Severity**: Blocker  
**Status**: ✅ Fixed

**Description**:
Web UI routes were hardcoded to connect to API at `http://localhost:10000` but inside Docker containers, services must use service names (e.g., `http://api:10000`).

**Location**: 
- `packages/web_ui/routes/auth.py`
- `packages/web_ui/routes/configuration.py`

**Error Message**: "Unable to connect to authentication service"

**Expected**:
Web UI should connect to API using Docker service name: `http://api:10000`

**Actual**:
Web UI was trying to connect to `http://localhost:10000` (doesn't work in Docker)

**Fix Applied**:
Changed to use environment variable with default: `API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")`

**Status**: ✅ Fixed

---

### Issue #3: Database Not Initialized on Startup
**Priority**: Critical  
**Severity**: Blocker  
**Status**: ✅ Fixed

**Description**:
API was not initializing the database or creating tables on startup, causing registration to fail with "Database not initialized" error.

**Location**: `packages/api/app.py`

**Error Message**: "Unexpected error during registration: Database not initialized. Call init_database() first."

**Expected**:
Database should be initialized and tables created automatically when API starts.

**Actual**:
- API didn't call `init_database()` on startup
- API didn't call `create_tables()` to create schema

**Fix Applied**:
1. Added `init_database()` and `create_tables()` calls in `create_app()` function
2. Added `psycopg2-binary` to requirements (PostgreSQL driver was missing)
3. Manually ran initialization to create all 11 database tables

**Status**: ✅ Fixed - All tables created

---

### Issue #4: Navigation Bar Not Showing Login Status
**Priority**: High  
**Severity**: Major (Functional)  
**Status**: ✅ Fixed

**Description**:
After successful login, the navigation bar still shows "Sign up" and "Log in" buttons instead of showing the logged-in user information and a "Logout" button.

**Location**: `packages/web_ui/templates/base.html`

**Expected**:
- After login, navigation should show user ID and "Logout" button
- "Sign up" and "Log in" buttons should be hidden when logged in

**Actual**:
- Navigation bar was hardcoded to always show "Sign up" and "Log in" buttons
- No check for `session.get('token')` to determine login status

**Fix Applied**:
Added conditional logic in base.html navigation:
```jinja2
{% if session.get('token') %}
    <!-- Show user ID and Logout button -->
{% else %}
    <!-- Show Sign up and Log in buttons -->
{% endif %}
```

**Status**: ✅ Fixed - Web UI restarted

---

### Issue #5: Session Cookie Not Being Set (HTTPS Required)
**Priority**: Critical  
**Severity**: Blocker  
**Status**: ✅ Fixed

**Description**:
After successful login, the session cookie was not being set in the browser, causing the user to appear logged out even though the login API call succeeded.

**Location**: `packages/web_ui/app.py`

**Root Cause**:
Flask was configured with `SESSION_COOKIE_SECURE = True`, which requires HTTPS connections. Since we're running on HTTP for local development (http://localhost:10001), the browser refused to set the secure cookie.

**Expected**:
- Session cookie should be set after successful login
- User should remain logged in across page navigations

**Actual**:
- Session cookie was not being set due to HTTPS requirement
- User appeared logged out immediately after login

**Fix Applied**:
Changed `SESSION_COOKIE_SECURE = False` for local development in `app.py`:
```python
app.config["SESSION_COOKIE_SECURE"] = False  # For local development
```

**Note**: In production with HTTPS, this should be set back to `True` for security.

**Status**: ✅ Fixed - Web UI restarted

---

### Issue #7: Pricing Data Not Initialized on Startup
**Priority**: Critical  
**Severity**: Blocker  
**Status**: ✅ Fixed

**Description**:
TCO calculation fails with "Error: Pricing data unavailable" because the pricing_data table in the database is empty. The application requires pricing data to calculate AWS costs.

**Location**: 
- `packages/pricing_service/fetcher.py`
- Database table: `pricing_data`

**Error Message**: "Error: Pricing data unavailable. Please try again later."

**Root Cause**:
- Pricing service tries to fetch from AWS Pricing API, which doesn't work with LocalStack
- No fallback pricing data was initialized in the database on startup
- TCO calculation requires pricing data to proceed

**Expected**:
- Pricing data should be initialized automatically on first startup
- Fallback pricing should be available when AWS API is unavailable

**Actual**:
- Database pricing_data table was empty
- TCO calculation failed immediately

**Fix Applied**:
Manually initialized pricing data with fallback values:
```bash
docker compose exec api python -c "..."
```

**Permanent Fix Needed**:
Add pricing data initialization to API startup in `packages/api/app.py`:
```python
# Initialize pricing data if not exists
from packages.pricing_service.fetcher import get_current_pricing, _store_pricing_data
if not get_current_pricing():
    # Store fallback pricing
    _store_pricing_data(fallback_pricing_data)
```

**Status**: ✅ Fixed - Pricing data initialized

---

## Performance Issues

_[To be filled during UAT]_

---

## Security Issues

_[To be filled during UAT]_

---

## Notes

- Continue UAT and document all issues here
- Prioritize functional issues over cosmetic ones
- Batch UI fixes together at the end

### Issue #8: Winner Badge Placed Incorrectly (String Comparison Bug)
**Priority**: High  
**Severity**: Major (Functional/Logic Error)  
**Status**: ✅ Fixed

**Description**:
The "Most Cost-Effective" badge is placed on the wrong option (AWS) even though On-Premises has a lower cost ($6,006.62 vs $11,555.28).

**Location**: `packages/web_ui/templates/tco_results.html`

**Root Cause**:
The API returns cost totals as strings (e.g., `"6006.62"`, `"11555.28"`), but the template was comparing them directly without converting to numbers. This caused string comparison instead of numeric comparison. In string comparison, `"11555.28" < "6006.62"` evaluates to `True` because `"1"` comes before `"6"` alphabetically.

**Expected**:
- Badge should appear on the option with the lower numeric cost
- On-Premises ($6,006.62) should have the badge, not AWS ($11,555.28)

**Actual**:
- Badge appeared on AWS due to incorrect string comparison
- String comparison: `"11555.28" < "6006.62"` = True (alphabetically)
- Numeric comparison: `11555.28 < 6006.62` = False (correct)

**Fix Applied**:
Added `|float` filter to convert strings to numbers before comparison in all three tabs (1-year, 3-year, 5-year):
```jinja2
{% if tco_data.on_prem_costs['1'].total|float < tco_data.aws_costs['1'].total|float %}
```

**Status**: ✅ Fixed - Web UI restarted

**Screenshot**: Provided

---

### Issue #9: Q&A Question Input Field Too Small
**Priority**: Low  
**Severity**: Minor (Cosmetic/UX)  
**Status**: Open

**Description**:
The question input field on the Q&A page is disproportionately small, making it difficult to see the full question being typed.

**Location**: Q&A page (http://localhost:10001/qa/...)

**Expected**:
- Input field should be large enough to comfortably type and review questions
- Should accommodate at least 100-150 characters visible at once
- Should be proportional to the page layout

**Actual**:
- Input field appears very small (looks like ~20-30 characters wide)
- Difficult to review longer questions before sending

**Suggested Fix**:
- Increase input field width to use more of the available horizontal space
- Consider using a textarea instead of input for multi-line questions
- Or increase font size and padding for better visibility

**Workaround**: Questions still work, just harder to review before sending

**Screenshot**: Provided

**Note**: Deferred for batch UI fix with Issues #1, #6, and #12

---

### Issue #12: Low Contrast Cost Details on TCO Results Page
**Priority**: Low  
**Severity**: Minor (Cosmetic/Accessibility)  
**Status**: Open

**Description**:
The cost breakdown details (line items) on the TCO results page use grey text on a black background, making it difficult to read the cost details.

**Location**: TCO results page (http://localhost:10001/tco/results/...)

**Affected Elements**:
- Cost line items under On-Premises card (grey text on dark purple/black background)
- Cost line items under AWS Cloud card (grey text on dark pink/black background)

**Expected**:
- Cost details should have sufficient contrast for readability
- Text should be easily readable against the card backgrounds
- Should meet WCAG AA accessibility standards (4.5:1 contrast ratio)

**Actual**:
- Grey text on black background is hard to read
- Users have to strain to see the cost breakdown details

**Suggested Fix**:
- Change text color to white or light grey with higher contrast
- Or lighten the background color behind the cost details
- Use Bulma's `has-text-white` or `has-text-light` classes

**Workaround**: None needed - text is still readable with effort

**Screenshot**: Provided

**Note**: Deferred for batch UI fix with Issues #1, #6, and #9

---

### Issue #10: Q&A API Endpoints Missing Proxy Routes
**Priority**: Critical  
**Severity**: Blocker  
**Status**: ✅ Fixed

**Description**:
Q&A service fails with "Sorry, I encountered an error processing your question" because the Web UI JavaScript makes API calls to `/api/qa/...` which are routed to the Web UI service (port 10001) instead of the API service (port 10000).

**Location**: `packages/web_ui/routes/qa.py`

**Root Cause**:
- Q&A template JavaScript uses relative URLs (`/api/qa/...`)
- These URLs are handled by the Web UI service, not the API service
- Web UI didn't have proxy endpoints to forward Q&A requests to the API

**Expected**:
- Q&A questions should be forwarded to the API service
- Responses should be returned to the browser
- Conversation history should be retrievable

**Actual**:
- Web UI returned 404 for `/api/qa/.../ask` and `/api/qa/.../history`
- Q&A service appeared broken to the user

**Fix Applied**:
Added two proxy endpoints in `packages/web_ui/routes/qa.py`:
1. `POST /api/qa/<config_id>/ask` - Forwards questions to API
2. `GET /api/qa/<config_id>/history` - Retrieves conversation history from API

Both endpoints:
- Check authentication
- Forward requests to API service at `http://api:10000`
- Handle errors gracefully
- Return appropriate status codes

**Status**: ✅ Fixed - Web UI restarted

---

### Issue #11: Configuration Validation Endpoint Wrong URL
**Priority**: Critical  
**Severity**: Blocker  
**Status**: ✅ Fixed

**Description**:
When clicking the "Validate" button on the configuration form, the validation fails with "Unable to validate configuration. Please try again." error.

**Location**: 
- `packages/web_ui/static/js/configuration.js`
- `packages/web_ui/routes/configuration.py`

**Root Cause**:
1. JavaScript was hardcoded to call `http://localhost:8000` (wrong port - should be 10000)
2. Web UI didn't have a proxy endpoint for `/api/configurations/validate`
3. Validation requests were failing because they couldn't reach the API

**Expected**:
- Validation button should validate configuration against API rules
- Success message should appear if configuration is valid
- Field-specific errors should appear if validation fails

**Actual**:
- Validation failed with generic error message
- API logs showed authentication errors (401)
- JavaScript was calling wrong URL

**Fix Applied**:
1. Changed JavaScript to use relative URL `/api/configurations/validate` instead of hardcoded `http://localhost:8000`
2. Added proxy endpoint in `packages/web_ui/routes/configuration.py`:
   - `POST /api/configurations/validate` - Forwards validation to API
   - Public endpoint (no authentication required)
   - Returns validation results to browser

**Files Modified**:
- `packages/web_ui/static/js/configuration.js` - Fixed API URL
- `packages/web_ui/routes/configuration.py` - Added validation proxy endpoint

**Status**: ✅ Fixed - Web UI restarted

---

### Issue #13: Q&A Service Limited Semantic Understanding
**Priority**: Medium  
**Severity**: Minor (Functional Limitation)  
**Status**: Open - Future Enhancement

**Description**:
The Q&A service works and returns responses, but has limited semantic understanding. It uses simple keyword matching rather than intelligent natural language processing, resulting in generic or incomplete answers for many questions.

**Location**: `packages/qa_service/processor.py`

**Examples of Limitations**:
1. "Compare storage costs" → Returns default help message (doesn't recognize "storage" maps to "hardware" for On-Prem and "EBS/S3" for AWS)
2. "Compare power costs" → Returns "Found power in on-premises costs ($933.12), but not in AWS costs" (doesn't understand AWS power is included in EC2 costs)
3. "What are one-time sunk costs" → Returns default help message (doesn't understand "sunk costs" = "hardware")

**Root Cause**:
- Q&A processor uses exact keyword matching (`if "power" in question_lower`)
- No semantic understanding or synonym mapping
- No context awareness (e.g., AWS power costs are embedded in EC2 pricing)
- Limited to predefined patterns and keywords

**Expected (Future Enhancement)**:
- Intelligent question understanding using NLP or LLM
- Semantic mapping of related terms (storage → hardware/EBS/S3, power → electricity/EC2)
- Context-aware responses that explain cost relationships
- Ability to answer open-ended questions about TCO methodology

**Actual**:
- Basic keyword matching with limited patterns
- Generic help message for unrecognized questions
- Partial answers when keywords only partially match

**Suggested Enhancement**:
- Integrate AI/LLM (e.g., OpenAI, Anthropic) for natural language understanding
- Add synonym mapping for common terms
- Enhance cost item categorization to show relationships
- Add more sophisticated question patterns

**Workaround**: 
- Users can ask questions using exact cost item names from the breakdown
- Use suggested question formats from the help message

**Note**: Q&A service is functional and working correctly - this is a feature enhancement request, not a bug

---

### Issue #14: AWS Provisioning Feature Incomplete - Missing Proxy Endpoints
**Priority**: Critical  
**Severity**: Blocker (Feature Not Functional)  
**Status**: Open - Requires Implementation

**Description**:
The AWS provisioning feature fails with "Provisioning failed: Load failed" error. The Web UI provisioning page renders correctly, but the JavaScript cannot communicate with the API to start provisioning because there are no proxy endpoints in the Web UI to forward provisioning requests to the API service.

**Location**: 
- `packages/web_ui/routes/provisioning.py` (missing proxy endpoints)
- `packages/web_ui/templates/provisioning.html` (JavaScript makes API calls)

**User Journey**:
1. User navigates to home page
2. Clicks "Provision Resources" button
3. Selects AWS Cloud Emulator
4. Enters container image URL (e.g., `nginx:latest`)
5. Enters environment variables (optional)
6. Clicks "Start Provisioning"
7. **ERROR**: "Provisioning failed: Load failed"

**Root Cause**:
- Web UI only has `GET /provision/<config_id>` endpoint (renders page)
- No proxy endpoints to forward provisioning API calls:
  - `POST /api/provision/aws` - Start AWS provisioning
  - `GET /api/provision/<provision_id>/status` - Check provisioning status
  - `GET /api/provision/<provision_id>` - Get provisioning details
- JavaScript tries to call API directly, which fails due to authentication/CORS
- Similar to Issues #10 and #11 (Q&A and validation proxy endpoints)

**Expected Behavior**:
1. User submits provisioning request
2. Web UI forwards request to API with authentication token
3. API provisions resources in LocalStack:
   - EC2 instances (based on config: 3 instances, 8 cores, 32GB RAM)
   - EBS volumes (500GB SSD, 3000 IOPS)
   - S3 buckets (for object storage)
   - Network configuration (10Gbps bandwidth)
   - Deploy container image on provisioned infrastructure
4. User sees provisioning progress/status
5. Success message when provisioning completes

**Actual Behavior**:
- Provisioning request fails immediately
- Error message: "Provisioning failed: Load failed"
- No resources created in LocalStack
- API logs show authentication errors (401)

**API Logs**:
```
Authentication error: 401 Unauthorized: Invalid or expired session
HTTP error 401: AUTHENTICATION_REQUIRED - Authentication failed
```

**Required Implementation**:

### 1. Add Web UI Proxy Endpoints
File: `packages/web_ui/routes/provisioning.py`

Add the following proxy endpoints:

```python
import os
import requests
from flask import jsonify, request

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")

@bp.route("/api/provision/aws", methods=["POST"])
def provision_aws():
    """
    Proxy endpoint for starting AWS provisioning.
    
    POST: Forward provisioning request to API
    """
    token = session.get("token")
    if not token:
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        data = request.get_json()
        
        response = requests.post(
            f"{API_BASE_URL}/api/provision/aws",
            json=data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.Timeout:
        logger.error("API request timeout during AWS provisioning")
        return jsonify({"error": "Request timeout"}), 504
    
    except requests.exceptions.ConnectionError:
        logger.error("API connection error during AWS provisioning")
        return jsonify({"error": "Unable to connect to service"}), 503
    
    except Exception as e:
        logger.error(f"Unexpected error during AWS provisioning: {e}")
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
```

### 2. Verify API Endpoints Exist
Check that these endpoints are implemented in `packages/api/routes/provisioning.py`:
- `POST /api/provision/aws` - Start AWS provisioning
- `GET /api/provision/<provision_id>/status` - Get status
- `GET /api/provision/<provision_id>` - Get details

### 3. Test with LocalStack
Verify that:
- LocalStack is running and healthy
- API can connect to LocalStack at `http://localstack:4566`
- EC2, EBS, S3, and ECS services are available in LocalStack

### 4. Update JavaScript (if needed)
Check `packages/web_ui/templates/provisioning.html` to ensure JavaScript uses relative URLs:
- Should call `/api/provision/aws` (not `http://localhost:8000/api/provision/aws`)
- Should call `/api/provision/<id>/status` for status polling

**Test Data for Remediation**:
- Config ID: Use any valid configuration from database
- Container Image: `nginx:latest`
- Environment Variables: `{"NGINX_PORT": "80"}` (optional)
- Expected Infrastructure:
  - 3 EC2 instances (8 cores, 32GB RAM each)
  - 500GB SSD EBS volumes with 3000 IOPS
  - S3 buckets for object storage
  - 10Gbps network bandwidth

**Estimated Fix Time**: 1-1.5 hours
- Add proxy endpoints: 30-45 minutes
- Verify API endpoints: 15-20 minutes
- Test end-to-end: 20-30 minutes

**Dependencies**:
- LocalStack must be running and healthy
- API provisioning routes must be implemented
- Authentication middleware must be working

**Related Issues**:
- Similar to Issue #10 (Q&A proxy endpoints)
- Similar to Issue #11 (Configuration validation proxy endpoint)
- Pattern: Web UI needs proxy endpoints for all API calls

**Workaround**: None - feature is non-functional

**Impact**: 
- Users cannot provision AWS resources
- Cannot test full user workflow (Analyze → Provision → Monitor)
- Monitoring feature may depend on provisioned resources

**Screenshot**: Provided (shows "Provisioning failed: Load failed" error)

**Status**: Open - Deferred to post-UAT remediation session

---
