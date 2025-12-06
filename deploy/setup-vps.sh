#!/bin/bash
# Hypnos API - VPS Setup Script
# Run this script on your Vultr VPS as root

set -e

echo "=== Hypnos API VPS Setup ==="

# Update system
echo "[1/8] Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
echo "[2/8] Installing dependencies..."
apt install -y python3 python3-pip python3-venv nginx git

# Create hypnos user
echo "[3/8] Creating hypnos user..."
if ! id "hypnos" &>/dev/null; then
    useradd -m -s /bin/bash hypnos
    usermod -aG www-data hypnos
fi

# Create application directory
echo "[4/8] Setting up application directory..."
mkdir -p /opt/hypnos-api
mkdir -p /var/log/hypnos
chown -R hypnos:www-data /opt/hypnos-api
chown -R hypnos:www-data /var/log/hypnos

echo "[5/8] Cloning repository..."
echo "Please clone your repository manually or copy files to /opt/hypnos-api"
echo ""
echo "If using Git:"
echo "  cd /opt/hypnos-api"
echo "  git clone <your-repo-url> ."
echo ""
echo "Or use rsync from your local machine:"
echo "  rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.env' \\"
echo "    /path/to/api/ root@your-vps-ip:/opt/hypnos-api/"

# Setup Python environment
echo "[6/8] Setting up Python virtual environment..."
cd /opt/hypnos-api
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Setup systemd service
echo "[7/8] Setting up systemd service..."
cp deploy/hypnos-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable hypnos-api

# Setup nginx
echo "[8/8] Setting up nginx..."
cp deploy/nginx-hypnos-api.conf /etc/nginx/sites-available/hypnos-api
ln -sf /etc/nginx/sites-available/hypnos-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Create /opt/hypnos-api/.env with your production settings"
echo "2. Ensure MongoDB is running and accessible"
echo "3. Start the API: systemctl start hypnos-api"
echo "4. Check status: systemctl status hypnos-api"
echo "5. View logs: tail -f /var/log/hypnos/error.log"
echo ""
echo "Your API will be available at: http://YOUR_VPS_IP/"
