# HomeGuide AI backend

- `main.py` — API + database
- `agent.py` — chat agent
- `fetch_data.py` — import real listings + zip market stats from RentCast
- `data.py` — mock listings (fallback)

## Run

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

uvicorn main:app --reload
```

## Real data import

Add to `.env`:

```env
RENTCAST_API_KEY=your-rentcast-key
USE_MOCK_DATA=false
```

Get a key at https://app.rentcast.io

Import:

```bash
python fetch_data.py Austin TX 20
```

This fetches:
- **Listings** from RentCast (address, price, beds, baths, sqft, property type, year built, days on market, etc.)
- **ZIP market stats** into neighborhood info (median price, days on market, property-type breakdown)

Ask the agent about a ZIP code, e.g. *"How's the 78723 market?"*

## Mock data

Leave `USE_MOCK_DATA=true` to use sample listings in `data.py`.

## Frontend

```bash
cd frontend && npm install && npm run dev
```

## Test

```bash
pytest
```
