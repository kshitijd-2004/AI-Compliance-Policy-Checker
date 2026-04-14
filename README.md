# AI Compliance Policy Checker

An LLM-powered system that evaluates draft text against organizational policies using retrieval-augmented generation (RAG), structured AI outputs, and a full-stack web interface.

---

## Overview

### What It Does

Organizations regularly produce internal documents — policies, contracts, communications — that must conform to regulatory, legal, or HR standards. Manually checking each document against a growing policy library is slow, inconsistent, and error-prone.

This system allows a user to upload policy documents (PDFs), then submit draft text for automated compliance evaluation. The system retrieves semantically relevant policy sections, sends them to an LLM alongside the draft, and returns a structured risk assessment with specific issues identified and a suggested rewrite.

### Why It Exists

Compliance review is a domain where LLMs can add immediate value: the task is text-intensive, the rules are well-defined (in policy documents), and the output needs to be structured and auditable. This project explores how to build that pipeline reliably — combining vector search for context retrieval, LangGraph for workflow orchestration, and PostgreSQL for persistent audit logging.

### Real-World Relevance

Similar pipelines are used in legal tech, enterprise governance tools, HR automation, and regulatory compliance platforms. The core pattern — ingest reference documents, retrieve relevant context, evaluate new content, log decisions — applies broadly across industries.

---

## Key Features

- **PDF Policy Ingestion**: Uploads PDF documents, extracts text using PyMuPDF, splits into overlapping chunks, and stores both relational records (PostgreSQL) and vector embeddings (Pinecone).
- **Semantic Retrieval**: Uses OpenAI `text-embedding-3-small` to embed query text and retrieve the most relevant policy chunks from Pinecone, optionally filtered by department or policy type.
- **LLM-Based Compliance Analysis**: Sends retrieved policy context and draft text to `gpt-4.1-mini` with a structured output contract, returning overall risk level, specific issues, and a suggested compliant rewrite.
- **Orchestrated Pipeline via LangGraph**: The classification, retrieval, and analysis steps are modeled as a `StateGraph` with conditional routing — the graph skips the LLM analysis node entirely when no relevant policy chunks are found.
- **Auto-Classification**: When a user doesn't specify department or policy type, an LLM-powered classification node infers them from the draft text before retrieval.
- **Audit Logging**: Every compliance check is persisted to PostgreSQL with the input text, risk level, issues (stored as JSONB), and suggested rewrite — enabling full auditability.
- **REST API**: FastAPI backend exposes endpoints for policy upload, compliance checking, log retrieval, and system health.
- **React Frontend**: A multi-page UI with a compliance check form, policy upload interface, audit history table, and a dashboard with risk distribution charts (Recharts).
- **Health Monitoring**: A `/health/` endpoint verifies both PostgreSQL connectivity and Pinecone index availability, returning 503 on failure.

---

## Architecture

### Compliance Pipeline (LangGraph StateGraph)

```
User Input (draft text, optional department/policy_type)
        │
        ▼
[ FastAPI: POST /compliance/check ]
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  LangGraph: StateGraph                              │
│                                                     │
│  Node 1: classify_content                           │
│    ├─ If department & policy_type provided → pass    │
│    └─ Otherwise → LLM infers them (gpt-4.1-mini)   │
│           │                                         │
│           ▼                                         │
│  Node 2: retrieve_policies                          │
│    └─ Embed input (text-embedding-3-small)          │
│    └─ Query Pinecone (top-k, metadata filters)      │
│    └─ Concatenate retrieved chunk texts              │
│           │                                         │
│           ▼                                         │
│  ┌── Conditional Edge ──┐                           │
│  │ matches found?       │                           │
│  │                      │                           │
│  ▼ YES                  ▼ NO                        │
│  Node 3a:               Node 3b:                    │
│  analyze_and_rewrite    no_context_response          │
│  └─ LLM compliance      └─ Return NONE risk,       │
│     review + rewrite       no issues (skip LLM)     │
│  │                      │                           │
│  └──────────┬───────────┘                           │
│             ▼                                       │
│            END                                      │
└─────────────────────────────────────────────────────┘
        │
        ▼
[ FastAPI: persist ComplianceCheck to PostgreSQL ]
        │
        ▼
Structured Response → Client
```

### Ingestion Pipeline

```
PDF Upload
    │
    ▼
PyMuPDF text extraction
    │
    ▼
Sliding window chunking (2000 chars, 200 overlap)
    │
    ├─ PolicyDocument + PolicyChunk rows → PostgreSQL
    │
    └─ Embed each chunk → Upsert to Pinecone (with metadata)
```

### Components

| Component | Role |
|-----------|------|
| **FastAPI** | REST API layer; request validation via Pydantic; routing |
| **LangGraph** | Orchestrates the classify → retrieve → analyze workflow with conditional routing |
| **OpenAI API** | Embeddings (`text-embedding-3-small`) and chat completion (`gpt-4.1-mini`) |
| **Pinecone** | Hosted vector database for semantic policy chunk retrieval |
| **PostgreSQL** | Relational store for policy documents, chunks, and compliance audit logs |
| **SQLAlchemy** | ORM for database models and session management |
| **PyMuPDF** | PDF text extraction during policy ingestion |
| **React + Vite** | Frontend SPA with page routing (wouter), data fetching (TanStack Query), and charts (Recharts) |

---

## Tech Stack

**Backend**
- Python, FastAPI, Uvicorn
- LangGraph (workflow orchestration with conditional edges)
- OpenAI Python SDK (embeddings + chat completions)
- Pinecone (vector search)
- SQLAlchemy + PostgreSQL
- PyMuPDF (`fitz`) for PDF parsing
- Pydantic + pydantic-settings
- pytest + Starlette TestClient

**Frontend**
- React 19, TypeScript, Vite 7
- Tailwind CSS 4, Radix UI primitives (shadcn-style)
- TanStack Query (server state), wouter (routing)
- Recharts (data visualization)

**Infrastructure**
- Docker + Docker Compose
- PostgreSQL (local or hosted)
- Pinecone (hosted vector DB)
- OpenAI API

---

## How It Works: Example Flow

**Scenario**: A user wants to check whether a draft employee communication about remote work complies with the company's HR and data privacy policies.

1. **Policy Upload**: An HR manager previously uploaded `remote_work_policy.pdf` and `data_privacy_policy.pdf` via the Policies page. The backend extracted, chunked, and indexed these documents.

2. **Compliance Check**: The user pastes a draft message into the Check page, selects `HR` as the department, and submits.

3. **Classification**: The LangGraph pipeline starts. Since the user provided a department, the classification node passes through. If neither department nor policy type were given, the LLM would auto-classify them.

4. **Retrieval**: The draft text is embedded and queried against Pinecone with a `department=HR` metadata filter. The top 5 most semantically similar policy chunks are retrieved.

5. **Conditional Routing**: The graph checks whether any policy chunks were returned. If retrieval found matches, the pipeline continues to LLM analysis. If not, it returns a clean "no issues" response without wasting an LLM call.

6. **LLM Analysis**: The retrieved chunks and the draft are sent to `gpt-4.1-mini` with a prompt instructing it to identify compliance issues, assign an overall risk level (`low`, `medium`, `high`), and produce a revised version of the text.

7. **Structured Response**: The LLM returns a JSON object matching the `ComplianceCheckResponse` schema. This is validated, returned to the client, and logged to PostgreSQL.

8. **Audit Trail**: The compliance check appears in the History page, filterable by department, risk level, and date. The Dashboard updates its risk distribution chart.

---

## Repository Structure

```
├── app/
│   ├── main.py                  # FastAPI app setup, CORS, router registration
│   ├── database.py              # SQLAlchemy engine, session factory
│   ├── models.py                # ORM models: PolicyDocument, PolicyChunk, ComplianceCheck
│   ├── schemas.py               # Pydantic DTOs for requests and responses
│   ├── get_db.py                # Shared database session dependency
│   ├── agent_graph.py           # LangGraph StateGraph with classify → retrieve → analyze
│   ├── vectorstore.py           # Pinecone client, embed + upsert + query
│   ├── ingestion.py             # PDF extraction, chunking, DB + vector persistence
│   ├── routers_policies.py      # /policies/ endpoints (upload, list, delete, download)
│   ├── routers_compliance.py    # /compliance/ endpoints (check, logs)
│   ├── routers_health.py        # /health/ endpoint (DB + Pinecone status)
│   └── tests/                   # pytest test suite
│       ├── conftest.py          # Test fixtures, SQLite override
│       ├── test_compliance.py   # Compliance check flow tests
│       ├── test_policies.py     # Policy upload + list tests
│       ├── test_logs.py         # Log filtering tests
│       ├── test_health.py       # Health endpoint tests
│       └── test_validation.py   # Schema validation tests
│
├── frontend/
│   ├── src/
│   │   ├── pages/               # Home, Check, Policies, History
│   │   ├── components/          # Layout, RiskBadge, UI primitives
│   │   └── lib/api.ts           # Typed fetch client for FastAPI endpoints
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── Dockerfile                   # Backend container
├── docker-compose.yml           # Full-stack: backend + PostgreSQL + frontend
├── requirements.txt             # Python dependencies with version ranges
├── .env.example                 # Required environment variables template
└── storage/policies/            # Runtime PDF storage (gitignored)
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL database (local or hosted)
- Pinecone account with an index created
- OpenAI API key

### Quick Start with Docker

```bash
# Copy and fill in your credentials
cp .env.example .env

# Start everything (backend + PostgreSQL + frontend)
docker compose up --build
```

The API will be available at `http://localhost:8000` and the frontend at `http://localhost:5173`.

### Manual Setup

**Backend:**

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your credentials

uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Tables are created automatically on startup via `Base.metadata.create_all`.

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API calls to `http://127.0.0.1:8000`.

### Running Tests

```bash
pytest app/tests/
```

---

## Future Improvements

1. **Evaluation framework**: Add offline evaluation of LLM compliance decisions using labeled examples to measure accuracy and calibrate risk thresholds.
2. **Streaming responses**: Use OpenAI streaming and Server-Sent Events to surface partial LLM output to the UI progressively, improving perceived latency on longer documents.
3. **Authentication and multi-tenancy**: Add user authentication and department-scoped policy namespaces so different teams manage their own policy sets independently.
4. **Extended graph routing**: Add domain-specific sub-checks (e.g., a dedicated PII detection node) and a fallback node for ambiguous cases.
