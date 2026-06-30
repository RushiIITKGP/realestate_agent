# HomeGuide AI — chat-only backend

SQLite + LangGraph agent. One main endpoint: `POST /chat`.

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

Swagger: http://127.0.0.1:8000/docs

## API

### POST /chat

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1","message":"3 bed homes in Austin under 800k"}'
```

Reuse the same `session_id` for multi-turn memory.

## Project layout

```
backend/app/
  main.py           # FastAPI app (health + chat)
  agent.py          # LangGraph agent + tools
  search.py         # Listing search + embeddings (agent tools only)
  db.py             # SQLite models + session
  schemas.py        # Request/response models
  seed.py           # Seed on startup
  data_listings.py  # Mock listings data
  config.py
```

## Tests

```bash
pytest
```

## Environment

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Required for `/chat` and embedding index |
| `DATABASE_URL` | Default: `sqlite:///./data/realestate.db` |
| `CHECKPOINT_DB_URL` | Conversation memory DB |
| `LLM_MODEL` | Default: `gemini-3.1-flash-lite-preview` |
| `EMBEDDING_MODEL` | Default: `models/text-embedding-004` |
