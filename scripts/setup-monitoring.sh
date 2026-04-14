#!/bin/bash
# Setup basic monitoring and logging for production

set -e

echo "=========================================="
echo "Hybrid Cloud Controller - Monitoring Setup"
echo "=========================================="
echo ""

# Create directories for logs and backups
echo "Creating directories..."
mkdir -p logs
mkdir -p backups
mkdir -p monitoring

echo "✓ Directories created"
echo ""

# Create log rotation configuration
echo "Setting up log rotation..."
cat > logs/logrotate.conf << 'EOF'
# Log rotation configuration for Hybrid Cloud Controller

logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker compose restart api web_ui
    endscript
}
EOF

echo "✓ Log rotation configured"
echo ""

# Create backup script
echo "Creating backup script..."
cat > scripts/backup-database.sh << 'EOF'
#!/bin/bash
# Backup database script

set -e

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"

echo "Starting database backup..."
docker compose exec -T database pg_dump -U hybrid_cloud_user hybrid_cloud > "${BACKUP_FILE}"

# Compress backup
gzip "${BACKUP_FILE}"

echo "✓ Backup created: ${BACKUP_FILE}.gz"

# Clean up old backups (keep last 30 days)
find "${BACKUP_DIR}" -name "backup_*.sql.gz" -mtime +30 -delete

echo "✓ Old backups cleaned up"
EOF

chmod +x scripts/backup-database.sh

echo "✓ Backup script created"
echo ""

# Create monitoring script
echo "Creating monitoring script..."
cat > scripts/check-health.sh << 'EOF'
#!/bin/bash
# Health check script for monitoring

set -e

echo "=========================================="
echo "Health Check - $(date)"
echo "=========================================="
echo ""

# Check if services are running
echo "Checking services..."
docker compose ps

echo ""
echo "Checking API health..."
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:10000/api/health || echo "000")

if [ "$API_RESPONSE" = "401" ] || [ "$API_RESPONSE" = "200" ]; then
    echo "✓ API is responding (HTTP $API_RESPONSE)"
else
    echo "✗ API is not responding properly (HTTP $API_RESPONSE)"
    exit 1
fi

echo ""
echo "Checking Web UI..."
WEB_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:10001/ || echo "000")

if [ "$WEB_RESPONSE" = "200" ]; then
    echo "✓ Web UI is responding (HTTP $WEB_RESPONSE)"
else
    echo "✗ Web UI is not responding properly (HTTP $WEB_RESPONSE)"
    exit 1
fi

echo ""
echo "Checking database..."
DB_CHECK=$(docker compose exec -T database psql -U hybrid_cloud_user -d hybrid_cloud -c "SELECT 1;" 2>&1 || echo "FAILED")

if [[ "$DB_CHECK" == *"1 row"* ]]; then
    echo "✓ Database is responding"
else
    echo "✗ Database is not responding"
    exit 1
fi

echo ""
echo "Checking disk space..."
df -h | grep -E "Filesystem|/dev/"

echo ""
echo "=========================================="
echo "✓ All health checks passed"
echo "=========================================="
EOF

chmod +x scripts/check-health.sh

echo "✓ Health check script created"
echo ""

# Create metrics collection script
echo "Creating metrics collection script..."
cat > scripts/collect-metrics.sh << 'EOF'
#!/bin/bash
# Collect system metrics for monitoring

METRICS_FILE="monitoring/metrics_$(date +%Y%m%d).log"

{
    echo "=== Metrics Collection - $(date) ==="
    
    # Docker stats
    echo ""
    echo "Docker Container Stats:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    
    # Database size
    echo ""
    echo "Database Size:"
    docker compose exec -T database psql -U hybrid_cloud_user -d hybrid_cloud -c "SELECT pg_size_pretty(pg_database_size('hybrid_cloud'));"
    
    # Resource counts
    echo ""
    echo "Provisioned Resources:"
    docker compose exec -T database psql -U hybrid_cloud_user -d hybrid_cloud -c "SELECT resource_type, COUNT(*) FROM resources GROUP BY resource_type;"
    
    echo ""
    echo "=== End Metrics ==="
    echo ""
} >> "$METRICS_FILE"

# Keep only last 7 days of metrics
find monitoring -name "metrics_*.log" -mtime +7 -delete
EOF

chmod +x scripts/collect-metrics.sh

echo "✓ Metrics collection script created"
echo ""

# Create cron job helper
echo "Creating cron job setup helper..."
cat > scripts/setup-cron.sh << 'EOF'
#!/bin/bash
# Setup cron jobs for automated tasks

echo "Setting up cron jobs..."
echo ""

CRON_FILE="/tmp/hybrid_cloud_cron"
PROJECT_DIR=$(pwd)

# Create cron job entries
cat > "$CRON_FILE" << CRONEOF
# Hybrid Cloud Controller - Automated Tasks

# Database backup - Daily at 2 AM
0 2 * * * cd $PROJECT_DIR && ./scripts/backup-database.sh >> logs/backup.log 2>&1

# Health check - Every 5 minutes
*/5 * * * * cd $PROJECT_DIR && ./scripts/check-health.sh >> logs/health.log 2>&1

# Metrics collection - Every 15 minutes
*/15 * * * * cd $PROJECT_DIR && ./scripts/collect-metrics.sh

# Log rotation - Daily at 3 AM
0 3 * * * /usr/sbin/logrotate $PROJECT_DIR/logs/logrotate.conf --state $PROJECT_DIR/logs/logrotate.state

CRONEOF

echo "Cron jobs to be installed:"
cat "$CRON_FILE"
echo ""

read -p "Install these cron jobs? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    crontab -l > /tmp/current_cron 2>/dev/null || true
    cat /tmp/current_cron "$CRON_FILE" | crontab -
    echo "✓ Cron jobs installed"
else
    echo "Skipped cron job installation"
    echo "To install manually, run: crontab $CRON_FILE"
fi

rm -f "$CRON_FILE"
EOF

chmod +x scripts/setup-cron.sh

echo "✓ Cron setup helper created"
echo ""

echo "=========================================="
echo "✓ Monitoring setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run health check: ./scripts/check-health.sh"
echo "2. Test backup: ./scripts/backup-database.sh"
echo "3. Setup cron jobs: ./scripts/setup-cron.sh"
echo "4. Review logs in: logs/"
echo "5. Review metrics in: monitoring/"
echo ""

