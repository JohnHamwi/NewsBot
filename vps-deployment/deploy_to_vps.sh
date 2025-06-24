#!/bin/bash

# =============================================================================
# NewsBot Local Deployment Script
# =============================================================================
# This script packages the bot and deploys it to your VPS by creating a
# deployment package and uploading it with the deployment script.
#
# Usage: ./deploy_to_vps.sh
# Environment variables: VPS_IP, VPS_USER, SSH_KEY
# Last updated: 2025-01-16

set -e  # Exit on any error

# Configuration
VPS_IP="${VPS_IP:-159.89.90.90}"
VPS_USER="${VPS_USER:-root}"
SSH_KEY="${SSH_KEY:-/Users/johnhamwi/.ssh/id_rsa}"

# Check for quick update mode
QUICK_UPDATE=false
if [ "$1" = "--quick" ] || [ "$1" = "-q" ]; then
    QUICK_UPDATE=true
    echo "🚀 Quick update mode - deploying only source files..."
fi

echo "🚀 Starting NewsBot deployment to VPS..."
echo "📡 Target: $VPS_USER@$VPS_IP"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found at $SSH_KEY"
    echo "Please set SSH_KEY environment variable or ensure key exists"
    exit 1
fi

# Check if we can connect to VPS
echo "🔗 Testing VPS connection..."
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$VPS_USER@$VPS_IP" "echo 'Connection successful'" 2>/dev/null; then
    echo "❌ Cannot connect to VPS. Please check:"
    echo "   - VPS IP address: $VPS_IP"
    echo "   - SSH key: $SSH_KEY"
    echo "   - VPS is running and accessible"
    exit 1
fi

# Quick update mode - just update source files
if [ "$QUICK_UPDATE" = true ]; then
    echo "⚡ Quick update: Uploading source files..."
    
    # Create temporary archive with just source files
    TEMP_DIR=$(mktemp -d)
    cp -r src "$TEMP_DIR/"
    cd "$TEMP_DIR"
    tar -czf "newsbot-src-update.tar.gz" src/
    
    # Upload and extract
    scp -i "$SSH_KEY" "newsbot-src-update.tar.gz" "$VPS_USER@$VPS_IP:/tmp/"
    ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "
        cd /tmp && 
        tar -xzf newsbot-src-update.tar.gz && 
        cp -r src/* /home/newsbot/src/ && 
        chown -R newsbot:newsbot /home/newsbot/src/ && 
        systemctl restart newsbot &&
        echo '✅ Quick update completed and bot restarted'
    "
    
    # Cleanup
    cd "$OLDPWD"
    rm -rf "$TEMP_DIR"
    
    echo "🎉 Quick update completed!"
    echo "📋 Check status: ssh -i $SSH_KEY $VPS_USER@$VPS_IP 'systemctl status newsbot'"
    exit 0
fi

# Create deployment package
echo "📦 Creating deployment package..."
TEMP_DIR=$(mktemp -d)
PACKAGE_NAME="newsbot-vps-deploy.tar.gz"

# Copy essential files
cp -r src "$TEMP_DIR/"
cp run.py "$TEMP_DIR/"
cp requirements.txt "$TEMP_DIR/"

# Copy unified configuration files
mkdir -p "$TEMP_DIR/config"
cp config/unified_config.yaml "$TEMP_DIR/config/" 2>/dev/null || echo "⚠️  unified_config.yaml not found, will use template"

mkdir -p "$TEMP_DIR/data"
cp data/botdata.json "$TEMP_DIR/data/" 2>/dev/null || echo "⚠️  botdata.json not found, will create new"

# Create the package
cd "$TEMP_DIR"
tar -czf "$PACKAGE_NAME" src/ run.py requirements.txt config/ data/

# Move package to original directory
mv "$PACKAGE_NAME" "$OLDPWD/"
cd "$OLDPWD"

# Clean up temp directory
rm -rf "$TEMP_DIR"

echo "✅ Package created: $PACKAGE_NAME ($(du -h $PACKAGE_NAME | cut -f1))"

# Upload files to VPS
echo "📤 Uploading files to VPS..."
scp -i "$SSH_KEY" "$PACKAGE_NAME" "$VPS_USER@$VPS_IP:/tmp/"
scp -i "$SSH_KEY" "vps-deployment/deploy_vps.sh" "$VPS_USER@$VPS_IP:/tmp/"

# Make deployment script executable
ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "chmod +x /tmp/deploy_vps.sh"

echo "✅ Files uploaded successfully"

# Ask user if they want to run the deployment script
echo ""
echo "📋 Files uploaded to VPS. Next steps:"
echo "1. Connect to your VPS: ssh -i $SSH_KEY $VPS_USER@$VPS_IP"
echo "2. Run the deployment script: /tmp/deploy_vps.sh"
echo "3. Start the bot: sudo systemctl start newsbot"
echo "4. Check status: sudo systemctl status newsbot"
echo ""

read -p "🤖 Would you like to automatically run the deployment script now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Running deployment script on VPS..."
    ssh -i "$SSH_KEY" "$VPS_USER@$VPS_IP" "/tmp/deploy_vps.sh"
    
    echo ""
    echo "🎉 Deployment completed!"
    echo "📋 Final steps:"
    echo "1. Start the bot: ssh -i $SSH_KEY $VPS_USER@$VPS_IP 'sudo systemctl start newsbot'"
    echo "2. Check status: ssh -i $SSH_KEY $VPS_USER@$VPS_IP 'sudo systemctl status newsbot'"
    echo "3. Authenticate Telegram: ssh -i $SSH_KEY $VPS_USER@$VPS_IP 'sudo -u newsbot /home/newsbot/venv/bin/python /home/newsbot/authenticate_telegram.py'"
else
    echo "✅ Files ready for manual deployment on VPS"
fi

# Clean up local package
rm -f "$PACKAGE_NAME"
echo "🧹 Cleaned up local deployment package" 