# Falcon AI Local Deployment Guide

## 1. Quick Start (Native Local Development)

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Git

### A. Backend Setup
1. Navigate to `myvoice-os/server`:
   ```bash
   cd myvoice-os/server
   ```
2. Create and activate virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create your `.env` configuration file (copy from `.env.example`):
   ```bash
   ADMIN_PASSWORD=your-secure-admin-password
   ENROLLMENT_KEY=your-random-32-byte-enrollment-key
   DATABASE_PATH=./myvoice.db
   OPENAI_API_KEY=sk-... # Optional if using Gemini or Mock
   GEMINI_API_KEY=AIzaSy... # Optional if using OpenAI or Mock
   ```
4. Start the FastAPI server daemon:
   ```bash
   .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### B. Frontend Setup (Live Hot-Reloading)
1. In a new terminal, navigate to `myvoice-os/server/frontend`:
   ```bash
   cd myvoice-os/server/frontend
   npm install
   npm run dev -- --host 0.0.0.0
   ```
2. Open your browser at:
   `http://localhost:5173/` (Vite Hot-Reload) or `http://localhost:8000/` (FastAPI Integrated UI).
3. Sign in with username `admin` and your configured `ADMIN_PASSWORD`.

---

## 2. Docker Compose Deployment

Falcon AI includes a production-ready `docker-compose.yml` in `myvoice-os/`:

```yaml
version: "3.8"
services:
  falcon-server:
    build: .
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ADMIN_PASSWORD=your-admin-password
      - ENROLLMENT_KEY=your-enrollment-key
      - DATABASE_PATH=/data/falcon.db
      - GEMINI_API_KEY=your-gemini-key
    volumes:
      - falcon_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  falcon_data:
```

### Launch Container
```bash
cd myvoice-os
docker compose up -d
```

### Check Logs
```bash
docker compose logs -f falcon-server
```
