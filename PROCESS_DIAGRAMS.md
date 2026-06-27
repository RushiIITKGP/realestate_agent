# Homes AI–Style Project — Process Diagrams

Backend-focused process diagrams for building a conversational real estate assistant similar to [Homes.com Homes AI](https://www.homes.com).

These diagrams cover system architecture, request flows, agent logic, search, memory, streaming, deployment, and error handling.

---

## 1. High-Level System Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer (later)"]
        UI[Web / Mobile / CLI / Swagger]
    end

    subgraph API["FastAPI Backend"]
        REST[REST Endpoints]
        SSE[SSE Stream Endpoint]
        WS[WebSocket Endpoint - optional]
        Auth[Auth Middleware - optional]
    end

    subgraph Agent["LangGraph Agent Layer"]
        Graph[LangGraph State Machine]
        LLM[LLM - GPT-4o / Claude]
        Tools[Tool Router]
        Memory[Checkpointer / Session Memory]
    end

    subgraph Services["Domain Services"]
        SearchSvc[Property Search Service]
        NeighborhoodSvc[Neighborhood Service]
        CompareSvc[Compare Service]
        EmbedSvc[Embedding Service - optional]
    end

    subgraph Data["Data Layer"]
        PG[(PostgreSQL)]
        PGV[pgvector - semantic search]
        Redis[(Redis - sessions/cache)]
        S3[(S3/R2 - images - optional)]
    end

    subgraph External["External APIs (optional)"]
        OpenAI[OpenAI API]
        Maps[Mapbox / Geocoding]
        MLS[MLS / RESO API - production]
    end

    subgraph Observability["Observability"]
        LangSmith[LangSmith Traces]
    end

    UI --> REST
    UI --> SSE
    UI --> WS

    REST --> Auth
    SSE --> Auth
    WS --> Auth

    Auth --> Graph
    Graph --> LLM
    Graph --> Tools
    Graph --> Memory

    Tools --> SearchSvc
    Tools --> NeighborhoodSvc
    Tools --> CompareSvc

    SearchSvc --> PG
    SearchSvc --> PGV
    SearchSvc --> EmbedSvc
    NeighborhoodSvc --> PG
    CompareSvc --> PG

    Memory --> Redis
    Memory --> PG

    LLM --> OpenAI
    EmbedSvc --> OpenAI
    SearchSvc --> Maps
    SearchSvc --> MLS

    Graph --> LangSmith
    LLM --> LangSmith
```

---

## 2. Main User Chat Flow (Backend Core)

This is the primary loop to build first.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / CLI / Swagger
    participant API as FastAPI /chat
    participant CP as Checkpointer
    participant Graph as LangGraph Agent
    participant LLM as LLM
    participant Tools as Tool Executor
    participant DB as PostgreSQL

    User->>API: POST /chat<br/>{session_id, message}
    API->>CP: Load conversation state<br/>for session_id
    CP-->>API: Prior messages + preferences

    API->>Graph: Invoke graph with new user message
    Graph->>LLM: System prompt + history + user message

    alt LLM decides to call tools
        LLM-->>Graph: Tool call(s)<br/>e.g. search_properties(...)
        Graph->>Tools: Execute tool
        Tools->>DB: SQL / vector / geo query
        DB-->>Tools: Structured results
        Tools-->>Graph: Tool output JSON
        Graph->>LLM: Tool results + continue reasoning
        LLM-->>Graph: Final natural language answer
    else LLM answers directly
        LLM-->>Graph: Clarifying question or direct reply
    end

    Graph->>CP: Save updated state<br/>(history, preferences, last results)
    Graph-->>API: Assistant response + property IDs
    API-->>User: JSON response<br/>{message, properties[], session_id}
```

---

## 3. LangGraph Agent Internal Flow

How the agent graph should be structured.

```mermaid
flowchart TD
    Start([User Message Received]) --> LoadState[Load Session State<br/>from Checkpointer]

    LoadState --> ParsePrefs[Extract / Update Preferences<br/>budget, city, beds, lifestyle]

    ParsePrefs --> AgentNode[Agent Node<br/>LLM with tools]

    AgentNode --> Decision{LLM output?}

    Decision -->|Tool calls| ToolNode[Tool Execution Node]
    Decision -->|Direct reply| FormatReply[Format Assistant Response]
    Decision -->|Needs clarification| AskUser[Generate Clarifying Question]

    ToolNode --> ToolType{Which tool?}

    ToolType -->|search_properties| Search[Property Search Service]
    ToolType -->|get_property_details| Details[Get Listing by ID]
    ToolType -->|get_neighborhood_info| Hood[Neighborhood Service]
    ToolType -->|compare_properties| Compare[Compare Service]

    Search --> ToolResult[Normalize Tool Result]
    Details --> ToolResult
    Hood --> ToolResult
    Compare --> ToolResult

    ToolResult --> MoreTools{More tools<br/>needed?}
    MoreTools -->|Yes| AgentNode
    MoreTools -->|No| AgentNode

    AskUser --> SaveState[Save State to Checkpointer]
    FormatReply --> SaveState

    SaveState --> End([Return Response to API])
```

---

## 4. Property Search Tool Flow

What happens inside `search_properties`.

```mermaid
flowchart LR
    Input[Tool Input<br/>city, maxPrice, minBeds,<br/>keywords, neighborhood] --> Validate[Validate & Normalize<br/>Pydantic schema]

    Validate --> ParseNL{Natural language<br/>keywords present?}

    ParseNL -->|Yes| Embed[Generate query embedding]
    ParseNL -->|No| SQLOnly[Structured SQL filters only]

    Embed --> Hybrid[Hybrid Search]
    SQLOnly --> SQL[SQLAlchemy Query]

    Hybrid --> SQL
    Hybrid --> Vector[pgvector similarity search]

    SQL --> Filter[Apply filters:<br/>price, beds, baths,<br/>city, type, status]
    Vector --> Filter

    Filter --> Geo{Location radius<br/>or map bounds?}
    Geo -->|Yes| PostGIS[PostGIS spatial filter]
    Geo -->|No| Rank[Rank & limit results]

    PostGIS --> Rank
    Rank --> Format[Format listing summaries<br/>id, address, price, beds,<br/>neighborhood, highlights]
    Format --> Return[Return JSON to Agent]

    Return --> Agent[LLM interprets results<br/>and writes user-facing answer]
```

---

## 5. Multi-Turn Conversation & Memory Flow

How the agent remembers and refines preferences across turns.

```mermaid
stateDiagram-v2
    [*] --> NewSession: First message

    NewSession --> CollectingPrefs: User vague<br/>"looking for a family home"

    CollectingPrefs --> CollectingPrefs: Agent asks clarifiers<br/>"Which city? Budget?"
    CollectingPrefs --> Searching: Enough prefs known

    Searching --> PresentResults: Tool returns listings
    PresentResults --> Refining: User adjusts<br/>"cheaper" / "more walkable"
    Refining --> Searching: Updated filters

    PresentResults --> DetailView: User asks about one home<br/>"tell me about #3"
    DetailView --> Compare: User asks<br/>"compare top two"
    Compare --> PresentResults

    PresentResults --> CollectingPrefs: User changes city entirely
    PresentResults --> [*]: User ends session

    note right of CollectingPrefs
        State stores:
        - message history
        - budget range
        - location
        - beds/baths
        - last result IDs
        - rejected preferences
    end note
```

---

## 6. Streaming Response Flow (SSE)

Token streaming without a full frontend.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / CLI
    participant API as FastAPI /chat/stream
    participant Graph as LangGraph Agent
    participant LLM as LLM Stream
    participant Tools as Tools

    User->>API: POST /chat/stream
    API->>Graph: Start graph run (async)

    loop Token stream
        Graph->>LLM: Stream completion
        LLM-->>API: token chunk
        API-->>User: SSE event: text delta
    end

    alt Tool call mid-stream
        LLM-->>Graph: tool_call event
        API-->>User: SSE event: tool_started
        Graph->>Tools: Execute search
        Tools-->>Graph: Results
        API-->>User: SSE event: properties_found
        Graph->>LLM: Continue with tool output
    end

    Graph-->>API: Final structured payload
    API-->>User: SSE event: done<br/>{properties, session_id}
```

---

## 7. Backend-Only Development Phases

Suggested build order mapped to the diagrams above.

```mermaid
flowchart TD
    P1[Phase 1: Data Foundation]
    P2[Phase 2: REST + Search]
    P3[Phase 3: LangGraph Agent]
    P4[Phase 4: Memory + Multi-turn]
    P5[Phase 5: Streaming SSE]
    P6[Phase 6: Semantic Search]
    P7[Phase 7: Voice / Realtime - optional]

    P1 --> P1a[SQLAlchemy models]
    P1 --> P1b[Seed mock listings]
    P1 --> P1c[Alembic migrations]

    P2 --> P2a[GET /properties]
    P2 --> P2b[Search service with filters]
    P2 --> P2c[Swagger testing]

    P3 --> P3a[Define tools]
    P3 --> P3b[LangGraph graph]
    P3 --> P3c[POST /chat JSON response]

    P4 --> P4a[Checkpointer]
    P4 --> P4b[Session preferences in state]
    P4 --> P4c[CLI test loop]

    P5 --> P5a[StreamingResponse / SSE]
    P5 --> P5b[Tool events in stream]

    P6 --> P6a[Embeddings pipeline]
    P6 --> P6b[pgvector hybrid search]

    P7 --> P7a[Realtime session endpoint]
    P7 --> P7b[Tool webhook for voice agent]

    P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7
```

---

## 8. Docker / Runtime Deployment Flow

How services run together locally.

```mermaid
flowchart TB
    subgraph DockerCompose["docker-compose (local dev)"]
        subgraph AppContainer["app container"]
            FastAPI[FastAPI + Uvicorn]
            Agent[LangGraph Agent]
        end

        subgraph DataContainers["data containers"]
            Postgres[(PostgreSQL + pgvector)]
            Redis[(Redis)]
        end
    end

    Dev[Developer / CLI / Swagger] -->|:8000| FastAPI
    FastAPI --> Agent
    Agent --> Postgres
    Agent --> Redis
    Agent --> OpenAI[OpenAI API - external]

    Seed[Seed Script] --> Postgres
    Migrate[Alembic Migrate] --> Postgres
```

---

## 9. Error & Fallback Flow

How the backend should behave when things go wrong.

```mermaid
flowchart TD
    Request[Incoming /chat request] --> Valid{Valid session<br/>& message?}
    Valid -->|No| E400[400 Bad Request]
    Valid -->|Yes| RunAgent[Run LangGraph]

    RunAgent --> ToolCall[Tool execution]
    ToolCall --> Results{Results found?}

    Results -->|Yes| Success[LLM summarizes listings]
    Results -->|No| Relax[LLM suggests relaxing one filter]
    Results -->|DB error| E500[500 + log to Sentry]

    RunAgent --> LLMFail{LLM timeout / error?}
    LLMFail -->|Yes| Retry[Retry once]
    Retry --> LLMFail2{Still failing?}
    LLMFail2 -->|Yes| Fallback[Return friendly error message]
    LLMFail2 -->|No| Success

    Success --> Response[200 + message + properties]
    Relax --> Response
    Fallback --> Response
```

---

## 10. One-Page Summary (ASCII)

```
┌──────────────┐     POST /chat      ┌──────────────┐
│ User / CLI   │ ──────────────────► │   FastAPI    │
│ Swagger      │ ◄────────────────── │   Backend    │
└──────────────┘   JSON / SSE stream └──────┬───────┘
                                            │
                                            ▼
                                   ┌────────────────┐
                                   │   LangGraph    │
                                   │   Agent Graph  │
                                   └───────┬────────┘
                                           │
                         ┌─────────────────┼─────────────────┐
                         ▼                 ▼                 ▼
                    ┌─────────┐      ┌───────────┐     ┌──────────┐
                    │   LLM   │      │   Tools   │     │ Checkptr │
                    │ OpenAI  │      │ search    │     │ SQLite/  │
                    └─────────┘      │ details   │     │ Postgres │
                                       │ neighbor  │     └──────────┘
                                       │ compare   │
                                       └─────┬─────┘
                                             ▼
                                    ┌─────────────────┐
                                    │ Property Search │
                                    │   Service       │
                                    └────────┬────────┘
                                             ▼
                                    ┌─────────────────┐
                                    │   PostgreSQL    │
                                    │ + pgvector      │
                                    └─────────────────┘
```

---

## Recommended Starting Point (Backend Only)

Focus on **Diagrams 2, 3, and 4** first:

1. User sends message → FastAPI
2. LangGraph decides → call tools or ask clarifying questions
3. Tools query PostgreSQL → return structured listings
4. LLM writes the final answer → save session → respond

That gives you the core Homes AI loop without any frontend.

---

## Related Documentation

- [TECH_STACK_LEARNING.md](./TECH_STACK_LEARNING.md) — Full tech stack learning roadmap

---

*Last updated: June 2025*
