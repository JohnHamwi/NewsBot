#!/bin/bash

# =============================================================================
# NewsBot Telegram Re-Authentication Script
# =============================================================================
# Quickly re-authenticate Telegram when session issues occur
# Usage: ./reauth_telegram.sh

# VPS Configuration
VPS_IP="159.89.90.90"
SSH_KEY="~/.ssh/id_rsa"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}                     NewsBot Telegram Re-Authentication                      ${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# Test VPS connection
echo -e "${YELLOW}🔗 Testing VPS connection...${NC}"
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 root@$VPS_IP "echo 'Connection successful'" 2>/dev/null; then
    echo -e "${RED}❌ Cannot connect to VPS${NC}"
    echo -e "${YELLOW}💡 Make sure VPS is running and SSH key is correct${NC}"
    exit 1
fi
echo -e "${GREEN}✅ VPS connection successful${NC}"
echo ""

# Check if re-authentication is needed
echo -e "${YELLOW}🔍 Checking current Telegram session status...${NC}"
TELEGRAM_STATUS=$(ssh -i "$SSH_KEY" root@$VPS_IP "journalctl -u newsbot --since '5 minutes ago' | grep -E '(session|auth|Telegram.*not authorized|Failed to connect to Telegram)' | tail -1")

if [[ $TELEGRAM_STATUS == *"not authorized"* ]] || [[ $TELEGRAM_STATUS == *"session"* ]] || [[ $TELEGRAM_STATUS == *"Failed to connect"* ]]; then
    echo -e "${RED}⚠️  Telegram session issue detected${NC}"
    echo -e "${CYAN}Issue: $TELEGRAM_STATUS${NC}"
    echo ""
else
    echo -e "${GREEN}✅ No obvious Telegram issues detected${NC}"
    echo -e "${YELLOW}💭 Continuing with re-authentication anyway...${NC}"
    echo ""
fi

# Stop the bot
echo -e "${YELLOW}🛑 Stopping bot service...${NC}"
ssh -i "$SSH_KEY" root@$VPS_IP "systemctl stop newsbot"
echo -e "${GREEN}✅ Bot stopped${NC}"
echo ""

# Backup and remove session
echo -e "${YELLOW}🔧 Backing up and removing current session...${NC}"
ssh -i "$SSH_KEY" root@$VPS_IP "
cd /home/newsbot/data/sessions/
if [ -f newsbot.session ]; then
    cp newsbot.session newsbot.session.backup.\$(date +%Y%m%d_%H%M%S)
    rm -f newsbot.session
    echo 'Session backed up and removed'
else
    echo 'No existing session file found'
fi
"
echo ""

# Instructions for authentication
echo -e "${CYAN}📱 TELEGRAM AUTHENTICATION REQUIRED${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo -e "${YELLOW}The following commands will run interactively:${NC}"
echo -e "${BLUE}1. Connect to VPS as newsbot user${NC}"
echo -e "${BLUE}2. Activate virtual environment${NC}"
echo -e "${BLUE}3. Run authentication script${NC}"
echo ""
echo -e "${YELLOW}You will need to:${NC}"
echo -e "${CYAN}• Enter your phone number (with country code, e.g., +1234567890)${NC}"
echo -e "${CYAN}• Enter the verification code Telegram sends you${NC}"
echo ""
echo -e "${GREEN}Press ENTER when ready to continue...${NC}"
read -r

# Connect and run authentication
echo -e "${YELLOW}🚀 Connecting to VPS and starting authentication...${NC}"
echo ""

ssh -i "$SSH_KEY" -t root@$VPS_IP "
echo -e '${CYAN}📱 Starting Telegram authentication process...${NC}'
echo -e '${YELLOW}Switching to newsbot user and activating environment...${NC}'
echo ''

sudo -u newsbot bash -c '
cd /home/newsbot
source venv/bin/activate
echo -e \"${GREEN}✅ Virtual environment activated${NC}\"
echo -e \"${YELLOW}🔐 Running Telegram authentication...${NC}\"
echo \"\"
python3 authenticate_telegram.py
'
"

# Check if authentication was successful
echo ""
echo -e "${YELLOW}🔍 Checking authentication result...${NC}"
sleep 2

SESSION_EXISTS=$(ssh -i "$SSH_KEY" root@$VPS_IP "[ -f /home/newsbot/data/sessions/newsbot.session ] && echo 'exists' || echo 'missing'")

if [ "$SESSION_EXISTS" = "exists" ]; then
    echo -e "${GREEN}✅ Authentication successful - session file created${NC}"
    
    # Start the bot
    echo -e "${YELLOW}🚀 Starting bot service...${NC}"
    ssh -i "$SSH_KEY" root@$VPS_IP "systemctl start newsbot"
    
    echo -e "${YELLOW}⏳ Waiting for bot startup...${NC}"
    sleep 10
    
    # Check startup status
    echo -e "${YELLOW}🔍 Checking bot status...${NC}"
    STARTUP_STATUS=$(ssh -i "$SSH_KEY" root@$VPS_IP "journalctl -u newsbot --since '30 seconds ago' | grep -E '(Telegram.*connected|STARTUP COMPLETE|session)' | tail -2")
    
    if [[ $STARTUP_STATUS == *"connected"* ]] || [[ $STARTUP_STATUS == *"COMPLETE"* ]]; then
        echo -e "${GREEN}🎉 SUCCESS! Bot is running with new Telegram session${NC}"
        echo ""
        echo -e "${CYAN}Recent status:${NC}"
        echo -e "${CYAN}$STARTUP_STATUS${NC}"
    else
        echo -e "${YELLOW}⚠️  Bot started but checking status...${NC}"
        ssh -i "$SSH_KEY" root@$VPS_IP "systemctl status newsbot --no-pager -l | head -10"
    fi
    
else
    echo -e "${RED}❌ Authentication may have failed - session file not found${NC}"
    echo -e "${YELLOW}💡 You may need to run the authentication manually${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎯 Telegram re-authentication completed!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo -e "${CYAN}• Monitor logs: ./monitor_bot.sh live${NC}"
echo -e "${CYAN}• Check status: ./check_bot_status.sh${NC}"
echo -e "${CYAN}• Test translation by sending a message to monitored channels${NC}"
echo ""
echo -e "${BLUE}==============================================================================${NC}" 