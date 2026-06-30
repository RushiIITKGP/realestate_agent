# Frontend Handoff — HomeGuide AI

**Read this entire doc first.** It has everything you need to build the frontend. You do **not** need to read `backend/main.py` or `backend/agent.py`.

---

## Your job

Build the **frontend UI** for a chat-first real estate app (Homes.com Homes AI style).

- **The chat is the whole product** — users type natural language; the backend agent searches listings and streams replies + property cards.
- **Design is up to you** — the `frontend/` folder in this repo is a minimal reference demo. Rebuild the UI however you want.
- **You do not need to change the backend** — treat it as an external API.

---

## What's in this repo

```
backend/                 ← API (already built — run it, don't rewrite it)
  main.py                ← defines POST /chat/stream (you don't need to open this)
  agent.py
  requirements.txt
  .env.example           ← template for API keys
  README.md              ← extra backend notes

frontend/                ← reference only (minimal Vite demo)
  src/main.js            ← working SSE client — copy logic if helpful
  src/style.css
  package.json
  vite.config.js

FRONTEND_HANDOFF.md      ← this file
```

### What is NOT in git (you create locally)

| Folder / file | What it is |
|---------------|------------|
| `frontend/node_modules/` | npm installed packages — run `npm install` to create. **Do not commit.** Like Python's `.venv`. |
| `backend/.venv/` | Python virtual env — run `python3 -m venv .venv` to create. **Do not commit.** |
| `backend/.env` | Your secret API keys — copy from `.env.example`. **Do not commit.** |
| `backend/data/*.db` | Local SQLite database (listings + chat memory). **Do not commit.** |

---

## Connecting to the backend (no backend code needed)

The frontend talks to **one URL**. You never need to read Python source files.

| Piece | Value |
|-------|--------|
| **Method** | `POST` |
| **Path** | `/chat/stream` |
| **Full URL (local)** | `http://127.0.0.1:8000/chat/stream` |
| **Request body** | `{ "session_id": "uuid", "message": "user text" }` |
| **Response** | SSE stream (`text/event-stream`) |

Set the base URL in an env var — never hardcode for production:

```env
# Vite
VITE_API_URL=http://127.0.0.1:8000

# Next.js
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Your fetch call:

```typescript
fetch(`${API_URL}/chat/stream`, { method: "POST", ... })
```

### Explore the API without reading Python

With the backend running, open in a browser:

- **Swagger UI:** http://127.0.0.1:8000/docs — see `POST /chat/stream`, try it live
- **Health check:** http://127.0.0.1:8000/health → `{ "status": "ok" }`

---

## Remote development (not on the same WiFi)

`http://127.0.0.1:8000` only works on **your own machine**. If the backend dev is far away, pick one:

### Option A — Run the backend yourself (recommended)

Clone this repo, set up `backend/` on **your** laptop (see below), use:

```env
VITE_API_URL=http://127.0.0.1:8000
```

You and the backend dev share the same code + this doc. You each run the API locally with your own (or shared) API keys.

### Option B — Backend dev gives you a public URL

They deploy the backend (Render, Railway, Fly.io, etc.) or use a tunnel (ngrok) and send you:

```env
VITE_API_URL=https://their-public-url.com
```

Your frontend code stays the same — only the env var changes.

---

## Run the backend (required for the chat to work)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and add API keys (get from backend dev or create your own):

```env
GOOGLE_API_KEY=...          # https://aistudio.google.com/apikey
RENTCAST_API_KEY=...        # https://app.rentcast.io
```

Start the API:

```bash
uvicorn main:app --reload
```

| Resource | URL |
|----------|-----|
| API base | http://127.0.0.1:8000 |
| Swagger docs | http://127.0.0.1:8000/docs |

### Load listing data

Chat needs listings in the database. On first start the backend auto-imports Austin, TX (if DB is empty).

To import more manually:

```bash
cd backend
source .venv/bin/activate
python main.py Austin TX 100
```

Multi-city (add without wiping previous cities):

```python
from dotenv import load_dotenv
load_dotenv()
from main import import_listings

import_listings("Austin", "TX", 100, replace=True)   # first: wipes + imports
import_listings("Dallas", "TX", 100, replace=False)  # adds on top
```

Verify:

```bash
sqlite3 data/realestate.db "SELECT city, COUNT(*) FROM properties GROUP BY city;"
```

Run sqlite from the `backend/` folder.

---

## What to build (MVP)

### 1. Chat UI

- Message list: user + assistant messages
- Text input + send button
- **New chat** button (new `session_id`, clear messages)
- Loading/status while waiting (5–15 seconds is normal)
- Empty state with suggested prompts:
  - "3 bed homes in Austin under $800k"
  - "Modern minimalist condo under 600k in Austin"
  - "Homes in Dallas under $400k"

### 2. SSE streaming (`POST /chat/stream`)

**Request:**

```http
POST /chat/stream
Content-Type: application/json

{
  "session_id": "uuid-from-localStorage",
  "message": "Modern minimalist condo under 600k in Austin"
}
```

**Response:** lines of `data: {json}\n\n`

```
data: {"type":"status","content":"Searching homes in Austin..."}
data: {"type":"text","content":"I found "}
data: {"type":"text","content":"a few options..."}
data: {"type":"properties","properties":[...]}
data: {"type":"done"}
```

### 3. Handle each event type

| `type` | Payload | What to do |
|--------|---------|------------|
| `status` | `{ "content": "..." }` | Show loading text ("Searching homes...") |
| `text` | `{ "content": "..." }` | Append to assistant bubble (streaming) |
| `properties` | `{ "properties": [...] }` | Render property cards |
| `done` | `{}` | Stream finished — re-enable send |
| `error` | `{ "message": "..." }` | Show error message |

### 4. Property cards

Each item in `properties`:

```json
{
  "id": "11604-Moore-Rd,-Austin,-TX-78719",
  "address": "11604 Moore Rd",
  "city": "Austin",
  "state": "TX",
  "price": 1400000,
  "beds": 4,
  "baths": 2.5,
  "sqft": 2345,
  "neighborhood": "78719",
  "property_type": "house",
  "description": "Single Family for sale in Austin, TX. 4 bedrooms..."
}
```

| Field | UI |
|-------|-----|
| `price` | Formatted: `$1,400,000` |
| `beds`, `baths` | `4bd / 2.5ba` |
| `address`, `city`, `state` | Address line |
| `neighborhood` | ZIP code |
| `property_type` | `house`, `condo`, `townhouse` |
| `sqft`, `description` | Optional |

**Not available:** photos, walk score, school ratings (data source doesn't provide them).

### 5. Session memory (required)

```typescript
function getSessionId(): string {
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("session_id", id);
  }
  return id;
}
```

- Send the **same** `session_id` on every message
- **New chat** → new UUID + clear UI

**Multi-turn example:**

```
User:  Show me homes in Austin under $800k
Agent: [status → text → property cards]

User:  Find something with the same vibe as the 2nd one
Agent: [similar homes based on prior results]
```

---

## Suggested layout

```
┌─────────────────────────────────────┐
│  HomeGuide AI          [New chat]   │
├─────────────────────────────────────┤
│  User: Modern condo in Austin...    │
│  Agent: I found a few options...    │
│  ┌──────────┐  ┌──────────┐        │
│  │ $525k    │  │ $489k    │        │
│  │ 2bd/2ba  │  │ 2bd/1ba  │        │
│  │ Austin   │  │ Austin   │        │
│  └──────────┘  └──────────┘        │
├─────────────────────────────────────┤
│  [ Type your message...      ] Send │
└─────────────────────────────────────┘
```

---

## Your frontend setup

**Tech stack:** your choice (Next.js, React + Vite, etc.)

If using the reference `frontend/` folder:

```bash
cd frontend
npm install        # creates node_modules/ — do NOT commit this folder
npm run dev        # starts dev server (usually http://localhost:5173)
```

The reference Vite app proxies `/chat` to port 8000. In your own project, call the full API URL via env var instead.

CORS is already open on the backend (`allow_origins: *`).

### Full SSE client example (TypeScript)

```typescript
const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

interface Property {
  id: string;
  address: string;
  city: string;
  state: string;
  price: number;
  beds: number;
  baths: number;
  sqft: number;
  neighborhood: string;
  property_type: string;
  description: string;
}

function getSessionId(): string {
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("session_id", id);
  }
  return id;
}

async function streamChat(
  message: string,
  onStatus: (text: string) => void,
  onText: (chunk: string) => void,
  onProperties: (properties: Property[]) => void,
): Promise<void> {
  const response = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: getSessionId(), message }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail ?? `Error ${response.status}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const event = JSON.parse(line.slice(6));

      if (event.type === "status") onStatus(event.content);
      else if (event.type === "text") onText(event.content);
      else if (event.type === "properties") onProperties(event.properties);
      else if (event.type === "error") throw new Error(event.message);
    }
  }
}
```

### Reference implementation

`frontend/src/main.js` — working vanilla JS version of the above. Copy the stream-parsing logic; rebuild the UI and styling yourself.

---

## Error handling

| Situation | Meaning | Show in UI |
|-----------|---------|------------|
| `200` + SSE stream | Success | Stream status → text → cards |
| `503` | Missing `GOOGLE_API_KEY` or `RENTCAST_API_KEY` in backend `.env` | "Chat unavailable — backend not configured" |
| `type: "error"` in stream | Runtime error | `event.message` |
| Network / fetch failed | Backend not running or wrong `VITE_API_URL` | "Cannot reach server" |

- Disable send button while streaming
- Don't allow double-send

---

## Do NOT build for MVP

- Filter sidebar / search forms (city, price, beds dropdowns)
- Browse-all-listings catalog page
- Map with pins
- Standalone keyword search bar
- Login / auth / favorites
- Calling listing REST endpoints directly (chat only)

The agent handles all search through conversation.

---

## Optional (not required)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | `{ "status": "ok" }` — test if backend is up |
| `POST /listings/import?city=Austin&state=TX&limit=100` | Admin only — import listings. Not a UI feature. |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| CORS error | Backend already allows `*`. Check `VITE_API_URL` is correct. |
| `503` on chat | Add both API keys to `backend/.env`, restart uvicorn. |
| No listings returned | Import data: `python main.py Austin TX 100` from `backend/`. |
| `node_modules` missing | Run `npm install` in `frontend/`. |
| Can't find database | It's at `backend/data/realestate.db` (created on first run). |
| Chat forgets context | Same `session_id` in localStorage? Don't regenerate unless "New chat". |
| RentCast `403 billing/subscription-inactive` | Activate API plan at https://app.rentcast.io |

---

## Definition of done

- [ ] Chat UI with message history
- [ ] `POST /chat/stream` via env var (`VITE_API_URL`)
- [ ] SSE events: `status`, `text`, `properties`, `done`, `error`
- [ ] Assistant text streams token-by-token
- [ ] Property cards inline in the thread
- [ ] Loading and error states
- [ ] New chat → new session + clear messages
- [ ] Multi-turn works ("tell me about the 2nd one", vibe queries)
- [ ] Runs against a running backend (local or deployed URL)

---

## Quick start checklist

1. Clone repo
2. Read this file
3. Set up `backend/` (venv, `.env`, keys, `uvicorn main:app --reload`)
4. Import listings (`python main.py Austin TX 100`)
5. Open http://127.0.0.1:8000/docs to confirm API works
6. Create your frontend project (or fork reference `frontend/`)
7. Set `VITE_API_URL=http://127.0.0.1:8000`
8. Implement chat UI + SSE client
9. Test multi-turn conversation

---

## Related docs

- [backend/README.md](backend/README.md) — import, embeddings, extra backend detail
- [README.md](README.md) — project overview
