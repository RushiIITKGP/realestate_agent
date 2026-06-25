# Tech Stack to Learn — Homes AI–Style Real Estate Assistant

A learning roadmap for building a conversational home search product similar to [Homes.com Homes AI](https://www.homes.com).

**Your current stack:** LangGraph, LangChain, Python, Docker, SQLite, SQLAlchemy, LangGraph agents, FastAPI

This document lists what you already know, what you still need to learn, and a suggested learning order.

---

## Stack overview

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND          React / Next.js, Tailwind, WebSockets   │
├─────────────────────────────────────────────────────────────┤
│  API LAYER         FastAPI (REST, SSE, WebSockets)          │
├─────────────────────────────────────────────────────────────┤
│  AI / AGENTS       LangGraph, LangChain, LangSmith          │
├─────────────────────────────────────────────────────────────┤
│  LLM / VOICE       OpenAI API, Realtime API, Embeddings     │
├─────────────────────────────────────────────────────────────┤
│  DATA              PostgreSQL, pgvector, PostGIS, Redis     │
├─────────────────────────────────────────────────────────────┤
│  SEARCH            Full-text + semantic / hybrid search      │
├─────────────────────────────────────────────────────────────┤
│  REAL ESTATE DATA  Listings, maps, schools, neighborhoods   │
├─────────────────────────────────────────────────────────────┤
│  MEDIA             S3 / R2, CDN                             │
├─────────────────────────────────────────────────────────────┤
│  INFRA             Docker, CI/CD, monitoring, hosting       │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Already in your toolkit (keep sharpening)

| Technology | Role | What to deepen |
|---|---|---|
| **Python** | Backend language | Async (`asyncio`), type hints, Pydantic v2 |
| **FastAPI** | HTTP API, WebSockets, SSE | Streaming responses, dependency injection, middleware |
| **LangChain** | LLM integrations, prompts, tools | Structured output, retrievers, embeddings |
| **LangGraph** | Agent orchestration, state, memory | Checkpointers, human-in-the-loop, multi-agent graphs |
| **SQLAlchemy** | ORM, migrations | Async SQLAlchemy, Alembic migrations |
| **SQLite** | Local dev database | Good for MVP; plan migration to Postgres |
| **Docker** | Containerization | Multi-stage builds, docker-compose for local stack |
| **LangGraph agents** | Tool-calling workflows | Real estate–specific tool design and error handling |

---

## 2. Must learn (core gaps)

### Frontend & UX

| Technology | Why you need it | Priority |
|---|---|---|
| **HTML / CSS / JavaScript** | Web fundamentals | High |
| **TypeScript** | Safer frontend code | High |
| **React** | Component-based UI | High |
| **Next.js** | Full-stack React, routing, API routes | High |
| **Tailwind CSS** | Fast, consistent styling | Medium |
| **TanStack Query (React Query)** | Server state, caching, refetch | Medium |

**What to build:** listing grid, map view, floating chat panel, streaming message UI, property cards inline in chat.

---

### Real-time communication

| Technology | Why you need it | Priority |
|---|---|---|
| **Server-Sent Events (SSE)** | Stream LLM tokens to browser (text chat) | High |
| **WebSockets** | Bidirectional real-time (chat + voice signaling) | High |
| **FastAPI streaming** | `StreamingResponse`, async generators | High |

**Learn first:** SSE for text chat. Add WebSockets when you add voice.

---

### Production database & search

| Technology | Why you need it | Priority |
|---|---|---|
| **PostgreSQL** | Production DB (upgrade from SQLite) | High |
| **Alembic** | Database migrations with SQLAlchemy | High |
| **pgvector** | Vector embeddings for semantic property search | High |
| **PostGIS** | Geospatial queries (radius, map bounds) | Medium |
| **Redis** | Session cache, rate limits, job queues | Medium |
| **Meilisearch** or **Elasticsearch** | Fast full-text + faceted search (optional) | Medium |

**Key concept:** hybrid search = structured filters (price, beds) + semantic search (natural language descriptions).

---

### LLM & AI services

| Technology | Why you need it | Priority |
|---|---|---|
| **OpenAI API** | GPT-4o / GPT-4o-mini for agent reasoning | High |
| **OpenAI Embeddings** | `text-embedding-3-small` for listing/neighborhood search | High |
| **LangSmith** | Trace agent runs, debug tools, evaluate prompts | High |
| **Pydantic** | Tool schemas, request/response validation | High |
| **Prompt engineering** | System prompts, tool descriptions, guardrails | High |

---

### LangGraph production patterns

| Concept | Why you need it | Priority |
|---|---|---|
| **Checkpointers** | Persist conversation state across requests | High |
| **Tool design** | `search_properties`, `get_property`, `get_neighborhood` | High |
| **Streaming from graph** | Token stream + tool results to frontend | High |
| **Memory / state schema** | User preferences, budget, location in graph state | High |
| **Error recovery** | Graceful handling when tools return empty results | Medium |

---

## 3. Learn next (voice & polish)

Homes AI supports **voice + text**. Add these after text chat works.

| Technology | Why you need it | Priority |
|---|---|---|
| **OpenAI Realtime API** | Low-latency speech-to-speech (like Homes AI) | Medium |
| **WebRTC** | Browser audio streaming for voice mode | Medium |
| **Deepgram** or **Whisper API** | Speech-to-text (cheaper alternative to Realtime) | Medium |
| **OpenAI TTS** or **ElevenLabs** | Text-to-speech (STT → agent → TTS pipeline) | Medium |
| **LiveKit** or **Pipecat** | Voice agent infrastructure (optional abstraction) | Low |

**Two voice paths:**

1. **Full Realtime (Homes AI–like):** OpenAI Realtime API + WebRTC — single model, lowest latency.
2. **Pipeline (simpler):** STT → LangGraph agent → TTS — more control, higher latency.

---

## 4. Real estate domain & data

| Technology / Source | Why you need it | Priority |
|---|---|---|
| **RESO Web API** | Standard MLS listing data format | Medium (production) |
| **Bridge Interactive / Spark API** | MLS data aggregators (require licensing) | Low (production) |
| **Mapbox** or **Google Maps Platform** | Maps, geocoding, autocomplete | Medium |
| **MapLibre GL JS** | Open-source map rendering (Mapbox alternative) | Medium |
| **GreatSchools API** | School ratings | Low |
| **Walk Score API** | Walkability / transit scores | Low |
| **OpenStreetMap / Nominatim** | Free geocoding (MVP) | Medium |
| **CSV / seed data** | Mock listings for MVP | High (start here) |

**Important:** Listing data licensing is the hardest part of a real product. Start with mock data; solve MLS access later.

---

## 5. Media & storage

| Technology | Why you need it | Priority |
|---|---|---|
| **AWS S3** or **Cloudflare R2** | Listing photos, documents | Medium |
| **MinIO** | Self-hosted S3-compatible storage (local dev) | Medium |
| **CDN (Cloudflare)** | Fast image delivery | Low |

---

## 6. Auth & user accounts (when needed)

| Technology | Why you need it | Priority |
|---|---|---|
| **JWT + FastAPI** | Simple auth for saved searches / chat history | Medium |
| **Auth0** or **Clerk** | Managed auth (OAuth, social login) | Low |
| **Supabase Auth** | Auth + Postgres in one | Low |

Skip for MVP; add when users need saved searches or cross-device history.

---

## 7. DevOps & production

| Technology | Why you need it | Priority |
|---|---|---|
| **docker-compose** | Local stack: API + Postgres + Redis + frontend | High |
| **GitHub Actions** | CI/CD (test, lint, deploy) | Medium |
| **Railway / Fly.io / AWS ECS** | Hosting containers in production | Medium |
| **nginx** or **Caddy** | Reverse proxy, TLS termination | Medium |
| **Celery + Redis** or **ARQ** | Background jobs (MLS sync, re-index embeddings) | Medium |
| **Sentry** | Error tracking | Medium |
| **Prometheus + Grafana** or **Datadog** | Metrics and dashboards | Low |

---

## 8. Optional advanced features (Homes AI extras)

| Feature | Technologies | Priority |
|---|---|---|
| 3D / virtual tours | Matterport SDK/API | Low |
| Image understanding | GPT-4o Vision | Low |
| Room visualization ("defurnish") | Custom CV or third-party API | Low |
| Phone / SIP voice | OpenAI Realtime SIP support | Low |

---

## Suggested learning order

### Phase 1 — Text MVP (4–8 weeks of learning + building)

1. **React + Next.js** basics (components, state, fetch)
2. **PostgreSQL + pgvector** (migrate from SQLite)
3. **FastAPI SSE streaming** (LLM tokens to browser)
4. **LangGraph checkpointer + property tools**
5. **Embeddings + semantic search** over mock listings
6. **LangSmith** for debugging agent flows

**Outcome:** Text chat that searches mock listings conversationally.

---

### Phase 2 — Real product feel (4–6 weeks)

1. **WebSockets** in FastAPI
2. **Mapbox / MapLibre** — map + listing pins
3. **Redis** — sessions and caching
4. **Hybrid search** — filters + semantic
5. **Tailwind** — polish the UI
6. **docker-compose** — full local stack

**Outcome:** Embedded chat + map + listing cards, production-shaped architecture.

---

### Phase 3 — Voice (4+ weeks)

1. **OpenAI Realtime API** or STT/TTS pipeline
2. **WebRTC** basics
3. Wire voice to same LangGraph tools as text

**Outcome:** Voice-enabled home search like Homes AI.

---

### Phase 4 — Production data & scale

1. MLS / listing data licensing
2. **PostGIS** geospatial queries
3. **Celery** background indexing
4. Auth, monitoring, CI/CD
5. Cloud deployment

---

## Quick reference: tools for your agent

Design these LangGraph tools early — they mirror what Homes AI needs internally:

| Tool | Purpose |
|---|---|
| `search_properties` | Filter by price, beds, city, keywords, walk score |
| `get_property_details` | Full listing by ID |
| `get_neighborhood_info` | Schools, amenities, median price, summary |
| `compare_properties` | Side-by-side comparison of 2–4 listings |
| `geocode_location` | Turn "near downtown Austin" into coordinates |
| `schedule_tour` | (Later) Connect user to listing agent |

---

## Learning resources (starting points)

| Topic | Resource |
|---|---|
| LangGraph | [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/) |
| FastAPI streaming | [fastapi.tiangolo.com/advanced/custom-response](https://fastapi.tiangolo.com/advanced/custom-response/) |
| pgvector | [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) |
| Next.js | [nextjs.org/learn](https://nextjs.org/learn) |
| OpenAI Realtime API | [platform.openai.com/docs/guides/realtime](https://platform.openai.com/docs/guides/realtime) |
| LangSmith | [docs.smith.langchain.com](https://docs.smith.langchain.com/) |
| Mapbox | [docs.mapbox.com](https://docs.mapbox.com/) |
| RESO Web API | [reso.org/reso-web-api](https://www.reso.org/reso-web-api/) |

---

## Summary checklist

### Already know
- [x] Python
- [x] FastAPI
- [x] LangChain
- [x] LangGraph
- [x] SQLAlchemy
- [x] SQLite
- [x] Docker

### Learn first (MVP)
- [ ] React / Next.js
- [ ] TypeScript
- [ ] PostgreSQL + pgvector
- [ ] Alembic
- [ ] FastAPI SSE / streaming
- [ ] LangGraph checkpointers
- [ ] OpenAI API + embeddings
- [ ] LangSmith
- [ ] Tailwind CSS

### Learn second (product polish)
- [ ] WebSockets
- [ ] Redis
- [ ] Mapbox / MapLibre
- [ ] docker-compose
- [ ] Hybrid search (Meilisearch optional)

### Learn third (voice)
- [ ] OpenAI Realtime API
- [ ] WebRTC
- [ ] STT/TTS alternatives (Deepgram, ElevenLabs)

### Learn fourth (production)
- [ ] MLS / listing data APIs
- [ ] PostGIS
- [ ] Celery / background jobs
- [ ] CI/CD (GitHub Actions)
- [ ] Cloud hosting
- [ ] Auth (JWT or managed)
- [ ] S3 / R2 + CDN

---

*Last updated: June 2025*
