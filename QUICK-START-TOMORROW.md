# Quick Start Guide for Tomorrow's UAT Session

## 🚀 Getting Started (5 minutes)

### Step 1: Start Docker Desktop
Make sure Docker Desktop is running on your Mac.

### Step 2: Navigate to Project
```bash
cd ~/Dev/hybrid_cloud_controller
```

### Step 3: Check Services Status
```bash
docker compose ps
```

**Expected Output**: All 4 services should show "Up" or "Healthy"
- hybrid-cloud-db (Healthy)
- hybrid-cloud-localstack (Healthy)
- hybrid-cloud-api (Up)
- hybrid-cloud-web-ui (Up)

### Step 4: If Services Aren't Running
```bash
docker compose up -d
# Wait 30 seconds for services to start
docker compose ps
```

### Step 5: Open Browser
Navigate to: **http://localhost:10001**

You should see the Hybrid Cloud Controller home page!

---

## 📋 UAT Testing Guide

### Option 1: Quick Smoke Test (15 minutes)
Follow the "Quick Smoke Test" section in `UAT-GUIDED-SESSION.md`

**Tests**:
1. ✅ Register and login
2. ✅ Submit configuration
3. ✅ View TCO results
4. ✅ Provision AWS resources
5. ✅ Check monitoring dashboard
6. ✅ Test SQL injection prevention

### Option 2: Comprehensive UAT (3-4 hours)
Follow the complete `UAT-GUIDED-SESSION.md` step-by-step

**Covers**:
- All authentication features
- Configuration validation
- TCO calculations
- Q&A service
- All provisioning paths (AWS, IaaS, CaaS)
- Monitoring dashboard
- Security testing
- API testing

### Option 3: Specific Test Suites
Use `UAT-TEST-PLAN.md` to pick specific test suites:
- Test Suite 1: Authentication
- Test Suite 2: Configuration
- Test Suite 3: TCO Results
- Test Suite 4: Q&A Service
- Test Suite 5-7: Provisioning
- Test Suite 8: Monitoring
- Test Suite 9: Security

---

## 🧪 Test Data

### User Credentials (to create during testing)
- Username: `testuser`
- Password: `TestPassword123!`

### Sample Configuration
```
Compute:
  CPU Cores: 8
  Memory (GB): 32
  Instance Count: 3

Storage:
  Type: SSD
  Capacity (GB): 500
  IOPS: 3000

Network:
  Bandwidth (Gbps): 10
  Data Transfer (GB): 1000

Workload:
  Utilization (%): 75
  Operating Hours: 720
```

### Container Images for Testing
- Docker Hub: `nginx:latest`
- Simple test: `hello-world`

---

## 🔧 Troubleshooting

### Services Not Running
```bash
# Check logs
docker compose logs

# Restart specific service
docker compose restart <service-name>

# Restart all services
docker compose down
docker compose up -d
```

### Web UI Not Loading
```bash
# Check web_ui logs
docker compose logs web_ui

# Restart web_ui
docker compose restart web_ui

# Verify it's on HTTP (not HTTPS)
curl http://localhost:10001
```

### Database Issues
```bash
# Check database
docker compose logs database

# Restart database
docker compose restart database
```

### LocalStack Issues
```bash
# Check LocalStack health
curl http://localhost:4566/_localstack/health

# Restart LocalStack
docker compose restart localstack
```

---

## 📊 What to Document During Testing

### For Each Test
- ✅ Pass / ❌ Fail / ⚠️ Issue
- What you observed
- Any error messages
- Screenshots (if helpful)

### Issues Found
Use the issue template in `UAT-TEST-PLAN.md`:
- Test case number
- Steps to reproduce
- Expected vs actual result
- Screenshots/logs

---

## 🎯 Success Criteria

**Critical Features Must Work**:
- [ ] User can register and login
- [ ] Configuration can be submitted
- [ ] TCO results display correctly
- [ ] At least one provisioning path works
- [ ] Monitoring dashboard shows data
- [ ] Security measures prevent attacks

**If All Pass**: Application is ready for production! 🎉

---

## 📝 After Testing

### Document Results
1. Fill out test summary in `UAT-GUIDED-SESSION.md`
2. List any issues found
3. Decide: Ready for production? Needs fixes?

### Stop Services (Optional)
```bash
# Stop but keep data
docker compose stop

# Stop and remove everything
docker compose down

# Stop and remove including volumes (database data)
docker compose down -v
```

---

## 🆘 Need Help?

### Check Documentation
- `UAT-GUIDED-SESSION.md` - Step-by-step testing guide
- `UAT-TEST-PLAN.md` - Detailed test cases
- `SESSION-SUMMARY-2026-03-09.md` - What we did today
- `README.md` - General application info

### Common Commands
```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f web_ui
docker compose logs -f api

# Check service status
docker compose ps

# Restart everything
docker compose restart
```

---

## ✨ You're All Set!

Everything is ready for testing. The application is running and waiting for you.

**Start here**: Open http://localhost:10001 in your browser

**Follow this**: `UAT-GUIDED-SESSION.md`

**Have fun testing!** 🚀

---

**Last Updated**: 2026-03-09
**Services Status**: ✅ All Running
**Ready for**: User Acceptance Testing
