# Hypnos API - Deployment Guide

## Quick Start

### Step 1: Prepare your VPS (SSH into your Vultr VPS)

```bash
ssh root@216.238.107.157
```

### Step 2: Install dependencies

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv nginx git rsync
```

### Step 3: Create application user

```bash
useradd -m -s /bin/bash hypnos
usermod -aG www-data hypnos
```

### Step 4: Create directories

```bash
mkdir -p /opt/hypnos-api
mkdir -p /var/log/hypnos
chown -R hypnos:www-data /opt/hypnos-api
chown -R hypnos:www-data /var/log/hypnos
```

### Step 5: Copy files to VPS (from your local machine)

```bash
# Run this from your LOCAL machine (not VPS)
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.env' --exclude '.git' \
  /Users/brunoconrado/development/projects/hypnos_workspace/api/ \
  root@216.238.107.157:/opt/hypnos-api/
```

### Step 6: Setup Python environment (on VPS)

```bash
cd /opt/hypnos-api
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 7: Create production .env file

```bash
cp deploy/.env.production.example .env
nano .env  # Edit with your production values
```

Generate secure keys:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Step 8: Setup systemd service

```bash
cp deploy/hypnos-api.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable hypnos-api
```

### Step 9: Setup nginx

```bash
cp deploy/nginx-hypnos-api.conf /etc/nginx/sites-available/hypnos-api
ln -sf /etc/nginx/sites-available/hypnos-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

### Step 10: Fix permissions and start

```bash
chown -R hypnos:www-data /opt/hypnos-api
chmod +x /opt/hypnos-api/deploy/*.sh
systemctl start hypnos-api
```

### Step 11: Verify deployment

```bash
# Check service status
systemctl status hypnos-api

# Check logs
tail -f /var/log/hypnos/error.log

# Test API
curl http://localhost:5000/
curl http://216.238.107.157/
```

---

## MongoDB Setup (if not already done)

If MongoDB isn't installed yet:

```bash
# Import MongoDB GPG key
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg

# Add repository (Ubuntu 22.04)
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Install
apt update
apt install -y mongodb-org

# Start MongoDB
systemctl start mongod
systemctl enable mongod
```

---

## Useful Commands

```bash
# Restart API
systemctl restart hypnos-api

# View logs
journalctl -u hypnos-api -f
tail -f /var/log/hypnos/error.log
tail -f /var/log/hypnos/access.log

# Check nginx logs
tail -f /var/log/nginx/error.log

# Update code
cd /opt/hypnos-api
git pull  # if using git
systemctl restart hypnos-api
```

---

## Firewall Setup (UFW)

```bash
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS (for future SSL)
ufw enable
```

---

## SSL with Let's Encrypt (Optional, requires domain)

```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

---

## Updating the API

From your local machine:
```bash
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.env' --exclude '.git' \
  /Users/brunoconrado/development/projects/hypnos_workspace/api/ \
  root@216.238.107.157:/opt/hypnos-api/

ssh root@216.238.107.157 "systemctl restart hypnos-api"
```
