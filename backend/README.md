# HomeGuide AI backend

- `main.py` — API + database
- `agent.py` — chat agent
- `fetch_data.py` — import real listings + walk scores + zip market stats
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
WALKSCORE_API_KEY=your-walkscore-key
USE_MOCK_DATA=false
```

Get keys:
- RentCast (listings + zip market stats): https://app.rentcast.io
- Walk Score: https://www.walkscore.com/professional/api.php

Import:

```bash
python fetch_data.py Austin TX 20
```

This fetches:
- **Listings** from RentCast (address, price, beds, etc.)
- **Walk Score** per property (Walk Score API)
- **ZIP market stats** into neighborhood info (median price, days on market, property-type breakdown)

Ask the agent about a ZIP code, e.g. *"How's the 78723 market?"*

**Note:** School ratings are still not available from these APIs (would need GreatSchools or similar).

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
