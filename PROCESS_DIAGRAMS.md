# HomeGuide AI — Architecture & Process Diagrams

Diagrams for the current project: flat `main.py` + `agent.py`, RentCast data, Gemini chat, SQLite, SSE streaming.

---

## 1. System architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend (Vite / custom UI)"]
        ChatUI[Chat UI]
        Session[session_id in localStorage]
    end

    subgraph Backend["Backend (FastAPI)"]
        Main[main.py]
        Agent[agent.py]
    end

    subgraph AgentLayer["LangGraph Agent"]
        Gemini[Google Gemini LLM]
        Tools[5 Tools]
        Checkpoint[Session Memory]
    end

    subgraph Data["Local SQLite"]
        RE[(realestate.db)]
        CP[(checkpoints.db)]
    end

    subgraph External["External APIs"]
        RC[RentCast API]
        GE[Google Embeddings API]
    end

    ChatUI -->|POST /chat/stream SSE| Main
    Session --> ChatUI

    Main --> Agent
    Agent --> Gemini
    Agent --> Tools
    Agent --> Checkpoint

    Tools --> RE
    Checkpoint --> CP

    Main -->|import on startup / manual| RC
    Main -->|index embeddings| GE
    Gemini -->|chat| Gemini

    RE --- Props[properties + embeddings]
    RE --- Hoods[neighborhoods / zip markets]
```

---

## 2. Project structure

```mermaid
flowchart LR
    subgraph Repo["realestate_agent/"]
        subgraph BE["backend/"]
            MP[main.py<br/>API · DB · RentCast · embeddings]
            AG[agent.py<br/>LangGraph · tools · SSE stream]
            DB[data/realestate.db]
            CK[data/checkpoints.db]
        end
        subgraph FE["frontend/"]
            HTML[index.html]
            JS[src/main.js<br/>reference SSE client]
        end
        HOOK[FRONTEND_HANDOFF.md]
    end

    MP --> DB
    AG --> CK
    AG --> MP
    FE -->|HTTP SSE| MP
```

| File | Role |
|------|------|
| `main.py` | FastAPI app, SQLite models, RentCast import, embedding index, search functions |
| `agent.py` | Gemini agent, tools, streams events to frontend |
| `realestate.db` | Listings, zip market stats, embedding vectors |
| `checkpoints.db` | Multi-turn chat memory per `session_id` |
| `frontend/` | Reference chat UI (replaceable) |

---

## 3. Chat process flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Frontend
    participant API as main.py
    participant Agent as agent.py
    participant LLM as Google Gemini
    participant DB as realestate.db
    participant Mem as checkpoints.db

    User->>UI: Type message
    UI->>API: POST /chat/stream<br/>{session_id, message}

    API->>Agent: stream_chat(db, session_id, message)
    Agent->>Mem: Load chat history (thread_id)

    Agent-->>UI: SSE status "Thinking..."
    Agent->>LLM: User message + tools

    alt Needs search
        LLM->>Agent: Call tool
        Agent-->>UI: SSE status "Searching Austin..."
        Agent->>DB: SQL or semantic search
        DB-->>Agent: Listings
        Agent->>LLM: Tool result (JSON)
    end

    loop Stream tokens
        LLM-->>Agent: Text chunk
        Agent-->>UI: SSE text chunk
    end

    Agent-->>UI: SSE properties [cards]
    Agent-->>UI: SSE done
    Agent->>Mem: Save updated history
    UI->>User: Show text + property cards
```

---

## 4. Data import process

```mermaid
flowchart TD
    Start([Startup or manual import]) --> Empty{DB has listings?}
    Empty -->|No| Auto[RentCast: fetch listings + zip markets]
    Empty -->|Yes| Missing{Missing embeddings?}
    Missing -->|Yes| Embed[Index embeddings via Gemini]
    Missing -->|No| Ready([Ready for chat])
    Auto --> Save[Save to realestate.db]
    Save --> Embed
    Embed --> Ready

    Manual[python main.py City ST 100<br/>or POST /listings/import] --> RC[RentCast API]
    RC --> Save

    Replace{replace=True?}
    Manual --> Replace
    Replace -->|Yes| Wipe[Delete all listings first]
    Replace -->|No| Merge[Add / update listings]
    Wipe --> RC
    Merge --> RC
```

**RentCast provides:** listings (address, price, beds, baths, sqft, etc.) + zip-level market stats.

**On import:** each listing gets an embedding (`gemini-embedding-001`) stored in SQLite for vibe/similar search.

---

## 5. Agent tool routing

```mermaid
flowchart TD
    UserMsg[User message] --> LLM[Gemini decides tool]

    LLM -->|filters only<br/>city, price, beds| T1[search_properties<br/>SQL filters]
    LLM -->|vibe / style language| T2[search_properties_semantic<br/>embedding search]
    LLM -->|same vibe as listing X| T3[find_similar_properties<br/>cosine similarity]
    LLM -->|one listing id| T4[get_property_details]
    LLM -->|zip / area market| T5[get_neighborhood_info]

    T1 --> DB[(realestate.db)]
    T2 --> DB
    T3 --> DB
    T4 --> DB
    T5 --> DB

    DB --> LLM
    LLM --> Reply[Stream text + property cards]
```

| User says | Tool used |
|-----------|-----------|
| "Homes in Austin under $800k" | `search_properties` |
| "Modern minimalist condo under 600k in Austin" | `search_properties_semantic` |
| "Same vibe as the 2nd listing" | `find_similar_properties` |
| "Tell me more about listing X" | `get_property_details` |
| "How's the 78723 market?" | `get_neighborhood_info` |

---

## 6. Search types

```mermaid
flowchart LR
    subgraph SQL["search_properties"]
        F1[city filter]
        F2[max price]
        F3[min beds]
        F4[keyword LIKE]
    end

    subgraph Semantic["search_properties_semantic"]
        Q1[Embed user query]
        Q2[Cosine similarity vs listing embeddings]
        Q3[Optional city + price filters]
    end

    subgraph Similar["find_similar_properties"]
        S1[Load reference listing embedding]
        S2[Rank other listings by similarity]
    end

    SQL --> Results[Listings]
    Semantic --> Results
    Similar --> Results
```

---

## 7. SSE events to frontend

```mermaid
flowchart LR
    API[POST /chat/stream] --> E1[status<br/>Searching...]
    E1 --> E2[text<br/>streamed chunks]
    E2 --> E3[properties<br/>listing cards]
    E3 --> E4[done]
    API -.->|on failure| E5[error]
```

---

## 8. Deployment view (typical dev)

```mermaid
flowchart LR
    Dev[Developer laptop]

    subgraph Ports
        P1[:5173 Frontend]
        P2[:8000 Backend]
    end

    subgraph Local
        DB1[realestate.db]
        DB2[checkpoints.db]
    end

    Dev --> P1
    Dev --> P2
    P1 -->|VITE_API_URL| P2
    P2 --> DB1
    P2 --> DB2
    P2 --> RentCast[RentCast cloud]
    P2 --> Google[Google Gemini cloud]
```

Remote frontend dev: runs backend locally on their machine **or** points `VITE_API_URL` at a deployed/tunnel URL.

---

## Related docs

- [README.md](README.md) — quick start
- [FRONTEND_HANDOFF.md](FRONTEND_HANDOFF.md) — frontend spec
- [backend/README.md](backend/README.md) — backend setup & import
