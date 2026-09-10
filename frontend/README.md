# Resume Screener Frontend (Next.js)

## Prerequisites

- Node.js 18+
- Django backend running on port 4000
- Ollama running locally

## Setup

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open http://localhost:3000

## Environment

```env
NEXT_PUBLIC_API_URL=http://localhost:4000
```

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server (port 3000) |
| `npm run build` | Production build |
| `npm run start` | Start production server |

## Reference

The original Vite frontend is preserved in `frontend-vite/`.
