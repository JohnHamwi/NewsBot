#!/bin/bash

# =============================================================================
# NewsBot Cron Jobs Setup Script
# =============================================================================
# Sets up automated maintenance tasks for 24/7 VPS operation

echo "🕒 Setting up NewsBot cron jobs for 24/7 operation..."

# Create cron jobs
(crontab -l 2>/dev/null; cat << 'EOF'
# NewsBot 24/7 VPS Maintenance Jobs

# Auto-recovery check every 5 minutes
*/5 * * * * /home/newsbot/vps-deployment/auto_recovery.sh >/dev/null 2>&1

# Backup every 6 hours
0 */6 * * * /home/newsbot/scripts/backup_manager.py create scheduled >/dev/null 2>&1

# Daily maintenance at 3 AM
0 3 * * * /home/newsbot/vps-deployment/daily_maintenance.sh

# Weekly VPS restart (Sunday 4 AM) for memory cleanup
0 4 * * 0 /sbin/shutdown -r +5 "Scheduled weekly restart for maintenance"

# Check disk space daily at 2 AM
0 2 * * * df -h | grep -E "9[0-9]%" && echo "Disk space critical" | wall

# Clean temporary files daily at 1 AM
0 1 * * * find /tmp -type f -atime +1 -delete

# Update system packages weekly (Sunday 2 AM)
0 2 * * 0 apt update && apt upgrade -y

# Rotate logs manually if logrotate fails
0 0 * * * /usr/sbin/logrotate -f /etc/logrotate.d/newsbot

# Health check every hour and log results
0 * * * * /home/newsbot/vps-deployment/health_check.sh --detailed >> /var/log/newsbot-health.log 2>&1

# Check for zombie processes every hour
0 * * * * ps aux | awk '$8 ~ /^Z/ { print $2 }' | xargs -r kill -9

EOF
) | crontab -

echo "✅ Cron jobs installed successfully!"
echo ""
echo "📋 Installed maintenance jobs:"
echo "  • Auto-recovery check: Every 5 minutes"
echo "  • Automated backups: Every 6 hours"
echo "  • Daily maintenance: 3 AM"
echo "  • Weekly restart: Sunday 4 AM"
echo "  • Disk space check: Daily 2 AM"
echo "  • Temp cleanup: Daily 1 AM"
echo "  • System updates: Sunday 2 AM"
echo "  • Log rotation: Daily midnight"
echo "  • Health checks: Every hour"
echo "  • Zombie cleanup: Every hour"
echo ""
echo "🔍 View installed cron jobs: crontab -l"
echo "📝 Logs location: /var/log/newsbot-*.log" 