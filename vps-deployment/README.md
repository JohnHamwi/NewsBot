# NewsBot VPS Deployment Guide

This directory contains everything you need to deploy NewsBot to a VPS (Virtual Private Server).

## 📋 Prerequisites

- Ubuntu 20.04+ VPS with root access
- SSH key configured for VPS access
- ✅ **All credentials already configured** (Discord, Telegram, OpenAI)

## 📂 Files in this Directory

### 🚀 Deployment Scripts
- `deploy_to_vps.sh` - Local script to package and upload bot to VPS
- `deploy_vps.sh` - VPS script to install and configure the bot
- `quick_fix.sh` - Deploy single file fixes without full redeployment

### 🔍 Monitoring & Management Scripts
- `monitor_bot.sh` - Comprehensive log monitoring with multiple modes
- `check_bot_status.sh` - Quick status check and system info
- `health_check.sh` - Comprehensive health check with detailed analysis
- `stop_bot.sh` - Stop bot service and optionally shutdown VPS

### 💾 Backup & Recovery Scripts
- `backup_bot.sh` - Create backups of bot data and configuration

### 📁 Configuration Files
- `config-template.yaml` - Pre-filled configuration with your actual values
- `README.md` - This comprehensive guide

## 🚀 Quick Deployment

### Step 1: Configure Your VPS Details (if different)

Edit the deployment script or set environment variables:

```bash
export VPS_IP="159.89.90.90"  # Your VPS IP (already set)
export VPS_USER="root"
export SSH_KEY="/Users/johnhamwi/.ssh/id_rsa"  # Your SSH key (already set)
```

### Step 2: Run Deployment

```bash
# Make script executable
chmod +x vps-deployment/deploy_to_vps.sh

# Run deployment
./vps-deployment/deploy_to_vps.sh
```

### Step 3: Start the Bot

The configuration is **automatically created** with your settings! Just start the bot:

```bash
# Connect to VPS
ssh -i /Users/johnhamwi/.ssh/id_rsa root@159.89.90.90

# Start the bot
sudo systemctl start newsbot
sudo systemctl status newsbot
```

**That's it!** No manual configuration needed - everything is pre-filled.

## 🎮 VPS Management Commands Reference

### 🎯 Discord Commands (Primary Method)
Use these commands directly in Discord to manage your VPS bot:

```
/admin system status      # Bot health, uptime, and system info
/admin system logs        # View recent bot logs
/admin system restart     # Restart the bot remotely
/admin autopost status    # Check auto-posting configuration
/admin channels list      # View all configured channels
/bot status               # Quick health check
/bot uptime               # Show bot uptime
```

### 🖥️ SSH Commands (Direct VPS Access)

#### Connect to VPS
```bash
ssh -i ~/.ssh/id_rsa root@159.89.90.90
```

#### Bot Service Management
```bash
# Check bot status
sudo systemctl status newsbot

# Start bot
sudo systemctl start newsbot

# Stop bot
sudo systemctl stop newsbot

# Restart bot
sudo systemctl restart newsbot

# Enable auto-start on boot
sudo systemctl enable newsbot

# Disable auto-start on boot
sudo systemctl disable newsbot
```

#### Log Monitoring
```bash
# View live logs (follow mode)
sudo journalctl -u newsbot -f

# View last 50 log entries
sudo journalctl -u newsbot --lines=50

# View logs from today
sudo journalctl -u newsbot --since today

# View logs with timestamps
sudo journalctl -u newsbot --lines=20 --no-pager

# Search logs for specific text
sudo journalctl -u newsbot | grep "ERROR"
sudo journalctl -u newsbot | grep "auto-post"
```

#### System Monitoring
```bash
# Check system resources
htop                    # Interactive process viewer
top                     # Basic process viewer

# Check disk space
df -h                   # Human readable disk usage
du -sh /home/newsbot/   # Bot directory size

# Check memory usage
free -h                 # Memory usage
cat /proc/meminfo       # Detailed memory info

# Check system load
uptime                  # System uptime and load
w                       # Who's logged in and system load
```

#### File Management
```bash
# Navigate to bot directory
cd /home/newsbot/

# Check file permissions
ls -la /home/newsbot/
ls -la /home/newsbot/config/

# Fix ownership (if needed)
sudo chown -R newsbot:newsbot /home/newsbot/

# Fix permissions (if needed)
sudo chmod 755 /home/newsbot/
sudo chmod 600 /home/newsbot/config/config.yaml
```

### 🚀 Deployment Commands (From Local Machine)

#### Quick File Update
```bash
# Update single file (like we did for the rich presence fix)
scp -i ~/.ssh/id_rsa src/bot/background_tasks.py root@159.89.90.90:/home/newsbot/src/bot/
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "chown newsbot:newsbot /home/newsbot/src/bot/background_tasks.py && systemctl restart newsbot"
```

#### Full Deployment
```bash
# Deploy all changes
./vps-deployment/deploy_to_vps.sh

# Alternative: Manual deployment
tar -czf newsbot-update.tar.gz src/ run.py requirements.txt
scp -i ~/.ssh/id_rsa newsbot-update.tar.gz root@159.89.90.90:/tmp/
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "cd /tmp && tar -xzf newsbot-update.tar.gz && cp -r src/* /home/newsbot/src/ && cp run.py /home/newsbot/ && chown -R newsbot:newsbot /home/newsbot/ && systemctl restart newsbot"
```

### 🔍 Troubleshooting Commands

#### Check Bot Health
```bash
# Comprehensive status check
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "
echo '=== Bot Service Status ==='
systemctl status newsbot
echo -e '\n=== Recent Logs ==='
journalctl -u newsbot --lines=10 --no-pager
echo -e '\n=== System Resources ==='
free -h
df -h /home/newsbot
"
```

#### Debug Connection Issues
```bash
# Test VPS connection
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "echo 'VPS connection successful'"

# Test bot configuration
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "sudo -u newsbot python3 -c 'import yaml; print(\"Config can be loaded\")'"

# Test Python environment
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "sudo -u newsbot /home/newsbot/venv/bin/python --version"
```

### 📊 Monitoring Commands

#### Real-time Monitoring
```bash
# Monitor logs in real-time
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "journalctl -u newsbot -f"

# Monitor system resources
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "htop"

# Monitor network connections
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "netstat -tulnp | grep python"
```

#### Performance Checks
```bash
# Check bot performance
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "
echo '=== CPU Usage ==='
top -bn1 | grep newsbot
echo -e '\n=== Memory Usage ==='
ps aux | grep newsbot
echo -e '\n=== Disk Usage ==='
du -sh /home/newsbot/logs/
"
```

## 🔧 Manual Deployment

If you prefer manual deployment:

### 1. Upload Files to VPS

```bash
# Create deployment package
tar -czf newsbot-deploy.tar.gz src/ run.py requirements.txt

# Upload to VPS
scp newsbot-deploy.tar.gz root@159.89.90.90:/tmp/
scp vps-deployment/deploy_vps.sh root@159.89.90.90:/tmp/
```

### 2. Run Installation Script

```bash
ssh root@159.89.90.90
chmod +x /tmp/deploy_vps.sh
/tmp/deploy_vps.sh
```

## ✅ Pre-Configured Settings

Your deployment includes these **pre-filled** values:

### Discord Configuration ✅
- **Application ID**: 1378540050006147114
- **Guild ID**: 1228455909827805308
- **Admin Role ID**: 1271183251041681501
- **Admin User ID**: 259725211664908288
- **News Role ID**: 1312489916764131390
- **News Channel**: 1382112473423020062
- **Errors Channel**: 1378781937279176774
- **Logs Channel**: 1378553893083938957
- **Bot Token**: Configured ✅

### Telegram Configuration ✅
- **API ID**: 23834972
- **API Hash**: Configured ✅
- **Bot Token**: Configured ✅

### OpenAI Configuration ✅
- **API Key**: Configured ✅

## 🛠️ Bot Management

Once deployed, use these commands on your VPS:

### Service Management
```bash
# Start bot
sudo systemctl start newsbot

# Stop bot
sudo systemctl stop newsbot

# Restart bot
sudo systemctl restart newsbot

# Check status
sudo systemctl status newsbot

# View logs
journalctl -u newsbot -f
```

### Management Scripts
```bash
# Bot manager (all-in-one script)
/home/newsbot/scripts/bot-manager.sh {start|stop|restart|status|logs|update}

# Health check
/home/newsbot/scripts/health-check.sh
```

## 🔍 Troubleshooting

### Bot Won't Start

1. Check configuration:
   ```bash
   sudo -u newsbot /home/newsbot/venv/bin/python -c "
   import yaml
   with open('/home/newsbot/config/config.yaml') as f:
       config = yaml.safe_load(f)
   print('Config loaded successfully')
   "
   ```

2. Check logs:
   ```bash
   journalctl -u newsbot -n 50
   ```

3. Test bot manually:
   ```bash
   sudo -u newsbot /home/newsbot/venv/bin/python /home/newsbot/run.py
   ```

### Permission Issues

```bash
# Fix ownership
sudo chown -R newsbot:newsbot /home/newsbot/

# Fix permissions
sudo chmod 755 /home/newsbot/
sudo chmod 600 /home/newsbot/config/config.yaml
```

### Network Issues

```bash
# Check firewall
sudo ufw status

# Allow required ports
sudo ufw allow 8000  # Metrics port
```

## 🔒 Security Notes

- The bot runs as a non-privileged `newsbot` user
- Configuration files have restricted permissions (600)
- SystemD service includes security hardening
- Firewall is configured to only allow necessary ports

## 📊 Monitoring

- **Logs**: `/home/newsbot/logs/` and `journalctl -u newsbot`
- **Metrics**: Available on port 8000 (if enabled)
- **Health Check**: `/home/newsbot/scripts/health-check.sh`

## 🔄 Updates

To update the bot:

1. Make changes to your local code
2. Run the deployment script again: `./vps-deployment/deploy_to_vps.sh`
3. Or use the update command: `/home/newsbot/scripts/bot-manager.sh update`

## 💡 Tips

- Configuration is automatically backed up during updates
- Monitor logs regularly for any issues
- Use the health check script to verify everything is working
- All your credentials are pre-configured - no manual setup needed!

## 🆘 Support

If you encounter issues:

1. Check the logs: `journalctl -u newsbot -f`
2. Verify bot is running: `systemctl status newsbot`
3. Test network connectivity: Ensure Discord and Telegram APIs are accessible
4. Check system resources: `htop` or `/home/newsbot/scripts/health-check.sh`

## 🎯 Quick Commands Summary

### 🚀 Deployment Commands
```bash
# Full deployment
./vps-deployment/deploy_to_vps.sh

# Quick update (source files only)
./vps-deployment/deploy_to_vps.sh --quick

# Deploy single file fix
./vps-deployment/quick_fix.sh src/bot/background_tasks.py "Rich presence fix"
```

### 🔍 Monitoring Commands
```bash
# Comprehensive health check
./vps-deployment/health_check.sh

# Quick status check
./vps-deployment/check_bot_status.sh

# Live log monitoring
./vps-deployment/monitor_bot.sh live

# Monitor only errors
./vps-deployment/monitor_bot.sh errors

# Monitor AI activity
./vps-deployment/monitor_bot.sh ai
```

### 💾 Backup Commands
```bash
# Create backup from VPS
./vps-deployment/backup_bot.sh remote

# List existing backups
./vps-deployment/backup_bot.sh list

# Show restore instructions
./vps-deployment/backup_bot.sh restore
```

### 🖥️ Direct VPS Commands
```bash
# Connect to VPS
ssh -i /Users/johnhamwi/.ssh/id_rsa root@159.89.90.90

# Start bot
sudo systemctl start newsbot

# Check status
sudo systemctl status newsbot

# View logs
journalctl -u newsbot -f

# Restart bot
sudo systemctl restart newsbot

# Stop bot
./vps-deployment/stop_bot.sh
```

**Everything is pre-configured - just deploy and start! 🚀** 