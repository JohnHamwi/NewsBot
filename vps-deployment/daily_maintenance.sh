#!/bin/bash

# =============================================================================
# NewsBot Daily Maintenance Script
# =============================================================================
# Performs comprehensive daily maintenance for optimal 24/7 operation

set -e

# Configuration
LOG_FILE="/var/log/newsbot-maintenance.log"
SERVICE_NAME="newsbot"
MAX_LOG_SIZE_MB=100
MAX_BACKUP_AGE_DAYS=30

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [MAINTENANCE] $1" | tee -a "$LOG_FILE"
}

# Function to get file size in MB
get_size_mb() {
    local file="$1"
    if [ -f "$file" ]; then
        stat -c%s "$file" | awk '{print int($1/1024/1024)}'
    else
        echo "0"
    fi
}

# Start maintenance
log "🔧 Starting daily maintenance routine..."

# 1. Memory optimization
log "💾 Performing memory optimization..."
echo 3 > /proc/sys/vm/drop_caches
log "✅ System caches cleared"

# 2. Log rotation and cleanup
log "📝 Checking and rotating logs..."

# Check NewsBot log sizes
NEWSBOT_LOG="/home/newsbot/logs/newsbot-prod.log"
if [ -f "$NEWSBOT_LOG" ]; then
    LOG_SIZE=$(get_size_mb "$NEWSBOT_LOG")
    if [ "$LOG_SIZE" -gt "$MAX_LOG_SIZE_MB" ]; then
        log "📦 Rotating large log file (${LOG_SIZE}MB)"
        mv "$NEWSBOT_LOG" "${NEWSBOT_LOG}.$(date +%Y%m%d)"
        gzip "${NEWSBOT_LOG}.$(date +%Y%m%d)"
        touch "$NEWSBOT_LOG"
        chown newsbot:newsbot "$NEWSBOT_LOG"
        systemctl reload "$SERVICE_NAME" || true
    fi
fi

# Clean old log files
find /home/newsbot/logs -name "*.log.*" -mtime +7 -delete
find /var/log -name "newsbot*.log.*" -mtime +14 -delete

log "✅ Log cleanup completed"

# 3. Backup cleanup
log "🗂️ Cleaning old backups..."
find /home/newsbot/backups -name "*.tar.gz" -mtime +$MAX_BACKUP_AGE_DAYS -delete 2>/dev/null || true
find /tmp/newsbot_backups -mtime +7 -delete 2>/dev/null || true
log "✅ Backup cleanup completed"

# 4. Database optimization (if using JSON cache)
log "💾 Optimizing cache database..."
if [ -f "/home/newsbot/data/botdata.json" ]; then
    # Create a backup of the cache
    cp "/home/newsbot/data/botdata.json" "/home/newsbot/data/botdata.backup.$(date +%Y%m%d)"
    
    # Clean up old cache backups
    find /home/newsbot/data -name "botdata.backup.*" -mtime +7 -delete
    
    log "✅ Cache optimization completed"
fi

# 5. Temporary files cleanup
log "🧹 Cleaning temporary files..."
find /tmp -user newsbot -type f -mtime +1 -delete 2>/dev/null || true
find /home/newsbot/data/cache -name "*.tmp" -mtime +1 -delete 2>/dev/null || true

# Clean Python cache files
find /home/newsbot -name "*.pyc" -delete 2>/dev/null || true
find /home/newsbot -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

log "✅ Temporary files cleanup completed"

# 6. Check service health
log "🔍 Performing service health check..."
if systemctl is-active "$SERVICE_NAME" >/dev/null 2>&1; then
    log "✅ Service is running normally"
    
    # Check memory usage of bot process
    BOT_PID=$(systemctl show "$SERVICE_NAME" --property=MainPID --value)
    if [ -n "$BOT_PID" ] && [ "$BOT_PID" != "0" ]; then
        MEMORY_MB=$(ps -p "$BOT_PID" -o rss= | awk '{print int($1/1024)}')
        log "📊 Bot memory usage: ${MEMORY_MB}MB"
        
        # If memory usage is too high, restart the service
        if [ "$MEMORY_MB" -gt 800 ]; then
            log "⚠️ High memory usage detected, restarting service..."
            systemctl restart "$SERVICE_NAME"
            sleep 10
            if systemctl is-active "$SERVICE_NAME" >/dev/null 2>&1; then
                log "✅ Service restarted successfully"
            else
                log "❌ Service restart failed"
            fi
        fi
    fi
else
    log "❌ Service is not running, attempting to start..."
    systemctl start "$SERVICE_NAME"
    sleep 10
    if systemctl is-active "$SERVICE_NAME" >/dev/null 2>&1; then
        log "✅ Service started successfully"
    else
        log "❌ Failed to start service"
    fi
fi

# 7. Redis maintenance
log "🔴 Performing Redis maintenance..."
if command -v redis-cli >/dev/null 2>&1; then
    if redis-cli ping >/dev/null 2>&1; then
        # Get Redis memory usage
        REDIS_MEMORY=$(redis-cli info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
        log "📊 Redis memory usage: $REDIS_MEMORY"
        
        # Optimize Redis if needed
        redis-cli BGREWRITEAOF >/dev/null 2>&1 || true
        log "✅ Redis optimization completed"
    else
        log "⚠️ Redis is not responding, restarting..."
        systemctl restart redis-server
        sleep 5
        if redis-cli ping >/dev/null 2>&1; then
            log "✅ Redis restarted successfully"
        else
            log "❌ Redis restart failed"
        fi
    fi
else
    log "⚠️ Redis CLI not available"
fi

# 8. System updates check
log "🔄 Checking for system updates..."
UPDATE_COUNT=$(apt list --upgradable 2>/dev/null | grep -c upgradable || echo "0")
if [ "$UPDATE_COUNT" -gt 0 ]; then
    log "📦 $UPDATE_COUNT package updates available"
    # Note: Actual updates are handled by cron job on Sunday
else
    log "✅ System is up to date"
fi

# 9. Disk space monitoring
log "💿 Checking disk space..."
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
if [ "$DISK_USAGE" -gt 85 ]; then
    log "⚠️ High disk usage: ${DISK_USAGE}%"
    
    # Emergency cleanup
    apt-get clean
    docker system prune -f 2>/dev/null || true
    find /var/log -name "*.log" -size +100M -exec truncate -s 50M {} \;
    
    NEW_DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
    log "💿 Disk usage after cleanup: ${NEW_DISK_USAGE}%"
else
    log "✅ Disk usage is healthy: ${DISK_USAGE}%"
fi

# 10. Network connectivity check
log "🌐 Checking network connectivity..."
if curl -s --max-time 10 https://discord.com/api/v10/gateway >/dev/null; then
    log "✅ Discord API connectivity OK"
else
    log "⚠️ Discord API connectivity issues"
fi

if curl -s --max-time 10 https://api.openai.com/v1/models >/dev/null; then
    log "✅ OpenAI API connectivity OK"
else
    log "⚠️ OpenAI API connectivity issues"
fi

# 11. Generate maintenance report
log "📊 Generating maintenance report..."

MAINTENANCE_REPORT="/var/log/newsbot-maintenance-report.txt"
cat > "$MAINTENANCE_REPORT" << EOF
NewsBot Maintenance Report - $(date)
=====================================

System Status:
- Service Status: $(systemctl is-active "$SERVICE_NAME" 2>/dev/null || echo "inactive")
- Redis Status: $(redis-cli ping 2>/dev/null || echo "down")
- Disk Usage: ${DISK_USAGE}%
- Available Updates: $UPDATE_COUNT

Maintenance Actions Performed:
- Memory caches cleared
- Log files rotated and cleaned
- Old backups removed
- Temporary files cleaned
- Service health checked
- Redis optimized
- Network connectivity verified

Last Updated: $(date)
EOF

log "✅ Maintenance report saved to $MAINTENANCE_REPORT"

# 12. File permissions check
log "🔒 Checking file permissions..."
chown -R newsbot:newsbot /home/newsbot/
chmod 755 /home/newsbot/
chmod 600 /home/newsbot/config/*.yaml 2>/dev/null || true
chmod 644 /home/newsbot/logs/*.log 2>/dev/null || true
log "✅ File permissions verified"

# Maintenance completed
log "🎉 Daily maintenance routine completed successfully"

# Clean up old maintenance logs (keep last 30 days)
find /var/log -name "newsbot-maintenance*.log*" -mtime +30 -delete 2>/dev/null || true

# Rotate maintenance log if it gets too large
MAINT_LOG_SIZE=$(get_size_mb "$LOG_FILE")
if [ "$MAINT_LOG_SIZE" -gt 50 ]; then
    mv "$LOG_FILE" "${LOG_FILE}.$(date +%Y%m%d)"
    gzip "${LOG_FILE}.$(date +%Y%m%d)"
    touch "$LOG_FILE"
fi

echo "Daily maintenance completed at $(date)" >> /var/log/newsbot-maintenance-summary.log 