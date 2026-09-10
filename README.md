# Resume Screening Tool (RAG + LLM Powered)

AI-powered resume analysis against job descriptions using **Retrieval-Augmented Generation (RAG)**, **embeddings**, and **local Ollama LLMs**.

## Stack (Current)

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 15, TypeScript, React, App Router |
| Backend | Django 5, Django REST Framework, Python |
| AI | Ollama (`mxbai-embed-large`, `llama3.2`) |

## Project Structure

```text
Resume-Screening-Tool/
├── backend/                 # Django REST API (port 4000)
│   ├── config/
│   ├── screening/
│   │   ├── views.py
│   │   └── services/
│   ├── manage.py
│   └── requirements.txt
├── frontend/                # Next.js UI (port 3000)
│   ├── app/
│   ├── lib/
│   └── types/
├── backend-node/            # Reference: original Express backend
├── frontend-vite/           # Reference: original Vite frontend
└── sample-data/             # Test resume + JD files
```

## Prerequisites

- Python 3.12+
- Node.js 18+
- Ollama running locally with models pulled:
  ```powershell
  ollama pull mxbai-embed-large
  ollama pull llama3.2
  ```

## Backend Setup

```powershell
cd backend
python -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver 4000
```

Backend: http://localhost:4000

## Frontend Setup

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Frontend: http://localhost:3000

## Environment Variables

### Backend (`backend/.env`)

| Variable | Example | Description |
|----------|---------|-------------|
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | `change-me` | Django secret key |
| `DB_NAME` | `resume_screener` | PostgreSQL database name |
| `DB_USER` | `postgres` | PostgreSQL user |
| `DB_PASSWORD` | *(your password)* | PostgreSQL password |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `USE_OLLAMA` | `true` | Flag exposed in health endpoint |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `EMBEDDING_MODEL` | `mxbai-embed-large` | Embedding model name (1024-dim) |
| `CHAT_MODEL` | `llama3.2` | Chat/generation model name |

### Frontend (`frontend/.env.local`)

| Variable | Example | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:4000` | Django backend URL |

## API Endpoints

### GET `/api/health`

```json
{
  "ok": true,
  "useOllama": "true",
  "ollamaBaseUrl": "http://localhost:11434",
  "embeddingModel": "mxbai-embed-large",
  "chatModel": "llama3.2"
}
```

### POST `/api/analyze`

**Request:** `multipart/form-data` with fields `resume` and `jd` (PDF or TXT)

**Response:**

```json
{
  "ok": true,
  "sessionId": "uuid-here",
  "chunks": 1,
  "evaluation": {
    "score": 60,
    "strengths": ["..."],
    "gaps": ["..."],
    "suggestions": ["..."]
  },
  "resumeSummary": "..."
}
```

### POST `/api/chat`

**Request:**

```json
{ "question": "Does the candidate have Python experience?", "sessionId": "uuid-from-analyze" }
```

**Response:**

```json
{
  "ok": true,
  "answer": "...",
  "sources": [
    { "id": "resume-0", "score": 0.71, "preview": "..." }
  ]
}
```

## Migration Notes

### What was migrated

- **Backend:** Express/TypeScript → Django REST Framework/Python
  - PDF extraction: `pdf-parse` → PyMuPDF
  - Chunking: 1800-char fixed slices (from `chunkText.ts`)
  - Embeddings/chat: Ollama HTTP API (same endpoints)
  - Vector store: in-memory cosine similarity (top 4 chunks)
  - ATS evaluation: same LLM prompt + JSON parsing with fallback

- **Frontend:** Vite/React → Next.js App Router/TypeScript
  - Same UI layout and dark theme CSS
  - CSS classes aligned with stylesheet (`.app`, `.grid2`, `.chip`, etc.)
  - Added chat sources panel showing retrieved chunks and scores

### Behavior preserved

- Same API contract (`/api/health`, `/api/analyze`, `/api/chat`)
- Same form field names (`resume`, `jd`)
- Same RAG flow (analyze first, then chat)
- Same evaluation output structure
- PDF and TXT file support

### Behavior changes

- Frontend runs on port **3000** (was 5173 with Vite)
- Chat UI now displays retrieved **sources** with similarity scores
- CSS styling is fully applied (fixed class name mismatch from Vite version)
- `/api/analyze` returns **`resumeSummary`** (LLM-generated candidate overview) instead of raw `resumePreview` text
- **Scanned/image-only PDFs** (no text layer) are now supported via RapidOCR fallback (`rapidocr` + `onnxruntime`)
- Clearer `400` error identifies which uploaded file had no readable text

## Testing Results

Verified on migration date:

| Test | Result |
|------|--------|
| Django starts on :4000 | Pass |
| GET `/api/health` | Pass |
| POST `/api/analyze` (sample TXT files) | Pass — score 60, structured evaluation |
| POST `/api/chat` (after analyze) | Pass — answer + 1 source |
| 400 on missing files | Pass |
| 400 on missing question | Pass |
| Next.js build | Pass |
| Next.js dev server on :3000 | Pass (HTTP 200) |
| Ollama embeddings + chat | Pass |

## Reference Implementations

The original working stack is preserved for comparison:

- `backend-node/` — Express + TypeScript backend
- `frontend-vite/` — Vite + React frontend

Remove these only after you have fully validated the new stack in your environment.

## Scripts

### Backend

```powershell
python manage.py runserver 4000
```

### Frontend

```powershell
npm run dev      # development
npm run build    # production build
npm run start    # production server
```
