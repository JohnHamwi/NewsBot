#!/bin/bash

# =============================================================================
# NewsBot VPS Backup Script
# =============================================================================
# Backup bot configuration, data, and logs from VPS
# Usage: ./backup_bot.sh [local|remote]

# VPS Configuration
VPS_IP="159.89.90.90"
SSH_KEY="~/.ssh/id_rsa"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Backup directory
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="newsbot_backup_$TIMESTAMP"

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}                           NewsBot Backup Script                            ${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Function to create remote backup
create_remote_backup() {
    echo -e "${YELLOW}📦 Creating backup on VPS...${NC}"
    
    ssh -i ~/.ssh/id_rsa root@$VPS_IP "
        # Create backup directory
        mkdir -p /tmp/newsbot_backups
        
        # Create timestamped backup
        BACKUP_PATH=/tmp/newsbot_backups/$BACKUP_NAME
        mkdir -p \$BACKUP_PATH
        
        echo '📁 Backing up configuration...'
        cp -r /home/newsbot/config \$BACKUP_PATH/ 2>/dev/null || echo 'No config directory'
        
        echo '📊 Backing up data...'
        cp -r /home/newsbot/data \$BACKUP_PATH/ 2>/dev/null || echo 'No data directory'
        
        echo '📝 Backing up recent logs...'
        mkdir -p \$BACKUP_PATH/logs
        cp /home/newsbot/logs/*.log \$BACKUP_PATH/logs/ 2>/dev/null || echo 'No log files'
        
        echo '📋 Backing up service configuration...'
        cp /etc/systemd/system/newsbot.service \$BACKUP_PATH/ 2>/dev/null || echo 'No service file'
        
        echo '🗃️ Creating system info...'
        echo '=== System Information ===' > \$BACKUP_PATH/system_info.txt
        date >> \$BACKUP_PATH/system_info.txt
        systemctl status newsbot --no-pager >> \$BACKUP_PATH/system_info.txt
        echo '' >> \$BACKUP_PATH/system_info.txt
        echo '=== Recent Logs ===' >> \$BACKUP_PATH/system_info.txt
        journalctl -u newsbot --since '24 hours ago' --no-pager | tail -50 >> \$BACKUP_PATH/system_info.txt
        
        echo '📦 Creating archive...'
        cd /tmp/newsbot_backups
        tar -czf $BACKUP_NAME.tar.gz $BACKUP_NAME/
        
        echo '✅ Remote backup created: /tmp/newsbot_backups/$BACKUP_NAME.tar.gz'
    "
}

# Function to download backup
download_backup() {
    echo -e "${YELLOW}📥 Downloading backup from VPS...${NC}"
    
    scp -i ~/.ssh/id_rsa root@$VPS_IP:/tmp/newsbot_backups/$BACKUP_NAME.tar.gz "$BACKUP_DIR/"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Backup downloaded to: $BACKUP_DIR/$BACKUP_NAME.tar.gz${NC}"
        
        # Extract locally for easy access
        cd "$BACKUP_DIR"
        tar -xzf "$BACKUP_NAME.tar.gz"
        echo -e "${GREEN}✅ Backup extracted to: $BACKUP_DIR/$BACKUP_NAME/${NC}"
        
        # Show backup contents
        echo -e "${BLUE}📋 Backup contents:${NC}"
        ls -la "$BACKUP_NAME/"
        
        # Cleanup remote backup
        ssh -i ~/.ssh/id_rsa root@$VPS_IP "rm -rf /tmp/newsbot_backups/$BACKUP_NAME*"
        echo -e "${GREEN}🧹 Remote backup cleaned up${NC}"
        
    else
        echo -e "${RED}❌ Failed to download backup${NC}"
        exit 1
    fi
}

# Function to create local backup (from existing local files)
create_local_backup() {
    echo -e "${YELLOW}📦 Creating local backup...${NC}"
    
    LOCAL_BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    mkdir -p "$LOCAL_BACKUP_PATH"
    
    # Backup local files
    if [ -d "config" ]; then
        cp -r config "$LOCAL_BACKUP_PATH/"
        echo -e "${GREEN}✅ Config backed up${NC}"
    fi
    
    if [ -d "data" ]; then
        cp -r data "$LOCAL_BACKUP_PATH/"
        echo -e "${GREEN}✅ Data backed up${NC}"
    fi
    
    if [ -d "logs" ]; then
        cp -r logs "$LOCAL_BACKUP_PATH/"
        echo -e "${GREEN}✅ Logs backed up${NC}"
    fi
    
    if [ -d "src" ]; then
        cp -r src "$LOCAL_BACKUP_PATH/"
        echo -e "${GREEN}✅ Source code backed up${NC}"
    fi
    
    # Create archive
    cd "$BACKUP_DIR"
    tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME/"
    rm -rf "$BACKUP_NAME"
    
    echo -e "${GREEN}✅ Local backup created: $BACKUP_DIR/$BACKUP_NAME.tar.gz${NC}"
}

# Function to list existing backups
list_backups() {
    echo -e "${BLUE}📋 Existing backups:${NC}"
    
    if [ -d "$BACKUP_DIR" ] && [ "$(ls -A $BACKUP_DIR)" ]; then
        ls -lah "$BACKUP_DIR"/*.tar.gz 2>/dev/null | while read -r line; do
            echo -e "${CYAN}  $line${NC}"
        done
    else
        echo -e "${YELLOW}  No backups found${NC}"
    fi
}

# Function to restore backup
restore_backup() {
    echo -e "${YELLOW}🔄 Backup restoration guide:${NC}"
    echo ""
    echo -e "${BLUE}To restore a backup:${NC}"
    echo -e "1. Extract backup: ${CYAN}tar -xzf $BACKUP_DIR/newsbot_backup_YYYYMMDD_HHMMSS.tar.gz${NC}"
    echo -e "2. Stop bot: ${CYAN}ssh -i ~/.ssh/id_rsa root@$VPS_IP 'systemctl stop newsbot'${NC}"
    echo -e "3. Upload config: ${CYAN}scp -r newsbot_backup_*/config root@$VPS_IP:/home/newsbot/${NC}"
    echo -e "4. Upload data: ${CYAN}scp -r newsbot_backup_*/data root@$VPS_IP:/home/newsbot/${NC}"
    echo -e "5. Fix permissions: ${CYAN}ssh -i ~/.ssh/id_rsa root@$VPS_IP 'chown -R newsbot:newsbot /home/newsbot'${NC}"
    echo -e "6. Start bot: ${CYAN}ssh -i ~/.ssh/id_rsa root@$VPS_IP 'systemctl start newsbot'${NC}"
}

# Main execution
case "${1:-remote}" in
    "remote")
        echo -e "${BLUE}🌐 Creating remote backup from VPS...${NC}"
        create_remote_backup
        download_backup
        ;;
    "local")
        echo -e "${BLUE}💻 Creating local backup...${NC}"
        create_local_backup
        ;;
    "list")
        list_backups
        ;;
    "restore")
        restore_backup
        ;;
    *)
        echo -e "${RED}❌ Unknown option: $1${NC}"
        echo ""
        echo -e "${YELLOW}Usage: ./backup_bot.sh [remote|local|list|restore]${NC}"
        echo -e "  remote  - Backup from VPS (default)"
        echo -e "  local   - Backup local files"
        echo -e "  list    - List existing backups"
        echo -e "  restore - Show restoration instructions"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}🎯 Backup operation completed!${NC}"
echo -e "${BLUE}==============================================================================${NC}" 