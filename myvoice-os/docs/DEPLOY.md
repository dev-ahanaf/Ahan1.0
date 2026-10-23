# MyVoice OS - Production Deployment Guide (v1.0.0-rc1)

## 1. Overview

This document provides complete instructions for deploying MyVoice OS in a production environment with HTTPS, persistent database storage, automatic migrations, and hardened network security.

Two deployment methods are supported:
- Method A (Recommended): Docker Compose with Caddy reverse proxy (automatic TLS/HTTPS).
- Method B (Bare Metal / VM): Python virtual environment with systemd and manual reverse proxy.

---

## 2. Prerequisites

- Linux Host (Ubuntu 22.04 LTS, Debian 12, or macOS server).
- Minimum Hardware: 1 vCPU, 1 GB RAM, 10 GB disk space.
- Public domain or local DNS name pointing to your server (e.g., `myvoice.home.arpa` or `assistant.yourdomain.com`).
- Port 80 and 443 open for web and device WebSocket traffic.

---

## 3. Method A: Docker Compose Deployment (Recommended)

### Step 1: Clone Repository and Configure Environment
```bash
git clone <repository_url> myvoice-os
cd myvoice-os

# Create server/.env file from template
cat << 'EOF' > server/.env
ADMIN_PASSWORD=change-me-to-a-very-strong-admin-password-at-least-16-chars
ENROLLMENT_KEY=change-me-to-a-very-strong-enrollment-key-at-least-24-chars
DATABASE_PATH=/app/data/myvoice.db
AI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your-openai-api-key-here
BRAVE_SEARCH_API_KEY=your-brave-search-api-key-here
EOF
```

### Step 2: Configure Domain in Caddyfile
Edit `Caddyfile` with your domain:
```caddyfile
assistant.yourdomain.com {
    encode gzip zstd

    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
        X-XSS-Protection "1; mode=block"
        -Server
    }

    reverse_proxy app:8000 {
        header_up X-Forwarded-Proto {scheme}
        header_up X-Real-IP {remote_host}
    }
}
```

### Step 3: Build and Launch Containers
```bash
docker compose up -d --build
```

### Step 4: Verify Container Health
```bash
docker compose ps
docker compose logs -f app
```
The server will automatically run Alembic migrations on startup (`alembic upgrade head`) and listen on port 8000 behind Caddy.

---

## 4. Method B: Bare-Metal Deployment (systemd + Python)

### Step 1: Install System Dependencies
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm curl gcc g++
```

### Step 2: Build Frontend Production Assets
```bash
cd server/frontend
npm ci
npm run build
cd ../..
```

### Step 3: Set Up Python Virtual Environment
```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
cd ..
```

### Step 4: Create systemd Service Unit
Create `/etc/systemd/system/myvoice.service`:
```ini
[Unit]
Description=MyVoice OS Assistant Backend
After=network.target

[Service]
Type=simple
User=myvoice
WorkingDirectory=/opt/myvoice-os/server
EnvironmentFile=/opt/myvoice-os/server/.env
ExecStart=/opt/myvoice-os/server/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips='*'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now myvoice.service
sudo systemctl status myvoice.service
```

---

## 5. Backup and Disaster Recovery

### Database Backup (SQLite)
To perform an online, non-blocking backup of the SQLite database:
```bash
# Inside docker container or host:
sqlite3 server/data/myvoice.db ".backup server/data/myvoice_backup_$(date +%Y%m%d_%H%M%S).db"
```

### Firmware Catalog Backup
The uploaded OTA binaries reside in `firmware_catalog/`:
```bash
tar -czvf firmware_catalog_backup.tar.gz server/firmware_catalog/
```

---

## 6. Security Hardening Checklist

1. Strong Secrets: Ensure `ADMIN_PASSWORD` >= 16 characters and `ENROLLMENT_KEY` >= 24 characters.
2. Local Network Isolation: For home deployments, place IoT devices and the MyVoice server on an isolated IoT VLAN.
3. TLS Certificates: Always access the dashboard and WebSocket endpoints over HTTPS/WSS in production.
4. Token Rotation: If an ESP32 device is compromised or lost, immediately revoke it via the dashboard Fleet view.
