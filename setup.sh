#!/bin/bash
# ══════════════════════════════════════════════════════
#  RainCaster — EC2 Setup Script
#  Run this ONCE on a fresh EC2 t3.small (Ubuntu 22.04)
#  Usage: bash setup.sh
# ══════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════"
echo "  RainCaster Backend — EC2 Setup"
echo "═══════════════════════════════════"

# 1. System updates
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv git nginx

# 2. Create app directory
mkdir -p /home/ubuntu/raincaster
cd /home/ubuntu/raincaster

# 3. Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create systemd service (keeps API running after SSH disconnect)
sudo tee /etc/systemd/system/raincaster.service > /dev/null <<EOF
[Unit]
Description=RainCaster FastAPI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/raincaster
ExecStart=/home/ubuntu/raincaster/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 6. Configure nginx as reverse proxy (handles HTTPS via port 80 → 8000)
sudo tee /etc/nginx/sites-available/raincaster > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;

        # CORS headers (backup — FastAPI already sets these)
        add_header 'Access-Control-Allow-Origin' '*' always;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/raincaster /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 7. Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable raincaster
sudo systemctl start raincaster

echo ""
echo "✅ Setup complete!"
echo "   API running at: http://$(curl -s ifconfig.me):80"
echo "   Health check:   http://$(curl -s ifconfig.me)/health"
echo "   API docs:       http://$(curl -s ifconfig.me)/docs"
echo ""
echo "To check logs: sudo journalctl -u raincaster -f"
