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
- **Orchestrated Pipeline via LangGraph**: The retrieval and analysis steps are modeled as a `StateGraph`, making the workflow explicit and extensible.
- **Audit Logging**: Every compliance check is persisted to PostgreSQL with the input text, risk level, issues (stored as JSONB), and suggested rewrite — enabling full auditability.
- **REST API**: FastAPI backend exposes endpoints for policy upload, compliance checking, log retrieval, and system health.
- **React Frontend**: A multi-page UI with a compliance check form, policy upload interface, audit history table, and a dashboard with risk distribution charts (Recharts).
- **Health Monitoring**: A `/health/` endpoint verifies both PostgreSQL connectivity and Pinecone index availability, returning 503 on failure.

---

## Architecture

### Pipeline

```
User Input (draft text)
        │
        ▼
[ FastAPI: POST /compliance/check ]
        │
        ▼
[ LangGraph: StateGraph ]
   │
   ├─ Node 1: query_policy_chunks
   │    └─ Embed input text (OpenAI text-embedding-3-small)
   │    └─ Query Pinecone index (top-k, with metadata filters)
   │    └─ Concatenate retrieved chunk texts into context
   │
   └─ Node 2: analyze_and_rewrite
        └─ Prompt gpt-4.1-mini with draft + policy context
        └─ Parse structured JSON response
        └─ Return: overall_risk, issues[], suggested_text
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
| **LangGraph** | Orchestrates the two-step retrieve → analyze workflow |
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
- LangGraph (workflow orchestration)
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

**Infrastructure / Tooling**
- PostgreSQL (local or hosted)
- Pinecone (hosted vector DB)
- OpenAI API

---

## How It Works: Example Flow

**Scenario**: A user wants to check whether a draft employee communication about remote work complies with the company's HR and data privacy policies.

1. **Policy Upload**: An HR manager previously uploaded `remote_work_policy.pdf` and `data_privacy_policy.pdf` via the Policies page. The backend extracted, chunked, and indexed these documents.

2. **Compliance Check**: The user pastes a draft message into the Check page, selects `HR` as the department, and submits.

3. **Retrieval**: The draft text is embedded and queried against Pinecone with a `department=HR` metadata filter. The top 5 most semantically similar policy chunks are retrieved.

4. **LLM Analysis**: The retrieved chunks and the draft are sent to `gpt-4.1-mini` with a prompt instructing it to identify compliance issues, assign an overall risk level (`low`, `medium`, `high`), and produce a revised version of the text.

5. **Structured Response**: The LLM returns a JSON object matching the `ComplianceCheckResponse` schema. This is validated, returned to the client, and logged to PostgreSQL.

6. **Audit Trail**: The compliance check appears in the History page, filterable by department, risk level, and date. The Dashboard updates its risk distribution chart.

---

## Repository Structure

```
├── app/
│   ├── main.py                  # FastAPI app setup, CORS, router registration
│   ├── database.py              # SQLAlchemy engine, session factory
│   ├── models.py                # ORM models: PolicyDocument, PolicyChunk, ComplianceCheck
│   ├── schemas.py               # Pydantic DTOs for requests and responses
│   ├── agent_graph.py           # LangGraph StateGraph definition
│   ├── vectorstore.py           # Pinecone client, embed + upsert + query
│   ├── ingestion.py             # PDF extraction, chunking, DB + vector persistence
│   ├── routers_policies.py      # /policies/ endpoints (upload, list)
│   ├── routers_compliance.py    # /compliance/ endpoints (check, logs)
│   ├── routers_health.py        # /health/ endpoint (DB + Pinecone status)
│   └── tests/                   # pytest test suite
│
├── frontend/
│   ├── src/
│   │   ├── pages/               # Home, Check, Policies, History (React pages)
│   │   ├── components/          # Layout, RiskBadge, UI primitives
│   │   └── lib/api.ts           # Fetch client for FastAPI endpoints
│   ├── package.json
│   └── vite.config.js
│
└── storage/policies/            # Runtime PDF storage (gitignored)
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL database (local or hosted)
- Pinecone account with an index created
- OpenAI API key

### Backend Setup

```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies (no requirements.txt yet — see Current Status)
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic pydantic-settings \
    openai langgraph pinecone PyMuPDF pytest httpx
```

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/compliance_db
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=your-index-name
```

```bash
# Start the backend
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Tables are created automatically on startup via `Base.metadata.create_all`.

### Frontend Setup

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

## Current Status

This is a **working prototype** focused on validating the core pipeline: policy ingestion, semantic retrieval, LLM-based compliance evaluation, and audit logging. The primary data flow is functional end-to-end.

**Implemented:**
- Full ingestion pipeline (PDF → chunks → PostgreSQL + Pinecone)
- LangGraph workflow with retrieval and LLM analysis nodes
- Compliance check API with structured output validation and audit logging
- Policy and compliance log REST endpoints
- React frontend with check form, policy list, audit history, and dashboard charts
- System health endpoint covering both DB and vector store

**Not yet complete:**
- No `requirements.txt` or `pyproject.toml` — dependency management is manual
- No Docker or deployment configuration
- No `.env.example` — environment setup is undocumented in the repo
- An auto-classify feature (`classify_context_with_llm`) is implemented but not connected to any route

---

## Future Improvements

1. **Dependency management**: Add `requirements.txt` or `pyproject.toml` with pinned versions for reproducible installs.
2. **Deployment**: Containerize with Docker and Docker Compose (FastAPI + PostgreSQL); add a deployment target (Railway, Render, or AWS ECS).
3. **Evaluation framework**: Add offline evaluation of LLM compliance decisions using labeled examples to measure accuracy and calibrate risk thresholds.
4. **Multi-branch LangGraph workflow**: Extend the graph to support routing (e.g., auto-classify policy type, run domain-specific sub-checks, handle ambiguous cases with a fallback node).
5. **Authentication and multi-tenancy**: Add user authentication and department-scoped policy namespaces so different teams manage their own policy sets independently.
6. **Streaming responses**: Use OpenAI streaming and Server-Sent Events to surface partial LLM output to the UI progressively, improving perceived latency on longer documents.
