# Falcon AI Production Deployment Guide

## 1. Cloud VPS Architecture (Ubuntu / Debian)

For production deployment on a cloud VPS (DigitalOcean, Hetzner, AWS EC2, Linode):

```
Internet (HTTPS / WSS)
        |
    [ Caddy / Nginx Reverse Proxy with Let's Encrypt TLS ]
        |
        +---> Port 8000: Uvicorn ASGI / FastAPI (Falcon AI)
                 |
                 +---> SQLite (WAL Mode) / PostgreSQL
                 +---> Firmware OTA Artifact Storage (/data/firmware)
```

---

## 2. Reverse Proxy Configuration

### Caddy (Recommended)
Caddy automatically manages SSL/TLS certificates and native WebSocket proxying without additional headers:

```caddyfile
falcon.yourdomain.com {
    reverse_proxy 127.0.0.1:8000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
    }
}
```

### Nginx
```nginx
server {
    server_name falcon.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

---

## 3. Systemd Service Configuration

Create `/etc/systemd/system/falcon-ai.service`:

```ini
[Unit]
Description=Falcon AI Voice Assistant Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/falcon-ai/myvoice-os/server
EnvironmentFile=/opt/falcon-ai/myvoice-os/server/.env
ExecStart=/opt/falcon-ai/myvoice-os/server/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now falcon-ai
sudo systemctl status falcon-ai
```

---

## 4. Vercel Multi-Service Deployment

This repository includes a root `vercel.json` configuring Vercel multi-service hosting:
- **Service `server`**: FastAPI backend with entrypoint `myvoice-os/server/main.py`.
- **Service `frontend`**: Vite React 18 Console with environment binding `SERVER_URL`.
- Rewrites map `/api/*` to the `server` service and `/*` to the `frontend` service.
