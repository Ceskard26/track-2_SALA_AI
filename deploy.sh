#!/bin/bash
# ══════════════════════════════════════════════════════
#  RainCaster — Deploy Script
#  Run from your LOCAL machine to push updates to EC2
#  Usage: bash deploy.sh <EC2_PUBLIC_IP>
#
#  Example: bash deploy.sh 54.123.45.67
# ══════════════════════════════════════════════════════

set -e

EC2_IP=${1:?"Usage: bash deploy.sh <EC2_PUBLIC_IP>"}
EC2_USER="ubuntu"
KEY="~/.ssh/raincaster-key.pem"   # TODO: change to your actual key path
REMOTE="/home/ubuntu/raincaster"

echo "🚀 Deploying to EC2: $EC2_IP"

# 1. Copy files to EC2
scp -i $KEY -o StrictHostKeyChecking=no \
    main.py requirements.txt \
    $EC2_USER@$EC2_IP:$REMOTE/

# 2. If model checkpoint exists locally, upload it too
if [ -f "checkpoints/best_model.pt" ]; then
    echo "📦 Uploading model checkpoint..."
    ssh -i $KEY $EC2_USER@$EC2_IP "mkdir -p $REMOTE/checkpoints"
    scp -i $KEY checkpoints/best_model.pt \
        $EC2_USER@$EC2_IP:$REMOTE/checkpoints/
fi

# 3. Restart the service
ssh -i $KEY $EC2_USER@$EC2_IP \
    "cd $REMOTE && source venv/bin/activate && pip install -q -r requirements.txt && sudo systemctl restart raincaster"

echo ""
echo "✅ Deploy complete!"
echo "   API: http://$EC2_IP/health"
echo "   Docs: http://$EC2_IP/docs"
