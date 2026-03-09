# User Acceptance Testing (UAT) Plan
# Hybrid Cloud Controller

**Version**: 1.0  
**Date**: 2026-03-08  
**Purpose**: Comprehensive testing of all application features before production deployment

---

## Table of Contents

1. [Pre-Test Setup](#pre-test-setup)
2. [Test Environment](#test-environment)
3. [UAT Test Cases](#uat-test-cases)
4. [Test Execution Checklist](#test-execution-checklist)
5. [Issue Reporting Template](#issue-reporting-template)

---

## Pre-Test Setup

### Prerequisites

- Docker and Docker Compose installed
- Git repository cloned
- Ports 5432, 4566, 10000, 10001 available
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Environment Setup

```bash
# 1. Navigate to project directory
cd hybrid-cloud-controller

# 2. Copy environment variables
cp .env.example .env

# 3. Start all services
docker-compose up -d

# 4. Wait for services to be healthy (30-60 seconds)
docker-compose ps

# 5. Check service logs if needed
docker-compose logs -f
```

### Verify Services Running

```bash
# Check all services are healthy
docker-compose ps

# Expected output:
# - hybrid-cloud-db: Up (healthy)
# - hybrid-cloud-localstack: Up (healthy)
# - hybrid-cloud-api: Up
# - hybrid-cloud-web-ui: Up
```


### Access Points

- **Web UI**: http://localhost:10001
- **API**: http://localhost:10000
- **LocalStack**: http://localhost:4566
- **Database**: localhost:5432

---

## Test Environment

### Test Data

**Test User Credentials** (to be created during testing):
- Username: `testuser`
- Password: `TestPassword123!`

**Sample Configuration Data**:
```json
{
  "compute": {
    "cpu_cores": 8,
    "memory_gb": 32,
    "instance_count": 3
  },
  "storage": {
    "type": "SSD",
    "capacity_gb": 500,
    "iops": 3000
  },
  "network": {
    "bandwidth_gbps": 10,
    "data_transfer_gb": 1000
  },
  "workload": {
    "utilization_percent": 75,
    "operating_hours": 720
  }
}
```

**Sample Container Image URLs**:
- Docker Hub: `nginx:latest`
- ECR: `123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.0`
- Private: `registry.example.com/myapp:latest`

---

## UAT Test Cases

---

### TEST SUITE 1: Authentication & User Management

#### TC-1.1: User Registration
**Priority**: Critical  
**Objective**: Verify new users can register successfully

**Steps**:
1. Navigate to http://localhost:10001
2. Click "Register" link or navigate to `/register`
3. Enter username: `testuser`
4. Enter password: `TestPassword123!`
5. Click "Register" button

**Expected Results**:
- ✅ Registration form displays correctly
- ✅ Form accepts valid username and password
- ✅ Success message displayed after registration
- ✅ User redirected to login page
- ✅ No error messages displayed

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

**Notes**: _[Any observations]_

---

#### TC-1.2: User Login
**Priority**: Critical  
**Objective**: Verify registered users can log in

**Steps**:
1. Navigate to http://localhost:10001/login
2. Enter username: `testuser`
3. Enter password: `TestPassword123!`
4. Click "Login" button

**Expected Results**:
- ✅ Login form displays correctly
- ✅ Valid credentials accepted
- ✅ User redirected to configuration page (home)
- ✅ Navigation shows user is logged in
- ✅ Session cookie created

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

**Notes**: _[Any observations]_

---

#### TC-1.3: Invalid Login Attempts
**Priority**: High  
**Objective**: Verify system handles invalid credentials properly

**Steps**:
1. Navigate to http://localhost:10001/login
2. Enter username: `testuser`
3. Enter password: `WrongPassword`
4. Click "Login" button

**Expected Results**:
- ✅ Error message displayed: "Invalid credentials"
- ✅ User remains on login page
- ✅ No session created
- ✅ Password field cleared for security

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-1.4: User Logout
**Priority**: High  
**Objective**: Verify users can log out successfully

**Steps**:
1. Log in as `testuser`
2. Click "Logout" link in navigation
3. Attempt to access protected page (e.g., `/configuration`)

**Expected Results**:
- ✅ User logged out successfully
- ✅ Session invalidated
- ✅ Redirected to login page
- ✅ Cannot access protected pages without re-login

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-1.5: Session Timeout
**Priority**: Medium  
**Objective**: Verify session expires after 30 minutes of inactivity

**Steps**:
1. Log in as `testuser`
2. Wait 31 minutes without any activity
3. Attempt to navigate to any page

**Expected Results**:
- ✅ Session expires after 30 minutes
- ✅ User redirected to login page
- ✅ Message indicates session expired

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

**Notes**: _This test takes 31 minutes - can be skipped for quick UAT_

---

### TEST SUITE 2: Configuration Input & Validation

#### TC-2.1: Valid Configuration Submission
**Priority**: Critical  
**Objective**: Verify users can submit valid configuration

**Steps**:
1. Log in as `testuser`
2. Navigate to configuration page (home page after login)
3. Fill in compute specs:
   - CPU Cores: `8`
   - Memory (GB): `32`
   - Instance Count: `3`
4. Fill in storage specs:
   - Type: `SSD`
   - Capacity (GB): `500`
   - IOPS: `3000`
5. Fill in network specs:
   - Bandwidth (Gbps): `10`
   - Data Transfer (GB): `1000`
6. Fill in workload profile:
   - Utilization (%): `75`
   - Operating Hours: `720`
7. Click "Calculate TCO" button

**Expected Results**:
- ✅ All form fields display correctly
- ✅ Form accepts valid input
- ✅ No validation errors
- ✅ Configuration saved successfully
- ✅ Redirected to TCO results page
- ✅ Configuration ID generated

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-2.2: Invalid Configuration - Negative Values
**Priority**: High  
**Objective**: Verify validation rejects negative values

**Steps**:
1. Navigate to configuration page
2. Enter CPU Cores: `-5`
3. Click "Calculate TCO" button

**Expected Results**:
- ✅ Validation error displayed
- ✅ Error message: "CPU cores must be positive"
- ✅ Form not submitted
- ✅ User remains on configuration page

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-2.3: Invalid Configuration - Out of Range
**Priority**: High  
**Objective**: Verify validation enforces range limits

**Steps**:
1. Navigate to configuration page
2. Enter Utilization: `150` (exceeds 100%)
3. Click "Calculate TCO" button

**Expected Results**:
- ✅ Validation error displayed
- ✅ Error message: "Utilization must be between 0 and 100"
- ✅ Form not submitted

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-2.4: Invalid Configuration - Operating Hours
**Priority**: High  
**Objective**: Verify operating hours validation (0-744 hours/month)

**Steps**:
1. Navigate to configuration page
2. Enter Operating Hours: `800` (exceeds 744)
3. Click "Calculate TCO" button

**Expected Results**:
- ✅ Validation error displayed
- ✅ Error message: "Operating hours must be between 0 and 744"
- ✅ Form not submitted

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-2.5: Configuration - Required Fields
**Priority**: High  
**Objective**: Verify all required fields must be filled

**Steps**:
1. Navigate to configuration page
2. Leave CPU Cores field empty
3. Fill other fields with valid data
4. Click "Calculate TCO" button

**Expected Results**:
- ✅ Validation error displayed
- ✅ Error indicates required field missing
- ✅ Form not submitted

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 3: TCO Calculation & Results

#### TC-3.1: TCO Results Display
**Priority**: Critical  
**Objective**: Verify TCO results display correctly

**Steps**:
1. Submit valid configuration (use TC-2.1 data)
2. View TCO results page

**Expected Results**:
- ✅ Results page loads successfully
- ✅ Side-by-side comparison displayed (On-Premises vs AWS)
- ✅ Total costs shown for both options
- ✅ Winner badge displayed (lower cost option)
- ✅ Cost breakdown by category visible
- ✅ All cost values are positive numbers
- ✅ Currency formatting correct (e.g., $1,234.56)

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-3.2: TCO Cost Breakdown
**Priority**: High  
**Objective**: Verify itemized cost breakdown displays all categories

**Steps**:
1. View TCO results from TC-3.1
2. Examine cost breakdown sections

**Expected Results**:
- ✅ On-Premises breakdown includes:
  - Hardware costs
  - Power costs
  - Cooling costs
  - Maintenance costs
  - Data transfer costs
- ✅ AWS breakdown includes:
  - EC2 costs
  - EBS costs
  - S3 costs
  - Data transfer costs
- ✅ All categories have values
- ✅ Subtotals add up to total

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-3.3: TCO Projections (1-Year, 3-Year, 5-Year)
**Priority**: High  
**Objective**: Verify cost projections for different time periods

**Steps**:
1. View TCO results from TC-3.1
2. Click on "1-Year" tab
3. Click on "3-Year" tab
4. Click on "5-Year" tab

**Expected Results**:
- ✅ Three projection tabs visible
- ✅ 1-Year projection displays correctly
- ✅ 3-Year projection >= 1-Year projection
- ✅ 5-Year projection >= 3-Year projection
- ✅ Projections include both on-premises and AWS
- ✅ Tab switching works smoothly

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-3.4: TCO Results - Navigation
**Priority**: Medium  
**Objective**: Verify navigation from results page

**Steps**:
1. View TCO results page
2. Click "Ask Questions" button/link
3. Go back and click "Provision" button/link
4. Go back and click "New Configuration" button/link

**Expected Results**:
- ✅ "Ask Questions" navigates to Q&A page
- ✅ "Provision" navigates to provisioning page
- ✅ "New Configuration" navigates to configuration page
- ✅ Configuration ID preserved in URLs
- ✅ Back button works correctly

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 4: Q&A Service

#### TC-4.1: Ask Question About Cost Item
**Priority**: High  
**Objective**: Verify Q&A service answers questions about specific costs

**Steps**:
1. Navigate to Q&A page from TCO results
2. Enter question: "Why are power costs so high?"
3. Click "Send" or press Enter

**Expected Results**:
- ✅ Q&A interface displays correctly
- ✅ Question submitted successfully
- ✅ Response received and displayed
- ✅ Response is relevant to the question
- ✅ Response references configuration data
- ✅ Conversation history shows both question and answer

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-4.2: Ask Comparison Question
**Priority**: High  
**Objective**: Verify Q&A can compare on-premises vs AWS

**Steps**:
1. On Q&A page, enter question: "Compare storage costs between on-premises and AWS"
2. Submit question

**Expected Results**:
- ✅ Response compares both options
- ✅ Response includes specific cost figures
- ✅ Response explains differences
- ✅ Response is clear and helpful

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-4.3: Request Recommendation
**Priority**: High  
**Objective**: Verify Q&A provides recommendations

**Steps**:
1. On Q&A page, enter question: "Which option do you recommend for my workload?"
2. Submit question

**Expected Results**:
- ✅ Response provides clear recommendation
- ✅ Recommendation based on workload profile
- ✅ Justification provided
- ✅ Considers cost and other factors

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-4.4: Conversation History
**Priority**: Medium  
**Objective**: Verify conversation history is maintained

**Steps**:
1. Ask 3 different questions in sequence
2. Scroll up to view previous questions and answers
3. Refresh the page

**Expected Results**:
- ✅ All questions and answers displayed in order
- ✅ Timestamps shown for each message
- ✅ User messages and assistant messages visually distinct
- ✅ History persists after page refresh
- ✅ Scrolling works smoothly

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-4.5: Q&A - Empty Question
**Priority**: Low  
**Objective**: Verify system handles empty questions

**Steps**:
1. On Q&A page, leave question field empty
2. Click "Send" button

**Expected Results**:
- ✅ Validation prevents submission OR
- ✅ Error message displayed
- ✅ No empty message in conversation

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 5: Provisioning - AWS Path

#### TC-5.1: AWS Provisioning - Infrastructure Only
**Priority**: Critical  
**Objective**: Verify AWS infrastructure provisioning via LocalStack

**Steps**:
1. Navigate to provisioning page from TCO results
2. Select "AWS" cloud path
3. Select "Infrastructure Only" (no container deployment)
4. Click "Provision" button
5. Wait for provisioning to complete

**Expected Results**:
- ✅ Cloud path selection displays correctly
- ✅ AWS option selectable
- ✅ Provisioning starts successfully
- ✅ Progress indicator shown
- ✅ Provisioning completes without errors
- ✅ Resource details displayed (EC2 instances, EBS volumes, VPC)
- ✅ Resource IDs shown
- ✅ Status shows "provisioned"

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-5.2: AWS Provisioning - With Container Deployment
**Priority**: High  
**Objective**: Verify AWS provisioning with ECS container deployment

**Steps**:
1. Navigate to provisioning page
2. Select "AWS" cloud path
3. Select "Deploy Container"
4. Enter container image URL: `nginx:latest`
5. Click "Provision" button
6. Wait for provisioning and deployment to complete

**Expected Results**:
- ✅ Container image URL field appears
- ✅ Valid Docker Hub URL accepted
- ✅ Provisioning completes successfully
- ✅ Container deployed to ECS
- ✅ Deployment endpoint URL displayed
- ✅ Deployment logs shown
- ✅ Status shows "deployed"

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-5.3: AWS Provisioning - Invalid Container URL
**Priority**: Medium  
**Objective**: Verify validation of container image URLs

**Steps**:
1. Navigate to provisioning page
2. Select "AWS" with "Deploy Container"
3. Enter invalid URL: `not-a-valid-url`
4. Click "Provision" button

**Expected Results**:
- ✅ Validation error displayed
- ✅ Error message indicates invalid URL format
- ✅ Provisioning does not start
- ✅ User can correct the URL

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 6: Provisioning - On-Premises IaaS Path

#### TC-6.1: On-Premises IaaS Provisioning
**Priority**: Critical  
**Objective**: Verify on-premises IaaS (VM) provisioning

**Steps**:
1. Navigate to provisioning page
2. Select "On-Premises" cloud path
3. Select "IaaS (Virtual Machines)"
4. Click "Provision" button
5. Wait for provisioning to complete

**Expected Results**:
- ✅ On-premises option selectable
- ✅ IaaS option selectable
- ✅ Provisioning starts successfully
- ✅ VMs created (or simulated in Mock Mode)
- ✅ VM details displayed (CPU, memory, storage)
- ✅ SSH connection details shown (IP, port, credentials)
- ✅ Status shows "provisioned"

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-6.2: On-Premises IaaS - Resource Matching
**Priority**: High  
**Objective**: Verify provisioned resources match configuration

**Steps**:
1. Complete TC-6.1
2. Compare provisioned resources with original configuration

**Expected Results**:
- ✅ Number of VMs matches instance_count
- ✅ CPU cores per VM matches cpu_cores
- ✅ Memory per VM matches memory_gb
- ✅ Storage matches capacity_gb
- ✅ All resources accounted for

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 7: Provisioning - On-Premises CaaS Path

#### TC-7.1: On-Premises CaaS Provisioning
**Priority**: Critical  
**Objective**: Verify on-premises CaaS (container) provisioning

**Steps**:
1. Navigate to provisioning page
2. Select "On-Premises" cloud path
3. Select "CaaS (Containers)"
4. Enter container image URL: `nginx:latest`
5. Click "Provision" button
6. Wait for provisioning to complete

**Expected Results**:
- ✅ CaaS option selectable
- ✅ Container image URL field appears
- ✅ Valid URL accepted
- ✅ Provisioning starts successfully
- ✅ Containers created
- ✅ Container details displayed
- ✅ Endpoint URL shown
- ✅ Resource limits applied
- ✅ Status shows "deployed"

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-7.2: CaaS - Environment Variables
**Priority**: Medium  
**Objective**: Verify environment variables can be injected into containers

**Steps**:
1. Navigate to provisioning page
2. Select "On-Premises" → "CaaS"
3. Enter container image URL
4. Add environment variables (if UI supports):
   - `ENV_VAR_1=value1`
   - `ENV_VAR_2=value2`
5. Provision container

**Expected Results**:
- ✅ Environment variable input available
- ✅ Multiple variables can be added
- ✅ Variables passed to container
- ✅ Deployment successful

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

**Notes**: _Check if UI supports env var input, or if it's API-only_

---

### TEST SUITE 8: Monitoring Dashboard

#### TC-8.1: Monitoring Dashboard - Initial View
**Priority**: High  
**Objective**: Verify monitoring dashboard displays correctly

**Steps**:
1. After provisioning resources (any path), navigate to monitoring page
2. View dashboard

**Expected Results**:
- ✅ Dashboard loads successfully
- ✅ List of provisioned resources displayed
- ✅ Current metrics shown for each resource
- ✅ Metrics include: CPU, Memory, Storage, Network
- ✅ Utilization percentages displayed
- ✅ Visual indicators (progress bars, charts)
- ✅ Timestamp of last update shown

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-8.2: Monitoring - Auto-Refresh
**Priority**: High  
**Objective**: Verify metrics auto-refresh every 30 seconds

**Steps**:
1. View monitoring dashboard
2. Note current metric values and timestamp
3. Wait 30-35 seconds
4. Observe dashboard

**Expected Results**:
- ✅ Metrics update automatically after 30 seconds
- ✅ Timestamp updates
- ✅ New metric values displayed
- ✅ No page reload required
- ✅ Updates smooth without flickering

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-8.3: Monitoring - Historical Metrics
**Priority**: Medium  
**Objective**: Verify historical metrics for different time ranges

**Steps**:
1. View monitoring dashboard
2. Select "1 Hour" time range
3. Select "24 Hours" time range
4. Select "7 Days" time range

**Expected Results**:
- ✅ Time range selector visible
- ✅ Historical data displayed for each range
- ✅ Charts/graphs show trends over time
- ✅ Data appropriate for selected range
- ✅ Switching between ranges works smoothly

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-8.4: Monitoring - High Utilization Alerts
**Priority**: High  
**Objective**: Verify alerts generated when utilization exceeds 80%

**Steps**:
1. View monitoring dashboard
2. Look for resources with >80% utilization
3. Check alert indicators

**Expected Results**:
- ✅ Resources with >80% utilization highlighted
- ✅ Visual indicator (red/orange color, warning icon)
- ✅ Alert message displayed
- ✅ Alert includes resource name and metric type
- ✅ Alerts update in real-time

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

**Notes**: _May need to simulate high utilization or wait for natural occurrence_

---

#### TC-8.5: Monitoring - Resource Health Status
**Priority**: High  
**Objective**: Verify resource health/reachability status

**Steps**:
1. View monitoring dashboard
2. Check health status for each resource
3. If possible, stop a resource and observe status change

**Expected Results**:
- ✅ Health status displayed for each resource
- ✅ Status indicators: Healthy, Unhealthy, Unreachable
- ✅ Color coding (green=healthy, red=unhealthy)
- ✅ Status updates when resource state changes
- ✅ Unreachable resources clearly marked

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-8.6: Monitoring - No Resources
**Priority**: Low  
**Objective**: Verify dashboard handles no provisioned resources

**Steps**:
1. Before provisioning any resources, navigate to monitoring page
2. View dashboard

**Expected Results**:
- ✅ Dashboard loads without errors
- ✅ Message displayed: "No resources provisioned"
- ✅ Helpful guidance shown (e.g., "Provision resources first")
- ✅ No broken UI elements

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 9: Security & Data Protection

#### TC-9.1: Password Security
**Priority**: Critical  
**Objective**: Verify passwords are hashed and not stored in plaintext

**Steps**:
1. Register a new user with password: `TestPassword123!`
2. Access database directly:
   ```bash
   docker-compose exec database psql -U hybrid_cloud_user -d hybrid_cloud
   SELECT username, password_hash FROM users;
   ```

**Expected Results**:
- ✅ Password not visible in plaintext
- ✅ Password hash stored (bcrypt format)
- ✅ Hash starts with `$2b$` or `$2a$`
- ✅ Hash is long string (60+ characters)

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-9.2: SQL Injection Prevention
**Priority**: Critical  
**Objective**: Verify system prevents SQL injection attacks

**Steps**:
1. On login page, enter username: `admin' OR '1'='1`
2. Enter any password
3. Click "Login"

**Expected Results**:
- ✅ Login fails
- ✅ No SQL error displayed
- ✅ Generic error message shown
- ✅ No unauthorized access granted
- ✅ Application remains stable

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-9.3: XSS Prevention
**Priority**: High  
**Objective**: Verify system prevents cross-site scripting attacks

**Steps**:
1. On configuration page, enter CPU Cores: `<script>alert('XSS')</script>`
2. Submit form

**Expected Results**:
- ✅ Script not executed
- ✅ Input sanitized or rejected
- ✅ No alert popup appears
- ✅ Input displayed as plain text if shown
- ✅ Application remains secure

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-9.4: Session Security
**Priority**: High  
**Objective**: Verify session tokens are secure

**Steps**:
1. Log in as `testuser`
2. Open browser developer tools → Application/Storage → Cookies
3. Examine session cookie

**Expected Results**:
- ✅ Session cookie exists
- ✅ Cookie has HttpOnly flag (if HTTPS enabled)
- ✅ Cookie has Secure flag (if HTTPS enabled)
- ✅ Cookie value is random/unpredictable
- ✅ Cookie has expiration time

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-9.5: Credential Encryption
**Priority**: Critical  
**Objective**: Verify AWS credentials are encrypted in database

**Steps**:
1. Provision AWS resources (credentials stored)
2. Access database:
   ```bash
   docker-compose exec database psql -U hybrid_cloud_user -d hybrid_cloud
   SELECT * FROM credentials;
   ```

**Expected Results**:
- ✅ Credentials not visible in plaintext
- ✅ Encrypted values stored
- ✅ Encryption uses AES-256
- ✅ Encrypted data is unreadable

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 10: API Endpoints

#### TC-10.1: API - Health Check
**Priority**: Medium  
**Objective**: Verify API is accessible and responding

**Steps**:
1. Open terminal or API client (Postman, curl)
2. Execute:
   ```bash
   curl http://localhost:10000/api/health
   ```

**Expected Results**:
- ✅ Response received
- ✅ Status code: 200 OK
- ✅ Response body indicates healthy status
- ✅ Response time < 1 second

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-10.2: API - Authentication Endpoints
**Priority**: High  
**Objective**: Verify API authentication endpoints work correctly

**Steps**:
1. Register via API:
   ```bash
   curl -X POST http://localhost:10000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username":"apiuser","password":"ApiPass123!"}'
   ```
2. Login via API:
   ```bash
   curl -X POST http://localhost:10000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"apiuser","password":"ApiPass123!"}'
   ```

**Expected Results**:
- ✅ Register returns 201 Created
- ✅ Login returns 200 OK
- ✅ Login response includes session token
- ✅ Error responses have proper status codes
- ✅ JSON responses well-formatted

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-10.3: API - Configuration Validation
**Priority**: High  
**Objective**: Verify API validates configuration data

**Steps**:
1. Get session token from TC-10.2
2. Validate configuration:
   ```bash
   curl -X POST http://localhost:10000/api/configurations/validate \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{
       "compute": {"cpu_cores": 8, "memory_gb": 32, "instance_count": 3},
       "storage": {"type": "SSD", "capacity_gb": 500, "iops": 3000},
       "network": {"bandwidth_gbps": 10, "data_transfer_gb": 1000},
       "workload": {"utilization_percent": 75, "operating_hours": 720}
     }'
   ```

**Expected Results**:
- ✅ Valid configuration returns 200 OK
- ✅ Response indicates validation passed
- ✅ Invalid configuration returns 400 Bad Request
- ✅ Error messages specific and helpful

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-10.4: API - TCO Calculation
**Priority**: High  
**Objective**: Verify API calculates TCO correctly

**Steps**:
1. Create configuration via API (save config_id)
2. Calculate TCO:
   ```bash
   curl -X POST http://localhost:10000/api/tco/<config_id>/calculate \
     -H "Authorization: Bearer <token>"
   ```
3. Retrieve results:
   ```bash
   curl http://localhost:10000/api/tco/<config_id> \
     -H "Authorization: Bearer <token>"
   ```

**Expected Results**:
- ✅ Calculate returns 200 OK
- ✅ Results include on-premises and AWS costs
- ✅ Cost breakdown by category included
- ✅ Projections for 1y, 3y, 5y included
- ✅ All values are valid numbers
- ✅ JSON structure correct

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 11: User Interface & Usability

#### TC-11.1: UI - Responsive Design
**Priority**: Medium  
**Objective**: Verify UI works on different screen sizes

**Steps**:
1. Open application in browser
2. Resize browser window to different widths:
   - Desktop: 1920px
   - Tablet: 768px
   - Mobile: 375px
3. Navigate through all pages

**Expected Results**:
- ✅ Layout adapts to screen size
- ✅ All content accessible on small screens
- ✅ No horizontal scrolling required
- ✅ Buttons and forms usable on mobile
- ✅ Text readable at all sizes
- ✅ Navigation menu works on mobile

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-11.2: UI - Navigation
**Priority**: High  
**Objective**: Verify navigation works correctly throughout app

**Steps**:
1. Log in
2. Click through all navigation links
3. Use browser back/forward buttons
4. Test breadcrumbs (if present)

**Expected Results**:
- ✅ All navigation links work
- ✅ Current page highlighted in navigation
- ✅ Back button works correctly
- ✅ Forward button works correctly
- ✅ No broken links
- ✅ URLs are meaningful and bookmarkable

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-11.3: UI - Error Messages
**Priority**: High  
**Objective**: Verify error messages are clear and helpful

**Steps**:
1. Trigger various errors (invalid input, network issues, etc.)
2. Observe error messages

**Expected Results**:
- ✅ Error messages displayed prominently
- ✅ Messages are clear and specific
- ✅ Messages explain what went wrong
- ✅ Messages suggest how to fix the issue
- ✅ No technical jargon or stack traces
- ✅ Errors dismissible or auto-hide

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-11.4: UI - Loading States
**Priority**: Medium  
**Objective**: Verify loading indicators shown during operations

**Steps**:
1. Perform operations that take time:
   - TCO calculation
   - Provisioning
   - Q&A responses
2. Observe UI during processing

**Expected Results**:
- ✅ Loading indicator shown during processing
- ✅ Indicator is visible and clear
- ✅ User cannot submit duplicate requests
- ✅ Buttons disabled during processing
- ✅ Loading indicator disappears when complete

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-11.5: UI - Form Validation Feedback
**Priority**: High  
**Objective**: Verify form validation provides immediate feedback

**Steps**:
1. On configuration page, enter invalid values
2. Tab to next field or click outside field
3. Observe validation feedback

**Expected Results**:
- ✅ Validation occurs on blur or submit
- ✅ Error messages appear near invalid fields
- ✅ Invalid fields highlighted (red border)
- ✅ Error messages specific to the issue
- ✅ Valid fields show success indicator (optional)
- ✅ Form cannot be submitted with errors

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 12: Performance & Reliability

#### TC-12.1: Performance - Page Load Times
**Priority**: Medium  
**Objective**: Verify pages load within acceptable time

**Steps**:
1. Open browser developer tools → Network tab
2. Navigate to each page
3. Record load times

**Expected Results**:
- ✅ Home/Configuration page: < 2 seconds
- ✅ TCO Results page: < 3 seconds
- ✅ Q&A page: < 2 seconds
- ✅ Provisioning page: < 2 seconds
- ✅ Monitoring page: < 3 seconds
- ✅ No timeout errors

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-12.2: Performance - TCO Calculation Time
**Priority**: High  
**Objective**: Verify TCO calculation completes quickly

**Steps**:
1. Submit configuration
2. Measure time until results displayed

**Expected Results**:
- ✅ Calculation completes in < 5 seconds
- ✅ Progress indicator shown
- ✅ No timeout errors
- ✅ Results accurate and complete

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-12.3: Performance - Provisioning Time
**Priority**: Medium  
**Objective**: Verify provisioning completes in reasonable time

**Steps**:
1. Start provisioning (any path)
2. Measure time until completion

**Expected Results**:
- ✅ AWS provisioning: < 30 seconds
- ✅ IaaS provisioning: < 60 seconds
- ✅ CaaS provisioning: < 45 seconds
- ✅ Progress updates shown
- ✅ No timeout errors

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-12.4: Reliability - Service Restart
**Priority**: High  
**Objective**: Verify application recovers from service restart

**Steps**:
1. Create configuration and provision resources
2. Restart services:
   ```bash
   docker-compose restart
   ```
3. Wait for services to be healthy
4. Log in and check data

**Expected Results**:
- ✅ All services restart successfully
- ✅ Data persists after restart
- ✅ Configurations still accessible
- ✅ Provisioned resources still tracked
- ✅ User sessions may need re-login (acceptable)

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-12.5: Reliability - Database Connection Loss
**Priority**: High  
**Objective**: Verify application handles database disconnection gracefully

**Steps**:
1. Stop database:
   ```bash
   docker-compose stop database
   ```
2. Try to perform operations in UI
3. Restart database:
   ```bash
   docker-compose start database
   ```
4. Retry operations

**Expected Results**:
- ✅ Graceful error messages when DB unavailable
- ✅ No application crashes
- ✅ Application recovers when DB restored
- ✅ No data corruption
- ✅ User can retry operations

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-12.6: Reliability - LocalStack Connection Loss
**Priority**: Medium  
**Objective**: Verify application handles LocalStack disconnection

**Steps**:
1. Stop LocalStack:
   ```bash
   docker-compose stop localstack
   ```
2. Try to provision AWS resources
3. Restart LocalStack:
   ```bash
   docker-compose start localstack
   ```
4. Retry provisioning

**Expected Results**:
- ✅ Clear error message when LocalStack unavailable
- ✅ No application crashes
- ✅ Application recovers when LocalStack restored
- ✅ User can retry provisioning

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 13: Browser Compatibility

#### TC-13.1: Chrome Browser
**Priority**: High  
**Objective**: Verify application works in Chrome

**Steps**:
1. Open application in Google Chrome (latest version)
2. Execute critical test cases (TC-1.2, TC-2.1, TC-3.1, TC-5.1)

**Expected Results**:
- ✅ All features work correctly
- ✅ UI renders properly
- ✅ No console errors
- ✅ Forms submit correctly
- ✅ JavaScript functions work

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-13.2: Firefox Browser
**Priority**: High  
**Objective**: Verify application works in Firefox

**Steps**:
1. Open application in Mozilla Firefox (latest version)
2. Execute critical test cases

**Expected Results**:
- ✅ All features work correctly
- ✅ UI renders properly
- ✅ No console errors
- ✅ Consistent with Chrome experience

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-13.3: Safari Browser
**Priority**: Medium  
**Objective**: Verify application works in Safari

**Steps**:
1. Open application in Safari (latest version)
2. Execute critical test cases

**Expected Results**:
- ✅ All features work correctly
- ✅ UI renders properly
- ✅ No console errors

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

### TEST SUITE 14: Data Persistence & Integrity

#### TC-14.1: Configuration Persistence
**Priority**: High  
**Objective**: Verify configurations are saved and retrievable

**Steps**:
1. Create configuration A
2. Create configuration B
3. Log out and log back in
4. Retrieve both configurations

**Expected Results**:
- ✅ Both configurations saved
- ✅ Configurations retrievable after logout
- ✅ All configuration data intact
- ✅ Configurations associated with correct user

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-14.2: TCO Results Persistence
**Priority**: High  
**Objective**: Verify TCO results are saved and retrievable

**Steps**:
1. Calculate TCO for a configuration
2. Navigate away from results page
3. Return to results page using configuration ID
4. Restart services and check again

**Expected Results**:
- ✅ Results saved in database
- ✅ Results retrievable by configuration ID
- ✅ All cost data intact
- ✅ Results persist after service restart

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-14.3: Provisioning State Persistence
**Priority**: High  
**Objective**: Verify provisioning state is tracked correctly

**Steps**:
1. Provision resources
2. Restart services
3. Check provisioning status

**Expected Results**:
- ✅ Provisioning state saved
- ✅ Resource IDs preserved
- ✅ Status accurate after restart
- ✅ Terraform state preserved

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

#### TC-14.4: Conversation History Persistence
**Priority**: Medium  
**Objective**: Verify Q&A conversation history is saved

**Steps**:
1. Ask 3 questions in Q&A
2. Navigate away
3. Return to Q&A page
4. Restart services and check again

**Expected Results**:
- ✅ Conversation history saved
- ✅ All messages retrievable
- ✅ Messages in correct order
- ✅ History persists after restart

**Actual Results**: _[To be filled during testing]_

**Status**: ⬜ Pass / ⬜ Fail / ⬜ Blocked

---

---

## Test Execution Checklist

### Pre-Execution
- [ ] Environment setup complete
- [ ] All services running and healthy
- [ ] Test data prepared
- [ ] Browser(s) ready
- [ ] API client ready (if testing APIs)

### Critical Path Tests (Must Pass)
- [ ] TC-1.1: User Registration
- [ ] TC-1.2: User Login
- [ ] TC-2.1: Valid Configuration Submission
- [ ] TC-3.1: TCO Results Display
- [ ] TC-5.1: AWS Provisioning
- [ ] TC-6.1: On-Premises IaaS Provisioning
- [ ] TC-7.1: On-Premises CaaS Provisioning
- [ ] TC-8.1: Monitoring Dashboard
- [ ] TC-9.1: Password Security
- [ ] TC-9.2: SQL Injection Prevention

### High Priority Tests (Should Pass)
- [ ] All remaining "Priority: High" test cases

### Medium/Low Priority Tests (Nice to Have)
- [ ] All remaining "Priority: Medium" test cases
- [ ] All remaining "Priority: Low" test cases

### Post-Execution
- [ ] All critical tests passed
- [ ] Issues documented
- [ ] Test results compiled
- [ ] Sign-off obtained (if required)

---

## Issue Reporting Template

When you find an issue during testing, document it using this template:

```markdown
### Issue #[NUMBER]: [Brief Description]

**Test Case**: TC-X.X  
**Priority**: Critical / High / Medium / Low  
**Severity**: Blocker / Major / Minor / Trivial

**Environment**:
- Browser: [Chrome/Firefox/Safari] [Version]
- OS: [macOS/Windows/Linux]
- Date: [YYYY-MM-DD]

**Steps to Reproduce**:
1. Step 1
2. Step 2
3. Step 3

**Expected Result**:
[What should happen]

**Actual Result**:
[What actually happened]

**Screenshots/Logs**:
[Attach if available]

**Workaround**:
[If any workaround exists]

**Additional Notes**:
[Any other relevant information]
```

---

## Test Summary Report Template

After completing UAT, fill out this summary:

```markdown
# UAT Summary Report
**Date**: [YYYY-MM-DD]  
**Tester**: [Name]  
**Version**: 1.0

## Test Statistics
- Total Test Cases: [X]
- Passed: [X]
- Failed: [X]
- Blocked: [X]
- Pass Rate: [X%]

## Critical Issues Found
1. [Issue description]
2. [Issue description]

## Recommendations
- [ ] Ready for production
- [ ] Needs fixes before production
- [ ] Requires additional testing

## Sign-off
**Tester**: ________________  
**Date**: ________________

**Product Owner**: ________________  
**Date**: ________________
```

---

## Quick Test Scenarios

For rapid smoke testing, execute these end-to-end scenarios:

### Scenario 1: Complete User Journey (15 minutes)
1. Register new user
2. Log in
3. Submit configuration
4. View TCO results
5. Ask 2 questions in Q&A
6. Provision AWS resources
7. View monitoring dashboard
8. Log out

**Success Criteria**: All steps complete without errors

---

### Scenario 2: Configuration Variations (10 minutes)
1. Submit minimal configuration (low values)
2. Submit maximal configuration (high values)
3. Submit typical configuration (medium values)
4. Compare TCO results

**Success Criteria**: All configurations accepted, results reasonable

---

### Scenario 3: All Provisioning Paths (20 minutes)
1. Provision AWS infrastructure only
2. Provision AWS with container
3. Provision On-Premises IaaS
4. Provision On-Premises CaaS
5. Check monitoring for all resources

**Success Criteria**: All provisioning paths work, resources tracked

---

### Scenario 4: Security Testing (10 minutes)
1. Attempt SQL injection
2. Attempt XSS
3. Verify password hashing
4. Test session timeout (if time permits)

**Success Criteria**: All attacks prevented, security measures working

---

## Troubleshooting Common Issues

### Services Not Starting
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose down
docker-compose up -d

# Check service health
docker-compose ps
```

### Database Connection Errors
```bash
# Verify database is running
docker-compose ps database

# Check database logs
docker-compose logs database

# Restart database
docker-compose restart database
```

### LocalStack Not Responding
```bash
# Check LocalStack health
curl http://localhost:4566/_localstack/health

# Restart LocalStack
docker-compose restart localstack

# Check logs
docker-compose logs localstack
```

### Port Already in Use
```bash
# Find process using port
lsof -i :10000
lsof -i :10001

# Kill process or change port in docker-compose.yml
```

---

## Notes

- **Test Duration**: Full UAT suite takes approximately 3-4 hours
- **Quick Smoke Test**: Critical path tests take approximately 45 minutes
- **Recommended Approach**: Start with critical path, then expand to high priority tests
- **Documentation**: Take screenshots of any issues found
- **Environment**: Always test on a clean environment (fresh docker-compose up)

---

**End of UAT Test Plan**
