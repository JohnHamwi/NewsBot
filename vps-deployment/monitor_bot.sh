#!/bin/bash

# =============================================================================
# NewsBot VPS Log Monitor Script
# =============================================================================
# Easy monitoring of your NewsBot running on DigitalOcean VPS
# Usage: ./monitor_bot.sh [option]
# Options: live, errors, ai, activity, status, recent, config, fix-token

# VPS Configuration
VPS_IP="159.89.90.90"
SSH_KEY="~/.ssh/id_rsa"
SERVICE_NAME="newsbot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to display usage
show_usage() {
    echo -e "${CYAN}==============================================================================${NC}"
    echo -e "${CYAN}                        NewsBot VPS Log Monitor${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC} ./monitor_bot.sh [option]"
    echo ""
    echo -e "${GREEN}Available options:${NC}"
    echo -e "  ${BLUE}live${NC}     - Live log streaming (default)"
    echo -e "  ${BLUE}errors${NC}   - Show only errors and warnings"
    echo -e "  ${BLUE}ai${NC}       - Show AI analysis and urgency detection"
    echo -e "  ${BLUE}activity${NC} - Show posting and fetch activity"
    echo -e "  ${BLUE}status${NC}   - Show bot status and system info"
    echo -e "  ${BLUE}recent${NC}   - Show last 50 log entries"
    echo -e "  ${BLUE}restart${NC}  - Restart the bot service"
    echo -e "  ${BLUE}config${NC}   - Show current configuration (tokens masked)"
    echo -e "  ${BLUE}fix-token${NC} - Interactive token fixing"
    echo -e "  ${BLUE}help${NC}     - Show this help message"
    echo ""
    echo -e "${PURPLE}Examples:${NC}"
    echo -e "  ./monitor_bot.sh live     ${CYAN}# Watch live logs${NC}"
    echo -e "  ./monitor_bot.sh errors   ${CYAN}# Monitor errors only${NC}"
    echo -e "  ./monitor_bot.sh ai       ${CYAN}# Watch AI decisions${NC}"
    echo -e "  ./monitor_bot.sh config   ${CYAN}# Check configuration${NC}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop live monitoring${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
}

# Function to check if bot is running
check_bot_status() {
    echo -e "${YELLOW}Checking bot status...${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "systemctl is-active $SERVICE_NAME" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Bot is running${NC}"
        return 0
    else
        echo -e "${RED}❌ Bot is not running${NC}"
        return 1
    fi
}

# Function to show configuration (with masked tokens)
show_config() {
    echo -e "${BLUE}🔧 Current Bot Configuration${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "cd /home/newsbot && cat config/config_profiles.yaml | sed 's/\(token.*: \).*/\1[MASKED]/g' | sed 's/\(api_key.*: \).*/\1[MASKED]/g'"
    echo ""
    echo -e "${YELLOW}📁 Configuration Files:${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "ls -la /home/newsbot/config/"
}

# Function for interactive token fixing
fix_token() {
    echo -e "${YELLOW}🔧 Discord Token Configuration Fix${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    echo ""
    echo -e "${RED}Current Error: Improper token has been passed${NC}"
    echo ""
    echo -e "${YELLOW}This usually means:${NC}"
    echo -e "  1. Discord token is invalid or expired"
    echo -e "  2. Token has extra characters (spaces, quotes)"
    echo -e "  3. Token is from wrong bot application"
    echo ""
    echo -e "${BLUE}Let's check the current token format...${NC}"
    
    # Check current token (first and last 10 characters only for security)
    echo -e "${YELLOW}Current token format check:${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "cd /home/newsbot && python3 -c \"
import yaml
with open('config/config_profiles.yaml', 'r') as f:
    config = yaml.safe_load(f)
token = config['production']['discord']['token']
if len(token) > 20:
    print(f'Token length: {len(token)} characters')
    print(f'Starts with: {token[:10]}...')
    print(f'Ends with: ...{token[-10:]}')
    if token.startswith('Bot '):
        print('⚠️  Token includes \"Bot \" prefix - this should be removed')
    elif not token.startswith(('MTA', 'MTM', 'OTk', 'MTE')):
        print('⚠️  Token doesn\\'t start with expected Discord bot token format')
    else:
        print('✅ Token format looks correct')
else:
    print('❌ Token is too short or missing')
\""
    
    echo ""
    echo -e "${YELLOW}Would you like to update the Discord token? (y/n):${NC}"
    read -r update_token
    
    if [[ $update_token =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Please enter the correct Discord bot token:${NC}"
        echo -e "${YELLOW}(You can find this in Discord Developer Portal > Bot > Token)${NC}"
        read -r -s new_token
        
        if [[ ${#new_token} -gt 50 ]]; then
            echo -e "${YELLOW}Updating token on VPS...${NC}"
            ssh -i $SSH_KEY root@$VPS_IP "cd /home/newsbot && python3 -c \"
import yaml
with open('config/config_profiles.yaml', 'r') as f:
    config = yaml.safe_load(f)
config['production']['discord']['token'] = '$new_token'
with open('config/config_profiles.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
print('✅ Token updated successfully')
\""
            echo -e "${GREEN}✅ Token updated! Restarting bot...${NC}"
            restart_bot
        else
            echo -e "${RED}❌ Token appears too short. Please check and try again.${NC}"
        fi
    fi
}

# Function for live log monitoring (Method 1)
monitor_live() {
    echo -e "${GREEN}🔴 Starting live log monitoring...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "journalctl -u $SERVICE_NAME -n 20 -f"
}

# Function for error monitoring
monitor_errors() {
    echo -e "${RED}🚨 Monitoring errors and warnings only...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "journalctl -u $SERVICE_NAME -p warning -f"
}

# Function for AI monitoring
monitor_ai() {
    echo -e "${PURPLE}🤖 Monitoring AI analysis and urgency detection...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "journalctl -u $SERVICE_NAME -f | grep -E '(AI|🤖|urgency|BREAKING|IMPORTANT|📊|🔍)'"
}

# Function for activity monitoring
monitor_activity() {
    echo -e "${BLUE}📤 Monitoring posting and fetch activity...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "journalctl -u $SERVICE_NAME -f | grep -E '(FETCH|POST|📤|🚨|📢|✅|❌|BLACKLIST)'"
}

# Function for status check
show_status() {
    echo -e "${GREEN}📊 Bot Status Information${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "systemctl status $SERVICE_NAME --no-pager -l"
    echo ""
    echo -e "${YELLOW}System Resources:${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "free -h && echo '' && df -h / && echo '' && uptime"
}

# Function for recent logs
show_recent() {
    echo -e "${BLUE}📋 Last 50 log entries${NC}"
    echo -e "${CYAN}==============================================================================${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "journalctl -u $SERVICE_NAME -n 50 --no-pager"
}

# Function to restart bot
restart_bot() {
    echo -e "${YELLOW}🔄 Restarting bot service...${NC}"
    ssh -i $SSH_KEY root@$VPS_IP "systemctl restart $SERVICE_NAME"
    echo -e "${GREEN}✅ Restart command sent${NC}"
    echo -e "${YELLOW}Waiting 5 seconds for restart...${NC}"
    sleep 5
    show_status
}

# Main script logic
case "${1:-live}" in
    "live")
        check_bot_status && monitor_live
        ;;
    "errors")
        check_bot_status && monitor_errors
        ;;
    "ai")
        check_bot_status && monitor_ai
        ;;
    "activity")
        check_bot_status && monitor_activity
        ;;
    "status")
        show_status
        ;;
    "recent")
        show_recent
        ;;
    "restart")
        restart_bot
        ;;
    "config")
        show_config
        ;;
    "fix-token")
        fix_token
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        echo -e "${RED}❌ Unknown option: $1${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac 