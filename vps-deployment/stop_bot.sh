#!/bin/bash

# =============================================================================
# NewsBot VPS Stop Script
# =============================================================================
# Stop the NewsBot and optionally shut down the VPS
# Usage: ./stop_bot.sh [shutdown]

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
echo -e "${BLUE}                           NewsBot Stop Script                              ${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# Function to stop the bot
stop_bot() {
    echo -e "${YELLOW}🛑 Stopping NewsBot service...${NC}"
    ssh -i ~/.ssh/id_rsa root@159.89.90.90 "systemctl stop newsbot"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ NewsBot service stopped successfully${NC}"
        
        # Get final status
        echo -e "${BLUE}📊 Final Status:${NC}"
        ssh -i ~/.ssh/id_rsa root@159.89.90.90 "systemctl status newsbot --no-pager -l" | head -10
        
        # Show resource usage
        echo -e "${BLUE}💾 Resource Usage Summary:${NC}"
        ssh -i ~/.ssh/id_rsa root@159.89.90.90 "systemctl show newsbot --property=MemoryPeak,CPUUsageNSec"
        
    else
        echo -e "${RED}❌ Failed to stop NewsBot service${NC}"
        return 1
    fi
}

# Function to shutdown VPS
shutdown_vps() {
    echo ""
    echo -e "${YELLOW}⚠️  WARNING: This will shut down the entire VPS!${NC}"
    echo -e "${YELLOW}⚠️  The VPS will need to be manually restarted from DigitalOcean dashboard${NC}"
    echo ""
    read -p "Are you sure you want to shutdown the VPS? (type 'yes' to confirm): " confirm
    
    if [ "$confirm" = "yes" ]; then
        echo -e "${RED}🔌 Shutting down VPS...${NC}"
        ssh -i ~/.ssh/id_rsa root@159.89.90.90 "shutdown -h now"
        echo -e "${GREEN}✅ VPS shutdown command sent${NC}"
        echo -e "${BLUE}📱 You can restart the VPS from: https://cloud.digitalocean.com/droplets${NC}"
    else
        echo -e "${YELLOW}🚫 VPS shutdown cancelled${NC}"
    fi
}

# Main execution
echo -e "${BLUE}🔍 Checking current bot status...${NC}"
ssh -i ~/.ssh/id_rsa root@159.89.90.90 "systemctl is-active newsbot" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Bot is currently running${NC}"
    stop_bot
else
    echo -e "${YELLOW}⚠️  Bot is already stopped${NC}"
fi

echo ""

# Check if shutdown was requested
if [ "$1" = "shutdown" ]; then
    shutdown_vps
else
    echo -e "${BLUE}💡 Bot stopped. To also shutdown the VPS, run: ./stop_bot.sh shutdown${NC}"
    echo -e "${BLUE}💡 To restart just the bot later, run: ssh -i ~/.ssh/id_rsa root@159.89.90.90 'systemctl start newsbot'${NC}"
fi

echo ""
echo -e "${GREEN}🎯 Stop script completed!${NC}"
echo -e "${BLUE}==============================================================================${NC}" 