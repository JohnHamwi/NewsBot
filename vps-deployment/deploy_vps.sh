#!/bin/bash

# =============================================================================
# NewsBot VPS Deployment Script (Unified Config)
# =============================================================================
# This script sets up the NewsBot on a fresh Ubuntu VPS with the new unified
# configuration system.
#
# Usage: ./deploy_vps_unified.sh
# Requirements: Ubuntu 20.04+ VPS with root access
# Last updated: 2025-01-16

set -e  # Exit on any error

echo "🚀 Starting NewsBot VPS Deployment (Unified Config)..."

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install required packages
echo "🔧 Installing required packages..."
apt install -y python3 python3-pip python3-venv git redis-server nginx htop curl wget unzip screen

# Create newsbot user
echo "👤 Creating newsbot user..."
if ! id "newsbot" &>/dev/null; then
    useradd -m -s /bin/bash newsbot
    usermod -aG sudo newsbot
fi

# Extract bot files
echo "📁 Extracting bot files..."
if [ -f "/tmp/newsbot-vps-deploy.tar.gz" ]; then
    cd /tmp
    tar -xzf newsbot-vps-deploy.tar.gz
    
    # Copy files to newsbot home
    cp -r src /home/newsbot/
    cp run.py /home/newsbot/
    cp requirements.txt /home/newsbot/
    
    # Create necessary directories
    mkdir -p /home/newsbot/{config,data/sessions,data/cache,logs}
    
    # Copy configuration files
    if [ -f "config/unified_config.yaml" ]; then
        cp config/unified_config.yaml /home/newsbot/config/
    fi
    
    if [ -f "data/botdata.json" ]; then
        cp data/botdata.json /home/newsbot/data/
    fi
    
    # Set ownership
    chown -R newsbot:newsbot /home/newsbot/
else
    echo "❌ Error: newsbot-vps-deploy.tar.gz not found in /tmp/"
    echo "Please upload the deployment package first:"
    echo "scp newsbot-vps-deploy.tar.gz user@your-vps:/tmp/"
    exit 1
fi

# Create Python virtual environment
echo "🐍 Setting up Python virtual environment..."
sudo -u newsbot python3 -m venv /home/newsbot/venv
sudo -u newsbot /home/newsbot/venv/bin/pip install --upgrade pip

# Install Python dependencies
echo "📚 Installing Python dependencies..."
sudo -u newsbot /home/newsbot/venv/bin/pip install -r /home/newsbot/requirements.txt

# Start and enable Redis
echo "🔴 Configuring Redis..."
systemctl start redis-server
systemctl enable redis-server

# Create systemd service
echo "⚙️ Creating systemd service..."
cat > /etc/systemd/system/newsbot.service << EOF
[Unit]
Description=NewsBot Discord Bot
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=newsbot
Group=newsbot
WorkingDirectory=/home/newsbot
Environment=PATH=/home/newsbot/venv/bin
ExecStart=/home/newsbot/venv/bin/python /home/newsbot/run.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=newsbot

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/home/newsbot
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes

[Install]
WantedBy=multi-user.target
EOF

# Set up log rotation
echo "📝 Setting up log rotation..."
cat > /etc/logrotate.d/newsbot << EOF
/home/newsbot/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 newsbot newsbot
    postrotate
        systemctl reload newsbot || true
    endscript
}
EOF

# Create monitoring script
echo "📊 Setting up monitoring..."
cat > /home/newsbot/monitor.sh << 'EOF'
#!/bin/bash
# NewsBot Monitoring Script

echo "=== NewsBot Status ==="
systemctl status newsbot --no-pager -l

echo -e "\n=== Recent Logs ==="
journalctl -u newsbot --no-pager -n 20

echo -e "\n=== System Resources ==="
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory Usage: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')"
echo "Disk Usage: $(df -h / | awk 'NR==2 {print $5}')"

echo -e "\n=== Redis Status ==="
redis-cli ping

echo -e "\n=== Bot Process ==="
ps aux | grep python | grep newsbot
EOF

chmod +x /home/newsbot/monitor.sh
chown newsbot:newsbot /home/newsbot/monitor.sh

# Reload systemd and start the service
echo "🔄 Starting NewsBot service..."
systemctl daemon-reload
systemctl enable newsbot

# Set up firewall (if ufw is available)
if command -v ufw &> /dev/null; then
    echo "🔥 Configuring firewall..."
    ufw allow ssh
    ufw allow 80
    ufw allow 443
    ufw --force enable
fi

echo ""
echo "✅ NewsBot VPS deployment completed!"
echo ""
echo "🔧 Next steps:"
echo "1. Configure your Telegram authentication:"
echo "   sudo -u newsbot /home/newsbot/venv/bin/python /home/newsbot/authenticate_telegram.py"
echo ""
echo "2. Start the bot:"
echo "   systemctl start newsbot"
echo ""
echo "3. Check status:"
echo "   systemctl status newsbot"
echo "   /home/newsbot/monitor.sh"
echo ""
echo "4. View logs:"
echo "   journalctl -u newsbot -f"
echo "   tail -f /home/newsbot/logs/*.log"
echo ""
echo "📁 Bot files located at: /home/newsbot/"
echo "⚙️ Service name: newsbot"
echo "👤 Running as user: newsbot"
echo "" 