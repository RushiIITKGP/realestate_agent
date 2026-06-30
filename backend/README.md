# HomeGuide AI backend

Two files do almost everything:

- `main.py` — FastAPI, database, listings, `/chat/stream`
- `agent.py` — Gemini agent + tools + streaming

## Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add GOOGLE_API_KEY

uvicorn main:app --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Test

```bash
pytest
```
