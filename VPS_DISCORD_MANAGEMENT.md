# 🎮 **Discord-Based VPS Management Guide**

## 🚀 **Quick Deployment**

### **1. Deploy to Your VPS**
```bash
# Run this from your local machine:
chmod +x deploy_to_vps.sh
./deploy_to_vps.sh
```

### **2. Configure Bot on VPS**
```bash
# SSH into your VPS:
ssh -i ~/.ssh/id_rsa root@159.89.90.90

# Edit configuration:
sudo -u newsbot nano /home/newsbot/config/config.yaml

# Start the bot:
sudo systemctl start newsbot
```

---

## 🎯 **Discord Commands for VPS Management**

### **🔧 System Operations**
Use `/admin system` command with these operations:

| Command | Description | Use Case |
|---------|-------------|----------|
| `🛡️ Health Check` | Check all systems status | Daily monitoring |
| `📊 System Info` | View bot configuration | Check settings |
| `🔄 Restart Bot` | Restart the bot process | After config changes |
| `🗑️ Clear Cache` | Clear system cache | Performance issues |
| `🔄 Sync Commands` | Sync slash commands | After updates |

### **⏰ Auto-posting Control**
Use `/admin autopost` command:

| Action | Description | When to Use |
|--------|-------------|-------------|
| `✅ Enable` | Start auto-posting | Begin autonomous operation |
| `⏸️ Disable` | Stop auto-posting | Maintenance mode |
| `⏰ Set Interval` | Change posting frequency | Adjust activity level |
| `📊 Show Status` | View current settings | Check configuration |
| `🔄 Reload Config` | Reload from config file | After manual edits |

### **📺 Channel Management**
Use `/admin channels` command:

| Action | Description | Remote Management |
|--------|-------------|-------------------|
| `📋 List All` | View all channels | Monitor setup |
| `➕ Add Channel` | Add new Telegram channel | Expand sources |
| `🟢 Activate` | Enable channel | Include in rotation |
| `🔴 Deactivate` | Disable channel | Temporarily exclude |
| `📊 Statistics` | View channel stats | Performance monitoring |
| `🔄 Reset Rotation` | Reset posting order | Fresh start |

### **🚀 Manual Operations**
Use `/admin post` command:

| Action | Description | Use Case |
|--------|-------------|----------|
| `🚀 Trigger Auto-Post` | Force immediate post | Test or urgent update |
| `📱 Manual Fetch` | Fetch specific content | Review before posting |
| `📊 Post Status` | View posting statistics | Monitor activity |

### **📋 Monitoring Commands**
Use `/admin logs` command:

| Level | Description | When to Use |
|-------|-------------|-------------|
| `🔴 Error` | Show only errors | Troubleshooting |
| `⚠️ Warning` | Show warnings | Monitor issues |
| `ℹ️ Info` | Show info messages | General monitoring |
| `📋 All` | Show all logs | Detailed analysis |

---

## 📊 **VPS Monitoring Through Discord**

### **Daily Health Check Routine**
```
1. /admin system operation:health
   ✅ Check Discord: Connected
   ✅ Check Telegram: Connected  
   ✅ Check Cache: Available

2. /admin autopost action:status
   ✅ Verify auto-posting is enabled
   ✅ Check last post time
   ✅ Confirm interval settings

3. /admin logs level:error lines:20
   ✅ Check for any errors
   ✅ Monitor system stability
```

### **Performance Monitoring**
```
1. /admin system operation:info
   📊 View system configuration
   📈 Check resource usage
   🔍 Monitor performance metrics

2. /admin channels action:statistics
   📺 View channel performance
   📊 Check posting success rates
   🎯 Monitor content quality
```

### **Troubleshooting Commands**
```
# If bot seems stuck:
/admin system operation:restart

# If commands not working:
/admin system operation:sync_commands

# If cache issues:
/admin system operation:clear_cache

# If auto-posting stopped:
/admin autopost action:enable
```

---

## 🔧 **VPS Shell Commands (When Needed)**

### **Connect to VPS**
```bash
ssh -i ~/.ssh/id_rsa root@159.89.90.90
```

### **Bot Management Commands**
```bash
# Quick status check
newsbot-status

# View live logs
newsbot-logs follow

# Restart bot
newsbot-restart

# Stop bot
newsbot-stop

# Start bot
newsbot-start
```

### **System Monitoring**
```bash
# Check system resources
htop

# Check disk space
df -h

# Check memory usage
free -h

# Check bot process
ps aux | grep newsbot
```

### **Configuration Management**
```bash
# Edit bot config
sudo -u newsbot nano /home/newsbot/config/config.yaml

# View bot logs
sudo journalctl -u newsbot -f

# Check service status
systemctl status newsbot
```

---

## 🎯 **Autonomous Operation Setup**

### **1. Initial Configuration**
```
1. Deploy bot to VPS ✅
2. Configure tokens and settings ✅
3. Add Telegram channels ✅
4. Test manual posting ✅
5. Enable auto-posting ✅
```

### **2. Discord Commands for Full Autonomy**
```bash
# Enable auto-posting
/admin autopost action:enable

# Set posting interval (e.g., every 30 minutes)
/admin autopost action:interval value:30

# Verify all channels are active
/admin channels action:list

# Check system health
/admin system operation:health
```

### **3. Monitoring Schedule**
- **Daily**: Health check via Discord
- **Weekly**: Performance review via Discord
- **Monthly**: VPS resource check via SSH

---

## 🚨 **Emergency Procedures**

### **Bot Not Responding**
```
1. /admin system operation:health
   - If no response, SSH to VPS

2. SSH Commands:
   newsbot-status
   newsbot-restart
```

### **High Resource Usage**
```
1. SSH to VPS: ssh -i ~/.ssh/id_rsa root@159.89.90.90
2. Check resources: htop
3. Restart if needed: newsbot-restart
4. Monitor: newsbot-logs follow
```

### **Auto-posting Issues**
```
1. /admin autopost action:status
2. /admin autopost action:reload
3. /admin post action:trigger (test)
4. If failed: /admin system operation:restart
```

---

## 🎉 **Ready for Autonomous Operation!**

Once deployed and configured, your bot will run completely autonomously on the VPS. You can manage everything through Discord commands without ever needing to SSH into the server for normal operations.

**Key Benefits:**
- ✅ **24/7 Operation** - Runs continuously on VPS
- ✅ **Discord Control** - Manage everything through Discord
- ✅ **Auto-restart** - SystemD ensures reliability
- ✅ **Log Rotation** - Automatic log management
- ✅ **Resource Monitoring** - Built-in health checks
- ✅ **Remote Management** - No SSH needed for daily ops 