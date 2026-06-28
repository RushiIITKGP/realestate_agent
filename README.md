# realestate_agent

Conversational real estate assistant inspired by Homes.com Homes AI.

## Project structure

- **`backend/`** — FastAPI + LangGraph + Google Gemini (Phases 1–4)
- **`PROCESS_DIAGRAMS.md`** — Architecture and flow diagrams
- **`TECH_STACK_LEARNING.md`** — Learning roadmap

## Backend quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add GOOGLE_API_KEY
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

See [backend/README.md](backend/README.md) for full setup.

## Frontend (optional, later)

Next.js scaffold is included for future frontend work:

```bash
npm install
npm run dev
```
