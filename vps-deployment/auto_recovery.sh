#!/bin/bash

# =============================================================================
# NewsBot Auto-Recovery System
# =============================================================================
# Monitors and automatically fixes common issues in production
# Usage: Run as a cron job every 5 minutes

set -e

# Configuration
VPS_IP="159.89.90.90"
SSH_KEY="~/.ssh/id_rsa"
SERVICE_NAME="newsbot"
LOG_FILE="/var/log/newsbot-recovery.log"
DISCORD_WEBHOOK_URL=""  # Set your Discord webhook URL here
MAX_MEMORY_PERCENT=85
MAX_CPU_PERCENT=90
MAX_DISK_PERCENT=95

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Send Discord alert
send_alert() {
    local title="$1"
    local message="$2"
    local color="$3"  # 0xFF0000 for red, 0xFFAA00 for orange
    
    if [ -n "$DISCORD_WEBHOOK_URL" ]; then
        curl -s -H "Content-Type: application/json" \
             -X POST \
             -d "{
                \"username\": \"NewsBot Auto-Recovery\",
                \"embeds\": [{
                    \"title\": \"$title\",
                    \"description\": \"$message\",
                    \"color\": $color,
                    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
                }]
             }" \
             "$DISCORD_WEBHOOK_URL" > /dev/null
    fi
}

# Check if bot service is running
check_service_health() {
    log "🔍 Checking service health..."
    
    local status=$(systemctl is-active "$SERVICE_NAME" 2>/dev/null || echo "inactive")
    local enabled=$(systemctl is-enabled "$SERVICE_NAME" 2>/dev/null || echo "disabled")
    
    if [ "$status" != "active" ]; then
        log "❌ Service is $status - attempting restart"
        send_alert "🚨 Bot Service Down" "NewsBot service was $status, attempting automatic restart" "0xFF0000"
        
        systemctl start "$SERVICE_NAME"
        sleep 10
        
        if systemctl is-active "$SERVICE_NAME" >/dev/null 2>&1; then
            log "✅ Service restarted successfully"
            send_alert "✅ Auto-Recovery Success" "NewsBot service restarted successfully" "0x00FF00"
            return 0
        else
            log "❌ Service restart failed"
            send_alert "❌ Auto-Recovery Failed" "Failed to restart NewsBot service - manual intervention required" "0xFF0000"
            return 1
        fi
    fi
    
    if [ "$enabled" != "enabled" ]; then
        log "⚠️ Service not enabled for auto-start - enabling"
        systemctl enable "$SERVICE_NAME"
    fi
    
    return 0
}

# Check system resources
check_system_resources() {
    log "💻 Checking system resources..."
    
    # Memory check
    local memory_percent=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$memory_percent" -gt "$MAX_MEMORY_PERCENT" ]; then
        log "⚠️ High memory usage: ${memory_percent}% - performing cleanup"
        
        # Clear caches
        sync
        echo 3 > /proc/sys/vm/drop_caches
        
        # Force garbage collection if possible
        systemctl reload "$SERVICE_NAME" || true
        
        send_alert "⚠️ High Memory Usage" "Memory usage was ${memory_percent}% - performed automatic cleanup" "0xFFAA00"
    fi
    
    # Disk space check
    local disk_percent=$(df / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
    if [ "$disk_percent" -gt "$MAX_DISK_PERCENT" ]; then
        log "⚠️ High disk usage: ${disk_percent}% - performing cleanup"
        
        # Clean old logs
        find /var/log -name "*.log" -type f -mtime +7 -delete
        journalctl --vacuum-time=7d
        
        # Clean temp files
        find /tmp -type f -atime +1 -delete
        
        # Clean apt cache
        apt-get clean
        
        send_alert "⚠️ High Disk Usage" "Disk usage was ${disk_percent}% - performed automatic cleanup" "0xFFAA00"
    fi
    
    # CPU check (if sustained high usage, restart service)
    local cpu_percent=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d'.' -f1)
    if [ "$cpu_percent" -gt "$MAX_CPU_PERCENT" ]; then
        log "⚠️ High CPU usage: ${cpu_percent}% - checking if bot is causing it"
        
        # Check if bot process is consuming CPU
        local bot_cpu=$(ps aux | grep python | grep newsbot | awk '{print $3}' | head -1)
        if [ -n "$bot_cpu" ] && [ "$(echo "$bot_cpu > 50" | bc -l)" = "1" ]; then
            log "🔄 Bot consuming high CPU - restarting service"
            systemctl restart "$SERVICE_NAME"
            send_alert "🔄 High CPU Recovery" "Bot was consuming ${bot_cpu}% CPU - restarted service" "0xFFAA00"
        fi
    fi
}

# Check Redis health
check_redis_health() {
    log "🔴 Checking Redis health..."
    
    if ! redis-cli ping >/dev/null 2>&1; then
        log "❌ Redis is down - attempting restart"
        send_alert "🚨 Redis Down" "Redis server is down, attempting automatic restart" "0xFF0000"
        
        systemctl restart redis-server
        sleep 5
        
        if redis-cli ping >/dev/null 2>&1; then
            log "✅ Redis restarted successfully"
            send_alert "✅ Redis Recovery" "Redis server restarted successfully" "0x00FF00"
        else
            log "❌ Redis restart failed"
            send_alert "❌ Redis Recovery Failed" "Failed to restart Redis - manual intervention required" "0xFF0000"
            return 1
        fi
    fi
    
    return 0
}

# Check for bot-specific issues
check_bot_health() {
    log "🤖 Checking bot-specific health..."
    
    # Check if bot process exists
    local bot_processes=$(pgrep -f "python.*run.py" | wc -l)
    
    if [ "$bot_processes" -eq 0 ]; then
        log "❌ No bot processes found"
        return 1
    elif [ "$bot_processes" -gt 1 ]; then
        log "⚠️ Multiple bot processes detected ($bot_processes) - cleaning up"
        
        # Kill extra processes
        pkill -f "python.*run.py"
        sleep 5
        systemctl start "$SERVICE_NAME"
        
        send_alert "🔄 Process Cleanup" "Found $bot_processes bot processes - cleaned up and restarted" "0xFFAA00"
    fi
    
    # Check recent error logs
    local recent_errors=$(journalctl -u "$SERVICE_NAME" --since "5 minutes ago" | grep -c "ERROR\|CRITICAL" || echo "0")
    
    if [ "$recent_errors" -gt 10 ]; then
        log "⚠️ High error rate detected ($recent_errors errors in last 5 minutes)"
        
        # Get last few error messages
        local error_sample=$(journalctl -u "$SERVICE_NAME" --since "5 minutes ago" | grep "ERROR\|CRITICAL" | tail -3 | cut -d' ' -f5-)
        
        send_alert "⚠️ High Error Rate" "Detected $recent_errors errors in last 5 minutes:\n\`\`\`\n$error_sample\n\`\`\`" "0xFFAA00"
        
        # If too many errors, restart
        if [ "$recent_errors" -gt 20 ]; then
            log "🔄 Too many errors - restarting service"
            systemctl restart "$SERVICE_NAME"
        fi
    fi
}

# Check network connectivity
check_network_health() {
    log "🌐 Checking network connectivity..."
    
    # Check Discord API
    if ! curl -s --max-time 10 https://discord.com/api/v10/gateway >/dev/null; then
        log "⚠️ Discord API unreachable"
        send_alert "⚠️ Network Issue" "Discord API appears unreachable" "0xFFAA00"
    fi
    
    # Check OpenAI API
    if ! curl -s --max-time 10 https://api.openai.com/v1/models >/dev/null; then
        log "⚠️ OpenAI API unreachable"
        send_alert "⚠️ Network Issue" "OpenAI API appears unreachable" "0xFFAA00"
    fi
}

# Check file permissions
check_file_permissions() {
    log "📁 Checking file permissions..."
    
    # Check ownership
    if [ "$(stat -c %U /home/newsbot)" != "newsbot" ]; then
        log "🔧 Fixing ownership for /home/newsbot"
        chown -R newsbot:newsbot /home/newsbot
    fi
    
    # Check log directory
    if [ ! -d "/home/newsbot/logs" ]; then
        log "📝 Creating logs directory"
        mkdir -p /home/newsbot/logs
        chown newsbot:newsbot /home/newsbot/logs
    fi
    
    # Check data directory
    if [ ! -d "/home/newsbot/data" ]; then
        log "💾 Creating data directory"
        mkdir -p /home/newsbot/data
        chown newsbot:newsbot /home/newsbot/data
    fi
}

# Main recovery function
main() {
    log "🚀 Starting auto-recovery check..."
    
    local issues_found=0
    
    # Run all health checks
    check_file_permissions
    
    if ! check_redis_health; then
        issues_found=$((issues_found + 1))
    fi
    
    if ! check_service_health; then
        issues_found=$((issues_found + 1))
    fi
    
    check_system_resources
    check_bot_health
    check_network_health
    
    if [ "$issues_found" -eq 0 ]; then
        log "✅ All systems healthy"
    else
        log "⚠️ Found and attempted to fix $issues_found critical issues"
    fi
    
    log "🏁 Auto-recovery check completed"
}

# Create log file if it doesn't exist
touch "$LOG_FILE"

# Run main function
main

# Clean up old log entries (keep last 1000 lines)
tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE" 