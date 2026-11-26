# AI Shopping Agent

A full-stack conversational shopping assistant built with **FastAPI**, **PostgreSQL 16**, **LangChain**, **Google Gemini**, and **Next.js 14**. Instead of a traditional e-commerce storefront, users interact with an agent-first chat interface featuring real-time SSE streaming, inline product cards, visual product search, and a synchronized cart & order-history drawer.

**[Watch Demo Video (Google Drive)](https://drive.google.com/file/d/1rwWQ-cVN1tcGYtgiQsj7rawgd3MHxdHf/view?usp=sharing)**

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Natural Language Product Search** | Weighted PostgreSQL `tsvector` + GIN full-text search with price, rating, organic, and category filters |
| **85 Seeded Products & Reviews** | Idempotent database migration & seed script with category images and customer ratings |
| **SSE Streaming Chat** | Real-time `/api/chat` stream emitting token chunks plus structured `products`, `cart`, and `order` events |
| **Session-Bound Cart & Checkout** | Per-session (`X-Session-Id`) cart CRUD, inventory & 20-unit per-item limits, and transactional checkout |
| **Order History & Chat Memory** | Persistent per-session order history and multi-turn conversation memory in PostgreSQL |
| **Visual Product Search** | Upload a product photo in chat to identify items and search matching catalog products |
| **Guardrails** | Enforces grocery-domain boundaries, distinguishes fresh produce from derived products, and requires explicit checkout confirmation |

---

## Architecture

```
┌─────────────────────────┐     SSE + REST      ┌──────────────────────────┐
│   Next.js 14 Frontend   │ ◀─────────────────▶ │     FastAPI Backend      │
│  (React 18, CartContext)│   X-Session-Id      │  (asyncpg, LangChain)    │
└─────────────────────────┘                     └────────────┬─────────────┘
                                                             │
                                        ┌────────────────────┴────────────────────┐
                                        ▼                                         ▼
                          ┌──────────────────────────┐              ┌──────────────────────────┐
                          │      PostgreSQL 16       │              │      Google Gemini       │
                          │  GIN tsvector, Cart,     │              │  (Text + Vision LLM)     │
                          │  Orders, Reviews, Chat   │              └──────────────────────────┘
                          └──────────────────────────┘
```

---

## Tech Stack

- **Backend:** Python 3.13, FastAPI (async), Uvicorn, `uv`
- **Agent Framework:** LangChain (`create_agent`, `@tool`), Google Gemini (`gemini-2.5-flash` configurable via `GEMINI_MODEL`)
- **Database:** PostgreSQL 16 (`asyncpg`), `tsvector` + GIN index with auto-update trigger
- **Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS
- **Testing:** `pytest`, `pytest-asyncio`, `httpx` (`ASGITransport`)
- **Deployment:** Docker & Docker Compose (deployed on AWS EC2)

---

## Project Structure

```
Shopping-Agent-Using-Langchain/
├── backend/
│   ├── migrations/
│   │   └── 001_initial.sql       # Schema, GIN index, and search_vector trigger
│   ├── agent.py                  # LangChain agent, system prompt, and SSE streaming
│   ├── config.py                 # Environment settings
│   ├── db.py                     # Asyncpg pool & migration runner
│   ├── main.py                   # FastAPI endpoints
│   ├── seed.py                   # 85-product & review seed script
│   ├── services.py               # DB queries, cart/inventory limits, checkout
│   ├── tools.py                  # Session-bound LangChain tools
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router pages & layout
│   │   ├── components/           # ChatInterface, ProductCard, CartDrawer
│   │   ├── context/              # CartContext (session + cart/order sync)
│   │   └── types/                # TypeScript interfaces
│   ├── package.json
│   └── Dockerfile
├── tests/
│   ├── test_agent_tools.py       # Session-bound tool & bulk-limit tests
│   └── test_api.py               # FastAPI, cart, checkout, and SSE tests
├── deprecated/                   # Archived initial Streamlit + SQLite prototype
├── docker-compose.yml            # Local PostgreSQL 16 (port 5433)
├── docker-compose.prod.yml       # Full 3-container production stack
└── pyproject.toml
```

---

## Quick Start (Local Development)

### Prerequisites
- Python **3.13+**, `uv`
- Node.js **20+**
- Docker & Docker Compose
- **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/apikey))

### 1. Configure `.env`
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/shopping
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

### 2. Start PostgreSQL & Backend
```bash
docker compose up -d
uv sync
uv run uvicorn backend.main:app --reload --port 8000
```
The backend automatically runs migrations and seeds 85 products on startup.

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000`.

---

## Production Deployment (Docker Compose)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```
Set `CORS_ORIGINS` and `NEXT_PUBLIC_API_BASE` in `.env` to your server's public URL/IP before building.

---

## Running Tests

```bash
uv run pytest -v
```
