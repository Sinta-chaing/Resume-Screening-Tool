# Resume Screener Backend (Django + PostgreSQL + pgvector)

> **Hosting guide:** see [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
> (gunicorn, Nginx, systemd, PostgreSQL/pgvector provisioning, backups).

## Prerequisites

- Python 3.12+
- PostgreSQL 15+ with **pgvector** extension
- Ollama with `mxbai-embed-large` and `llama3.2`

## 1. Install pgvector on PostgreSQL (Windows)

Your error means PostgreSQL is running but **pgvector is not installed**. You have **PostgreSQL 18** at `C:\Program Files\PostgreSQL\18`.

### Quick install (recommended)

1. **Open PowerShell as Administrator** (right-click → Run as administrator)
2. Run:

```powershell
cd "D:\Data Insight\Resume Screening\Resume-Screening-Tool-with-RAG-LLM-Powered-\backend\scripts"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install_pgvector.ps1
```

3. Then migrate:

```powershell
cd ..\..
.\env\Scripts\Activate.ps1
python manage.py migrate
```

The script downloads prebuilt pgvector v0.8.6 for PG18, stops Postgres, copies files, and restarts the service.

### Alternative — Docker (if Docker Desktop is running)

```powershell
docker run -d --name resume-pg `
  -e POSTGRES_PASSWORD=your_password `
  -e POSTGRES_DB=resume_screener `
  -p 5433:5432 `
  pgvector/pgvector:pg18
```

Then set `DB_PORT=5433` in `backend/.env`.

### Manual SQL (after install script)

```sql
CREATE DATABASE resume_screener;
\c resume_screener
CREATE EXTENSION vector;
```

See also `scripts/setup_postgres.sql`.

## 2. Configure environment

```powershell
cd backend
copy .env.example .env
```

Edit `backend/.env` with **your** PostgreSQL credentials:

```env
DB_NAME=resume_screener
DB_USER=postgres
DB_PASSWORD=your_actual_password
DB_HOST=localhost
DB_PORT=5432
```

## 3. Install and migrate

```powershell
python -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 4000
```

## Database schema

| Table | Purpose |
|-------|---------|
| `screening_analysissession` | One analyze run (evaluation, summary, filenames) |
| `screening_resumechunk` | Resume chunks + 768-dim embeddings (pgvector) |

## API changes (PostgreSQL migration)

### POST `/api/analyze`

Response now includes `sessionId` (UUID):

```json
{
  "ok": true,
  "sessionId": "a1b2c3d4-...",
  "chunks": 1,
  "evaluation": { ... },
  "resumeSummary": "..."
}
```

### POST `/api/chat`

Requires `sessionId` from analyze:

```json
{
  "question": "Does the candidate know Python?",
  "sessionId": "a1b2c3d4-..."
}
```

Embeddings are stored in PostgreSQL and retrieved via pgvector cosine distance — data survives server restarts.

## API endpoints

- `GET /api/health` — liveness probe: `{ok, useOllama, ollamaBaseUrl, embeddingModel, chatModel}`
- `POST /api/analyze` — multipart (`resume`, `jd`, PDF/TXT) → `{ok, sessionId, chunks, evaluation, resumeSummary, candidateName, position}`
- `POST /api/chat` — JSON `{question, sessionId}` → RAG answer `{answer, sources[]}`
- `GET /api/records?order=asc|desc` — list records sorted by score
- `GET /api/records/<session_id>` — full detail for one record
- `DELETE /api/records/<session_id>` — delete a record

## Reference

Original Express backend: `backend-node/`

## Benchmark & charts

Run Model + Chat model comparison and generate charts:

```powershell
python benchmark.py                 # default: mxbai-embed-large x llama3.2
python plot_results.py              # writes benchmark_chart.png
```
