# HomeGuide AI backend

Flat layout — two files:

- `main.py` — API, database, RentCast import
- `agent.py` — chat agent

All listing and market data comes from the [RentCast API](https://app.rentcast.io).

## Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add GOOGLE_API_KEY and RENTCAST_API_KEY

uvicorn main:app --reload
```

On first start, if the database is empty, listings are imported automatically for `DEFAULT_CITY` / `DEFAULT_STATE`.

## Import more listings

```bash
curl -X POST "http://127.0.0.1:8000/listings/import?city=Austin&state=TX&limit=20"
```

Or from the command line:

```bash
python main.py Austin TX 20
```

## Frontend

```bash
cd frontend && npm install && npm run dev
```

## Test

```bash
PYTHONPATH=. pytest
```
