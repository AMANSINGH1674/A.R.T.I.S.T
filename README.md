# ARTIST — Agentic Tool-Integrated Research & Intelligence System

An enterprise-grade AI orchestration platform built with **LangGraph**, **FastAPI**, and a multi-agent pipeline that performs dynamic routing, parallel research, synthesis, and iterative fact-checking — with long-term memory across sessions.

---

## Architecture

```
User Query
    │
    ▼
┌─────────┐
│ Planner │  classifies query → simple_factual | complex_research | code
└────┬────┘
     │
     ├─── simple_factual ──────────────────────────────┐
     │                                                  │
     ▼                                                  │
┌──────────┐  asyncio.gather()                         │
│ Research │  ┌─ KB Search (Milvus)                     │
│  Agent   │  └─ Web Search (DuckDuckGo, parallel)      │
└────┬─────┘                                            │
     │                                                  │
     ▼                                                  ▼
┌───────────┐                                  ┌───────────┐
│ Synthesis │ ← injects conversation history   │ Synthesis │
│   Agent   │                                  │   Agent   │
└─────┬─────┘                                  └─────┬─────┘
      │                                              │
      ▼                                              │
┌────────────┐                                       │
│ Fact Check │  confidence < 0.7 → cycle back ───────┘
│   Agent    │  (max 3 iterations)
└─────┬──────┘
      │ approved
      ▼
┌──────────────┐
│ Final Output │  structured: summary, confidence, sources, concerns
└──────────────┘
```

**What makes it non-trivial:**
- The graph is **cyclic** — low-confidence results trigger a refined re-research pass
- **Planner routes dynamically** — simple questions skip research entirely
- **KB + web search run in parallel** via `asyncio.gather`, not sequentially
- **Long-term memory** — each user's conversation history is stored in PostgreSQL and injected into the next session
- **Structured output** — every response includes confidence score, sources, verification status, and route metadata

---

## Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph `StateGraph` with conditional + cyclic edges |
| API | FastAPI (async), Gunicorn + Uvicorn workers |
| Task queue | Celery + Redis |
| Vector database | Milvus (semantic search over uploaded documents) |
| Relational database | PostgreSQL (users, workflow executions, conversation memory) |
| LLM providers | Groq · Anthropic · NVIDIA NIM · OpenAI (switchable via env var) |
| Web search | DuckDuckGo (free, no API key) · Google Custom Search (optional) |
| Auth | JWT (python-jose) + bcrypt password hashing |
| Observability | structlog (JSON logs) · Prometheus metrics · Sentry |
| Deployment | Docker Compose (7 services) |

---

## Quick Start

### Prerequisites

- Docker Desktop running
- At least one LLM API key (Groq is free and recommended)

### 1. Clone

```bash
git clone https://github.com/AMANSINGH1674/A.R.T.I.S.T.git
cd A.R.T.I.S.T
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — the minimum required fields:

```env
SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
GROQ_API_KEY=your_groq_api_key        # get free at console.groq.com
DEFAULT_LLM_PROVIDER=groq
DEFAULT_MODEL=llama-3.1-8b-instant
```

All other services (PostgreSQL, Redis, Milvus) run locally in Docker with the defaults already in `.env.example`.

### 3. Start

```bash
docker compose up --build -d
```

### 4. Create your first user

```bash
docker compose exec artist-app python3 -c "
from artist.database.session import SessionLocal
from artist.database.models import User
from artist.security.auth import AuthManager
db = SessionLocal()
auth = AuthManager()
user = User(username='admin', email='admin@example.com',
            hashed_password=auth.get_password_hash('yourpassword'),
            is_active=True, is_superuser=True, roles=['admin'])
db.add(user); db.commit(); print('User created')
"
```

### 5. Open

Go to **http://localhost:8000** → log in → start asking questions.

---

## Switching LLM Providers

Change `DEFAULT_LLM_PROVIDER` in `.env` and restart:

```env
# Groq (fast, free tier)
DEFAULT_LLM_PROVIDER=groq
DEFAULT_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=gsk_...

# Anthropic
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_MODEL=claude-3-5-haiku-20241022
ANTHROPIC_API_KEY=sk-ant-...

# NVIDIA NIM
DEFAULT_LLM_PROVIDER=nim
DEFAULT_MODEL=meta/llama-3.1-8b-instruct
NVIDIA_API_KEY=nvapi-...

# OpenAI
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

```bash
docker compose up -d --force-recreate artist-app celery-worker
```

---

## Uploading Documents to the Knowledge Base

Click **"Upload Doc"** in the top-right corner of the UI, or use the API:

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@your_document.pdf"
```

Supported formats: `.pdf`, `.txt`, `.md` (max 20 MB). Documents are chunked, embedded, and indexed into Milvus — immediately searchable by the Research Agent.

---

## API Reference

### Authentication

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}'
# → {"access_token": "eyJ...", "token_type": "bearer"}
```

### Execute a Workflow

```bash
curl -X POST http://localhost:8000/api/v1/workflow/execute \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_request": "Compare transformer and Mamba architectures"}'
# → {"task_id": "abc123", "result_url": "/api/v1/workflow/result/abc123"}
```

### Poll for Result

```bash
curl http://localhost:8000/api/v1/workflow/result/abc123 \
  -H "Authorization: Bearer TOKEN"
```

Response includes:
```json
{
  "final_output": {
    "summary": "...",
    "key_points": ["..."],
    "confidence": 0.88,
    "verified": true,
    "sources": ["https://..."],
    "concerns": [],
    "recommendation": "approved",
    "metadata": {
      "route_taken": "complex_research",
      "research_iterations": 1,
      "kb_results_found": 0,
      "web_results_found": 5
    }
  }
}
```

### Submit Feedback (RLHF)

```bash
curl -X POST http://localhost:8000/api/v1/rlhf/feedback/feedback \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "default", "run_id": "abc123", "feedback_type": "rating", "rating": 5}'
```

---

## Services

```bash
docker compose ps
```

| Service | Port | Purpose |
|---|---|---|
| `artist-app` | 8000 | FastAPI application + UI |
| `celery-worker` | — | Async workflow execution |
| `postgres` | — | Users, executions, conversation memory |
| `redis` | — | Celery broker + result backend |
| `milvus` | — | Vector database for RAG |
| `etcd` | — | Milvus metadata store |
| `minio` | — | Milvus object storage |

---

## Project Structure

```
artist/
├── agents/
│   ├── planner.py        # classifies query → determines workflow route
│   ├── research.py       # parallel KB + web search via asyncio.gather
│   ├── synthesis.py      # LLM synthesis with conversation history injection
│   ├── fact_check.py     # LLM-based fact verification against sources
│   └── final_output.py   # assembles structured final response
├── orchestration/
│   ├── engine.py         # LangGraph cyclic StateGraph with conditional edges
│   └── state.py          # WorkflowState TypedDict (all agent data)
├── knowledge/
│   └── rag.py            # Milvus vector store — add_documents, search
├── core/
│   └── memory.py         # MemoryService — PostgreSQL conversation history
├── tools/
│   └── web_search.py     # DuckDuckGo + Google Custom Search
├── api/endpoints/
│   ├── workflow.py       # execute, status, result
│   ├── knowledge.py      # document upload + KB stats
│   └── auth.py           # login, profile
├── worker/
│   └── tasks.py          # Celery task — memory retrieval, workflow execution, memory save
└── rlhf/
    ├── feedback.py       # collect human feedback
    └── reward_model.py   # sklearn reward model (TF-IDF + RandomForest)
static/
└── index.html            # single-page UI (vanilla JS, dark theme)
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | JWT signing key (min 32 chars) |
| `DEFAULT_LLM_PROVIDER` | Yes | `groq` \| `anthropic` \| `nim` \| `openai` |
| `DEFAULT_MODEL` | Yes | Model ID for the chosen provider |
| `GROQ_API_KEY` | If using Groq | From console.groq.com |
| `ANTHROPIC_API_KEY` | If using Anthropic | From console.anthropic.com |
| `NVIDIA_API_KEY` | If using NIM | From build.nvidia.com |
| `OPENAI_API_KEY` | If using OpenAI | From platform.openai.com |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `MILVUS_HOST` | Yes | Milvus hostname (default: `localhost`) |
| `EMBEDDING_PROVIDER` | Yes | `nim` \| `openai` |
| `GOOGLE_API_KEY` | No | For Google Custom Search (DuckDuckGo used otherwise) |

---

## License

MIT
