#!/bin/bash
# =============================================================================
# NewsBot VPS Deployment Script
# =============================================================================
# Automated deployment script for setting up NewsBot on a fresh Ubuntu VPS
# Run this script on your VPS after uploading your bot files

set -e  # Exit on any error

echo "🚀 Starting NewsBot VPS Deployment..."
echo "====================================="

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+ and pip
echo "🐍 Installing Python and dependencies..."
sudo apt install -y python3 python3-pip python3-venv git htop nano screen tmux curl wget

# Install system dependencies for media processing
sudo apt install -y ffmpeg libopus-dev libffi-dev libnacl-dev

# Create bot user (security best practice)
echo "👤 Creating bot user..."
sudo useradd -m -s /bin/bash newsbot || echo "User already exists"

# Switch to bot user directory
sudo -u newsbot bash << 'EOF'
cd /home/newsbot

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install bot dependencies
echo "📚 Installing Python dependencies..."
pip install -r /tmp/newsbot/requirements.txt

# Copy bot files
echo "📂 Setting up bot files..."
cp -r /tmp/newsbot/* .
chmod +x run.py

# Create necessary directories
mkdir -p logs data/cache data/sessions

# Set permissions
chmod 755 run.py
chmod 644 config/*

echo "✅ Bot files setup complete"
EOF

# Create systemd service for auto-start
echo "⚙️ Setting up systemd service..."
sudo tee /etc/systemd/system/newsbot.service > /dev/null << 'EOF'
[Unit]
Description=NewsBot Discord Bot
After=network.target

[Service]
Type=simple
User=newsbot
WorkingDirectory=/home/newsbot
Environment=PATH=/home/newsbot/venv/bin
ExecStart=/home/newsbot/venv/bin/python /home/newsbot/run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable newsbot
echo "✅ SystemD service created and enabled"

# Create log rotation
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/newsbot > /dev/null << 'EOF'
/home/newsbot/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 newsbot newsbot
}
EOF

# Setup firewall (optional but recommended)
echo "🛡️ Configuring firewall..."
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
echo "y" | sudo ufw enable

# Create management scripts
echo "🔧 Creating management scripts..."

# Start script
sudo tee /usr/local/bin/newsbot-start > /dev/null << 'EOF'
#!/bin/bash
sudo systemctl start newsbot
echo "✅ NewsBot started"
sudo systemctl status newsbot --no-pager
EOF

# Stop script  
sudo tee /usr/local/bin/newsbot-stop > /dev/null << 'EOF'
#!/bin/bash
sudo systemctl stop newsbot
echo "🛑 NewsBot stopped"
EOF

# Restart script
sudo tee /usr/local/bin/newsbot-restart > /dev/null << 'EOF'
#!/bin/bash
sudo systemctl restart newsbot
echo "🔄 NewsBot restarted"
sudo systemctl status newsbot --no-pager
EOF

# Status script
sudo tee /usr/local/bin/newsbot-status > /dev/null << 'EOF'
#!/bin/bash
echo "📊 NewsBot Status:"
sudo systemctl status newsbot --no-pager
echo ""
echo "📈 Resource Usage:"
ps aux | grep -E "(newsbot|python)" | grep -v grep
echo ""
echo "📝 Recent Logs:"
sudo journalctl -u newsbot --no-pager -n 10
EOF

# Logs script
sudo tee /usr/local/bin/newsbot-logs > /dev/null << 'EOF'
#!/bin/bash
if [ "$1" = "follow" ] || [ "$1" = "-f" ]; then
    sudo journalctl -u newsbot -f
else
    sudo journalctl -u newsbot --no-pager -n ${1:-50}
fi
EOF

# Make scripts executable
sudo chmod +x /usr/local/bin/newsbot-*

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================="
echo "✅ Bot installed as system service"
echo "✅ Auto-start on boot enabled"
echo "✅ Log rotation configured"
echo "✅ Management scripts created"
echo ""
echo "📋 Management Commands:"
echo "  newsbot-start    - Start the bot"
echo "  newsbot-stop     - Stop the bot"  
echo "  newsbot-restart  - Restart the bot"
echo "  newsbot-status   - Check bot status"
echo "  newsbot-logs     - View logs (add 'follow' to tail)"
echo ""
echo "🚀 To start your bot:"
echo "  sudo systemctl start newsbot"
echo ""
echo "📊 To check status:"
echo "  newsbot-status"
echo ""
echo "📝 To view logs:"
echo "  newsbot-logs follow" 