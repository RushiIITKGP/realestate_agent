# HomeGuide AI

Chat-first real estate assistant. Listings from [RentCast](https://app.rentcast.io), chat powered by Google Gemini.

## Structure

```
backend/
  main.py      # API + database + RentCast import
  agent.py     # chat agent
frontend/      # Vite chat UI
```

## Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add GOOGLE_API_KEY + RENTCAST_API_KEY
uvicorn main:app --reload
```

### 2. Frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

See [backend/README.md](backend/README.md) for more detail.
