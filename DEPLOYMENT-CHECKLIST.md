# Production Deployment Checklist

Use this checklist to track your production deployment progress.

---

## Pre-Deployment Tasks

### Security Hardening (UAT Recommendation #2)

- [ ] **Generate Production Keys**
  ```bash
  python3 scripts/generate-production-keys.py
  ```
  - [ ] Save DB_PASSWORD securely
  - [ ] Save ENCRYPTION_KEY securely
  - [ ] Save SECRET_KEY securely

- [ ] **Configure Environment**
  ```bash
  cp .env.production .env
  nano .env
  ```
  - [ ] Replace `DB_PASSWORD` placeholder
  - [ ] Replace `ENCRYPTION_KEY` placeholder
  - [ ] Replace `SECRET_KEY` placeholder
  - [ ] Update `DATABASE_URL` with DB_PASSWORD
  - [ ] Review `REQUIRE_HTTPS` setting
  - [ ] Review `FLASK_ENV=production`
  - [ ] Configure AWS credentials (if using real AWS)

- [ ] **Verify Security Settings**
  - [ ] SECRET_KEY is not default value
  - [ ] ENCRYPTION_KEY is not default value
  - [ ] DB_PASSWORD is not default value
  - [ ] .env file is in .gitignore
  - [ ] Keys backed up in secure location

### Monitoring & Logging (UAT Recommendation #4)

- [ ] **Setup Monitoring Infrastructure**
  ```bash
  chmod +x scripts/setup-monitoring.sh
  ./scripts/setup-monitoring.sh
  ```
  - [ ] Verify logs/ directory created
  - [ ] Verify backups/ directory created
  - [ ] Verify monitoring/ directory created
  - [ ] Verify scripts are executable

- [ ] **Test Monitoring Scripts**
  ```bash
  ./scripts/check-health.sh
  ./scripts/backup-database.sh
  ./scripts/collect-metrics.sh
  ```
  - [ ] Health check passes
  - [ ] Backup creates .sql.gz file
  - [ ] Metrics collected successfully

- [ ] **Setup Automated Tasks (Optional)**
  ```bash
  ./scripts/setup-cron.sh
  ```
  - [ ] Review cron job schedule
  - [ ] Confirm cron job installation
  - [ ] Verify cron jobs are running

---

## Deployment Tasks

### Build and Start Services

- [ ] **Stop Existing Services**
  ```bash
  docker compose down
  ```

- [ ] **Build Production Images**
  ```bash
  docker compose build --no-cache
  ```

- [ ] **Start Services**
  ```bash
  docker compose up -d
  ```

- [ ] **Verify Services Are Running**
  ```bash
  docker compose ps
  ```
  - [ ] hybrid-cloud-db: Up (healthy)
  - [ ] hybrid-cloud-localstack: Up (healthy)
  - [ ] hybrid-cloud-api: Up
  - [ ] hybrid-cloud-web-ui: Up

- [ ] **Check Logs for Errors**
  ```bash
  docker compose logs api | tail -50
  docker compose logs web_ui | tail -50
  ```
  - [ ] No critical errors in API logs
  - [ ] No critical errors in Web UI logs
  - [ ] Database initialized successfully
  - [ ] Monitoring collection started

---

## Smoke Testing

### API Testing

- [ ] **Test API Health**
  ```bash
  curl http://localhost:10000/api/health
  ```
  Expected: 401 (requires authentication) or 200

- [ ] **Test API Authentication**
  - [ ] Register new user via Web UI
  - [ ] Login successfully
  - [ ] Session token created

### Web UI Testing

- [ ] **Test Home Page**
  - [ ] Navigate to http://localhost:10001
  - [ ] Home page loads successfully
  - [ ] All feature cards visible

- [ ] **Test User Registration**
  - [ ] Navigate to registration page
  - [ ] Create test account
  - [ ] Registration succeeds

- [ ] **Test User Login**
  - [ ] Navigate to login page
  - [ ] Login with test account
  - [ ] Login succeeds
  - [ ] Navigation shows logged-in state

- [ ] **Test Configuration Submission**
  - [ ] Navigate to configuration page
  - [ ] Enter valid configuration
  - [ ] Validation passes
  - [ ] Configuration saved

- [ ] **Test TCO Calculation**
  - [ ] Submit configuration
  - [ ] TCO results displayed
  - [ ] Cost breakdown shown
  - [ ] Winner badge on correct option

- [ ] **Test Q&A Service**
  - [ ] Navigate to Q&A page
  - [ ] Submit question
  - [ ] Response received
  - [ ] Conversation history maintained

- [ ] **Test Provisioning**
  - [ ] Navigate to provisioning page
  - [ ] Select AWS provisioning
  - [ ] Start provisioning
  - [ ] Resources created successfully
  - [ ] Test IaaS provisioning (Mock Mode)
  - [ ] Test CaaS provisioning (Mock Mode)

- [ ] **Test Monitoring Dashboard**
  - [ ] Navigate to monitoring page
  - [ ] Resources displayed
  - [ ] Health status shows "healthy"
  - [ ] Metrics displayed
  - [ ] Time range selector works
  - [ ] Auto-refresh working

### Security Testing

- [ ] **Test Password Security**
  - [ ] Passwords hashed with bcrypt
  - [ ] Check database: passwords are hashed

- [ ] **Test SQL Injection Prevention**
  - [ ] Try SQL injection in login
  - [ ] Attack blocked

- [ ] **Test XSS Prevention**
  - [ ] Try pasting script tags
  - [ ] Input validation blocks scripts

- [ ] **Test Session Security**
  - [ ] Session cookies encrypted
  - [ ] Check browser dev tools

### Validation Testing

- [ ] **Test Input Validation**
  - [ ] Negative values rejected
  - [ ] Out of range values rejected
  - [ ] Operating hours limit enforced (≤744)
  - [ ] Required fields validated
  - [ ] Clear error messages displayed

---

## Post-Deployment Tasks

### Monitoring Verification

- [ ] **Verify Monitoring Collection**
  ```bash
  docker compose logs api | grep "monitoring collection"
  ```
  - [ ] Monitoring collection started
  - [ ] Metrics collected every 30 seconds

- [ ] **Verify Health Checks**
  ```bash
  ./scripts/check-health.sh
  ```
  - [ ] All health checks pass

- [ ] **Verify Backups**
  ```bash
  ls -lh backups/
  ```
  - [ ] Backup files exist
  - [ ] Backups are compressed (.gz)

- [ ] **Verify Metrics Collection**
  ```bash
  ls -lh monitoring/
  ```
  - [ ] Metrics log files exist
  - [ ] Metrics are being collected

### Database Verification

- [ ] **Test Database Backup**
  ```bash
  ./scripts/backup-database.sh
  ```
  - [ ] Backup created successfully
  - [ ] Backup file compressed

- [ ] **Test Database Restore** (optional, use test database)
  ```bash
  # Create test backup
  docker compose exec database pg_dump -U hybrid_cloud_user hybrid_cloud > test_backup.sql
  
  # Restore test backup
  docker compose exec -T database psql -U hybrid_cloud_user hybrid_cloud < test_backup.sql
  ```
  - [ ] Restore completes without errors

### Performance Verification

- [ ] **Check Resource Usage**
  ```bash
  docker stats --no-stream
  ```
  - [ ] CPU usage reasonable (<50% idle)
  - [ ] Memory usage reasonable (<80%)
  - [ ] No memory leaks

- [ ] **Check Disk Space**
  ```bash
  df -h
  ```
  - [ ] Sufficient disk space (>20% free)

---

## HTTPS Configuration (Optional for Initial Deployment)

### SSL/TLS Setup

- [ ] **Option 1: Reverse Proxy (Nginx/Apache)**
  - [ ] Install Nginx or Apache
  - [ ] Configure reverse proxy
  - [ ] Install SSL certificates
  - [ ] Test HTTPS access
  - [ ] Update `REQUIRE_HTTPS=true` in .env
  - [ ] Update `SESSION_COOKIE_SECURE=true` in code
  - [ ] Restart services

- [ ] **Option 2: Let's Encrypt**
  - [ ] Install certbot
  - [ ] Obtain SSL certificate
  - [ ] Configure auto-renewal
  - [ ] Test HTTPS access
  - [ ] Update `REQUIRE_HTTPS=true` in .env
  - [ ] Update `SESSION_COOKIE_SECURE=true` in code
  - [ ] Restart services

---

## Documentation

- [ ] **Update Documentation**
  - [ ] Document production environment details
  - [ ] Document any issues encountered
  - [ ] Document any deviations from guide

- [ ] **Create Runbook**
  - [ ] Document common operations
  - [ ] Document troubleshooting steps
  - [ ] Document rollback procedure

---

## Team Communication

- [ ] **Notify Team**
  - [ ] Deployment scheduled
  - [ ] Deployment completed
  - [ ] Any issues encountered
  - [ ] Access instructions

---

## Rollback Plan (If Needed)

- [ ] **Prepare Rollback**
  - [ ] Backup current .env file
  - [ ] Backup current database
  - [ ] Document current state

- [ ] **Execute Rollback** (if issues occur)
  ```bash
  # Stop services
  docker compose down
  
  # Restore previous configuration
  cp .env.backup .env
  
  # Restore database (if needed)
  docker compose exec -T database psql -U hybrid_cloud_user hybrid_cloud < backup_YYYYMMDD_HHMMSS.sql
  
  # Restart services
  docker compose up -d
  ```

---

## Sign-Off

### Deployment Completed By
- **Name**: ___________________________
- **Date**: ___________________________
- **Time**: ___________________________

### Deployment Verified By
- **Name**: ___________________________
- **Date**: ___________________________
- **Time**: ___________________________

### Issues Encountered
- [ ] No issues
- [ ] Issues documented in: ___________________________

### Deployment Status
- [ ] ✅ Successful - Ready for production use
- [ ] ⚠️ Successful with minor issues - Documented and monitored
- [ ] ❌ Failed - Rolled back, issues documented

---

## Notes

Use this section to document any additional notes, observations, or deviations from the standard deployment process:

```
[Add notes here]
```

---

**Reference Documents**:
- Production Deployment Guide: `PRODUCTION-DEPLOYMENT.md`
- Production Readiness Summary: `PRODUCTION-READINESS-SUMMARY.md`
- UAT Final Summary: `UAT-FINAL-SUMMARY.md`
- Change Log: `change-log.md`

