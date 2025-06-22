#!/bin/bash
# =============================================================================
# Deploy NewsBot to DigitalOcean VPS
# =============================================================================

VPS_IP="159.89.90.90"
VPS_USER="root"

echo "🚀 Deploying NewsBot to DigitalOcean VPS"
echo "========================================"

# Upload the deployment package
echo "📤 Uploading bot files to VPS..."
scp -i ~/.ssh/id_rsa newsbot-deploy.tar.gz root@${VPS_IP}:/tmp/

# Upload deployment script
scp -i ~/.ssh/id_rsa deploy_vps.sh root@${VPS_IP}:/tmp/

# Connect and run deployment
echo "🔧 Running deployment on VPS..."
ssh -i ~/.ssh/id_rsa root@${VPS_IP} << 'ENDSSH'
cd /tmp

# Extract files
echo "📂 Extracting bot files..."
tar -xzf newsbot-deploy.tar.gz
mkdir -p /tmp/newsbot
mv src config requirements* run.py PRODUCTION_READINESS_CHECKLIST.md /tmp/newsbot/

# Make deployment script executable and run it
chmod +x deploy_vps.sh
./deploy_vps.sh

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================="
echo "Your NewsBot is now installed on the VPS!"
echo ""
echo "📋 Next Steps:"
echo "1. Configure your bot tokens in /home/newsbot/config/"
echo "2. Start the bot: sudo systemctl start newsbot"
echo "3. Check status: newsbot-status"
echo "4. View logs: newsbot-logs follow"

echo ""
echo "🔧 Management Commands Available:"
echo "  newsbot-start    - Start the bot"
echo "  newsbot-stop     - Stop the bot"
echo "  newsbot-restart  - Restart the bot"
echo "  newsbot-status   - Check status"
echo "  newsbot-logs     - View logs"

ENDSSH

echo ""
echo "✅ Deployment script completed!"
echo ""
echo "🔑 To connect to your VPS:"
echo "  ssh -i ~/.ssh/id_rsa root@${VPS_IP}"
echo ""
echo "📋 Next: Configure your bot and start it!" 