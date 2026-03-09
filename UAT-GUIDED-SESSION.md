# Guided UAT Session - Hybrid Cloud Controller
**Interactive Test Drive Guide**

---

## 🚀 STEP 1: Start the Application

### Option A: Using Docker Compose (Recommended)

```bash
# Navigate to project directory
cd hybrid_cloud_controller

# Ensure .env file exists
cp .env.example .env

# Start all services
docker compose up -d

# Wait 30-60 seconds for services to start
# Check service status
docker compose ps
```

**Expected Output**: All 4 services should show "Up" status:
- `hybrid-cloud-db` (healthy)
- `hybrid-cloud-localstack` (healthy)
- `hybrid-cloud-api` (Up)
- `hybrid-cloud-web-ui` (Up)

**If services fail to start**:
```bash
# Check logs
docker compose logs

# Restart specific service
docker compose restart <service-name>
```

### Option B: Local Development (Without Docker)

If Docker is not available, you can run services locally:

```bash
# 1. Start PostgreSQL (install separately or use Docker for DB only)
docker run -d --name hybrid-cloud-db \
  -e POSTGRES_DB=hybrid_cloud \
  -e POSTGRES_USER=hybrid_cloud_user \
  -e POSTGRES_PASSWORD=dev_password_change_me \
  -p 5432:5432 \
  postgres:16-alpine

# 2. Start LocalStack
docker run -d --name hybrid-cloud-localstack \
  -e SERVICES=ec2,ebs,s3,ecs,pricing \
  -p 4566:4566 \
  localstack/localstack:latest

# 3. Install dependencies
pip install uv
uv pip install -r requirements-development.txt

# 4. Start API (in one terminal)
python -m packages.api.app

# 5. Start Web UI (in another terminal)
python -m packages.web_ui.app
```

---

## ✅ STEP 2: Verify Services Are Running

Open your browser and check these URLs:

1. **Web UI**: http://localhost:10001
   - Should show login/register page
   
2. **API Health**: http://localhost:10000/api/health
   - Should return JSON with health status

3. **LocalStack**: http://localhost:4566/_localstack/health
   - Should return JSON with service statuses

**✋ CHECKPOINT**: All three URLs should respond. If not, check logs and troubleshoot.

---

## 🧪 STEP 3: Test Drive - Complete User Journey

### 3.1: User Registration

1. Open browser to: http://localhost:10001
2. Click "Register" link
3. Fill in:
   - Username: `testuser`
   - Password: `TestPassword123!`
4. Click "Register" button

**✅ Expected**: 
- Success message displayed
- Redirected to login page

**📝 Notes**: _[Write your observations here]_

---

### 3.2: User Login

1. On login page, enter:
   - Username: `testuser`
   - Password: `TestPassword123!`
2. Click "Login" button

**✅ Expected**:
- Login successful
- Redirected to configuration page (home)
- Navigation shows you're logged in

**📝 Notes**: _[Write your observations here]_

---

### 3.3: Submit Configuration

You should now be on the configuration input page. Fill in these values:

**Compute Specifications**:
- CPU Cores: `8`
- Memory (GB): `32`
- Instance Count: `3`

**Storage Specifications**:
- Type: `SSD`
- Capacity (GB): `500`
- IOPS: `3000`

**Network Specifications**:
- Bandwidth (Gbps): `10`
- Data Transfer (GB): `1000`

**Workload Profile**:
- Utilization (%): `75`
- Operating Hours: `720`

Click "Calculate TCO" button

**✅ Expected**:
- Form validates successfully
- Redirected to TCO results page
- Loading indicator shown during calculation

**📝 Notes**: _[Write your observations here]_

---

### 3.4: Review TCO Results

You should now see the TCO comparison results.

**Check the following**:

1. **Side-by-Side Comparison**:
   - [ ] On-Premises total cost displayed
   - [ ] AWS total cost displayed
   - [ ] Winner badge shown (lower cost option)

2. **Cost Breakdown**:
   - [ ] On-Premises breakdown shows: Hardware, Power, Cooling, Maintenance, Data Transfer
   - [ ] AWS breakdown shows: EC2, EBS, S3, Data Transfer
   - [ ] All values are positive numbers
   - [ ] Currency formatting looks correct

3. **Projections**:
   - [ ] Click "1-Year" tab - shows 1-year costs
   - [ ] Click "3-Year" tab - shows 3-year costs (should be >= 1-year)
   - [ ] Click "5-Year" tab - shows 5-year costs (should be >= 3-year)

**✅ Expected**: All cost data displays correctly, projections make sense

**📝 Notes**: 
- On-Premises Total: $_________
- AWS Total: $_________
- Winner: _________
- Observations: _[Write here]_

---

### 3.5: Ask Questions (Q&A Service)

1. Click "Ask Questions" button or navigate to Q&A page
2. Enter question: `Why are power costs so high?`
3. Press Enter or click "Send"
4. Wait for response

**✅ Expected**:
- Question appears in chat
- Response received within a few seconds
- Response is relevant and references your configuration

**Try more questions**:
- `Compare storage costs between on-premises and AWS`
- `Which option do you recommend for my workload?`
- `What are the main cost drivers?`

**📝 Notes**: _[Write your observations about Q&A quality]_

---

### 3.6: Provision AWS Resources

1. Navigate back to TCO results or go to provisioning page
2. Select "AWS" cloud path
3. Choose one of:
   - **Option A**: Infrastructure Only (no container)
   - **Option B**: Deploy Container (enter `nginx:latest`)
4. Click "Provision" button
5. Watch provisioning progress

**✅ Expected**:
- Provisioning starts
- Progress indicator shown
- Provisioning completes (may take 15-30 seconds)
- Resource details displayed:
  - EC2 instance IDs
  - EBS volume IDs
  - VPC/networking details
  - (If container) ECS deployment endpoint

**📝 Notes**: 
- Provisioning time: _______ seconds
- Resources created: _[List here]_
- Any errors: _[Note here]_

---

### 3.7: Provision On-Premises IaaS

Let's test the on-premises path:

1. Go back to provisioning page (or create new configuration)
2. Select "On-Premises" cloud path
3. Select "IaaS (Virtual Machines)"
4. Click "Provision" button
5. Watch provisioning progress

**✅ Expected**:
- Provisioning starts
- VMs created (or simulated in Mock Mode)
- VM details displayed:
  - CPU, memory, storage specs
  - SSH connection details (IP, port, credentials)
- Status shows "provisioned"

**📝 Notes**: 
- Provisioning time: _______ seconds
- VM details: _[Note here]_
- Connection info provided: Yes / No

---

### 3.8: Provision On-Premises CaaS

Now test container deployment:

1. Go to provisioning page
2. Select "On-Premises" cloud path
3. Select "CaaS (Containers)"
4. Enter container image: `nginx:latest`
5. Click "Provision" button

**✅ Expected**:
- Container provisioning starts
- Container created successfully
- Container details displayed:
  - Container ID
  - Endpoint URL
  - Resource limits
- Status shows "deployed"

**📝 Notes**: 
- Provisioning time: _______ seconds
- Container endpoint: _[URL here]_
- Any issues: _[Note here]_

---

### 3.9: Monitor Resources

1. Navigate to Monitoring Dashboard
2. View current metrics

**Check the following**:

1. **Resource List**:
   - [ ] All provisioned resources listed
   - [ ] Resource names/IDs shown

2. **Current Metrics**:
   - [ ] CPU utilization displayed
   - [ ] Memory utilization displayed
   - [ ] Storage utilization displayed
   - [ ] Network throughput displayed
   - [ ] Timestamps shown

3. **Auto-Refresh**:
   - [ ] Wait 30-35 seconds
   - [ ] Metrics update automatically
   - [ ] Timestamp changes

4. **Historical Metrics**:
   - [ ] Select "1 Hour" time range
   - [ ] Select "24 Hours" time range
   - [ ] Select "7 Days" time range
   - [ ] Charts/graphs display correctly

5. **Alerts** (if any resources >80% utilization):
   - [ ] High utilization highlighted
   - [ ] Visual indicator (color, icon)
   - [ ] Alert message clear

**✅ Expected**: Dashboard displays all metrics, auto-refreshes, historical data available

**📝 Notes**: 
- Number of resources monitored: _______
- Metrics updating: Yes / No
- Any issues: _[Note here]_

---

## 🔒 STEP 4: Security Testing

### 4.1: Test SQL Injection Prevention

1. Log out
2. On login page, enter:
   - Username: `admin' OR '1'='1`
   - Password: `anything`
3. Click "Login"

**✅ Expected**:
- Login fails
- Generic error message (not SQL error)
- No unauthorized access

**📝 Result**: Pass / Fail

---

### 4.2: Test XSS Prevention

1. Log in
2. On configuration page, enter:
   - CPU Cores: `<script>alert('XSS')</script>`
3. Try to submit

**✅ Expected**:
- Script not executed
- No alert popup
- Input rejected or sanitized

**📝 Result**: Pass / Fail

---

### 4.3: Verify Password Hashing

Open a terminal and check the database:

```bash
docker compose exec database psql -U hybrid_cloud_user -d hybrid_cloud

# In psql prompt:
SELECT username, password_hash FROM users;

# Exit psql:
\q
```

**✅ Expected**:
- Password NOT visible in plaintext
- Hash starts with `$2b$` or `$2a$` (bcrypt)
- Hash is long string (60+ characters)

**📝 Result**: Pass / Fail

---

## 🧪 STEP 5: Validation Testing

### 5.1: Test Invalid Configuration

1. Go to configuration page
2. Enter invalid values:
   - CPU Cores: `-5` (negative)
   - Utilization: `150` (exceeds 100)
   - Operating Hours: `800` (exceeds 744)
3. Try to submit

**✅ Expected**:
- Validation errors displayed
- Specific error messages for each field
- Form not submitted

**📝 Result**: Pass / Fail

---

### 5.2: Test Required Fields

1. On configuration page, leave CPU Cores empty
2. Fill other fields
3. Try to submit

**✅ Expected**:
- Validation error for required field
- Form not submitted

**📝 Result**: Pass / Fail

---

## 🌐 STEP 6: API Testing (Optional)

Test the API directly using curl or a REST client:

### 6.1: Health Check

```bash
curl http://localhost:10000/api/health
```

**✅ Expected**: JSON response with health status

---

### 6.2: Register via API

```bash
curl -X POST http://localhost:10000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"apiuser","password":"ApiPass123!"}'
```

**✅ Expected**: 201 Created response

---

### 6.3: Login via API

```bash
curl -X POST http://localhost:10000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"apiuser","password":"ApiPass123!"}'
```

**✅ Expected**: 200 OK with session token

**📝 Notes**: _[API test results]_

---

## 📊 STEP 7: Test Summary

### Overall Assessment

**Critical Features** (Must Work):
- [ ] User registration and login
- [ ] Configuration submission
- [ ] TCO calculation and results display
- [ ] At least one provisioning path works
- [ ] Monitoring dashboard displays data
- [ ] Security measures in place

**High Priority Features** (Should Work):
- [ ] All three provisioning paths work
- [ ] Q&A service provides relevant answers
- [ ] Validation catches invalid input
- [ ] Metrics auto-refresh
- [ ] Historical metrics available

**Issues Found**:
1. _[List any issues here]_
2. _[...]_
3. _[...]_

### Recommendation

Based on testing:
- [ ] ✅ Ready for production
- [ ] ⚠️ Minor issues - can proceed with fixes
- [ ] ❌ Major issues - needs fixes before production

---

## 🛠️ Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker ps

# Check logs
docker compose logs

# Restart all services
docker compose down
docker compose up -d

# Check specific service
docker compose logs <service-name>
```

### Database Connection Errors

```bash
# Check database is running
docker compose ps database

# Restart database
docker compose restart database

# Check database logs
docker compose logs database
```

### LocalStack Not Responding

```bash
# Check LocalStack health
curl http://localhost:4566/_localstack/health

# Restart LocalStack
docker compose restart localstack

# Check logs
docker compose logs localstack
```

### Port Already in Use

```bash
# Find what's using the port
lsof -i :10000
lsof -i :10001

# Kill the process or change port in docker-compose.yml
```

### Web UI Not Loading

```bash
# Check web_ui service
docker compose logs web_ui

# Restart web_ui
docker compose restart web_ui

# Check if API is accessible
curl http://localhost:10000/api/health
```

---

## 🎯 Quick Smoke Test (15 minutes)

If you're short on time, run this abbreviated test:

1. ✅ Start services
2. ✅ Register and login
3. ✅ Submit one configuration
4. ✅ View TCO results
5. ✅ Provision AWS resources
6. ✅ Check monitoring dashboard
7. ✅ Test SQL injection prevention

If all 7 steps pass, the application is working!

---

## 📝 Next Steps After UAT

1. **Document Issues**: Use the issue template in UAT-TEST-PLAN.md
2. **Fix Critical Issues**: Address any blockers
3. **Re-test**: Verify fixes work
4. **Sign-off**: Get approval for production
5. **Deploy**: Follow deployment procedures

---

## 🎉 Congratulations!

You've completed the UAT test drive of the Hybrid Cloud Controller!

**Need Help?**
- Check UAT-TEST-PLAN.md for detailed test cases
- Review README.md for setup instructions
- Check docker-compose logs for errors

---

**Test Session Date**: _____________  
**Tester Name**: _____________  
**Overall Result**: Pass / Fail / Needs Work  
**Signature**: _____________
