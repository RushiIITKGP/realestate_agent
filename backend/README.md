# HomeGuide AI backend

- `main.py` — API + database
- `agent.py` — chat agent
- `fetch_data.py` — import real listings from RentCast
- `data.py` — mock listings (fallback)

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

## Real listings (RentCast)

1. Sign up at https://app.rentcast.io and copy your API key
2. Add to `.env`:
   ```
   RENTCAST_API_KEY=your-key
   USE_MOCK_DATA=false
   ```
3. Import listings (uses 1 API call):

```bash
python fetch_data.py Austin TX 20
```

Or via API:

```bash
curl -X POST "http://127.0.0.1:8000/listings/import?city=Austin&state=TX&limit=20"
```

4. Chat — the agent searches real imported listings.

**Note:** If you had an old database, delete it first so the wider listing ID column is created:

```bash
rm data/realestate.db
```

## Mock data (no RentCast key)

Leave `USE_MOCK_DATA=true` — 12 sample listings load automatically.

## Frontend

```bash
cd frontend && npm install && npm run dev
```

## Test

```bash
pytest
```
