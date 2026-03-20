# A.R.T.I.S.T — Complete Project Guide

**Agentic Tool-Integrated Research & Intelligence System**

Everything you need to understand, run, extend, and debug this project.

---

## Table of Contents

1. [What Is This?](#1-what-is-this)
2. [How It Works — The Big Picture](#2-how-it-works--the-big-picture)
3. [Architecture Deep Dive](#3-architecture-deep-dive)
4. [Directory Structure](#4-directory-structure)
5. [Every Component Explained](#5-every-component-explained)
6. [The Request Lifecycle](#6-the-request-lifecycle)
7. [Database Schema](#7-database-schema)
8. [Security Model](#8-security-model)
9. [Running Locally](#9-running-locally)
10. [Environment Variables Reference](#10-environment-variables-reference)
11. [API Reference](#11-api-reference)
12. [Extending the System](#12-extending-the-system)
13. [Observability & Monitoring](#13-observability--monitoring)
14. [Production Deployment](#14-production-deployment)
15. [Testing](#15-testing)
16. [Common Problems & Fixes](#16-common-problems--fixes)
17. [Glossary](#17-glossary)

---

## 1. What Is This?

ARTIST is a **multi-agent AI orchestration platform**. You give it a plain-English request and it:

1. **Classifies** the query and decides which agents to run
2. **Researches** in parallel — searching both a vector knowledge base and the live web simultaneously
3. **Synthesises** findings into a coherent answer, injecting your conversation history for continuity
4. **Fact-checks** the answer against the source documents — and cycles back to research if confidence is too low
5. **Returns** a structured result with confidence score, source URLs, verification status, and route metadata

It is built to be **enterprise-grade**: authenticated, rate-limited, audited, monitored, containerised, and self-improving via human feedback (RLHF).

---

## 2. How It Works — The Big Picture

```
User Query
    │
    ▼
┌─────────────┐     JWT Auth      ┌──────────────────────┐
│  FastAPI    │ ◄───────────────► │  PostgreSQL           │
│  REST API   │                   │  users, executions,   │
└──────┬──────┘                   │  conversation_memory  │
       │ enqueues task            └──────────────────────┘
       ▼
┌─────────────┐
│   Celery    │  async task queue via Redis
│   Worker    │  retrieves conversation history before running
└──────┬──────┘
       │ runs workflow
       ▼
┌──────────────────────────────────────────────────────────┐
│              Orchestration Engine (LangGraph)             │
│                                                          │
│  ┌─────────┐                                             │
│  │ Planner │ classifies: simple_factual / complex /code  │
│  └────┬────┘                                             │
│       │                                                  │
│  ┌────▼────┐  asyncio.gather()                           │
│  │Research │  ├─ KB Search  (Milvus)   ─┐               │
│  │  Agent  │  └─ Web Search (DuckDuckGo)┘ merged        │
│  └────┬────┘                                             │
│       │                                                  │
│  ┌────▼──────┐  + conversation history injected          │
│  │ Synthesis │  LLM call (Groq / Anthropic / NIM)        │
│  └────┬──────┘                                           │
│       │                                                  │
│  ┌────▼──────┐  confidence < 0.7? ──► loop back          │
│  │FactCheck  │  (max 3 iterations)                       │
│  └────┬──────┘                                           │
│       │ approved                                         │
│  ┌────▼────────┐                                         │
│  │FinalOutput  │  structured: summary, sources,          │
│  │   Agent     │  confidence, verified, metadata         │
│  └─────────────┘                                         │
└──────────────────────────────────────────────────────────┘
       │
       ▼
  Result stored in Redis ──► client polls ──► result delivered
  Conversation turn saved to PostgreSQL for next session
```

**Key behaviours:**
- API returns a `task_id` immediately — the work runs async in Celery
- The graph is **cyclic** — low confidence routes back to research (up to 3 times)
- **Simple questions** skip research entirely (planner routes directly to synthesis)
- **Conversation history** is stored in PostgreSQL and injected into every new session
- **Parallel research** — KB and web search run simultaneously via `asyncio.gather`

---

## 3. Architecture Deep Dive

### Tech Stack

| Layer | Technology | Why |
|---|---|---|
| API Framework | FastAPI | Async-native, Pydantic validation, automatic OpenAPI |
| Workflow Orchestration | LangGraph `StateGraph` | Stateful cyclic graphs, conditional edge routing |
| Task Queue | Celery + Redis | Long workflows don't block the API |
| Relational DB | PostgreSQL + SQLAlchemy | Users, executions, conversation memory |
| Vector DB | Milvus | Semantic search over uploaded documents |
| Object Storage | MinIO | Milvus backing store (S3-compatible) |
| LLM Providers | Groq / Anthropic / NIM / OpenAI | Switchable via env var |
| Web Search | DuckDuckGo (free) / Google CSE (optional) | Live web results, no API key required for DDG |
| Embeddings | NVIDIA NIM `nv-embedqa-e5-v5` / OpenAI | Converts text to vectors |
| Auth | JWT (python-jose) + bcrypt | Stateless tokens, secure passwords |
| Metrics | Prometheus + Grafana | Real-time performance dashboards |
| Tracing | LangSmith | Debug LLM calls and agent traces |
| Logging | structlog | Structured JSON logs |
| Code Execution | Docker sandbox | Isolated, memory-limited Python execution |
| ML (RLHF) | scikit-learn + joblib | RandomForest reward model from human feedback |
| Production Server | Gunicorn + Uvicorn workers | Multi-process, concurrent requests |

### Middleware Stack (request order)

```
Incoming Request
      │
      ▼
LoggingMiddleware       — logs method, path, status, duration, user_id
      │
      ▼
SecurityMiddleware      — decodes JWT, sets request.state.user_id
      │                   adds security headers (HSTS, X-Frame-Options, etc.)
      ▼
RateLimitMiddleware     — checks Redis: user under rate limit
      │
      ▼
Endpoint Function       — enforces auth via Depends(get_current_user)
      │
      ▼
Response
```

---

## 4. Directory Structure

```
A.R.T.I.S.T/
├── artist/
│   ├── main.py                      # App entry point, middleware, router registration
│   ├── config.py                    # All settings read from environment variables
│   ├── gunicorn.conf.py             # Production server configuration
│   │
│   ├── api/
│   │   ├── middleware.py            # Logging, security headers, JWT extraction
│   │   ├── exceptions.py            # Custom error types and handlers
│   │   └── endpoints/
│   │       ├── auth.py              # POST /login, GET /profile, POST /logout
│   │       ├── workflow.py          # POST /execute, GET /status, GET /result
│   │       ├── knowledge.py         # POST /upload, GET /stats  ← document ingestion
│   │       ├── agents.py            # GET /list, GET /{name}/status
│   │       ├── tools.py             # GET /list, GET /{name}/status
│   │       ├── monitoring.py        # GET /health, GET /metrics, GET /status
│   │       └── rlhf.py              # POST /feedback, POST /train
│   │
│   ├── orchestration/
│   │   ├── engine.py                # Cyclic LangGraph StateGraph with conditional edges
│   │   └── state.py                 # WorkflowState TypedDict — all shared agent data
│   │
│   ├── agents/
│   │   ├── base.py                  # BaseAgent abstract class
│   │   ├── planner.py               # Classifies query → routes workflow dynamically
│   │   ├── research.py              # Parallel KB + web search via asyncio.gather
│   │   ├── synthesis.py             # LLM synthesis with conversation history injection
│   │   ├── fact_check.py            # LLM-based fact verification against sources
│   │   └── final_output.py          # Assembles structured final response
│   │
│   ├── tools/
│   │   ├── base.py                  # BaseTool abstract class
│   │   ├── web_search.py            # DuckDuckGoSearchTool + WebSearchTool (Google CSE)
│   │   └── code_execution.py        # Docker-sandboxed Python execution
│   │
│   ├── knowledge/
│   │   └── rag.py                   # RAGSystem — Milvus vector store, add_documents, search
│   │
│   ├── core/
│   │   ├── memory.py                # MemoryService — PostgreSQL conversation history
│   │   ├── logging_config.py        # structlog setup
│   │   ├── rate_limiter.py          # Redis token-bucket rate limiter + circuit breaker
│   │   └── registries.py            # Dynamic agent/tool loading
│   │
│   ├── llm/
│   │   └── providers.py             # get_llm() — Groq / Anthropic / NIM / OpenAI factory
│   │
│   ├── security/
│   │   ├── auth.py                  # JWT + bcrypt — create/verify tokens, DB user lookup
│   │   ├── rbac.py                  # Role hierarchy, require_roles decorator
│   │   ├── prompt_guard.py          # Prompt injection detection
│   │   └── sandbox.py               # SecureCodeSandbox — Docker-based execution
│   │
│   ├── database/
│   │   ├── models.py                # SQLAlchemy ORM models (incl. ConversationMemory)
│   │   └── session.py               # DB engine, SessionLocal, get_db dependency
│   │
│   ├── observability/
│   │   ├── metrics.py               # Prometheus counters, histograms, gauges
│   │   └── langsmith.py             # LangSmith tracing integration
│   │
│   ├── rlhf/
│   │   ├── base.py                  # Data classes: HumanFeedback, RewardSignal
│   │   ├── feedback.py              # Feedback collection API + service
│   │   ├── reward_model.py          # TF-IDF + RandomForest reward model
│   │   └── trainer.py               # Orchestrates training cycles
│   │
│   └── worker/
│       ├── celery_app.py            # Celery config (broker = Redis)
│       └── tasks.py                 # execute_workflow_task — memory retrieval + workflow
│
├── static/
│   └── index.html                   # Single-page UI (login, chat, document upload)
│
├── migrations/
│   ├── env.py                       # Alembic runtime config
│   └── versions/
│       └── 0001_initial_schema.py   # Creates all tables + indexes
│
├── tests/
│   ├── conftest.py                  # Sets test env vars before imports
│   └── test_basic.py                # Unit tests for all major components
│
├── docker-compose.yml               # Full local stack — 7 services
├── Dockerfile                       # Dev image
├── Dockerfile.prod                  # Production multi-stage image
├── .dockerignore                    # Excludes secrets and build artifacts
├── alembic.ini                      # Alembic migration config
├── requirements.txt                 # Python dependencies
├── .env.example                     # Template for .env
└── PROJECT_GUIDE.md                 # This file
```

---

## 5. Every Component Explained

### PlannerAgent (`artist/agents/planner.py`)

The first agent every request hits. It calls the LLM with a deterministic prompt (`temperature=0.0`) to classify the query into one of three routes:

| Route | Meaning | Graph path |
|---|---|---|
| `simple_factual` | Short factual question (PM of India, capital of France) | planner → synthesis (skips research) |
| `complex_research` | Needs multiple sources, synthesis, verification | planner → research → synthesis → fact_check |
| `code` | Code writing, debugging, or explanation | planner → research → synthesis → fact_check |

This is where the latency savings for simple queries come from — they skip the research and fact-check steps entirely.

### ResearchAgent (`artist/agents/research.py`)

Runs **two searches simultaneously** using `asyncio.gather`:

1. **KB Search** — semantic similarity search over Milvus (your uploaded documents)
2. **Web Search** — DuckDuckGo live results (no API key required)

Results from both are merged and deduplicated by source URL. On re-search iterations (when fact-check cycles back), the query is refined using the specific concerns raised by the fact-checker.

### SynthesisAgent (`artist/agents/synthesis.py`)

- Reads `retrieved_documents` (from ResearchAgent) and `conversation_history` (from PostgreSQL)
- Injects conversation history as `HumanMessage` / `AIMessage` pairs before the current question — giving the LLM context from past sessions
- If no documents found: answers directly from LLM knowledge
- If documents found: builds a context string (capped at ~6000 chars) and synthesises across sources

### FactCheckAgent (`artist/agents/fact_check.py`)

- Calls the LLM with the synthesis summary and original source documents
- Expects a JSON response: `{verified, confidence_score, concerns, unsupported_claims, recommendation}`
- **Increments `research_iteration_count`** — this counter is what the engine uses to decide whether to cycle back or exit
- Falls back to a heuristic score if the LLM returns malformed JSON

### FinalOutputAgent (`artist/agents/final_output.py`)

Assembles the final structured response from all intermediate results:

```json
{
  "summary": "...",
  "key_points": ["..."],
  "confidence": 0.88,
  "verified": true,
  "concerns": [],
  "unsupported_claims": [],
  "recommendation": "approved",
  "sources": ["https://..."],
  "metadata": {
    "route_taken": "complex_research",
    "research_iterations": 1,
    "kb_results_found": 2,
    "web_results_found": 5,
    "total_sources": 7
  }
}
```

### OrchestrationEngine (`artist/orchestration/engine.py`)

Builds and runs the cyclic LangGraph `StateGraph`:

```python
# Conditional routing functions (pure Python, no side effects)
def _route_after_planner(state) -> str:
    return "synthesis" if state["route"] == "simple_factual" else "research"

def _route_after_fact_check(state) -> str:
    if state["research_iteration_count"] >= 3: return "final_output"
    if state["intermediate_results"]["fact_check"]["confidence_score"] < 0.7:
        return "research"   # ← THE CYCLE
    return "final_output"
```

The cycle is capped at 3 iterations to prevent infinite loops. On each iteration, the ResearchAgent refines its query based on the fact-checker's concerns.

### WorkflowState (`artist/orchestration/state.py`)

A Python `TypedDict` — the shared blackboard passed between every agent.

| Field | Type | Set by |
|---|---|---|
| `user_request` | str | Initial state |
| `route` | str | PlannerAgent |
| `research_iteration_count` | int | FactCheckAgent (incremented each pass) |
| `kb_results` | list | ResearchAgent |
| `web_results` | list | ResearchAgent |
| `retrieved_documents` | list | ResearchAgent (merged) |
| `conversation_history` | list | Injected from PostgreSQL before workflow starts |
| `intermediate_results` | dict | Each agent writes its output here |
| `final_output` | dict | FinalOutputAgent |
| `errors` | list | Any agent on failure |
| `status` | str | `running` → `completed` / `failed` |

### MemoryService (`artist/core/memory.py`)

Reads and writes per-user conversation history to the `conversation_memory` PostgreSQL table.

- **Before** the workflow: retrieves the last 6 turns (3 user + 3 assistant) and injects them into `WorkflowState.conversation_history`
- **After** the workflow: saves the new user question + assistant summary as two new rows

This is what makes the system remember context across separate sessions.

### LLM Providers (`artist/llm/providers.py`)

`get_llm()` returns a LangChain `BaseChatModel` for whichever provider is configured:

```
DEFAULT_LLM_PROVIDER=groq      → ChatOpenAI(base_url="https://api.groq.com/openai/v1")
DEFAULT_LLM_PROVIDER=anthropic → ChatAnthropic()
DEFAULT_LLM_PROVIDER=nim       → ChatOpenAI(base_url="https://integrate.api.nvidia.com/v1")
DEFAULT_LLM_PROVIDER=openai    → ChatOpenAI()
```

All providers are drop-in replacements — same LangChain interface, just different base URLs and API keys.

### RAGSystem (`artist/knowledge/rag.py`)

RAG = **Retrieval-Augmented Generation**. Lets you search your own documents at query time.

1. **Indexing** — `add_documents()` embeds text chunks and stores them in Milvus
2. **Retrieval** — `search(query, k=5)` converts the query to a vector, finds the k most similar chunks

The embedding provider is configurable (`EMBEDDING_PROVIDER=nim` or `openai`).

### Knowledge Upload (`artist/api/endpoints/knowledge.py`)

`POST /api/v1/knowledge/upload` accepts PDF, TXT, or MD files:
1. Extracts text (uses `pypdf` for PDFs)
2. Chunks text into ~1000-char overlapping segments
3. Calls `rag.add_documents()` to embed and index into Milvus

### Celery Worker (`artist/worker/tasks.py`)

The main async task. Executes in a background Celery process:
1. Retrieves conversation history from PostgreSQL
2. Initialises RAGSystem + OrchestrationEngine
3. Creates `WorkflowState` with history injected
4. Runs the LangGraph workflow
5. Saves the new conversation turn to PostgreSQL

### RLHF System (`artist/rlhf/`)

Users submit ratings → stored in DB → admin triggers training → `SimpleRewardModel` (TF-IDF + RandomForest) trains on feedback → saved to `models/reward_model.pkl`.

---

## 6. The Request Lifecycle

```
1. POST /api/v1/workflow/execute  {"user_request": "..."}
   └─ LoggingMiddleware, SecurityMiddleware, RateLimitMiddleware
   └─ get_current_user validates JWT → looks up user in PostgreSQL
   └─ execute_workflow_task.delay(...) pushes task to Redis
   └─ Returns {"task_id": "abc123", ...}

2. Celery worker picks up task
   └─ Retrieves conversation history from conversation_memory table
   └─ Creates WorkflowState with history injected

3. LangGraph graph runs
   └─ PlannerAgent: classifies query → sets state["route"]
   └─ (if complex) ResearchAgent:
       ├─ asyncio.gather(kb_search, web_search)  ← parallel
       └─ merges into state["retrieved_documents"]
   └─ SynthesisAgent: LLM call with history + docs → summary
   └─ FactCheckAgent: LLM verifies summary against sources
       └─ if confidence < 0.7: cycles back to ResearchAgent
   └─ FinalOutputAgent: structures the full response

4. Result stored in Redis
   └─ Conversation turn saved to PostgreSQL

5. Client polls GET /api/v1/workflow/result/{task_id}
   └─ Returns full WorkflowState with final_output
```

---

## 7. Database Schema

Seven tables, created by `migrations/versions/0001_initial_schema.py`:

```
users
├── id, username (unique), email (unique)
├── hashed_password, full_name
├── is_active, is_superuser
├── roles (JSON array: ["admin", "engineer"])
└── created_at, updated_at

conversation_memory              ← long-term memory store
├── id, user_id (indexed)
├── role ("user" | "assistant")
├── content (text)
├── run_id (links to workflow_executions)
└── created_at

workflow_definitions
├── id (string — e.g. "default")
├── name, description
├── definition (JSON — nodes, edges)
└── version, is_active, created_by

workflow_executions
├── id (UUID), task_id (Celery task ID)
├── workflow_id, user_id
├── user_request, request_metadata (JSON)
├── status, completed_steps (JSON), intermediate_results (JSON)
├── final_result (JSON), error_info (JSON)
└── started_at, completed_at, execution_time

agent_registry
├── id, name (unique), class_path
└── description, configuration (JSON), is_active

tool_registry
├── id, name (unique), class_path, category
└── configuration (JSON), is_active

audit_logs
├── id, user_id, action
├── resource_type, resource_id, details (JSON)
├── ip_address, user_agent
└── timestamp

system_metrics
├── id, metric_name, metric_value, metric_type
├── labels (JSON)
└── timestamp
```

---

## 8. Security Model

### Authentication
```
POST /api/v1/auth/login → JWT (30 min expiry)
All other requests → Authorization: Bearer <token>
```

### Role Hierarchy
```
admin
  └─ engineer
       └─ business_user
            └─ guest
```

| Role | Execute Workflow | View Results | RLHF Train | Admin Ops |
|---|---|---|---|---|
| admin | Yes | Yes | Yes | Yes |
| engineer | Yes | Yes | No | No |
| business_user | Yes | Yes | No | No |
| guest | No | Yes | No | No |

### Defence in Depth

1. **HTTPS** — HSTS header enforced in production
2. **JWT** — stateless, signed with `SECRET_KEY`, 30 min expiry
3. **bcrypt** — passwords hashed (direct `bcrypt` library, not passlib)
4. **Rate limiting** — 100 req/hour per user, Redis-backed
5. **RBAC** — role-based endpoint protection
6. **Prompt injection guard** — regex patterns block known injection phrases
7. **Docker sandbox** — code execution in isolated container (no network, 128MB RAM)
8. **CORS** — explicit origin whitelist, no wildcards with credentials
9. **Security headers** — X-Frame-Options, X-Content-Type-Options, Referrer-Policy
10. **Audit logs** — all sensitive actions written to `audit_logs` table
11. **SECRET_KEY validation** — app refuses to start if key is < 32 chars or matches the old leaked default

---

## 9. Running Locally

### Prerequisites
- Docker Desktop running
- At least one LLM API key

### Step 1 — Clone and configure

```bash
git clone https://github.com/AMANSINGH1674/A.R.T.I.S.T.git
cd A.R.T.I.S.T
cp .env.example .env
```

Edit `.env` — minimum required:

```env
SECRET_KEY=<python3 -c "import secrets; print(secrets.token_hex(32))">
POSTGRES_PASSWORD=a_strong_password
REDIS_PASSWORD=another_strong_password
MINIO_ACCESS_KEY=minio_user
MINIO_SECRET_KEY=minio_password

# Pick one LLM provider:
DEFAULT_LLM_PROVIDER=groq
DEFAULT_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=gsk_...           # free at console.groq.com

# Embedding (NIM is default — requires NVIDIA_API_KEY)
EMBEDDING_PROVIDER=nim
NVIDIA_API_KEY=nvapi-...       # free credits at build.nvidia.com
```

### Step 2 — Start all services

```bash
docker compose up --build -d
```

Starts: `artist-app`, `celery-worker`, `postgres`, `redis`, `milvus`, `etcd`, `minio`

### Step 3 — Create your first user

```bash
docker compose exec artist-app python3 -c "
from artist.database.session import SessionLocal
from artist.database.models import User
from artist.security.auth import AuthManager
db = SessionLocal()
auth = AuthManager()
user = User(
    username='admin',
    email='admin@example.com',
    hashed_password=auth.get_password_hash('yourpassword'),
    is_active=True,
    is_superuser=True,
    roles=['admin']
)
db.add(user)
db.commit()
print('User created successfully')
"
```

### Step 4 — Open the UI

Go to **http://localhost:8000** → log in → start asking questions.

To upload documents to the knowledge base: click **"Upload Doc"** in the top right.

### Step 5 — Test via API

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yourpassword"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Submit a question
TASK=$(curl -s -X POST http://localhost:8000/api/v1/workflow/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_request":"What are the latest AI breakthroughs in 2025?"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")

# Wait ~15s then get result
sleep 15
curl -s http://localhost:8000/api/v1/workflow/result/$TASK \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## 10. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | — | JWT signing key. Min 32 chars. |
| `POSTGRES_PASSWORD` | **Yes** | — | PostgreSQL password |
| `REDIS_PASSWORD` | **Yes** | — | Redis password |
| `MINIO_ACCESS_KEY` | **Yes** | — | MinIO username |
| `MINIO_SECRET_KEY` | **Yes** | — | MinIO password (min 8 chars) |
| `DEFAULT_LLM_PROVIDER` | **Yes** | `groq` | `groq` \| `anthropic` \| `nim` \| `openai` |
| `DEFAULT_MODEL` | **Yes** | `llama-3.1-8b-instant` | Model ID for the chosen provider |
| `GROQ_API_KEY` | If using Groq | — | From console.groq.com (free) |
| `ANTHROPIC_API_KEY` | If using Anthropic | — | From console.anthropic.com |
| `NVIDIA_API_KEY` | If using NIM | — | From build.nvidia.com (free credits) |
| `OPENAI_API_KEY` | If using OpenAI | — | From platform.openai.com |
| `EMBEDDING_PROVIDER` | **Yes** | `nim` | `nim` \| `openai` |
| `DATABASE_URL` | No | sqlite | Full PostgreSQL URL |
| `REDIS_URL` | No | localhost | Full Redis URL including password |
| `MILVUS_HOST` | No | `localhost` | Milvus hostname (use `milvus` in Docker) |
| `ENVIRONMENT` | No | `development` | `development` \| `production` |
| `DEBUG` | No | `false` | Enables `/docs` and hot reload |
| `ALLOWED_ORIGINS` | No | `["http://localhost:3000","http://localhost:8000"]` | JSON array of allowed CORS origins |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT token lifetime |
| `MAX_REQUEST_LENGTH` | No | `10000` | Max chars in user_request |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `RATE_LIMIT_REQUESTS` | No | `100` | Requests per window per user |
| `RATE_LIMIT_WINDOW` | No | `3600` | Window size in seconds |
| `GOOGLE_API_KEY` | No | — | Google Custom Search (DuckDuckGo used as free fallback) |
| `GOOGLE_SEARCH_ENGINE_ID` | No | — | Google CSE ID |
| `LANGSMITH_API_KEY` | No | — | LangSmith tracing |
| `SENTRY_DSN` | No | — | Sentry error tracking |

---

## 11. API Reference

All endpoints except `/health` and `/api/v1/auth/login` require:
```
Authorization: Bearer <jwt_token>
```

### Authentication

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/v1/auth/login` | `{username, password}` | `{access_token, token_type}` |
| GET | `/api/v1/auth/profile` | — | Current user object |
| POST | `/api/v1/auth/logout` | — | `{message}` |

### Workflows

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/v1/workflow/execute` | `{user_request, workflow_id?, metadata?}` | `{task_id, status_url, result_url}` |
| GET | `/api/v1/workflow/status/{task_id}` | — | `{status, info}` |
| GET | `/api/v1/workflow/result/{task_id}` | — | Full WorkflowState with `final_output` |

**Result shape:**
```json
{
  "status": "completed",
  "result": {
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
        "kb_results_found": 2,
        "web_results_found": 5
      }
    }
  }
}
```

### Knowledge Base

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/v1/knowledge/upload` | `file` (multipart) | `{filename, chunks_indexed, size_mb}` |
| GET | `/api/v1/knowledge/stats` | — | `{status, collection}` |

Supported file types: `.pdf`, `.txt`, `.md` (max 20 MB)

### RLHF

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/v1/rlhf/feedback/feedback` | `{workflow_id, run_id, feedback_type, rating?}` | `{status}` |
| POST | `/api/v1/rlhf/train` | `{training_type}` | `{status}` |
| GET | `/api/v1/rlhf/training/status` | — | Training status |

`feedback_type` values: `thumbs_up`, `thumbs_down`, `rating` (1–5), `detailed`, `comparison`

### Monitoring

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | Component health |
| GET | `/api/v1/monitoring/health` | DB + Redis health |
| GET | `/api/v1/monitoring/metrics` | Prometheus metrics (text) |
| GET | `/api/v1/monitoring/status` | Version, uptime, environment |

---

## 12. Extending the System

### Adding a new Agent

1. Create `artist/agents/my_agent.py`:

```python
from .base import BaseAgent
from ..orchestration.state import WorkflowState

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="my_agent", description="Does something useful")

    async def execute(self, state: WorkflowState, **kwargs) -> WorkflowState:
        # Read from state
        docs = state.get("retrieved_documents", [])

        # Do your work
        result = {"output": "...", "confidence": 0.9}

        # Write back to state
        state["intermediate_results"]["my_agent"] = result
        state["completed_steps"].append("my_agent")
        state["history"].append("my_agent completed")
        return state
```

2. Register it in `engine.py` — add a node and connect it with edges or conditional edges.

### Adding a new Tool

```python
from .base import BaseTool

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(name="my_tool", description="Does X")

    async def execute(self, input: str) -> dict:
        return {"result": "..."}
```

Pass it to an agent: `ResearchAgent(rag_system=rag, web_search_tool=MyTool())`

### Adding a conditional route

In `engine.py`, add a new routing function and use `add_conditional_edges`:

```python
def _my_router(state: WorkflowState) -> str:
    if some_condition(state):
        return "agent_a"
    return "agent_b"

workflow.add_conditional_edges(
    "some_node",
    _my_router,
    {"agent_a": "agent_a", "agent_b": "agent_b"}
)
```

### Switching LLM provider at runtime

Just change `.env` and restart:
```bash
# Change provider
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_MODEL=claude-3-5-haiku-20241022
ANTHROPIC_API_KEY=sk-ant-...

docker compose up -d --force-recreate artist-app celery-worker
```

---

## 13. Observability & Monitoring

### Prometheus Metrics (`GET /api/v1/monitoring/metrics`)

| Metric | Type |
|---|---|
| `artist_workflow_executions_total` | Counter |
| `artist_workflow_duration_seconds` | Histogram |
| `artist_agent_executions_total` | Counter |
| `artist_agent_duration_seconds` | Histogram |
| `artist_active_workflows` | Gauge |
| `artist_feedback_submissions_total` | Counter |

### Structured Logs

All logs are JSON in production. Each entry includes `timestamp`, `level`, `event`, `request_id`, `user_id`, `duration_ms`.

```bash
docker compose logs -f artist-app
docker compose logs -f celery-worker
```

### LangSmith

Set `LANGSMITH_API_KEY` in `.env`. Every LLM call and agent execution will be visible at [smith.langchain.com](https://smith.langchain.com).

---

## 14. Production Deployment

### Docker Compose

```bash
docker compose up -d
curl http://localhost:8000/health
```

### Production checklist

- [ ] `SECRET_KEY` randomly generated, stored in secrets manager
- [ ] `DEBUG=false`, `ENVIRONMENT=production`
- [ ] `ALLOWED_ORIGINS` set to your actual domain(s) as JSON array
- [ ] All passwords random and unique per service
- [ ] TLS terminated at load balancer or nginx
- [ ] `SENTRY_DSN` set for error tracking
- [ ] Regular PostgreSQL backups configured
- [ ] Prometheus/Grafana scraping metrics endpoint

---

## 15. Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=artist --cov-report=html
open htmlcov/index.html

# Specific test class
pytest tests/test_basic.py::TestAuthManager -v
```

| Test Class | What it covers |
|---|---|
| `TestWorkflowState` | State creation, new fields (route, iteration count, memory) |
| `TestOrchestrationEngine` | Engine init, graph compilation |
| `TestAgents` | Planner, research, synthesis, fact-check, final output |
| `TestAuthManager` | Password hashing, JWT create/verify/expire |
| `TestPromptGuard` | Injection detection |
| `TestRLHF` | Reward model training, feedback conversion |

---

## 16. Common Problems & Fixes

**App fails to start: `SECRET_KEY validation error`**
→ Set `SECRET_KEY` in `.env` (min 32 chars):
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**`DEFAULT_LLM_PROVIDER=groq but GROQ_API_KEY is not set`**
→ Add your Groq API key to `.env` and restart the containers.

**`The model X does not exist or you do not have access`**
→ The model ID is wrong for the provider. Check:
- Groq models: `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`
- NIM models: `meta/llama-3.1-8b-instruct`
- Anthropic models: `claude-3-5-haiku-20241022`

**Web search returns 0 results**
→ Verify `ddgs` is installed: `docker compose exec artist-app pip show ddgs`
→ DuckDuckGo may rate-limit briefly — try again in a minute.

**Milvus fails / embedding errors**
→ If `EMBEDDING_PROVIDER=nim` but `NVIDIA_API_KEY` is not set, the app won't start.
→ Switch to `EMBEDDING_PROVIDER=openai` with an OpenAI key, or get a free NIM key at build.nvidia.com.

**Celery task stuck in PENDING**
→ Celery worker isn't running: `docker compose up -d celery-worker`

**`pydantic_settings error: error parsing allowed_origins`**
→ `ALLOWED_ORIGINS` must be valid JSON: `["http://localhost:3000","http://localhost:8000"]`

**Rate limit hit (429)**
→ Increase `RATE_LIMIT_REQUESTS` in `.env` or wait for the window to reset.

**Login succeeds but questions fail**
→ Check `docker compose logs celery-worker` for errors — most issues are LLM API keys or Milvus connectivity.

**`Connection refused` to PostgreSQL or Redis**
→ Run `docker compose ps` to check all services are healthy before the app starts.

---

## 17. Glossary

| Term | Meaning |
|---|---|
| **Agent** | An autonomous AI module that does one specific job |
| **Cyclic Graph** | A workflow graph where execution can loop back to earlier nodes |
| **Dynamic Routing** | The planner decides at runtime which agents to run for a given query |
| **WorkflowState** | The shared TypedDict passed between agents like a baton |
| **RAG** | Retrieval-Augmented Generation — injecting relevant documents into LLM context |
| **Milvus** | Vector database — stores embeddings and finds semantically similar ones |
| **Embedding** | A list of ~1000 numbers representing the semantic meaning of a piece of text |
| **LangGraph** | Library for building stateful multi-agent workflows as directed graphs |
| **Conditional Edge** | A graph edge where the next node is determined by a routing function |
| **Long-term Memory** | Conversation history stored in PostgreSQL and injected into new sessions |
| **Celery** | Task queue — runs workflows asynchronously in background worker processes |
| **DuckDuckGo Search** | Free web search used when no Google API key is configured |
| **JWT** | JSON Web Token — signed, self-contained authentication token |
| **bcrypt** | Password hashing algorithm designed to resist brute-force |
| **RBAC** | Role-Based Access Control — permissions tied to user roles |
| **RLHF** | Reinforcement Learning from Human Feedback — system improves from user ratings |
| **Reward Model** | sklearn model trained to predict how good an agent output is |
| **Prometheus** | Time-series metrics database |
| **structlog** | Python logging library that outputs structured JSON |
| **MinIO** | S3-compatible object storage used by Milvus |
| **Alembic** | Database migration tool for SQLAlchemy |
