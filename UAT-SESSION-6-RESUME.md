# UAT Session 6 Resume Guide
**Date**: 2026-04-05  
**Status**: Ready to Resume UAT Testing  
**Previous Session**: Session 5 (Completed Step 3.6 - AWS Provisioning)

---

## 📋 Quick Summary

### What Was Fixed in Session 5

**Issues #16, #17, and #18 have been resolved!**

✅ **Issue #16 - Provisioning JavaScript URLs** (Hardcoded localhost:8000)
- Fixed JavaScript fetch calls to use relative URLs
- Changed `/api/provision` endpoints to route through Web UI proxy

✅ **Issue #17 - Flask Async Support** (Missing asgiref package)
- Installed `asgiref==3.11.1` for Flask async view support
- API async routes now work correctly

✅ **Issue #18 - LocalStack Endpoint** (Hardcoded localhost:4566)
- Updated `.env` to use Docker service name: `http://localstack:4566`
- Modified LocalStack adapter to read from `LOCALSTACK_ENDPOINT` environment variable
- All LocalStack connections now work inside Docker

### Testing Completed

✅ **Step 3.6: AWS Provisioning** - PASS
- Configuration submitted successfully
- TCO calculated correctly
- Provisioning completed without errors
- Resources verified in LocalStack:
  - 3 EC2 instances (m5.2xlarge, running)
  - 6 EBS volumes (3x8GB + 3x500GB)
  - VPC and networking configured
  - Security group created

✅ **Code Changes Committed**
- All fixes committed and ready to push
- Services running with updated code

---

## 🚀 How to Resume UAT

### Step 1: Verify Services Are Running

```bash
cd hybrid_cloud_controller
docker compose ps
```

**Expected**: All 4 services should be "Up" and healthy:
- hybrid-cloud-db (Up, healthy)
- hybrid-cloud-localstack (Up, healthy)
- hybrid-cloud-api (Up)
- hybrid-cloud-web-ui (Up)

If services are down:
```bash
docker compose up -d
```

### Step 2: Open Web UI

```bash
open http://localhost:10001
```

Or navigate to: http://localhost:10001

### Step 3: Login

Use your existing test account:
- **Username**: `testuser`
- **Password**: `TestPassword123!`

If you need to create a new account, register first.

---

## 📝 UAT Test Plan - Where to Resume

### Completed Steps (9/14 = 64%)

1. ✅ Step 1: Start Application
2. ✅ Step 2: Verify Services
3. ✅ Step 3.1: User Registration
4. ✅ Step 3.2: User Login
5. ✅ Step 3.3: Submit Configuration
6. ✅ Step 3.4: Review TCO Results
7. ✅ Step 3.5: Q&A Service
8. ✅ Step 3.6: AWS Provisioning
9. ✅ Step 3.7: On-Premises IaaS Provisioning

### Resume From Here (Step 3.8)

**Current Position**: Step 3.8 - On-Premises CaaS Provisioning

**Test Configuration** (reuse from previous session):
- CPU: 8 cores
- Memory: 32GB
- Instances: 3
- Storage: SSD, 500GB, 3000 IOPS
- Network: 10Gbps, 1000GB transfer
- Workload: 75% utilization, 720 hours

---

## 🧪 Test Steps to Execute

### Step 3.7: Test On-Premises IaaS Provisioning

**Status**: ✅ COMPLETED

**Results**:
- ✅ Provisioning completed successfully
- ✅ 3 Ubuntu VMs created (8 cores, 32GB RAM each)
- ✅ SSH connection details provided for each VM
- ✅ All VMs in running state
- ✅ Mock Mode worked correctly
- ✅ No errors encountered

**Provision ID**: `a83613bb-8f75-4a90-a6d3-b3cf94d4c543`

---

### Step 3.8: Test On-Premises CaaS Provisioning (NEXT)

**Objective**: Verify IaaS (VM) provisioning works

**Steps**:
1. From home page, click "Provision Resources" button
2. Select "On-Premises" → "IaaS (Virtual Machines)"
3. Check "Mock Mode" (for testing - no real VMs)
4. Click "Start Provisioning"
5. Wait for provisioning to complete
6. Verify VM details are displayed
7. Check SSH connection details (IP, port, credentials)

**Expected Results**:
- ✅ Provisioning request succeeds (no "Load failed" error)
- ✅ Provision ID is generated
- ✅ VM details displayed (CPU, memory, storage)
- ✅ SSH connection details shown
- ✅ Status shows "provisioned"

**What Changed**: 
- Previously would have returned "Provisioning failed: Load failed" (404 error)
- Now forwards request to API service correctly
- Should simulate VM provisioning successfully

---

### Step 3.8: Test On-Premises CaaS Provisioning

**Objective**: Verify CaaS (container) provisioning works

**Steps**:
1. Navigate to provisioning page
2. Select "On-Premises" → "CaaS (Containers)"
3. Enter container image URL: `nginx:latest`
4. (Optional) Add environment variables: `{"NGINX_PORT": "8080"}`
5. Click "Start Provisioning"
6. Wait for provisioning to complete
7. Verify container details are displayed
8. Check endpoint URL

**Expected Results**:
- ✅ Provisioning request succeeds (no "Load failed" error)
- ✅ Provision ID is generated
- ✅ Container details displayed
- ✅ Endpoint URL shown
- ✅ Resource limits applied
- ✅ Status shows "deployed"

**What Changed**:
- Previously would have returned "Provisioning failed: Load failed" (404 error)
- Now forwards request to API service correctly
- Should deploy containers successfully

---

### Step 3.9: Test Monitoring Dashboard

**Objective**: Verify monitoring dashboard displays metrics

**Steps**:
1. From home page, click "View Dashboard" button
2. Verify resources list loads
3. Select a provisioned resource (from Steps 3.6-3.8)
4. Verify metrics display (CPU, memory, storage, network)
5. Change time range to "24 Hours"
6. Verify metrics update with time range
7. Wait 30 seconds and verify auto-refresh

**Expected Results**:
- ✅ Dashboard loads without errors (no "Failed to load monitoring data")
- ✅ Resources list displays provisioned resources
- ✅ Metrics load for provisioned resources
- ✅ Time range selector works
- ✅ Metrics update when time range changes
- ✅ Auto-refresh works every 30 seconds

**What Changed**:
- Previously returned "Failed to load monitoring data" (404 errors)
- Now forwards requests to API service correctly
- Should display resources and metrics successfully

**Note**: You should have resources from Step 3.6 (AWS) to monitor. Can provision more in Steps 3.7-3.8.

---

### Remaining Steps (Not Yet Tested)

**Step 4: Security Testing**
- Test authentication and authorization
- Verify session management
- Check input validation
- Test error handling

**Step 5: Validation Testing**
- Test data validation rules
- Verify error messages
- Check edge cases
- Test boundary conditions

**Step 6: API Testing (Optional)**
- Test API endpoints directly
- Verify response formats
- Check error codes
- Test rate limiting

---

## 🐛 Known Issues (Still Open)

### Cosmetic Issues (Low Priority)
1. **Issue #1**: Card height inconsistency on home page
2. **Issue #6**: Low contrast instruction text on configuration form
3. **Issue #9**: Q&A input field too small
4. **Issue #12**: Low contrast cost details on TCO results page

**Note**: These are cosmetic issues and don't block UAT. Can be fixed in a batch later.

### Enhancement Requests
1. **Issue #13**: Q&A service semantic understanding (future enhancement)

---

## 📊 UAT Progress Tracker

**Overall Progress**: 64% (9/14 steps completed)

**Critical Issues**:
- 11 Fixed ✅
- 0 Open ❌

**Cosmetic Issues**:
- 4 Open (deferred)

**Enhancement Requests**:
- 1 Open (future)

---

## 🔍 Troubleshooting

### If Provisioning Fails

1. **Check Web UI logs**:
   ```bash
   docker compose logs web_ui --tail=50
   ```

2. **Check API logs**:
   ```bash
   docker compose logs api --tail=50
   ```

3. **Verify LocalStack is healthy**:
   ```bash
   docker compose ps localstack
   curl http://localhost:4566/_localstack/health
   ```

4. **Restart services** (if needed):
   ```bash
   docker compose restart api web_ui
   ```

### If Monitoring Dashboard Fails

1. **Check if resources are provisioned**:
   - Monitoring requires provisioned resources to display data
   - Try provisioning first (Steps 3.6-3.8)

2. **Check API monitoring endpoints**:
   ```bash
   # Test resources endpoint (replace <token> with your session token)
   curl -H "Authorization: Bearer <token>" http://localhost:10000/api/monitoring/resources
   ```

3. **Check Web UI logs** for proxy errors:
   ```bash
   docker compose logs web_ui | grep monitoring
   ```

---

## 📚 Reference Documents

- **UAT Test Plan**: `UAT-TEST-PLAN.md` (full test cases)
- **Issue Tracker**: `UAT-ISSUES.md` (all issues documented)
- **Session 5 Checkpoint**: `UAT-SESSION-5-RESUME.md` (previous session)
- **Spec Documentation**: `.kiro/specs/uat-proxy-endpoints-fix/` (fix details)

---

## ✅ Success Criteria

**For this session, UAT is successful if**:

1. ✅ IaaS provisioning completes without errors
2. ✅ CaaS provisioning completes without errors
3. ✅ Monitoring dashboard loads without errors
4. ✅ Resources and metrics display correctly in monitoring dashboard
5. ✅ All remaining UAT steps (4, 5, 6) complete successfully

---

## 🎯 Next Actions

1. **Start Docker services** (if not running)
2. **Open Web UI** at http://localhost:10001
3. **Login** with testuser account
4. **Test Step 3.7** - IaaS Provisioning
5. **Test Step 3.8** - CaaS Provisioning
6. **Test Step 3.9** - Monitoring Dashboard
7. **Continue with Steps 4-6** - Security, Validation, API Testing
8. **Document any new issues** in UAT-ISSUES.md
9. **Create Session 6 Checkpoint** when complete

---

**Status**: Ready to resume UAT testing ✅  
**Blockers**: None - All critical issues resolved  
**Recommendation**: Start with Step 3.7 (IaaS Provisioning) and work through Steps 3.7-3.9

---

**Good luck with UAT Session 6!** 🚀
