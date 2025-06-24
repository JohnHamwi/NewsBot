# 📱 Remote VPS Management Guide

**Complete Discord-based administration for 24/7 VPS operation**

## 🎯 Overview

This guide provides comprehensive remote management capabilities for your NewsBot VPS deployment. Everything can be managed through Discord commands, making it perfect for mobile administration when you're away from your computer.

## 🚀 Quick Start Commands

### **📱 Mobile Quick Commands (`/q`)**
*Optimized for mobile Discord usage*

```bash
/q status          # Quick system status
/q health          # Fast health check
/q restart         # Quick bot restart
/q logs            # Recent logs (mobile-friendly)
/q errors          # Error logs only
/q backup          # Create backup
/q emergency       # Emergency diagnostics
/q fix             # Auto-fix common issues
/q cleanup         # Clean temporary files
```

### **🖥️ Full Remote Admin (`/remote`)**
*Comprehensive VPS management*

```bash
# System Monitoring
/remote status          # Full system status
/remote resources       # Detailed resource usage
/remote processes       # Running processes
/remote uptime         # System uptime info

# Log Management
/remote logs [lines]    # View recent logs
/remote logs_error     # Error logs only
/remote logs_clear     # Clear old logs

# Service Control
/remote restart        # Restart bot service
/remote backup         # Manual backup
/remote health         # Comprehensive health check

# Emergency Tools
/remote emergency_info # Emergency diagnostics
/remote history        # Command history
```

### **🚨 Emergency Controls (`/emergency`)**
*Critical system interventions*

```bash
# Immediate Actions
/emergency kill_high_cpu     # Kill high CPU processes
/emergency force_restart     # Force bot restart
/emergency clear_memory      # Emergency memory cleanup
/emergency shutdown_safe     # Safe bot shutdown

# System Controls
/emergency reboot_vps        # Reboot entire VPS (last resort)
/emergency kill_process <pid> # Kill specific process
/emergency disk_emergency    # Emergency disk cleanup

# Diagnostics
/emergency system_info       # Critical system info
/emergency emergency_log     # View emergency actions
```

## 🔔 Notification System

### **Automatic Alerts**
The bot proactively monitors your VPS and sends alerts for:

- **🔥 Critical Issues**: CPU >95%, RAM >98%, Disk >98%
- **⚠️ Warnings**: CPU >85%, RAM >90%, Disk >95%
- **🤖 Bot Health**: Health score <70, High latency >5s
- **📊 Daily Reports**: 8 AM UTC system summary

### **Alert Channels**
- **DM Notifications**: Immediate alerts to admin user
- **Channel Notifications**: Alerts posted to designated channels
- **Smart Cooldowns**: Prevents alert spam (15-minute cooldowns)

### **Notification Commands**
```bash
/notify settings       # View notification settings
/notify test          # Send test notification
/notify history       # View recent alerts
/notify toggle_dm     # Toggle DM notifications
```

## 📊 System Monitoring

### **Real-Time Metrics**
Monitor your VPS health with detailed metrics:

- **CPU Usage**: Real-time and per-core monitoring
- **Memory Usage**: RAM, swap, and available memory
- **Disk Usage**: Space usage across all partitions
- **Network**: Data transfer statistics
- **Bot Health**: Performance and connectivity metrics

### **Health Scoring**
- **90-100**: Excellent health ✅
- **70-89**: Good with minor issues ⚠️
- **50-69**: Problems need attention ❌
- **<50**: Critical issues requiring immediate action 🔥

## 🛠️ Troubleshooting Scenarios

### **High CPU Usage**
```bash
1. /q status                    # Check current usage
2. /remote processes           # Identify problematic processes
3. /emergency kill_high_cpu    # Kill CPU-intensive processes
4. /q restart                  # Restart if needed
```

### **Memory Issues**
```bash
1. /q status                   # Check memory usage
2. /emergency clear_memory     # Free up memory
3. /q cleanup                  # Clean temporary files
4. /q restart                  # Restart to clear memory leaks
```

### **Disk Space Low**
```bash
1. /q status                   # Check disk usage
2. /q cleanup                  # Clean temporary files
3. /emergency disk_emergency   # Emergency cleanup
4. /remote logs_clear          # Clear old logs
```

### **Bot Not Responding**
```bash
1. /q emergency               # Get emergency diagnostics
2. /emergency system_info     # Check system status
3. /emergency force_restart   # Force restart if needed
4. /emergency reboot_vps      # Last resort - full reboot
```

### **Network Issues**
```bash
1. /remote status             # Check connectivity
2. /emergency system_info     # Detailed diagnostics
3. /q restart                 # Restart network services
4. Contact VPS provider if persistent
```

## 📱 Mobile Usage Tips

### **Optimized for Mobile**
- **Short Commands**: Use `/q` for quick actions
- **Readable Output**: Mobile-friendly formatting
- **Touch-Friendly**: Reaction-based confirmations
- **Minimal Typing**: Pre-configured quick actions

### **Emergency Contacts**
Set up these for critical situations:
- **Discord Mobile App**: Primary management interface
- **VPS Provider Support**: For hardware/network issues
- **Backup Admin**: Secondary person with access

### **Best Practices**
1. **Regular Checks**: Use `/q status` daily
2. **Monitor Alerts**: Enable DM notifications
3. **Document Actions**: Emergency log tracks all actions
4. **Test Commands**: Use `/notify test` to verify alerts work
5. **Know Limits**: Don't overuse emergency commands

## 🔒 Security Features

### **Admin Authentication**
- **Role-Based Access**: Only admin users can execute commands
- **Command Logging**: All actions logged with user details
- **Confirmation Prompts**: Critical actions require confirmation
- **Timeout Protection**: Commands timeout for safety

### **Safe Defaults**
- **Non-Destructive**: Most commands are read-only
- **Graceful Degradation**: Bot continues if commands fail
- **Backup Integration**: Automatic backups before changes
- **Rollback Capability**: Can restore from backups

## ⚡ Automation Features

### **Auto-Recovery**
The system automatically handles common issues:
- **Process Monitoring**: Restarts crashed services
- **Resource Management**: Cleans memory and disk space
- **Health Checks**: Continuous monitoring every 5 minutes
- **Alert Escalation**: Progressively stronger alerts

### **Scheduled Maintenance**
- **Daily Reports**: System health summary
- **Automated Cleanup**: Temporary files and logs
- **Backup Rotation**: Automatic old backup cleanup
- **Health Monitoring**: Continuous background checks

## 📋 Command Reference

### **Status Commands**
| Command | Description | Mobile | Admin |
|---------|-------------|--------|-------|
| `/q status` | Quick system overview | ✅ | ✅ |
| `/remote status` | Detailed system status | ❌ | ✅ |
| `/q health` | Fast health check | ✅ | ✅ |
| `/remote health` | Comprehensive health | ❌ | ✅ |

### **Control Commands**
| Command | Description | Risk | Confirmation |
|---------|-------------|------|-------------|
| `/q restart` | Quick bot restart | Low | ✅ |
| `/remote restart` | Service restart | Low | ✅ |
| `/emergency force_restart` | Force restart | Medium | ✅ |
| `/emergency reboot_vps` | Full VPS reboot | High | Double ✅ |

### **Diagnostic Commands**
| Command | Description | Output | Best For |
|---------|-------------|--------|----------|
| `/q logs` | Recent logs | Mobile | Quick check |
| `/remote logs [lines]` | Detailed logs | Desktop | Investigation |
| `/q errors` | Error logs only | Mobile | Problem solving |
| `/emergency system_info` | Critical metrics | Desktop | Emergencies |

## 🎯 Use Cases

### **Daily Management**
```bash
Morning: /q status + /notify history
Evening: /q health + /q backup
Issues: /q emergency + /q fix
```

### **On-the-Go Monitoring**
```bash
Quick Check: /q status
Problem Alert: /q emergency → /q fix → /q restart
Weekly Review: /remote history + /notify history
```

### **Emergency Response**
```bash
Bot Down: /emergency system_info → /emergency force_restart
High Resources: /emergency kill_high_cpu → /emergency clear_memory
VPS Issues: /emergency emergency_log → Contact support
```

### **Performance Optimization**
```bash
Regular: /q cleanup + /q health
Weekly: /remote backup + /remote logs_clear
Monthly: Review /notify history for patterns
```

## 📞 Support & Troubleshooting

### **Common Issues**
1. **Commands not working**: Check admin permissions
2. **No notifications**: Verify DM settings with `/notify settings`
3. **High resource usage**: Use emergency commands to investigate
4. **VPS unresponsive**: Use `/emergency reboot_vps` as last resort

### **Getting Help**
- **Command Help**: Each command group shows help when called without subcommands
- **Emergency Log**: `/emergency emergency_log` shows recent critical actions
- **Health Details**: `/remote health` provides comprehensive diagnostics
- **System Info**: `/emergency system_info` gives critical system details

### **Emergency Contacts**
When Discord commands aren't enough:
1. **VPS Provider Support**: For hardware/network issues
2. **SSH Access**: Direct terminal access if available
3. **Backup Admin**: Secondary person with access
4. **Recovery Plan**: Pre-planned steps for worst-case scenarios

---

**🛡️ Remember: This system gives you powerful remote control over your VPS. Use emergency commands carefully and always document significant actions in the emergency log.** 