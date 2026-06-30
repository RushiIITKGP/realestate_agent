# HomeGuide AI — chat-only backend

SQLite + LangGraph agent with streaming chat.

## Quick start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add GOOGLE_API_KEY to .env

uvicorn app.main:app --reload
```

## API

| Method | Path | Description |
|---|---|---|
| POST | `/chat/stream` | Streaming chat (SSE) — used by frontend |
| POST | `/chat` | Non-streaming chat |
| GET | `/health` | Health check |

### Streaming example

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1","message":"3 bed homes in Austin under 800k"}'
```

SSE events: `text` (token chunks), `properties`, `done`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/chat` to the backend.

## Tests

```bash
cd backend && pytest
```
