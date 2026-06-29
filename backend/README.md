# HomeGuide AI — Backend (Phases 1–4)

Conversational real estate assistant backend inspired by Homes.com Homes AI.

Implements **Phases 1–4** from [PROCESS_DIAGRAMS.md](../PROCESS_DIAGRAMS.md):

- **Phase 1:** SQLAlchemy models, Alembic migrations, seed data
- **Phase 2:** Property search service + REST endpoints
- **Phase 3:** LangGraph agent with tools + `POST /chat`
- **Phase 4:** SQLite checkpointer for multi-turn memory + CLI test client

## Stack

- FastAPI
- SQLAlchemy + SQLite (PostgreSQL-ready)
- LangGraph + LangChain + Google Gemini
- Alembic

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your GOOGLE_API_KEY to .env

uvicorn app.main:app --reload
```

Open Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Seed data

On startup the API auto-creates tables and seeds **12 mock listings** and **5 neighborhoods** if the database is empty.

Manual seed:

```bash
python -m app.seed.seed
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/properties` | Search listings (filters + keywords) |
| GET | `/properties/{id}` | Listing details |
| POST | `/chat` | Conversational search (LangGraph agent) |

### Example: search listings

```bash
curl "http://127.0.0.1:8000/properties?city=Austin&max_price=800000&min_beds=3"
```

### Example: chat

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1","message":"3 bed homes in Austin under 800k"}'
```

## CLI multi-turn testing (Phase 4)

```bash
python scripts/cli_chat.py
```

Use the same session across turns to test memory:

```
You: I'm looking for a family home
You: Austin, under 800k, at least 3 beds
You: Tell me more about the cheapest one
```

## Agent tools

| Tool | Purpose |
|---|---|
| `search_properties` | Filter by city, price, beds, keywords, etc. |
| `get_property_details` | Full listing by ID |
| `get_neighborhood_info` | Neighborhood guide |
| `compare_properties` | Side-by-side comparison |

Search uses **SQL filters + keyword matching** (no embeddings yet — Phase 6).

## Project layout

```
backend/
  app/
    main.py                 # FastAPI app
    api/routes/             # REST endpoints (health, properties, chat)
    agent/agent.py          # ★ LLM + tools + agent + run_chat() — start here
    db/                     # SQLAlchemy session
    models/                 # Property, Neighborhood
    schemas/                # Pydantic request/response models
    services/properties.py  # DB search functions
    seed/                   # Mock data
  alembic/
  scripts/cli_chat.py
  tests/
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

## Migrations

```bash
alembic upgrade head
```

## Tests

```bash
pytest
```

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | SQLite or PostgreSQL connection string |
| `CHECKPOINT_DB_URL` | LangGraph conversation memory DB |
| `GOOGLE_API_KEY` | Required for `/chat` |
| `LLM_MODEL` | Default: `gemini-3.1-flash-lite-preview` |
| `LLM_TEMPERATURE` | Default: `0.7` |

## Next phases

- **Phase 5:** SSE streaming on `/chat/stream`
- **Phase 6:** pgvector embeddings for semantic search
- **Phase 7:** Voice via OpenAI Realtime API

See [TECH_STACK_LEARNING.md](../TECH_STACK_LEARNING.md) and [PROCESS_DIAGRAMS.md](../PROCESS_DIAGRAMS.md).
