# 🚀 Agentic Code Reviewer & Guardrail Evaluator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141+-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Workflow-orange.svg)](https://python.langchain.com/docs/langgraph/)
[![LLM](https://img.shields.io/badge/LLM-Groq_llama--3.3--70b-purple.svg)](https://groq.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)](https://redis.io/)
[![Dockerized](https://img.shields.io/badge/Docker-Multi--stage-2496ED.svg)](https://www.docker.com/)
[![Package Manager](https://img.shields.io/badge/uv-Fast_Package_Manager-de5b44.svg)](https://github.com/astral-sh/uv)

An enterprise-grade, **autonomous multi-agent Python code reviewer** and **security guardrail evaluator** powered by **LangGraph**, **Groq (Llama-3.3-70b)**, **FastAPI**, **PostgreSQL**, and **Redis**.

Designed following Clean Architecture principles, this system performs deep static and semantic security evaluation of Python source code, enforces strict multi-tenant isolation guardrails, auto-refactors style/quality defects, and seamlessly posts automated code review comments directly on GitHub Pull Requests.

---

## 🌟 Key Features

- 🧠 **LangGraph Agentic Workflow**: Multi-step stateful decision graph. Automatically routes code through specialized security audit, emergency alert, and auto-refactoring nodes based on severity evaluation.
- 🛡️ **Strict Guardrail Rules**:
  - **Multi-Tenant Isolation**: Ensures tenant-id checks in cache keys and database queries.
  - **OWASP Top 10 & Secrets**: Detects hardcoded secrets, API tokens, and SQL Injection risks.
  - **Timezone Enforcement**: Flags naive `datetime` usages in favor of timezone-aware UTC datetime.
- ⚡ **High-Performance Redis Caching**: Computes SHA-256 hashes of input source code. Instantaneous sub-millisecond cache hits for unchanged files without incurring LLM cost/latency.
- 📊 **PostgreSQL Audit Trail**: Persists structured Pydantic analysis reports into PostgreSQL using SQLAlchemy 2.0 async engine and `asyncpg`.
- 🔗 **Automated GitHub Webhook Integration**: Listens to GitHub PR events (`opened`, `synchronize`), verifies HMAC SHA-256 signatures, evaluates changed `.py` files, and posts formatted Markdown review comments on PRs.
- 🐳 **Production-Grade Dockerization**: Multi-stage Docker build optimized with `uv` and standard `docker-compose` setup bringing up FastAPI, PostgreSQL 16, and Redis 7.

---

## 📐 Architecture & Agentic Workflow

```
                        ┌─────────────────────────────────────┐
                        │      HTTP POST / GitHub Webhook     │
                        └──────────────────┬──────────────────┘
                                           │
                                           ▼
                        ┌─────────────────────────────────────┐
                        │    SHA-256 Code Hash Verification    │
                        └──────────────────┬──────────────────┘
                                           │
                        ┌──────────────────┴──────────────────┐
                        │                                     │
                 [ Cache HIT ]                         [ Cache MISS ]
                        │                                     │
                        ▼                                     ▼
           ┌──────────────────────────┐      ┌──────────────────────────────────┐
           │ Return Cached JSON Report│      │  Execute LangGraph StateGraph   │
           └──────────────────────────┘      └────────────────┬─────────────────┘
                                                              │
                                                              ▼
                                                   ┌──────────────────────┐
                                                   │     analyze_node     │
                                                   │ (Groq Guardrail LLM) │
                                                   └──────────┬───────────┘
                                                              │
                                                  [ Conditional Routing ]
                                                              │
                                    ┌─────────────────────────┼─────────────────────────┐
                                    │                         │                         │
                                    ▼                         ▼                         ▼
                        (Critical/High Security)    (Style/Minor Findings)        (100% Safe)
                                    │                         │                         │
                                    ▼                         ▼                         ▼
                        ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
                        │ security_report_node │  │  auto_refactor_node  │  │  final_report_node   │
                        └──────────┬───────────┘  └──────────┬───────────┘  └──────────┬───────────┘
                                   │                         │                         │
                                   └─────────────────────────┼─────────────────────────┘
                                                             │
                                                             ▼
                                                ┌──────────────────────────┐
                                                │   PostgreSQL + Redis     │
                                                │ Persistence & Cache Sync │
                                                └──────────────────────────┘
```

---

## 🛠️ Technology Stack

- **Core Framework**: FastAPI, Pydantic v2, Python 3.11+
- **Agent Orchestration**: LangGraph, LangChain Core
- **LLM Engine**: Groq API (`llama-3.3-70b-versatile`)
- **Database Layer**: PostgreSQL 16, SQLAlchemy 2.0 (Async), `asyncpg`
- **Caching Layer**: Redis 7, `redis.asyncio`
- **Tooling & Package Manager**: `uv` (Fast Rust-based Python package manager)
- **Containerization**: Docker Multi-stage, Docker Compose

---

## 📁 Directory Structure (Clean Architecture)

```
agentic-code-reviewer/
├── src/
│   └── code_reviewer/
│       ├── agent/
│       │   └── workflow.py       # LangGraph state graph & conditional routing
│       ├── api/
│       │   ├── app.py            # Health check router
│       │   └── router.py         # /review & /webhook/github REST endpoints
│       ├── core/
│       │   ├── config.py         # Pydantic Settings configuration
│       │   └── schemas.py        # Finding & CodeReviewReport Pydantic models
│       ├── db/
│       │   ├── models.py         # SQLAlchemy 2.0 ORM DB models
│       │   └── session.py        # Async Database session & table initializer
│       ├── services/
│       │   ├── analyzer.py       # Core CodeAnalyzer orchestrator
│       │   ├── cache.py          # Redis caching service with SHA-256 hash
│       │   └── github.py         # Webhook HMAC verification & PR commenting
│       └── main.py               # FastAPI entrypoint with Lifespan manager
├── Dockerfile                    # Multi-stage production Docker build
├── docker-compose.yml            # Services orchestration (App, Postgres, Redis)
├── pyproject.toml                # Dependencies & project configuration
└── README.md                     # Showcase documentation
```

---

## ⚙️ Quick Start Guide

### Prerequisites
- Python 3.11+
- `uv` package manager (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Groq API Key ([Get one here](https://console.groq.com/))

### 1. Environment Setup
Create a `.env` file in the project root:
```env
PROJECT_NAME="Agentic Code Reviewer & Guardrail Evaluator"
DEBUG=True
GROQ_API_KEY="your_groq_api_key_here"

# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=code_reviewer_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# GitHub Integration (Optional for Webhooks)
GITHUB_TOKEN="your_github_personal_access_token"
GITHUB_WEBHOOK_SECRET="your_webhook_secret"
```

### 2. Local Installation with `uv`
```bash
# Install dependencies into virtual environment
uv sync

# Run database & redis locally or via docker-compose (see below)
# Start FastAPI application
uv run python -m code_reviewer.main
```

FastAPI Interactive Swagger Docs will be available at: `http://localhost:8000/docs`

---

## 🐳 Docker Deployment

To launch the complete enterprise environment (FastAPI + PostgreSQL + Redis) with a single command:

```bash
# Build and launch all containers
docker-compose up --build -d

# Check service logs
docker-compose logs -f app
```

---

## 💡 API Usage Examples

### 1. Analyze Code Endpoint (`POST /api/v1/review`)

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/review" \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "user_service.py",
    "code_content": "import datetime\nfrom sqlalchemy import text\n\ndef get_user_data(db, tenant_id, user_id):\n    # Vulnerable to SQL Injection and naive datetime\n    query = text(f\"SELECT * FROM users WHERE user_id = {user_id}\")\n    now = datetime.datetime.now()\n    return db.execute(query).fetchall()\n"
  }'
```

**Response (`200 OK` - Pydantic JSON Report):**
```json
{
  "file_name": "user_service.py",
  "is_secure": false,
  "summary": "🚨 [ACİL GÜVENLİK UYARISI] Kodda OWASP SQL Injection ve Multi-tenant eksikliği tespit edilmiştir.",
  "findings": [
    {
      "vulnerability_type": "OWASP SQLi",
      "severity": "CRITICAL",
      "line_number": 6,
      "description": "Raw string formatting used in SQL query parameter leading to SQL Injection.",
      "suggested_fix": "query = text('SELECT * FROM users WHERE tenant_id = :tenant_id AND user_id = :user_id')\ndb.execute(query, {'tenant_id': tenant_id, 'user_id': user_id})"
    },
    {
      "vulnerability_type": "Naive Datetime",
      "severity": "MEDIUM",
      "line_number": 7,
      "description": "Usage of naive datetime.datetime.now() without UTC timezone.",
      "suggested_fix": "from datetime import datetime, timezone\nnow = datetime.now(timezone.utc)"
    }
  ]
}
```

---

### 2. File Upload Endpoint (`POST /api/v1/review/file`)

Directly upload a `.py` file via Multipart Form-Data (compatible with Swagger UI):

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/review/file" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_security_risk.py;type=text/x-python"
```

### 2. GitHub Webhook Setup (`POST /api/v1/webhook/github`)

1. Forward your local endpoint using `ngrok` or `smee.io`:
   ```bash
   ngrok http 8000
   ```
2. In your GitHub Repository Settings ➔ Webhooks ➔ **Add Webhook**:
   - **Payload URL**: `https://your-ngrok-url.ngrok-free.app/api/v1/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: Set your `GITHUB_WEBHOOK_SECRET`
   - **Events**: Select **Pull requests**
3. Create or update a Pull Request containing Python files. The agent will automatically evaluate modified code and publish a rich Markdown review report on the PR!

---

## 🧪 Testing

Run tests using pytest:
```bash
uv run pytest
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more details.
