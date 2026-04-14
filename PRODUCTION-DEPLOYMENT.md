# Production Deployment Guide

This guide walks you through deploying the Hybrid Cloud Controller to production.

## Prerequisites

- Docker and Docker Compose installed
- SSL/TLS certificates (for HTTPS)
- Production database credentials
- AWS credentials (if using real AWS instead of LocalStack)

---

## Step 1: Generate Production Keys

Run the key generation script to create secure random keys:

```bash
cd hybrid_cloud_controller
python scripts/generate-production-keys.py
```

This will generate:
- Database password
- Encryption key (for credential storage)
- Secret key (for Flask sessions)

**IMPORTANT**: Save these keys securely! You'll need them in the next step.

---

## Step 2: Configure Production Environment

1. **Copy the production template**:
   ```bash
   cp .env.production.example .env.production
   ```

2. **Edit `.env.production` and replace all `CHANGE_ME` placeholders**:
   ```bash
   nano .env.production  # or use your preferred editor
   ```

3. **Update these critical values**:
   - `DB_PASSWORD`: Use the database password from Step 1
   - `ENCRYPTION_KEY`: Use the encryption key from Step 1
   - `SECRET_KEY`: Use the secret key from Step 1
   - `DATABASE_URL`: Update with the DB_PASSWORD

4. **Configure HTTPS** (if ready):
   - Set `REQUIRE_HTTPS=true`
   - Ensure SSL/TLS certificates are configured
   - Update `SESSION_COOKIE_SECURE=true` in code

5. **Configure AWS** (if using real AWS):
   - Comment out LocalStack settings
   - Uncomment and configure real AWS credentials
   - Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

---

## Step 3: Security Hardening Checklist

Before deploying, verify these security settings:

### Database Security
- [ ] Strong database password set (32+ characters)
- [ ] Database not exposed to public internet
- [ ] Database backups configured

### Application Security
- [ ] `SECRET_KEY` changed from default
- [ ] `ENCRYPTION_KEY` changed from default
- [ ] `REQUIRE_HTTPS=true` (when SSL configured)
- [ ] `SESSION_COOKIE_SECURE=true` in code (when HTTPS enabled)
- [ ] `FLASK_ENV=production`

### Network Security
- [ ] Firewall rules configured
- [ ] Only necessary ports exposed (443 for HTTPS, 5432 for DB if needed)
- [ ] Internal services not exposed to public

### Monitoring & Logging
- [ ] Log level set appropriately (`INFO` or `WARNING`)
- [ ] Log aggregation configured (optional but recommended)
- [ ] Monitoring alerts configured (optional but recommended)

---

## Step 4: Update Application Code for Production

### Enable Secure Cookies (when HTTPS is ready)

Edit `packages/web_ui/app.py`:

```python
# Change this line:
app.config["SESSION_COOKIE_SECURE"] = False  # Development

# To this:
app.config["SESSION_COOKIE_SECURE"] = True  # Production with HTTPS
```

### Load SECRET_KEY from Environment

Edit `packages/api/app.py`:

```python
# Update the SECRET_KEY configuration:
app.config.update(
    {
        "SECRET_KEY": os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
        "REQUIRE_HTTPS": os.getenv("REQUIRE_HTTPS", "true").lower() == "true",
        "SESSION_TIMEOUT_MINUTES": int(os.getenv("SESSION_TIMEOUT_MINUTES", "30")),
    }
)
```

Edit `packages/web_ui/app.py`:

```python
# Update the SECRET_KEY configuration:
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
```

---

## Step 5: Deploy to Production

1. **Stop existing services** (if running):
   ```bash
   docker compose down
   ```

2. **Build production images**:
   ```bash
   docker compose build --no-cache
   ```

3. **Start services**:
   ```bash
   docker compose up -d
   ```

4. **Verify services are healthy**:
   ```bash
   docker compose ps
   ```

   All services should show "Up" or "healthy" status.

5. **Check logs for errors**:
   ```bash
   docker compose logs api | tail -50
   docker compose logs web_ui | tail -50
   ```

---

## Step 6: Smoke Testing

Run basic smoke tests to verify the deployment:

1. **Test API health**:
   ```bash
   curl http://localhost:10000/api/health
   ```
   
   Expected: Should require authentication (401 or redirect)

2. **Test Web UI**:
   - Open browser to `http://localhost:10001` (or your domain)
   - Verify home page loads
   - Test user registration
   - Test user login
   - Test configuration submission
   - Test TCO calculation

3. **Test provisioning**:
   - Provision AWS resources (LocalStack or real AWS)
   - Verify resources are created
   - Check monitoring dashboard

4. **Test monitoring**:
   - Navigate to monitoring dashboard
   - Verify resources show as "healthy"
   - Check metrics are being collected

---

## Step 7: Database Backup Setup

### Manual Backup

```bash
# Backup database
docker compose exec database pg_dump -U hybrid_cloud_user hybrid_cloud > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database
docker compose exec -T database psql -U hybrid_cloud_user hybrid_cloud < backup_20260414_120000.sql
```

### Automated Backup (Recommended)

Create a cron job for daily backups:

```bash
# Edit crontab
crontab -e

# Add this line for daily backup at 2 AM
0 2 * * * cd /path/to/hybrid_cloud_controller && docker compose exec database pg_dump -U hybrid_cloud_user hybrid_cloud > backups/backup_$(date +\%Y\%m\%d_\%H\%M\%S).sql
```

---

## Step 8: Monitoring & Alerting (Optional but Recommended)

### Log Aggregation

Consider setting up log aggregation with:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- CloudWatch (if on AWS)
- Datadog

### Application Monitoring

Monitor these metrics:
- API response times
- Error rates
- Database connection pool usage
- Resource utilization (CPU, memory, storage)
- Provisioned resource health

### Alerting

Set up alerts for:
- High CPU usage (>80%)
- High memory usage (>80%)
- High storage usage (>85%)
- API errors (>5% error rate)
- Database connection failures
- Service downtime

---

## Step 9: SSL/TLS Configuration (HTTPS)

### Option 1: Reverse Proxy (Recommended)

Use Nginx or Apache as a reverse proxy with SSL termination:

```nginx
# /etc/nginx/sites-available/hybrid-cloud
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:10001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Option 2: Let's Encrypt (Free SSL)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

## Step 10: Post-Deployment Checklist

- [ ] All services running and healthy
- [ ] Smoke tests passed
- [ ] Database backups configured
- [ ] Monitoring configured (if applicable)
- [ ] SSL/TLS configured (if applicable)
- [ ] Firewall rules configured
- [ ] Documentation updated
- [ ] Team notified of deployment
- [ ] Rollback plan documented

---

## Rollback Procedure

If issues occur after deployment:

1. **Stop services**:
   ```bash
   docker compose down
   ```

2. **Restore previous configuration**:
   ```bash
   cp .env.backup .env
   ```

3. **Restore database** (if needed):
   ```bash
   docker compose exec -T database psql -U hybrid_cloud_user hybrid_cloud < backup_YYYYMMDD_HHMMSS.sql
   ```

4. **Restart services**:
   ```bash
   docker compose up -d
   ```

---

## Troubleshooting

### Services won't start

```bash
# Check logs
docker compose logs api
docker compose logs web_ui
docker compose logs database

# Check environment variables
docker compose config
```

### Database connection errors

```bash
# Verify database is running
docker compose ps database

# Check database logs
docker compose logs database

# Test database connection
docker compose exec database psql -U hybrid_cloud_user -d hybrid_cloud -c "SELECT 1;"
```

### Authentication errors

- Verify `SECRET_KEY` is set correctly in `.env`
- Check that `SECRET_KEY` matches between API and Web UI
- Verify session cookies are being set (check browser dev tools)

### HTTPS redirect loop

- Verify `REQUIRE_HTTPS` setting matches your SSL configuration
- Check reverse proxy configuration
- Ensure `X-Forwarded-Proto` header is set correctly

---

## Security Best Practices

1. **Never commit `.env` or `.env.production` to version control**
   - Add `.env` and `.env.production` to `.gitignore`
   - Use `.env.production.example` as a template

2. **Rotate keys regularly**
   - Change `SECRET_KEY` every 90 days
   - Update database passwords annually
   - Rotate AWS credentials as needed

3. **Monitor for security issues**
   - Review logs for suspicious activity
   - Monitor failed login attempts
   - Keep dependencies updated

4. **Implement rate limiting** (future enhancement)
   - Limit login attempts
   - Rate limit API endpoints
   - Implement CAPTCHA for registration

5. **Regular security audits**
   - Review access logs
   - Test for vulnerabilities
   - Update dependencies

---

## Support

For issues or questions:
- Review UAT documentation: `UAT-FINAL-SUMMARY.md`
- Check issue tracker: `UAT-ISSUES.md`
- Review application logs: `docker compose logs`

---

**Congratulations on your production deployment! 🚀**

