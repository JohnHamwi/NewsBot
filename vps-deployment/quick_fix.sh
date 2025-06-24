#!/bin/bash

# =============================================================================
# NewsBot Quick Fix Deployment Script
# =============================================================================
# Quickly deploy single file fixes to VPS without full redeployment
# Usage: ./quick_fix.sh <file_path> [description]

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
echo -e "${BLUE}                        NewsBot Quick Fix Deployment                        ${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# Check for help
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo -e "${CYAN}📖 Quick Fix Deployment Script${NC}"
    echo -e "${CYAN}Quickly deploy single file fixes to VPS without full redeployment${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC} ./quick_fix.sh <file_path> [description]"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  ${CYAN}./quick_fix.sh src/bot/background_tasks.py \"Rich presence time variable fix\"${NC}"
    echo -e "  ${CYAN}./quick_fix.sh src/utils/logger.py \"Logging improvements\"${NC}"
    echo -e "  ${CYAN}./quick_fix.sh config/unified_config.yaml \"Config update\"${NC}"
    echo ""
    echo -e "${YELLOW}Features:${NC}"
    echo "  • Automatic backup of existing files"
    echo "  • Proper permission setting based on file type"
    echo "  • Automatic bot restart and status check"
    echo "  • Easy rollback instructions"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo "  --help, -h    Show this help message"
    echo ""
    exit 0
fi

# Check if file path is provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: File path is required${NC}"
    echo ""
    echo -e "${YELLOW}Usage: ./quick_fix.sh <file_path> [description]${NC}"
    echo ""
    echo -e "${BLUE}Examples:${NC}"
    echo -e "  ${CYAN}./quick_fix.sh src/bot/background_tasks.py \"Rich presence time variable fix\"${NC}"
    echo -e "  ${CYAN}./quick_fix.sh src/utils/logger.py \"Logging improvements\"${NC}"
    echo -e "  ${CYAN}./quick_fix.sh config/unified_config.yaml \"Config update\"${NC}"
    echo ""
    echo -e "${YELLOW}💡 For help: ./quick_fix.sh --help${NC}"
    exit 1
fi

FILE_PATH="$1"
DESCRIPTION="${2:-Quick fix deployment}"

# Check if file exists
if [ ! -f "$FILE_PATH" ]; then
    echo -e "${RED}❌ Error: File '$FILE_PATH' not found${NC}"
    exit 1
fi

echo -e "${YELLOW}📁 File to deploy: ${CYAN}$FILE_PATH${NC}"
echo -e "${YELLOW}📝 Description: ${CYAN}$DESCRIPTION${NC}"
echo ""

# Test VPS connection
echo -e "${BLUE}🔗 Testing VPS connection...${NC}"
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 root@$VPS_IP "echo 'Connection successful'" 2>/dev/null; then
    echo -e "${RED}❌ Cannot connect to VPS${NC}"
    exit 1
fi
echo -e "${GREEN}✅ VPS connection successful${NC}"

# Determine target path on VPS
VPS_TARGET_PATH="/home/newsbot/$FILE_PATH"
VPS_TARGET_DIR=$(dirname "$VPS_TARGET_PATH")

echo -e "${BLUE}📤 Deploying file to VPS...${NC}"

# Create backup of existing file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="$(basename $FILE_PATH).backup.$TIMESTAMP"

ssh -i "$SSH_KEY" root@$VPS_IP "
    # Create backup directory if it doesn't exist
    mkdir -p /home/newsbot/backups
    
    # Backup existing file if it exists
    if [ -f '$VPS_TARGET_PATH' ]; then
        cp '$VPS_TARGET_PATH' '/home/newsbot/backups/$BACKUP_NAME'
        echo '📋 Backup created: /home/newsbot/backups/$BACKUP_NAME'
    fi
    
    # Ensure target directory exists
    mkdir -p '$VPS_TARGET_DIR'
"

# Upload the file
echo -e "${YELLOW}⬆️  Uploading file...${NC}"
scp -i "$SSH_KEY" "$FILE_PATH" "root@$VPS_IP:$VPS_TARGET_PATH"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ File uploaded successfully${NC}"
else
    echo -e "${RED}❌ Failed to upload file${NC}"
    exit 1
fi

# Fix permissions and restart bot
echo -e "${BLUE}🔧 Fixing permissions and restarting bot...${NC}"
ssh -i "$SSH_KEY" root@$VPS_IP "
    # Fix ownership
    chown newsbot:newsbot '$VPS_TARGET_PATH'
    
    # Fix permissions based on file type
    if [[ '$FILE_PATH' == *.py ]]; then
        chmod 644 '$VPS_TARGET_PATH'
    elif [[ '$FILE_PATH' == *.sh ]]; then
        chmod 755 '$VPS_TARGET_PATH'
    elif [[ '$FILE_PATH' == *.yaml ]] || [[ '$FILE_PATH' == *.yml ]]; then
        chmod 600 '$VPS_TARGET_PATH'
    else
        chmod 644 '$VPS_TARGET_PATH'
    fi
    
    echo '🔄 Restarting bot service...'
    systemctl restart newsbot
    
    # Wait a moment for restart
    sleep 3
    
    # Check if service started successfully
    if systemctl is-active newsbot >/dev/null 2>&1; then
        echo '✅ Bot restarted successfully'
    else
        echo '❌ Bot failed to restart - check logs'
        echo '📋 Recent logs:'
        journalctl -u newsbot --no-pager -n 10
    fi
"

echo ""
echo -e "${GREEN}🎉 Quick fix deployment completed!${NC}"
echo ""
echo -e "${BLUE}📋 Post-deployment actions:${NC}"
echo -e "  Check status: ${CYAN}./check_bot_status.sh${NC}"
echo -e "  Monitor logs: ${CYAN}./monitor_bot.sh live${NC}"
echo -e "  Health check: ${CYAN}./health_check.sh${NC}"
echo ""

# Show recent logs
echo -e "${BLUE}📝 Recent bot logs (last 10 lines):${NC}"
ssh -i "$SSH_KEY" root@$VPS_IP "journalctl -u newsbot --no-pager -n 10"

echo ""
echo -e "${YELLOW}💡 If the fix caused issues, you can restore from backup:${NC}"
echo -e "${CYAN}ssh -i $SSH_KEY root@$VPS_IP 'cp /home/newsbot/backups/$BACKUP_NAME $VPS_TARGET_PATH && systemctl restart newsbot'${NC}"
echo ""
echo -e "${BLUE}==============================================================================${NC}" 