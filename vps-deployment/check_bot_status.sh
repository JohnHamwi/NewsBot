#!/bin/bash

# =============================================================================
# NewsBot Status Check Script
# =============================================================================
# Quick health check for the NewsBot on VPS

# VPS Configuration
VPS_IP="159.89.90.90"
SSH_KEY="~/.ssh/id_rsa"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}                           NewsBot Status Check                             ${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# Check if bot service is running
echo -e "${BLUE}🔍 Checking bot service status...${NC}"
SERVICE_STATUS=$(ssh -i ~/.ssh/id_rsa root@159.89.90.90 "systemctl is-active newsbot" 2>/dev/null)

if [ "$SERVICE_STATUS" = "active" ]; then
    echo -e "${GREEN}✅ Bot service is running${NC}"
    
    # Get detailed status
    echo -e "${BLUE}📊 Service Details:${NC}"
    ssh -i ~/.ssh/id_rsa root@159.89.90.90 "systemctl status newsbot --no-pager -l" | head -15
    
    echo ""
    echo -e "${BLUE}📝 Recent Activity (last 10 lines):${NC}"
    ssh -i ~/.ssh/id_rsa root@159.89.90.90 "journalctl -u newsbot --no-pager -l --since '5 minutes ago' | tail -10"
    
    echo ""
    echo -e "${BLUE}💾 Resource Usage:${NC}"
    ssh -i ~/.ssh/id_rsa root@159.89.90.90 "ps aux | grep 'python.*run.py' | grep -v grep | awk '{print \"CPU: \" \$3 \"% | Memory: \" \$4 \"% | PID: \" \$2}'"
    
    echo ""
    echo -e "${BLUE}🌐 VPS System Status:${NC}"
    ssh -i ~/.ssh/id_rsa root@159.89.90.90 "uptime && df -h / | tail -1 && free -h | head -2"
    
else
    echo -e "${RED}❌ Bot service is not running (Status: $SERVICE_STATUS)${NC}"
    
    echo -e "${BLUE}📋 Last service logs:${NC}"
    ssh -i ~/.ssh/id_rsa root@159.89.90.90 "journalctl -u newsbot --no-pager -l --since '10 minutes ago' | tail -20"
    
    echo ""
    echo -e "${YELLOW}💡 To restart the bot, run: ssh -i ~/.ssh/id_rsa root@159.89.90.90 'systemctl start newsbot'${NC}"
fi

echo ""
echo -e "${GREEN}🎯 Status check completed!${NC}"
echo -e "${BLUE}==============================================================================${NC}" 