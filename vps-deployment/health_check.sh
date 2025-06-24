#!/bin/bash

# =============================================================================
# NewsBot VPS Health Check Script
# =============================================================================
# Comprehensive health check for NewsBot running on VPS
# Usage: ./health_check.sh [--detailed]

# VPS Configuration
VPS_IP="159.89.90.90"
SSH_KEY="~/.ssh/id_rsa"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Detailed mode flag
DETAILED=false
if [ "$1" = "--detailed" ] || [ "$1" = "-d" ]; then
    DETAILED=true
fi

echo -e "${CYAN}==============================================================================${NC}"
echo -e "${CYAN}                          NewsBot Health Check                              ${NC}"
echo -e "${CYAN}==============================================================================${NC}"
echo ""

# Function to check service status
check_service_status() {
    echo -e "${BLUE}🔍 Checking service status...${NC}"
    
    SERVICE_STATUS=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "systemctl is-active newsbot" 2>/dev/null)
    SERVICE_ENABLED=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "systemctl is-enabled newsbot" 2>/dev/null)
    
    if [ "$SERVICE_STATUS" = "active" ]; then
        echo -e "${GREEN}✅ Service Status: Running${NC}"
    else
        echo -e "${RED}❌ Service Status: $SERVICE_STATUS${NC}"
    fi
    
    if [ "$SERVICE_ENABLED" = "enabled" ]; then
        echo -e "${GREEN}✅ Auto-start: Enabled${NC}"
    else
        echo -e "${YELLOW}⚠️  Auto-start: $SERVICE_ENABLED${NC}"
    fi
}

# Function to check system resources
check_system_resources() {
    echo -e "${BLUE}💻 Checking system resources...${NC}"
    
    # Get system info
    SYSTEM_INFO=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "
        echo 'CPU_USAGE:'$(top -bn1 | grep 'Cpu(s)' | awk '{print \$2}' | cut -d'%' -f1)
        echo 'MEMORY_USAGE:'$(free | awk 'NR==2{printf \"%.1f\", \$3*100/\$2}')
        echo 'DISK_USAGE:'$(df -h / | awk 'NR==2 {print \$5}' | cut -d'%' -f1)
        echo 'UPTIME:'$(uptime -p)
        echo 'LOAD:'$(uptime | awk -F'load average:' '{print \$2}')
    ")
    
    # Parse and display
    while IFS= read -r line; do
        case $line in
            CPU_USAGE:*)
                cpu=${line#CPU_USAGE:}
                if (( $(echo "$cpu > 80" | bc -l) )); then
                    echo -e "${RED}❌ CPU Usage: ${cpu}% (High)${NC}"
                elif (( $(echo "$cpu > 60" | bc -l) )); then
                    echo -e "${YELLOW}⚠️  CPU Usage: ${cpu}% (Moderate)${NC}"
                else
                    echo -e "${GREEN}✅ CPU Usage: ${cpu}% (Good)${NC}"
                fi
                ;;
            MEMORY_USAGE:*)
                mem=${line#MEMORY_USAGE:}
                if (( $(echo "$mem > 85" | bc -l) )); then
                    echo -e "${RED}❌ Memory Usage: ${mem}% (High)${NC}"
                elif (( $(echo "$mem > 70" | bc -l) )); then
                    echo -e "${YELLOW}⚠️  Memory Usage: ${mem}% (Moderate)${NC}"
                else
                    echo -e "${GREEN}✅ Memory Usage: ${mem}% (Good)${NC}"
                fi
                ;;
            DISK_USAGE:*)
                disk=${line#DISK_USAGE:}
                if (( disk > 90 )); then
                    echo -e "${RED}❌ Disk Usage: ${disk}% (Critical)${NC}"
                elif (( disk > 80 )); then
                    echo -e "${YELLOW}⚠️  Disk Usage: ${disk}% (High)${NC}"
                else
                    echo -e "${GREEN}✅ Disk Usage: ${disk}% (Good)${NC}"
                fi
                ;;
            UPTIME:*)
                uptime=${line#UPTIME:}
                echo -e "${BLUE}📊 System Uptime: ${uptime}${NC}"
                ;;
            LOAD:*)
                load=${line#LOAD:}
                echo -e "${BLUE}📈 Load Average:${load}${NC}"
                ;;
        esac
    done <<< "$SYSTEM_INFO"
}

# Function to check bot connectivity
check_bot_connectivity() {
    echo -e "${BLUE}🌐 Checking bot connectivity...${NC}"
    
    # Check recent logs for connection issues
    CONN_CHECK=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "
        journalctl -u newsbot --since '5 minutes ago' | grep -E '(Connected|Disconnected|Login|Authentication|Error)' | tail -5
    ")
    
    if echo "$CONN_CHECK" | grep -q "Connected\|Login"; then
        echo -e "${GREEN}✅ Bot appears to be connected${NC}"
    elif echo "$CONN_CHECK" | grep -q "Error\|Failed"; then
        echo -e "${RED}❌ Connection issues detected${NC}"
        if [ "$DETAILED" = true ]; then
            echo -e "${YELLOW}Recent connection logs:${NC}"
            echo "$CONN_CHECK"
        fi
    else
        echo -e "${YELLOW}⚠️  No recent connection activity${NC}"
    fi
}

# Function to check for errors
check_recent_errors() {
    echo -e "${BLUE}🚨 Checking for recent errors...${NC}"
    
    ERROR_COUNT=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "
        journalctl -u newsbot --since '1 hour ago' | grep -c 'ERROR\|CRITICAL\|FATAL'
    ")
    
    if [ "$ERROR_COUNT" -eq 0 ]; then
        echo -e "${GREEN}✅ No errors in the last hour${NC}"
    elif [ "$ERROR_COUNT" -lt 5 ]; then
        echo -e "${YELLOW}⚠️  $ERROR_COUNT errors in the last hour${NC}"
    else
        echo -e "${RED}❌ $ERROR_COUNT errors in the last hour (High)${NC}"
    fi
    
    if [ "$DETAILED" = true ] && [ "$ERROR_COUNT" -gt 0 ]; then
        echo -e "${YELLOW}Recent errors:${NC}"
        ssh -i ~/.ssh/id_rsa root@$VPS_IP "
            journalctl -u newsbot --since '1 hour ago' | grep 'ERROR\|CRITICAL\|FATAL' | tail -3
        "
    fi
}

# Function to check dependencies
check_dependencies() {
    echo -e "${BLUE}🔧 Checking dependencies...${NC}"
    
    # Check Redis
    REDIS_STATUS=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "systemctl is-active redis-server" 2>/dev/null)
    if [ "$REDIS_STATUS" = "active" ]; then
        echo -e "${GREEN}✅ Redis: Running${NC}"
    else
        echo -e "${RED}❌ Redis: $REDIS_STATUS${NC}"
    fi
    
    # Check Python environment
    PYTHON_CHECK=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "sudo -u newsbot /home/newsbot/venv/bin/python --version" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Python Environment: OK ($PYTHON_CHECK)${NC}"
    else
        echo -e "${RED}❌ Python Environment: Issues detected${NC}"
    fi
    
    # Check config file
    CONFIG_CHECK=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "test -f /home/newsbot/config/unified_config.yaml && echo 'OK' || echo 'MISSING'")
    if [ "$CONFIG_CHECK" = "OK" ]; then
        echo -e "${GREEN}✅ Configuration: Present${NC}"
    else
        echo -e "${RED}❌ Configuration: Missing${NC}"
    fi
}

# Function to check bot performance
check_bot_performance() {
    echo -e "${BLUE}⚡ Checking bot performance...${NC}"
    
    # Get bot process info
    BOT_PROCESS=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "
        ps aux | grep 'python.*run.py' | grep -v grep | awk '{print \"PID:\" \$2 \" CPU:\" \$3 \"% MEM:\" \$4 \"% TIME:\" \$10}'
    ")
    
    if [ -n "$BOT_PROCESS" ]; then
        echo -e "${GREEN}✅ Bot Process: $BOT_PROCESS${NC}"
    else
        echo -e "${RED}❌ Bot Process: Not found${NC}"
    fi
    
    # Check log file size
    LOG_SIZE=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "du -sh /home/newsbot/logs/ 2>/dev/null | cut -f1")
    if [ -n "$LOG_SIZE" ]; then
        echo -e "${BLUE}📝 Log Directory Size: $LOG_SIZE${NC}"
    fi
}

# Function to show summary
show_summary() {
    echo ""
    echo -e "${CYAN}==============================================================================${NC}"
    echo -e "${CYAN}                              Summary                                       ${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    
    # Overall health assessment
    OVERALL_STATUS=$(ssh -i ~/.ssh/id_rsa root@$VPS_IP "
        if systemctl is-active newsbot >/dev/null 2>&1 && systemctl is-active redis-server >/dev/null 2>&1; then
            echo 'HEALTHY'
        else
            echo 'ISSUES'
        fi
    ")
    
    if [ "$OVERALL_STATUS" = "HEALTHY" ]; then
        echo -e "${GREEN}🎉 Overall Status: HEALTHY${NC}"
        echo -e "${GREEN}✅ Bot is running normally${NC}"
    else
        echo -e "${RED}⚠️  Overall Status: ISSUES DETECTED${NC}"
        echo -e "${YELLOW}🔧 Manual intervention may be required${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}📋 Quick Actions:${NC}"
    echo -e "  Monitor logs: ${CYAN}./monitor_bot.sh live${NC}"
    echo -e "  Check status: ${CYAN}./check_bot_status.sh${NC}"
    echo -e "  Restart bot:  ${CYAN}ssh -i ~/.ssh/id_rsa root@$VPS_IP 'systemctl restart newsbot'${NC}"
}

# Main execution
check_service_status
echo ""
check_system_resources
echo ""
check_bot_connectivity
echo ""
check_recent_errors
echo ""
check_dependencies
echo ""
check_bot_performance
echo ""
show_summary

echo ""
echo -e "${GREEN}🎯 Health check completed!${NC}"
echo -e "${YELLOW}💡 For detailed monitoring, run: ./monitor_bot.sh${NC}"
echo -e "${CYAN}==============================================================================${NC}" 