# Frontend Handoff — Chat-First HomeGuide AI

This product is a **conversational real estate assistant** (Homes AI–style), not a traditional listing site with filters.

**The AI chat is the product.** Users describe what they want in natural language; the agent searches listings and returns answers + property cards. Multi-turn conversation refines results over time.

---

## What to build (MVP)

### 1. Chat UI (the whole app)

- Message list: user messages + assistant messages
- Text input + send button
- Loading indicator while waiting for the API (responses can take 5–15 seconds)
- Empty state with suggested prompts, e.g.:
  - "3 bed homes in Austin under $800k"
  - "Family-friendly home near good schools"
  - "Something cozy with a backyard in Denver"

### 2. Connect to the backend

**Primary endpoint (everything goes through this):**

```
POST /chat
Content-Type: application/json

{
  "session_id": "user-abc-123",
  "message": "3 bed homes in Austin under 800k"
}
```

**Response:**

```json
{
  "session_id": "user-abc-123",
  "message": "I found 2 homes in Austin under $800k...",
  "properties": [
    {
      "id": "prop-003",
      "address": "903 Oak Hill Ln",
      "city": "Austin",
      "state": "TX",
      "zip": "78704",
      "price": 749000,
      "beds": 3,
      "baths": 2.5,
      "sqft": 1950,
      "property_type": "house",
      "neighborhood": "Zilker",
      "school_rating": 8,
      "walk_score": 78,
      "description": "...",
      "features": ["patio", "garage"],
      "image_url": "https://...",
      "status": "for_sale"
    }
  ]
}
```

### 3. Render the response

| Field | UI |
|---|---|
| `message` | Assistant text bubble |
| `properties` | Property cards inline below the message (image, price, address, beds/baths, neighborhood) |

### 4. Session memory (required)

- Generate a UUID on first visit, store in `localStorage` as `session_id`
- Send the **same** `session_id` on every `POST /chat` request
- Optional: "New chat" button generates a new UUID and clears the thread

Multi-turn example:

```
User: I'm looking for a family home
Agent: Which city and budget?

User: Austin, under 800k, at least 3 beds
Agent: [message + property cards]

User: Tell me more about the cheaper one
Agent: [details about that listing]
```

---

## Suggested layout

```
┌─────────────────────────────────────┐
│  HomeGuide AI          [New chat]   │
├─────────────────────────────────────┤
│                                     │
│  User: 3 bed homes in Austin...     │
│                                     │
│  Agent: I found 2 great options...  │
│  ┌─────────┐  ┌─────────┐          │
│  │ $749k   │  │ $1.1M   │          │
│  │ 3bd/2ba │  │ 4bd/3ba │          │
│  │ Zilker  │  │ Barton  │          │
│  └─────────┘  └─────────┘          │
│                                     │
├─────────────────────────────────────┤
│  [ Type your message...      ] Send │
└─────────────────────────────────────┘
```

---

## Optional (not required for MVP)

| Feature | Endpoint |
|---|---|
| Property detail modal on card click | `GET /properties/{id}` |
| Similar homes (detail view or via chat) | `GET /properties/{id}/similar` |
| Backend health check | `GET /health` |

---

## Do NOT build for MVP

- Filter sidebar / search forms (city, price, beds dropdowns)
- Browse-all-listings catalog page
- Map with pins
- Keyword search bar
- Auth / login / favorites

The agent handles search intent through conversation. Filter APIs exist on the backend for the agent's tools, not for human-facing filter UI.

---

## Run the backend locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # backend dev must add GOOGLE_API_KEY
uvicorn app.main:app --reload
```

| Resource | URL |
|---|---|
| API base | `http://127.0.0.1:8000` |
| Swagger docs | `http://127.0.0.1:8000/docs` |
| Backend README | `backend/README.md` |

**Note:** Chat requires `GOOGLE_API_KEY` in `backend/.env`. Without it, `POST /chat` returns `503`.

---

## Frontend tech (your choice)

- Next.js (scaffold exists at repo root) or React + Vite
- Env var: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
- `fetch` or axios for `POST /chat`
- Tailwind or similar for styling

### Example fetch

```typescript
const sessionId = localStorage.getItem("session_id") ?? crypto.randomUUID();
localStorage.setItem("session_id", sessionId);

const res = await fetch(`${API_URL}/chat`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ session_id: sessionId, message: userText }),
});

const data = await res.json();
// data.message → assistant bubble
// data.properties → render cards
```

---

## Error handling

| Status | Meaning | UI |
|---|---|---|
| `200` | Success | Show message + cards |
| `503` | Missing API key on backend | "Chat unavailable — backend not configured" |
| `502` | Agent/LLM error | "Something went wrong, try again" |
| Network error | Backend not running | "Cannot reach server" |

Show a loading state during the request. Do not allow double-send while loading.

---

## CORS

If the frontend runs on a different port (e.g. `localhost:3000`), the backend may need CORS enabled. Ask the backend dev to add your origin to FastAPI if you see CORS errors in the browser console.

---

## Not available yet

| Feature | Status |
|---|---|
| Streaming responses (token-by-token) | Phase 5 — not built |
| Voice input/output | Phase 7 — not built |
| User accounts / auth | Not built |
| Maps integration | Not built |

Build against full JSON responses from `POST /chat` (wait for complete response, then render).

---

## Definition of done

- [ ] Chat UI with message history
- [ ] `POST /chat` integrated with stable `session_id`
- [ ] Assistant `message` rendered as text
- [ ] `properties` rendered as cards in the thread
- [ ] Loading and error states
- [ ] Multi-turn works (same session, follow-up questions)
- [ ] Runs against local backend at `:8000`

---

## Related docs

- [backend/README.md](backend/README.md) — API setup and endpoints
- [PROCESS_DIAGRAMS.md](PROCESS_DIAGRAMS.md) — architecture (Diagram 2 = main chat flow)
