# Backend Deployment Guide

Deploy the Resume Screener **backend** to production: PostgreSQL (with pgvector) + Django API.
Frontend hosting is out of scope.

> Reference: `backend/.env.example` for the full list of environment variables.

---

## 1. Architecture

```
Client/Recruiter App
        │  HTTPS
        ▼
    Nginx (reverse proxy, TLS, client upload limit)
        │  proxy: 127.0.0.1:8000
        ▼
    Django API (gunicorn)  ──►  Ollama (embeddings + chat LLM)
        │                        (localhost or a dedicated GPU box)
        ▼
PostgreSQL + pgvector (resume chunks, 768-dim embeddings)
```

Three runnable pieces on the server:

| Component | Notes |
|-----------|-------|
| PostgreSQL 14+ | Must support **pgvector**. Create DB + user + extension. |
| Ollama | Serves `mxbai-embed-large` (1024-dim) + `llama3.2`. Needs RAM/GPU — may be a separate machine. |
| Django app | gunicorn worker serving the 5 API endpoints. |

---

## 2. Server prerequisites

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip nginx git curl
```

**PostgreSQL** (if not already installed):

```bash
sudo apt install -y postgresql postgresql-contrib
```

**Ollama** (install on the same box or a dedicated GPU machine):

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mxbai-embed-large
ollama pull llama3.2
```

Verify Ollama listens on its API:

```bash
curl http://localhost:11434/api/tags
```

---

## 3. Database setup

### 3.1 Create database + user

```bash
sudo -u postgres psql
```

```sql
CREATE USER resume_app WITH PASSWORD 'STRONG_DB_PASSWORD';
CREATE DATABASE resume_screener OWNER resume_app;
\c resume_screener
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL PRIVILEGES ON DATABASE resume_screener TO resume_app;
\q
```

> The `vector` extension is a hard requirement — `ResumeChunk.embedding` is a
> `VectorField(dimensions=1024)`. In `settings.py`, `EMBEDDING_MODEL` **must**
> output 1024 dims (that is `mxbai-embed-large`). Changing the embedding model
> means resizing the column (`screening/migrations/0003_resumechunk_embedding_dim1024.py`).

### 3.2 Optional hardening (recommended)

```bash
sudo -u postgres psql
```

```sql
ALTER SYSTEM SET password_encryption = 'scram-sha-256';
-- Restrict to loopback only if DB and app share the host:
-- Edit pg_hba.conf: `host  resume_screener  resume_app  127.0.0.1/32  scram-sha-256`
\q
sudo systemctl restart postgresql
```

If the DB is on a separate host, open `5432` **only** to the app server IP
(firewall, not 0.0.0.0).

---

## 4. Deploy the application code

```bash
# Pick a home for the app
sudo mkdir -p /opt/resume-screener
sudo chown "$USER":"$USER" /opt/resume-screener

cd /opt/resume-screener
git clone <your-repo-url> .          # or rsync/scp the backend folder

cd backend
python3 -m venv env
./env/bin/pip install --upgrade pip
./env/bin/pip install -r requirements.txt
```

> `setup_postgres.sql` and `install_pgvector.ps1` under `backend/scripts/` are
> for Windows local dev only — not needed on Linux.

---

## 5. Environment configuration

```bash
cp .env.example .env
nano .env
```

The important production values (never commit the real `.env`):

```env
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(50))">
DEBUG=False
ALLOWED_HOSTS=api.yourdomain.com

USE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434      # same host, or the GPU box's LAN IP
EMBEDDING_MODEL=mxbai-embed-large            # MUST be 1024-dim
CHAT_MODEL=llama3.2

CORS_ALLOW_ALL=false
CORS_ALLOWED_ORIGINS=https://frontend.yourdomain.com

DB_NAME=resume_screener
DB_USER=resume_app
DB_PASSWORD=STRONG_DB_PASSWORD
DB_HOST=127.0.0.1
DB_PORT=5432
```

---

## 6. Migrate, collect static, smoke test

```bash
cd /opt/resume-screener/backend
./env/bin/python manage.py migrate --noinput
./env/bin/python manage.py collectstatic --noinput

# Quick local smoke test
./env/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 &
curl http://127.0.0.1:8000/api/health
# {"ok":true,"useOllama":"true","ollamaBaseUrl":"http://localhost:11434","embeddingModel":"mxbai-embed-large","chatModel":"llama3.2"}
kill %1
```

---

## 7. Run gunicorn as a service (systemd)

Create `/etc/systemd/system/resume-screener.service`:

```ini
[Unit]
Description=Resume Screener Django API
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/resume-screener/backend
EnvironmentFile=/opt/resume-screener/backend/.env
ExecStart=/opt/resume-screener/backend/env/bin/gunicorn \
    config.wsgi:application \
    --workers 3 \
    --threads 2 \
    --bind 127.0.0.1:8000 \
    --timeout 600 \
    --max-requests 1000 \
    --max-requests-jitter 100
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> `--timeout 600` (10 min) matters: `POST /api/analyze` runs several LLM calls
> (embedding + evaluation + summary) which can be slow on CPU-only Ollama.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable resume-screener
sudo systemctl start resume-screener
sudo systemctl status resume-screener

journalctl -u resume-screener -f   # watch logs
```

---

## 8. Nginx reverse proxy

Create `/etc/nginx/sites-available/resume-screener`:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    client_max_body_size 25m;               # matches DATA_UPLOAD_MAX_MEMORY_SIZE (20MB)

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;            # long LLM calls
        proxy_connect_timeout   60s;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/resume-screener /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### TLS (use Certbot)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
sudo systemctl status certbot.timer   # auto-renew
```

---

## 9. Systemd service for Ollama

Ollama can run as a service so outage/boot restarts don't kill the API dependency:

```bash
sudo systemctl enable ollama
sudo systemctl start ollama
```

If Ollama is on a **different machine**, set `OLLAMA_BASE_URL=http://<llm-box-ip>:11434`
in `.env` and expose `11434` only to the app server.

---

## 10. Verification checklist

```bash
# 1. Health
curl -s https://api.yourdomain.com/api/health
#    expect {"ok":true, ...}

# 2. Analyze (upload resume + JD)
curl -s -X POST https://api.yourdomain.com/api/analyze \
  -F "resume=@resume.pdf" \
  -F "jd=@jd.txt"
#    expect {"ok":true,"sessionId":"<uuid>","evaluation":{...},...}

# 3. Chat
curl -s -X POST https://api.yourdomain.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"<uuid>","question":"Does the candidate know Python?"}'

# 4. Records
curl -s "https://api.yourdomain.com/api/records?order=desc"
curl -s "https://api.yourdomain.com/api/records/<uuid>"
```

---

## 11. Backups

```bash
# Nightly DB dump (keep retrievable to your own storage)
sudo -u postgres pg_dump resume_screener --no-owner | gzip > \
  /var/backups/resume_screener_$(date +%F_%H%M).sql.gz

# Cron: 0 2 * * *  (as above)
```

A pg_dump restore needs the `vector` extension to exist first:

```bash
sudo -u postgres psql -d resume_screener -c "CREATE EXTENSION IF NOT EXISTS vector;"
gunzip -c backup.sql.gz | sudo -u postgres psql resume_screener
```

---

## 12. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `GetNext from database failed` / vector errors | Confirm `CREATE EXTENSION vector;` ran in the target DB |
| `Embedding no viable dimension` | `EMBEDDING_MODEL` output dim != 1024; use `mxbai-embed-large` |
| `Ollama embeddings error: the input length exceeds the context length` | Input exceeds the model context (mxbai-embed-large = 512 tokens). Fixed by using `/api/embed` with `truncate` + 800-char chunks; if it reappears, shorten `EMBED_TEXT_LIMIT` in `scoring.py` |
| `Ollama embeddings error / connection refused` | Is Ollama running? `OLLAMA_BASE_URL` correct? |
| `DisallowedHost` | Add the host to `ALLOWED_HOSTS` in `.env` |
| 413 Request Entity Too Large | Raise `client_max_body_size` in Nginx |
| Analysis is very slow | LLM on CPU; lower `--timeout` won't help — add more gunicorn workers or a GPU |
| CORS blocked in browser | Check `CORS_ALLOWED_ORIGINS` includes the frontend origin |

---

## 13. Optional: Docker Compose

Ready-made files at the repo root:

- **`docker-compose.yml`** — PostgreSQL (pgvector) + Django API (gunicorn, auto-migrate)
- **`docker-compose.full.yml`** — the above **plus** a containerized Ollama service

### Quick start (DB + API only)

```bash
cp backend/.env.example backend/.env
# IMPORTANT: set DB_HOST=db in backend/.env (docker service name, not 127.0.0.1)
docker compose up -d --build
curl http://localhost:8000/api/health
```

### Quick start (including Ollama, no external GPU setup)

```bash
docker compose -f docker-compose.full.yml up -d --build
docker compose -f docker-compose.full.yml exec ollama ollama pull llama3.2
docker compose -f docker-compose.full.yml exec ollama ollama pull mxbai-embed-large
curl http://localhost:8000/api/health
```

Notes:

- `pgvector/pgvector:pg18` creates the `vector` extension automatically; no manual SQL needed.
- The host port for Postgres is `5433` to avoid clashing with a local PostgreSQL 18 install.
- `deploy.resources.reservations.devices` for NVIDIA GPU pass-through is commented in
  `docker-compose.full.yml` (requires `nvidia-container-toolkit`).
- Set `OLLAMA_BASE_URL=http://ollama:11434` if using the full file; on the plain
  `docker-compose.yml`, point `OLLAMA_BASE_URL` at your existing Ollama server instead.

---

## 14. Continuous Deployment (GitHub Actions + Docker Hub)

The pipeline is split into two workflows:

- **`.github/workflows/ci.yml`** — runs the backend test suite on every push/PR.
- **`.github/workflows/deploy.yml`** — builds the Docker image, pushes it to
  Docker Hub, and deploys on **main**, on `v*` git tags, or manually via
  **Actions → Deploy → Run workflow**. It:

  1. Logs in to Docker Hub with `docker/login-action`
  2. Builds the image from `backend/` (the `Dockerfile` in section 13's file)
     and pushes `latest` (and additionally tags `v*` tags with a version tag)
  3. On a **self-hosted runner** on the server: pulls the image, runs
     `migrate --noinput` in a throwaway container, then starts
     `resume-screener` (port `8000`, auto-restart) and health-checks it

### Required repository secrets

Add these in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `DOCKER_USERNAME` | Docker Hub username (used as the image namespace) |
| `DOCKER_PASSWORD` | Docker Hub access token (or password) |

### Server prerequisites (self-hosted runner)

1. **Docker** on the server:
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
2. **Register a self-hosted runner** on the server with the
   `self-hosted` label so the `deploy` job picks it up (Settings → Actions →
   Runners → New self-hosted runner; run the `config` script it prints as a
   service).
3. **Create the env file** once (never committed):
   ```bash
   sudo mkdir -p /opt/resume-screener
   sudo cp backend/.env.example /opt/resume-screener/.env   # then edit it
   ```
   Follow section 5 for the values. The API container reads this list via
   `--env-file`; set `DB_HOST` to wherever your PostgreSQL runs (e.g.
   `127.0.0.1` if the DB is on the same host, or a container on a shared
   Docker network).
4. PostgreSQL + pgvector must already exist (section 3). With plain `docker run`
   the DB is **not** started by the deploy — run it separately, e.g.:
   ```bash
   docker run -d --name resume-db \
     --restart unless-stopped \
     -p 5432:5432 \
     -e POSTGRES_USER=resume_app \
     -e POSTGRES_PASSWORD=<STRONG_DB_PASSWORD> \
     -e POSTGRES_DB=resume_screener \
     pgvector/pgvector:pg18
   ```
5. Nginx (section 8) or your reverse proxy keeps proxying `127.0.0.1:8000`,
   so the Docker deployment is invisible to clients.

> The `.env` file is never committed. Container secrets (DB password, etc.)
> live only in `/opt/resume-screener/.env` on the server.
>
> The deploy job is skipped while `DOCKER_USERNAME` is unset, so it is safe to
> push before adding the Docker Hub secrets.