# Frontend Handoff — HomeGuide AI

Chat-first real estate assistant (Homes.com Homes AI style). **The chat is the product** — users describe what they want in natural language; the agent searches listings and streams answers + property cards.

No filter sidebar, no browse-all-listings page, no map for MVP.

---

## What to build (MVP)

### 1. Chat UI

- Message list: user messages + assistant messages
- Text input + send button
- **New chat** button (new `session_id`, clear thread)
- Loading/status while the agent works (searches can take 5–15 seconds)
- Empty state with suggested prompts, e.g.:
  - "3 bed homes in Austin under $800k"
  - "Modern minimalist condo under 600k in Austin"
  - "Homes in Dallas under $400k"

### 2. Connect to the backend (SSE streaming)

**Primary endpoint:**

```
POST /chat/stream
Content-Type: application/json

{
  "session_id": "uuid-from-localStorage",
  "message": "Modern minimalist condo under 600k in Austin"
}
```

**Response:** `text/event-stream` (Server-Sent Events). Each line:

```
data: {"type":"status","content":"Searching homes in Austin..."}

data: {"type":"text","content":"I found "}

data: {"type":"text","content":"a few options..."}

data: {"type":"properties","properties":[...]}

data: {"type":"done"}
```

### 3. Handle event types

| `type` | Payload | UI |
|--------|---------|-----|
| `status` | `{ "content": "Searching homes in Austin..." }` | Show as loading/status text |
| `text` | `{ "content": "..." }` | Append to assistant message bubble (streaming) |
| `properties` | `{ "properties": [...] }` | Render property cards below the message |
| `done` | `{}` | Stream finished — re-enable send button |
| `error` | `{ "message": "..." }` | Show error in assistant bubble |

### 4. Property card fields

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

| Field | UI suggestion |
|-------|----------------|
| `price` | Large, formatted (`$1,400,000`) |
| `beds`, `baths` | `4bd / 2.5ba` |
| `address`, `city`, `state` | Full address line |
| `neighborhood` | ZIP code from RentCast |
| `property_type` | `house`, `condo`, `townhouse` |
| `sqft` | Optional |
| `description` | Optional, truncated |

**Not available:** `image_url`, `walk_score`, `school_rating` (RentCast does not provide these).

### 5. Session memory (required)

- Generate a UUID on first visit → `localStorage.setItem("session_id", id)`
- Send the **same** `session_id` on every `POST /chat/stream` request
- **New chat** → new UUID + clear message list

Multi-turn example:

```
User: Show me homes in Austin under $800k
Agent: [status → streaming text → property cards]

User: Find something with the same vibe as the 2nd one
Agent: [uses listing id from prior results → similar homes]
```

---

## Suggested layout

```
┌─────────────────────────────────────┐
│  HomeGuide AI          [New chat]   │
├─────────────────────────────────────┤
│                                     │
│  User: Modern condo in Austin...    │
│                                     │
│  Agent: I found a few options...    │
│  ┌──────────┐  ┌──────────┐        │
│  │ $525k    │  │ $489k    │        │
│  │ 2bd/2ba  │  │ 2bd/1ba  │        │
│  │ Austin   │  │ Austin   │        │
│  └──────────┘  └──────────┘        │
│                                     │
├─────────────────────────────────────┤
│  [ Type your message...      ] Send │
└─────────────────────────────────────┘
```

---

## Reference implementation

See `frontend/src/main.js` for a working SSE client (stream parsing, session id, property cards).  
See `frontend/src/style.css` for minimal styling. **Build your own UI** — this is reference only.

---

## Run the backend locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # backend dev adds GOOGLE_API_KEY + RENTCAST_API_KEY
uvicorn main:app --reload
```

| Resource | URL |
|----------|-----|
| API base | `http://127.0.0.1:8000` |
| Swagger docs | `http://127.0.0.1:8000/docs` |
| Backend README | `backend/README.md` |

Chat requires both `GOOGLE_API_KEY` and `RENTCAST_API_KEY` in `backend/.env`. Without them, `POST /chat/stream` returns `503`.

Listings must be in the database (auto-import on first start, or manual import — see backend README).

---

## Frontend setup

Tech stack is your choice: **Next.js, React + Vite, etc.**

Env var pointing at the API:

```env
# Vite
VITE_API_URL=http://127.0.0.1:8000

# Next.js
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

CORS is already enabled (`allow_origins: *`) on the backend.

### Example SSE client (TypeScript)

```typescript
const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

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
) {
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

---

## Error handling

| Status / event | Meaning | UI |
|----------------|---------|-----|
| `200` + SSE stream | Success | Stream status → text → cards |
| `503` | Missing API keys on backend | "Chat unavailable — backend not configured" |
| `type: "error"` in stream | Agent/runtime error | Show `message` in assistant bubble |
| Network error | Backend not running | "Cannot reach server" |

Disable send while streaming. Do not allow double-send.

---

## Optional endpoints (not required for MVP)

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Returns `{ "status": "ok" }` — connectivity check |
| `POST /listings/import?city=Austin&state=TX&limit=100` | **Backend/admin only** — imports listings from RentCast. Not a frontend feature. |

---

## Do NOT build for MVP

- Filter sidebar / search forms (city, price, beds dropdowns)
- Browse-all-listings catalog page
- Map with pins
- Keyword search bar (agent handles search via chat)
- Auth / login / favorites
- Direct listing REST APIs (removed — chat only)

---

## Definition of done

- [ ] Chat UI with message history
- [ ] `POST /chat/stream` integrated with stable `session_id`
- [ ] SSE events handled: `status`, `text`, `properties`, `done`, `error`
- [ ] Assistant text streams token-by-token
- [ ] Property cards rendered inline in the thread
- [ ] Loading and error states
- [ ] New chat clears thread + new session
- [ ] Multi-turn works (follow-up questions, "2nd listing", vibe queries)
- [ ] Runs against local backend at `:8000`

---

## Related docs

- [backend/README.md](backend/README.md) — API setup, data import, embeddings
- [README.md](README.md) — project overview
