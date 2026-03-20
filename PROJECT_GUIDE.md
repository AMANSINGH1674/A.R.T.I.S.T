# A.R.T.I.S.T — Complete Project Guide

**Agentic Tool-Integrated Large Language Model**

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

ARTIST is a **multi-agent orchestration platform**. You give it a plain-English request like *"Research the latest trends in AI and write a summary"* and it:

1. Breaks the work into steps
2. Assigns each step to a specialised AI agent
3. Runs those agents in sequence (or in parallel)
4. Returns a verified, synthesised result

Think of it as an AI assembly line. Instead of one model doing everything, multiple specialised agents each do one thing well, pass their output to the next, and the final result is better than any single model could produce alone.

It is built to be **enterprise-grade**: authenticated, rate-limited, audited, monitored, containerised, and self-improving via human feedback (RLHF).

---

## 2. How It Works — The Big Picture

```
User Request
     │
     ▼
┌─────────────┐     JWT Auth      ┌──────────────┐
│  FastAPI    │ ◄────────────────► │  PostgreSQL  │
│  REST API   │                   │  (users, DB) │
└──────┬──────┘                   └──────────────┘
       │  enqueues task
       ▼
┌─────────────┐
│   Celery    │  (async task queue via Redis)
│   Worker   │
└──────┬──────┘
       │  runs workflow
       ▼
┌──────────────────────────────────────┐
│         Orchestration Engine         │
│  (LangGraph StateGraph)              │
│                                      │
│  Research → Synthesis → FactCheck    │
│     │            │           │       │
│     ▼            ▼           ▼       │
│  RAG/Milvus   LLM Call   Scoring     │
└──────────────────────────────────────┘
       │
       ▼
  Final Result  ──►  Prometheus Metrics
                 ──►  LangSmith Traces
                 ──►  Human Feedback (RLHF)
```

**Key insight:** The API returns immediately with a `task_id`. The actual work happens asynchronously in a Celery worker. The client polls `/workflow/status/{task_id}` and eventually calls `/workflow/result/{task_id}`.

---

## 3. Architecture Deep Dive

### Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API Framework | FastAPI | Async-native, automatic OpenAPI docs, Pydantic validation |
| Workflow Orchestration | LangGraph | Stateful multi-agent graphs, conditional branching |
| Task Queue | Celery + Redis | Long-running workflows don't block the API |
| Database | PostgreSQL + SQLAlchemy | Audit logs, user management, workflow history |
| Vector Database | Milvus | Stores document embeddings for RAG search |
| Object Storage | MinIO | Stores files that Milvus needs (S3-compatible) |
| Embeddings | OpenAI `text-embedding-ada-002` | Converts text to vectors for semantic search |
| Auth | JWT (HS256) + bcrypt | Stateless tokens, secure password storage |
| Metrics | Prometheus + Grafana | Real-time performance dashboards |
| Tracing | LangSmith | Debug LLM calls, token usage, latency |
| Logging | structlog | Structured JSON logs, easy to query in ELK/Datadog |
| Code Execution | Docker sandbox | Runs user-submitted Python safely in an isolated container |
| ML (RLHF) | scikit-learn + joblib | RandomForest reward model trained on human feedback |
| Production Server | Gunicorn + Uvicorn workers | Multi-process, handles concurrent requests |

### Middleware Stack (request order)

Every HTTP request passes through these layers before hitting an endpoint:

```
Incoming Request
      │
      ▼
LoggingMiddleware       — logs method, path, status, duration, user_id
      │
      ▼
SecurityMiddleware      — decodes JWT (if present), sets request.state.user_id
      │                   adds security headers (X-Frame-Options, HSTS, etc.)
      ▼
RateLimitMiddleware     — checks Redis: user has not exceeded rate limit
      │
      ▼
Endpoint Function       — FastAPI route, enforces auth via Depends(get_current_user)
      │
      ▼
Response
```

---

## 4. Directory Structure

```
A.R.T.I.S.T/
├── artist/                     # All application code
│   ├── main.py                 # App entry point, middleware, router registration
│   ├── config.py               # All settings, read from environment variables
│   ├── gunicorn.conf.py        # Production server configuration
│   │
│   ├── api/                    # HTTP layer
│   │   ├── middleware.py       # Security headers, logging, JWT extraction
│   │   ├── exceptions.py       # Custom error types and handlers
│   │   └── endpoints/
│   │       ├── auth.py         # POST /login, GET /profile, POST /logout
│   │       ├── workflow.py     # POST /execute, GET /status, GET /result
│   │       ├── agents.py       # GET /list, GET /{name}, GET /{name}/status
│   │       ├── tools.py        # GET /list, GET /{name}, GET /{name}/status
│   │       ├── monitoring.py   # GET /health, GET /metrics, GET /status
│   │       └── rlhf.py         # POST /train, GET /training/status, POST /feedback
│   │
│   ├── orchestration/          # Workflow execution engine
│   │   ├── engine.py           # OrchestrationEngine — builds and runs LangGraph graphs
│   │   └── state.py            # WorkflowState TypedDict — shared state between agents
│   │
│   ├── agents/                 # The AI workers
│   │   ├── base.py             # BaseAgent abstract class
│   │   ├── research.py         # Searches knowledge base via RAG
│   │   ├── synthesis.py        # Combines and summarises retrieved documents
│   │   └── fact_check.py       # Scores and verifies synthesised output
│   │
│   ├── tools/                  # Capabilities agents can use
│   │   ├── base.py             # BaseTool abstract class
│   │   ├── code_execution.py   # Runs Python in Docker sandbox
│   │   └── web_search.py       # Google Custom Search API
│   │
│   ├── knowledge/
│   │   └── rag.py              # RAGSystem — Milvus vector search + OpenAI embeddings
│   │
│   ├── security/
│   │   ├── auth.py             # AuthManager — JWT creation/verification, DB user lookup
│   │   ├── rbac.py             # Role hierarchy, require_roles decorator
│   │   ├── prompt_guard.py     # Prompt injection detection and sanitisation
│   │   └── sandbox.py          # SecureCodeSandbox — Docker-based Python execution
│   │
│   ├── database/
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   └── session.py          # DB engine, SessionLocal, get_db dependency
│   │
│   ├── core/
│   │   ├── logging_config.py   # structlog setup
│   │   ├── rate_limiter.py     # Redis token-bucket rate limiter + circuit breaker
│   │   └── registries.py       # Dynamic agent/tool loading from DB
│   │
│   ├── observability/
│   │   ├── metrics.py          # Prometheus counters, histograms, gauges
│   │   └── langsmith.py        # LangSmith tracing integration
│   │
│   ├── rlhf/                   # Reinforcement Learning from Human Feedback
│   │   ├── base.py             # Data classes: HumanFeedback, RewardSignal, etc.
│   │   ├── feedback.py         # API endpoint + service for collecting feedback
│   │   ├── reward_model.py     # TF-IDF + RandomForest reward model (sklearn)
│   │   └── trainer.py          # Orchestrates training cycles
│   │
│   └── worker/
│       ├── celery_app.py       # Celery app config (broker=Redis)
│       └── tasks.py            # execute_workflow_task — the async Celery task
│
├── migrations/
│   ├── env.py                  # Alembic runtime config (reads DATABASE_URL)
│   └── versions/
│       └── 0001_initial_schema.py  # Creates all tables + indexes
│
├── tests/
│   ├── conftest.py             # Sets test env vars before imports
│   └── test_basic.py           # Unit tests for all major components
│
├── static/
│   └── index.html              # Simple web UI
│
├── grafana/
│   └── artist-dashboard.json   # Pre-built Grafana dashboard
│
├── k8s/
│   └── deployment.yaml         # Kubernetes deployment manifest
│
├── scripts/
│   ├── setup.py                # Dev setup script (venv, DB, Docker)
│   └── start.sh                # Simple startup script
│
├── docker-compose.yml          # Full local stack (app + all services)
├── Dockerfile                  # Dev image
├── Dockerfile.prod             # Production multi-stage image
├── .dockerignore               # Excludes secrets and build artifacts
├── alembic.ini                 # Alembic migration config
├── requirements.txt            # Python dependencies
├── .env.example                # Template for .env — copy and fill in
└── PROJECT_GUIDE.md            # This file
```

---

## 5. Every Component Explained

### OrchestrationEngine (`artist/orchestration/engine.py`)

The brain of the system. It:
- Loads **workflow definitions** (currently hardcoded in `load_workflow_definitions()`, extensible to DB)
- Builds a **LangGraph `StateGraph`** from the definition — nodes are agents, edges are the execution order
- Calls `workflow_graph.ainvoke(initial_state)` to run the graph asynchronously
- Returns the final `WorkflowState` after all agents have run

The default workflow is: `research → synthesis → fact_check → final_output`

### WorkflowState (`artist/orchestration/state.py`)

A Python `TypedDict` that acts as the **shared blackboard** passed between agents. Every agent reads from it and writes back to it. Key fields:

| Field | Type | Purpose |
|-------|------|---------|
| `user_request` | str | The original user prompt |
| `retrieved_documents` | list | Documents found by ResearchAgent |
| `intermediate_results` | dict | Each agent stores its output here keyed by name |
| `completed_steps` | list | Agents append their name when done |
| `errors` | list | Any agent failures are recorded here |
| `status` | str | `running`, `completed`, `failed` |
| `history` | list | Human-readable log of what happened |

### ResearchAgent (`artist/agents/research.py`)

- Receives `WorkflowState`
- Calls `RAGSystem.search(user_request, k=10)` to find relevant documents in Milvus
- Stores results in `state["retrieved_documents"]`
- Records summary in `state["intermediate_results"]["research"]`

### SynthesisAgent (`artist/agents/synthesis.py`)

- Reads `state["retrieved_documents"]` (set by ResearchAgent)
- Combines top-5 document texts into a summary
- In production this would use an LLM call — currently uses a simple concatenation as a placeholder
- Outputs a `confidence_score` and `key_points`

### FactCheckAgent (`artist/agents/fact_check.py`)

- Reads `state["intermediate_results"]["synthesis"]`
- Computes a fact-check score based on number of sources and confidence
- Returns `verified: true/false`, a `recommendation` (`approved` / `needs_review`), and any `concerns`

### RAGSystem (`artist/knowledge/rag.py`)

RAG = **Retrieval-Augmented Generation**. Instead of relying purely on what the LLM was trained on, RAG lets you inject relevant documents at query time.

How it works:
1. **Indexing** (offline): You call `add_documents()` with your knowledge base. Each document is converted to a 1536-dimension vector via OpenAI embeddings and stored in Milvus.
2. **Retrieval** (at query time): `search(query, k=5)` converts the query to a vector and finds the `k` most semantically similar documents in Milvus.
3. The retrieved documents are passed to the agents as context.

### Celery Worker (`artist/worker/tasks.py`)

When you `POST /workflow/execute`, the API does NOT run the workflow itself. It calls `execute_workflow_task.delay(...)` which:
- Puts a message on the Redis queue
- Returns a `task_id` immediately
- A Celery worker process picks up the task and runs `OrchestrationEngine.execute_workflow()`
- Progress is stored back in Redis so `/status/{task_id}` can report it

This is why the API is non-blocking — a workflow can take minutes but the API responds in milliseconds.

### AuthManager (`artist/security/auth.py`)

- `get_password_hash(password)` — bcrypt hashes a password for storage
- `verify_password(plain, hashed)` — verifies login attempt
- `create_access_token(data)` — creates a signed JWT with an expiry
- `verify_token(token)` — decodes and validates the JWT signature and expiry
- `authenticate_user(username, password, db)` — looks up user in PostgreSQL, verifies password
- `get_current_user(token, db)` — decodes JWT → looks up user in DB → returns user dict

The `get_current_user` FastAPI dependency is what protects endpoints. Any endpoint with `Depends(get_current_user)` will return 401 if no valid token is provided.

### RLHF System (`artist/rlhf/`)

The system can learn from user feedback over time:

1. Users submit ratings/thumbs via `POST /api/v1/rlhf/feedback`
2. Feedback is stored in the `workflow_executions.request_metadata` JSON column
3. An admin triggers `POST /api/v1/rlhf/train` to start a training cycle
4. `TrainingOrchestrator` collects feedback from DB, trains a `SimpleRewardModel` (TF-IDF features + RandomForest), saves it to `models/reward_model.pkl` via joblib
5. Future runs can use the reward model to score and rank agent actions

### SecureCodeSandbox (`artist/security/sandbox.py`)

When the `code_execution` tool is used, code runs inside a **Docker container** with:
- No network access (`network_disabled=True`)
- Read-only filesystem
- 128MB memory limit
- Runs as `nobody` user
- `no-new-privileges` security option
- Auto-removed after execution

Pre-execution, `_is_dangerous_code()` scans for dangerous imports and builtins.

---

## 6. The Request Lifecycle

Here is exactly what happens when you call `POST /api/v1/workflow/execute`:

```
1. Request arrives
   └─ LoggingMiddleware logs it
   └─ SecurityMiddleware extracts JWT, sets request.state.user_id
   └─ RateLimitMiddleware checks Redis: "rate_limit:user:alice" < 100 requests/hour

2. FastAPI routes to start_workflow()
   └─ get_current_user dependency: decodes JWT → queries users table → returns user dict
   └─ Pydantic validates WorkflowExecutionRequest (min_length, max_length on user_request)
   └─ Prompt injection check (optional — integrate is_prompt_injection() here)

3. execute_workflow_task.delay(...) is called
   └─ Celery serialises the task to JSON and pushes to Redis queue
   └─ Returns task_id (UUID) immediately

4. API responds: {"task_id": "...", "status_url": "...", "result_url": "..."}

5. (Async, in Celery worker process)
   └─ Worker picks up task from Redis
   └─ Creates RAGSystem + OrchestrationEngine
   └─ Calls rag_system.initialize() → connects to Milvus
   └─ Calls orchestration_engine.initialize() → loads workflow definitions
   └─ Creates WorkflowState with user_request, workflow_id, user_id
   └─ Calls execute_workflow("default", initial_state)
       └─ Builds LangGraph: research → synthesis → fact_check → final_output
       └─ Invokes graph: state flows through each node
           └─ ResearchAgent.execute(state) → searches Milvus → updates state
           └─ SynthesisAgent.execute(state) → synthesises docs → updates state
           └─ FactCheckAgent.execute(state) → scores result → updates state
   └─ Returns final WorkflowState
   └─ Stores result in Redis (via Celery result backend)

6. Client polls GET /api/v1/workflow/status/{task_id}
   └─ Returns {"status": "PROCESSING"} or {"status": "SUCCESS"}

7. Client calls GET /api/v1/workflow/result/{task_id}
   └─ Returns the full final WorkflowState as JSON
```

---

## 7. Database Schema

Six tables, all created by `migrations/versions/0001_initial_schema.py`:

```
users
├── id (PK)
├── username (unique, indexed)
├── email (unique, indexed)
├── hashed_password
├── full_name
├── is_active
├── is_superuser
├── roles (JSON array, e.g. ["admin", "engineer"])
└── created_at / updated_at

workflow_definitions
├── id (PK, string — e.g. "default")
├── name, description
├── definition (JSON — nodes, edges, entry/end points)
├── version, is_active
└── created_by (FK → users.id)

workflow_executions
├── id (PK, UUID string)
├── task_id (unique — Celery task ID)
├── workflow_id (FK → workflow_definitions.id, INDEXED)
├── user_id (FK → users.id, INDEXED)
├── user_request (text)
├── request_metadata (JSON — also stores feedback array)
├── status (pending/running/completed/failed)
├── completed_steps (JSON array)
├── intermediate_results (JSON)
├── final_result (JSON)
├── error_info (JSON)
└── started_at / completed_at / execution_time

agent_registry
├── id (PK)
├── name (unique)
├── class_path (e.g. "artist.agents.research.ResearchAgent")
├── description, configuration (JSON)
└── is_active, version

tool_registry
├── id (PK)
├── name (unique)
├── class_path, category
├── configuration (JSON)
└── is_active, version

audit_logs
├── id (PK)
├── user_id (FK → users.id)
├── action (e.g. "submit_feedback", "login")
├── resource_type, resource_id
├── details (JSON)
├── ip_address, user_agent
└── timestamp

system_metrics
├── id (PK)
├── metric_name, metric_value, metric_type
├── labels (JSON)
└── timestamp
```

---

## 8. Security Model

### Authentication Flow
```
Login → POST /api/v1/auth/login → JWT token (30 min expiry)
All other requests → Authorization: Bearer <token> header
```

### Role Hierarchy
```
admin
  └─ engineer
       └─ business_user
            └─ guest
```
An `admin` implicitly has all permissions of all roles below them.

### What each role can do
| Role | Workflow Execute | View Results | RLHF Train | Admin Ops |
|------|-----------------|-------------|------------|-----------|
| admin | Yes | Yes | Yes | Yes |
| engineer | Yes | Yes | No | No |
| business_user | Yes | Yes | No | No |
| guest | No | Yes | No | No |

### Security layers (defence in depth)
1. **HTTPS** — HSTS header enforced in production
2. **JWT** — stateless tokens, signed with SECRET_KEY, expire after 30 min
3. **bcrypt** — passwords hashed with cost factor 12+
4. **Rate limiting** — 100 requests/hour per user (Redis-backed)
5. **RBAC** — role-based endpoint access
6. **Prompt injection guard** — regex patterns block known injection phrases
7. **Docker sandbox** — code execution isolated in a container
8. **CORS** — explicit origin whitelist, no wildcards
9. **Security headers** — X-Frame-Options, X-Content-Type-Options, Referrer-Policy, etc.
10. **Audit logs** — all sensitive actions written to `audit_logs` table

---

## 9. Running Locally

### Prerequisites
- Python 3.11+
- Docker + Docker Compose
- At least one LLM API key (OpenAI or Anthropic)

### Step 1 — Environment

```bash
cd A.R.T.I.S.T
cp .env.example .env
```

Edit `.env` and fill in (minimum required):
```bash
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
POSTGRES_PASSWORD=<strong password>
REDIS_PASSWORD=<strong password>
MINIO_ACCESS_KEY=<any string, min 3 chars>
MINIO_SECRET_KEY=<any string, min 8 chars>
OPENAI_API_KEY=sk-...
```

### Step 2 — Start all services

```bash
docker-compose up -d
```

This starts: PostgreSQL, Redis, Milvus, etcd, MinIO, and the ARTIST app itself.

### Step 3 — Run migrations

```bash
pip install alembic
alembic upgrade head
```

### Step 4 — Create your first user

There is no registration endpoint yet. Insert directly:

```bash
docker-compose exec postgres psql -U artist -d artist -c "
INSERT INTO users (username, email, hashed_password, is_active, is_superuser, roles)
VALUES (
  'admin',
  'admin@example.com',
  '\$2b\$12\$your_bcrypt_hash_here',
  true, true, '[\"admin\"]'
);"
```

To generate the hash:
```bash
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('yourpassword'))"
```

### Step 5 — Test it

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}'

# Execute a workflow (use the token from above)
curl -X POST http://localhost:8000/api/v1/workflow/execute \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"user_request": "What are the main benefits of RAG systems?"}'

# Check status
curl http://localhost:8000/api/v1/workflow/status/<task_id> \
  -H "Authorization: Bearer <token>"

# Get result
curl http://localhost:8000/api/v1/workflow/result/<task_id> \
  -H "Authorization: Bearer <token>"
```

---

## 10. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** | none | JWT signing key. Min 32 chars. Generate with `secrets.token_hex(32)` |
| `POSTGRES_PASSWORD` | **Yes** | none | PostgreSQL password |
| `REDIS_PASSWORD` | **Yes** | none | Redis password |
| `MINIO_ACCESS_KEY` | **Yes** | none | MinIO access key (username) |
| `MINIO_SECRET_KEY` | **Yes** | none | MinIO secret key (password, min 8 chars) |
| `OPENAI_API_KEY` | **Yes*** | none | OpenAI key. *Required unless using Anthropic |
| `ANTHROPIC_API_KEY` | **Yes*** | none | Anthropic key. *Required unless using OpenAI |
| `DATABASE_URL` | No | sqlite | Full Postgres URL. Required for production |
| `REDIS_URL` | No | localhost | Full Redis URL including password |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `DEBUG` | No | `false` | Enables API docs at `/docs`, hot reload |
| `ALLOWED_ORIGINS` | No | `http://localhost:*` | Comma-separated CORS origins |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT expiry |
| `MAX_REQUEST_LENGTH` | No | `10000` | Max chars in user_request |
| `MILVUS_HOST` | No | `localhost` | Milvus hostname |
| `MILVUS_PORT` | No | `19530` | Milvus port |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | No | `json` | `json` or `console` |
| `RATE_LIMIT_REQUESTS` | No | `100` | Requests allowed per window |
| `RATE_LIMIT_WINDOW` | No | `3600` | Window size in seconds |
| `ENABLE_CODE_EXECUTION` | No | `true` | Enable the Docker code sandbox |
| `CODE_EXECUTION_TIMEOUT` | No | `30` | Max seconds for code execution |
| `ENABLE_RLHF` | No | `false` | Enable RLHF training endpoints |
| `LANGSMITH_API_KEY` | No | none | LangSmith tracing |
| `SENTRY_DSN` | No | none | Sentry error tracking |
| `GOOGLE_API_KEY` | No | none | Google Custom Search (web_search tool) |
| `GOOGLE_SEARCH_ENGINE_ID` | No | none | Google Custom Search engine ID |

---

## 11. API Reference

All endpoints except `/health`, `/api/v1/monitoring/*`, and `/api/v1/auth/login` require:
```
Authorization: Bearer <jwt_token>
```

### Authentication

| Method | Path | Body | Returns |
|--------|------|------|---------|
| POST | `/api/v1/auth/login` | `{username, password}` | `{access_token, token_type, expires_in}` |
| GET | `/api/v1/auth/profile` | — | Current user object |
| POST | `/api/v1/auth/logout` | — | `{message}` |

### Workflows

| Method | Path | Body | Returns |
|--------|------|------|---------|
| POST | `/api/v1/workflow/execute` | `{user_request, workflow_id?, metadata?}` | `{task_id, status_url, result_url}` |
| GET | `/api/v1/workflow/status/{task_id}` | — | `{status, info}` |
| GET | `/api/v1/workflow/result/{task_id}` | — | Full `WorkflowState` JSON |

**Workflow status values:** `PENDING` → `PROCESSING` → `SUCCESS` / `FAILURE`

### Agents & Tools

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/agents/list` | List of all agents |
| GET | `/api/v1/agents/{name}` | Single agent info |
| GET | `/api/v1/agents/{name}/status` | Agent health metrics |
| GET | `/api/v1/tools/list` | List of all tools |
| GET | `/api/v1/tools/{name}` | Single tool info |
| GET | `/api/v1/tools/{name}/status` | Tool health metrics |

### Monitoring (public)

| Method | Path | Returns |
|--------|------|---------|
| GET | `/health` | Component health (app-level) |
| GET | `/api/v1/monitoring/health` | DB + Redis health check |
| GET | `/api/v1/monitoring/metrics` | Prometheus metrics (text) |
| GET | `/api/v1/monitoring/status` | Version, uptime, environment |

### RLHF (admin only for training)

| Method | Path | Body | Returns |
|--------|------|------|---------|
| POST | `/api/v1/rlhf/feedback` | `{workflow_id, run_id, feedback_type, rating?}` | `{status}` |
| POST | `/api/v1/rlhf/train` | `{training_type, agent_name?}` | `{status, message}` |
| GET | `/api/v1/rlhf/training/status` | — | Training status |

**feedback_type values:** `thumbs_up`, `thumbs_down`, `rating` (1–5), `detailed`, `comparison`

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

2. Register it in `engine.py` `load_workflow_definitions()` by adding it to a workflow's `nodes` and `edges`.

3. Or insert it into the `agent_registry` DB table so it is loaded dynamically.

### Adding a new Tool

1. Create `artist/tools/my_tool.py`:

```python
from .base import BaseTool

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(name="my_tool", description="Does X")

    async def execute(self, input: str) -> dict:
        # Your logic
        return {"result": "..."}
```

2. Insert into the `tool_registry` table, or instantiate and attach to an agent with `agent.add_tool(MyTool())`.

### Adding a new Workflow

Insert into `workflow_definitions`:
```sql
INSERT INTO workflow_definitions (id, name, definition, is_active)
VALUES (
  'my_workflow',
  'My Custom Workflow',
  '{
    "nodes": ["research", "my_agent", "fact_check", "final_output"],
    "edges": [["research", "my_agent"], ["my_agent", "fact_check"], ["fact_check", "final_output"]],
    "entry_point": "research",
    "end_point": "final_output"
  }',
  true
);
```

Then call it with: `POST /workflow/execute` with `"workflow_id": "my_workflow"`.

### Adding a new User Role

Edit `artist/security/rbac.py`:
```python
class Role:
    ANALYST = "analyst"   # add here

ROLES_HIERARCHY = {
    Role.ADMIN: [Role.ENGINEER, Role.ANALYST, Role.BUSINESS_USER, Role.GUEST],
    Role.ANALYST: [Role.GUEST],
    ...
}
```

Then protect endpoints with:
```python
from ...security.rbac import require_roles, Role

@router.post("/sensitive")
@require_roles([Role.ADMIN, Role.ANALYST])
async def sensitive_endpoint(current_user = Depends(get_current_user)):
    ...
```

---

## 13. Observability & Monitoring

### Prometheus Metrics

Available at `GET /api/v1/monitoring/metrics`. Key metrics:

| Metric | Type | Labels |
|--------|------|--------|
| `artist_workflow_executions_total` | Counter | `workflow_id`, `status`, `user_id` |
| `artist_workflow_duration_seconds` | Histogram | `workflow_id` |
| `artist_agent_executions_total` | Counter | `agent_name`, `status` |
| `artist_agent_duration_seconds` | Histogram | `agent_name` |
| `artist_tool_executions_total` | Counter | `tool_name`, `status` |
| `artist_active_workflows` | Gauge | — |
| `artist_feedback_submissions_total` | Counter | `feedback_type`, `rating` |
| `artist_rlhf_training_cycles_total` | Counter | `training_type`, `status` |

### Grafana Dashboard

Import `grafana/artist-dashboard.json` into your Grafana instance.
Configure it to scrape `http://artist-app:8000/api/v1/monitoring/metrics`.

### LangSmith Tracing

Set `LANGSMITH_API_KEY` in `.env`. Every LLM call, agent execution, and tool use will appear at [smith.langchain.com](https://smith.langchain.com) in your project.

### Structured Logs

All logs are JSON (in production). Each log entry includes:
- `timestamp`, `level`, `event`
- `request_id` — correlation ID for tracing a request across logs
- `user_id`, `method`, `path`, `status_code`, `duration_ms`

To view logs: `docker-compose logs -f artist-app`

---

## 14. Production Deployment

### Docker Compose (single server)

```bash
# Set all env vars in .env, then:
docker-compose up -d

# Run migrations
docker-compose exec artist-app alembic upgrade head

# Check health
curl http://localhost:8000/health
```

### Kubernetes

```bash
# Create secrets
kubectl create secret generic artist-secrets \
  --from-literal=secret-key="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  --from-literal=database-url="postgresql://artist:PASSWORD@postgres:5432/artist" \
  --from-literal=openai-api-key="sk-..."

# Deploy
kubectl apply -f k8s/deployment.yaml
```

### Scaling

- **API** — scale horizontally: `docker-compose up --scale artist-app=3`
- **Workers** — run more Celery workers: `celery -A artist.worker.celery_app worker --concurrency=4`
- **Database** — use a managed Postgres (RDS, Cloud SQL, Supabase) for production
- **Milvus** — Milvus supports a distributed cluster mode for large-scale vector search

### Production checklist

- [ ] `SECRET_KEY` is randomly generated and stored in a secrets manager (not `.env`)
- [ ] `DEBUG=false` and `ENVIRONMENT=production`
- [ ] `ALLOWED_ORIGINS` set to your actual domain(s)
- [ ] All passwords are random and not shared between services
- [ ] TLS/HTTPS terminated at load balancer or nginx upstream
- [ ] `alembic upgrade head` run before first deploy
- [ ] Grafana dashboard imported and alerts configured
- [ ] `SENTRY_DSN` set for error tracking
- [ ] Regular database backups configured

---

## 15. Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=artist --cov-report=html
open htmlcov/index.html

# Run a specific test
pytest tests/test_basic.py::TestAuthManager -v
```

### Test structure

| Test Class | What it covers |
|-----------|----------------|
| `TestWorkflowState` | State creation, metadata storage |
| `TestOrchestrationEngine` | Engine init, workflow definition loading |
| `TestAgents` | Research/synthesis/fact-check execution, failure handling |
| `TestAuthManager` | Password hashing, JWT create/verify/expire, DB lookup, inactive user |
| `TestPromptGuard` | Injection detection patterns, sanitisation |
| `TestRLHF` | Reward model training, feedback conversion, untrained defaults |

Tests never hit a real database or Redis — they mock dependencies.

---

## 16. Common Problems & Fixes

**App fails to start with `SECRET_KEY validation error`**
→ You haven't set `SECRET_KEY` in `.env`. Generate one:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**`Connection refused` to PostgreSQL**
→ Run `docker-compose up -d postgres` and wait for the healthcheck to pass before starting the app.

**`Authentication failed` on Redis**
→ `REDIS_URL` in `.env` must include the password: `redis://:YOUR_PASSWORD@localhost:6379`

**Milvus takes too long / times out on startup**
→ Milvus depends on etcd and MinIO. Start `docker-compose up -d etcd minio` first, wait 10 seconds, then `docker-compose up -d milvus`.

**Celery tasks stuck in `PENDING`**
→ The Celery worker isn't running. Start it:
```bash
celery -A artist.worker.celery_app worker --loglevel=info
```

**`Module not found: artist`**
→ `PYTHONPATH` is not set. Run from the project root:
```bash
PYTHONPATH=. pytest
# or
PYTHONPATH=. python -m artist.main
```

**Rate limit hit (429)**
→ You've exceeded 100 requests per hour. Wait or increase `RATE_LIMIT_REQUESTS` in `.env`.

**JWT `Token has expired`**
→ Get a new token via `POST /api/v1/auth/login`. Increase `ACCESS_TOKEN_EXPIRE_MINUTES` if needed.

**Feedback not saving to DB**
→ This was a known bug (in-place JSON mutation not tracked by SQLAlchemy). It was fixed with `flag_modified()` in `rlhf/feedback.py`.

**`COPY ./static` fails in Docker build**
→ The `static/` directory must exist. It does in this repo (`static/index.html`). If you deleted it, create it: `mkdir static`.

---

## 17. Glossary

| Term | Meaning |
|------|---------|
| **Agent** | An autonomous AI module that does one specific job (research, synthesis, etc.) |
| **Workflow** | A defined sequence of agents connected as a graph |
| **WorkflowState** | The shared data structure passed between agents like a baton in a relay race |
| **RAG** | Retrieval-Augmented Generation — fetching relevant documents to give an LLM better context |
| **Milvus** | Vector database — stores embeddings and finds semantically similar ones |
| **Embedding** | A list of ~1500 numbers that represents the "meaning" of a piece of text |
| **LangGraph** | Library for building stateful multi-agent workflows as directed graphs |
| **Celery** | Task queue system — lets you run work asynchronously in background worker processes |
| **JWT** | JSON Web Token — a signed, self-contained authentication token |
| **bcrypt** | A password hashing algorithm designed to be slow and resist brute-force attacks |
| **RBAC** | Role-Based Access Control — what you can do depends on your role (admin/engineer/etc.) |
| **RLHF** | Reinforcement Learning from Human Feedback — the system improves based on user ratings |
| **Reward Model** | A model trained to predict how good an agent's output is, based on past human ratings |
| **Prometheus** | Time-series metrics database — collects and stores numeric measurements |
| **Grafana** | Dashboard tool that visualises Prometheus metrics |
| **LangSmith** | Debugging and tracing platform for LangChain/LangGraph applications |
| **Alembic** | Database migration tool for SQLAlchemy — manages schema changes over time |
| **structlog** | Python logging library that outputs structured JSON instead of plain text |
| **Circuit Breaker** | A pattern that stops calling a failing service temporarily to prevent cascade failures |
| **MinIO** | Open-source S3-compatible object storage — used by Milvus to store vector data |
