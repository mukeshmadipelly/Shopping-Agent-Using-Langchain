# AI Shopping Agent 🛒

An intelligent conversational shopping assistant built with **LangChain**, **Google Gemini**, **Streamlit**, and **LangSmith** for evaluation. The agent can search products, filter by price/organic preferences, retrieve reviews, process orders, maintain conversation history, and analyze product images.

---

## 🎯 Key Features

| Feature | Description |
|---------|-------------|
| **Natural Language Product Search** | "I want organic honey under $20 with 4.5+ rating" |
| **Smart Filtering** | Price ceiling, organic-only, minimum rating |
| **Review Integration** | Fetches average ratings & review counts per product |
| **Order Management** | Checkout flow with confirmation & SQLite persistence |
| **Order History** | "What have I ordered before?" — full history from DB |
| **Image-Based Search** | Upload a product photo → find similar items |
| **Guardrails** | Politely declines non-shopping queries |
| **Multi-turn Conversation** | Remembers context ("the first one", "that one") |
| **Evaluation Suite** | LLM-as-judge scoring via LangSmith (80% pass rate) |

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Streamlit UI  │────▶│  LangChain Agent │────▶│  SQLite (store.db)  │
│  (app.py)       │     │  (shopping_agent)│     │  Products/Orders    │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌───────────┐ ┌────────────┐
              │ Gemini   │ │ Reviews   │ │  Vision    │
              │ 3.5 Flash│ │  API      │ │  LLM       │
              └──────────┘ └───────────┘ └────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **LLM** | Google Gemini 3.5 Flash Lite (`chat-google-generative-ai`) |
| **Agent Framework** | LangChain (`create_agent`, `@tool` decorators) |
| **Database** | SQLite (`store.db` — products, orders tables) |
| **Frontend** | Streamlit (chat interface + image upload sidebar) |
| **Evaluation** | LangSmith tracing + LLM-as-judge (Gemini) |
| **Package Manager** | `uv` (fast Python packaging) |

---

## 📂 Project Structure

```
Shopping_Agent/
├── .env                          # API keys (not committed)
├── .gitignore
├── .python-version
├── pyproject.toml                # Dependencies & metadata
├── uv.lock
├── README.md
├── resources/
│   └── product_images/           # Sample images for vision search
└── src/
    └── shopping_agent/
        ├── __init__.py
        ├── app.py                # Streamlit UI entry point
        ├── shopping_agent.py     # Agent + 5 tools + system prompt
        ├── reviews_api.py        # Mock review API (extendable)
        ├── setup_db.py           # DB schema + seed data
        └── tests/
            ├── langsmith_eval_scored.py  # Full eval suite (5 tests)
            └── test_eval.py              # Tool-call accuracy test
```

---

## ⚡ Quick Start

### Prerequisites
- Python **3.13+**
- `uv` installed (`pip install uv`)
- **Google API Key** (Gemini) → [Get one](https://aistudio.google.com/apikey)
- **LangSmith API Key** (optional, for tracing) → [Get one](https://smith.langchain.com/settings)

### Installation

```bash
# Clone & enter
git clone https://github.com/<your-username>/Shopping_Agent.git
cd Shopping_Agent

# Install deps (uv handles venv automatically)
uv sync

# Configure environment
cp .env.example .env   # Create .env.example from .env template below
# Edit .env with your keys
```

### `.env` Template
```bash
GOOGLE_API_KEY=your_gemini_api_key_here
LANGCHAIN_API_KEY=your_langsmith_key_here      # Optional: tracing only
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=shopping-agent-eval
```

### Run the App
```bash
# Initialize database (one-time)
uv run python -m src.shopping_agent.setup_db

# Launch Streamlit UI
uv run streamlit run src/shopping_agent/app.py
```
Open `http://localhost:8501` in your browser.

---

## 💬 Example Interactions

| User Input | Agent Behavior |
|------------|----------------|
| `"I want organic honey under $20 with 4.5+ rating"` | Searches → filters → calls reviews API → returns numbered list |
| `"the first one"` | Checkouts product ID from previous message |
| `"what have I ordered before?"` | Queries `orders` table, returns history |
| `"organic almonds under $15"` | Search + filter + review fetch |
| *Upload photo of olive oil* → "Find similar" | Vision LLM extracts attributes → searches DB |

---

## 🧪 Evaluation

Run the full LLM-as-judge evaluation suite:

```bash
uv run python -m src.shopping_agent.tests.langsmith_eval_scored
```

**Current Results:** 4/5 tests pass (80%)
- ✅ Guardrail (refuses non-shopping)
- ✅ Search + filter + review
- ✅ Multi-turn checkout ("the first one")
- ✅ Order history retrieval
- ⚠️ Search returns multiple matches (judge strictness)

Traces appear in your LangSmith project: `shopping-agent-eval`

---

## 🧩 Extending the Agent

| To Add | Where |
|--------|-------|
| New product fields | `setup_db.py` + `search_products` tool |
| Real review API | `reviews_api.py` (replace mock) |
| Payment integration | `checkout` tool (add Stripe/PayPal) |
| User authentication | `app.py` (Streamlit auth) + DB schema |
| Vector search (RAG) | `shopping_agent.py` (add Chroma tool) |

---

## 📄 License

MIT License — feel free to use, modify, and distribute.

---

## 🙋‍♂️ Author

**Mukesh Madipelly**  
[GitHub](https://github.com/mukesh-madipelly) • [LinkedIn](https://linkedin.com/in/mukesh-madipelly)

*Built to demonstrate production-grade LLM agent patterns: tool use, memory, guardrails, evaluation, and observability.*