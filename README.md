# SMIT LangGraph Multi-Agent System

A complete, production-grade **LangGraph Multi-Agent System** featuring specialized sub-agents powered by **Supabase PostgreSQL + pgvector**, **Model Context Protocol (MCP)** over real stdio connections, **APScheduler** persistent SQLite job queue, and an intuitive **React + Vite** web interface.

---

## 🏛️ System Architecture

```
                             ┌───────────────────┐
                             │       USER        │
                             └─────────┬─────────┘
                                       │
                                       ▼
                             ┌───────────────────┐
                             │    LangGraph      │
                             │   Supervisor      │
                             └─────────┬─────────┘
                                       │
         ┌──────────────────┬──────────┴──────────┬──────────────────┐
         │                  │                     │                  │
         ▼                  ▼                     ▼                  ▼
  ┌──────────────┐   ┌──────────────┐      ┌──────────────┐   ┌──────────────┐
  │  RAG Agent   │   │ GitHub Agent │      │Calendar Agent│   │ Email Agent  │
  └──────┬───────┘   └──────┬───────┘      └──────┬───────┘   └──────┬───────┘
         │                  │                     │                  │
         ▼                  ▼                     ▼                  ▼
    [Supabase]         [GitHub MCP]        [Google Cal MCP]     [Email MCP]
 (PostgreSQL pgvector)  (stdio MCP)          (stdio MCP)        (stdio MCP)
                                                                     │
                                                                     ▼
                                                               [APScheduler]
                                                               (SQLite Store)
```

---

## 🧩 Implemented Modules & Capabilities

### 1. RAG Sub-Agent (`agents/rag_agent.py`)
- **Vector Store**: Hosted **Supabase PostgreSQL** with `pgvector` extension and HNSW indexing.
- **Embeddings**: Google Gemini `gemini-embedding-001` with explicit 768 dimensions (`vector(768)`).
- **Ingestion Pipeline**: Page-by-page extraction (`pypdf`), semantic chunking (`CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`), and batch indexing.
- **Strict Document Isolation**: Queries on Document A *never* cross-contaminate or retrieve chunks from Document B.
- **Anti-Hallucination**: If knowledge is absent from the retrieved chunks, the agent strictly replies: *"The information was not found in the document."*
- **Citations**: Returns exact page numbers, filenames, and excerpts in collapsible source citation cards.

### 2. GitHub MCP Sub-Agent (`agents/github_agent.py` & `mcp_tools/github.py`)
- **Protocol**: Real Model Context Protocol (MCP) server over `stdio` using official `@modelcontextprotocol/server-github`.
- **Read Capabilities**: Inspect repository details, commit histories, open pull requests, issues, and file contents (e.g. `octocat/Hello-World`).
- **Write Protection**: Any mutating operations (`create_issue`, etc.) are intercepted with **Human-in-the-Loop** confirmation cards.

### 3. Google Calendar MCP Sub-Agent (`agents/calendar_agent.py` & `mcp_tools/calendar.py`)
- **Protocol**: Real Model Context Protocol (MCP) server over `stdio` via `FastMCP` (`mcp_tools/calendar_server.py`).
- **Features**:
  - List upcoming events and inspect date ranges.
  - Natural language scheduling ("tomorrow at 3pm") resolved with the user's timezone (`Asia/Karachi`).
  - **Conflict Detection**: Checks for overlapping appointments before creating an event and warns the user.
  - Fallback local store (`local_calendar.json`) when Google OAuth credentials are not provided.

### 4. Email MCP Sub-Agent (`agents/email_agent.py` & `mcp_tools/email.py`)
- **Protocol**: Real Model Context Protocol (MCP) server over `stdio` via `FastMCP` (`mcp_tools/email_server.py`).
- **Features**:
  - Compose emails and drafts.
  - **Human-in-the-Loop (HITL)**: Direct sending is intercepted to require user confirmation.
  - **Persistent Scheduling**: Integrated with `APScheduler` backed by a SQLite persistent job store (`scheduled_emails.db`), surviving server restarts.
  - Sandbox local outbox (`local_email_outbox.json`) for safe verification.

### 5. LangGraph Supervisor (`supervisor.py`)
- **Orchestration**: StateGraph orchestrator that dynamically inspects conversation history, determines intent, routes to the appropriate worker, and chains multi-step queries (e.g. "Summarize the document, then email the summary").
- **Universal API**: Exposed via `POST /api/agent`.

---

## 📁 Directory Structure

```text
LangGraph Multi-Agent System/
│
├── .env                              # Active secrets (gemini, supabase, tokens)
├── .env.example                      # Template with all required settings
├── .gitignore                        # Protects credentials, virtual environments & dbs
├── requirements.txt                  # Python dependencies
├── scheduled_emails.db               # Persistent SQLite job store for APScheduler
├── local_calendar.json               # Local calendar persistent store
├── local_email_outbox.json           # Local email outbox store
│
├── agents/                           # Multi-Agent Implementations
│   ├── rag_agent.py                  # RAG sub-agent with pgvector & page citations
│   ├── github_agent.py               # GitHub MCP sub-agent
│   ├── calendar_agent.py             # Google Calendar MCP sub-agent
│   └── email_agent.py                # Email MCP sub-agent with HITL
│
├── mcp_tools/                        # Real MCP stdio Servers & Clients
│   ├── github.py                     # GitHub MCP client
│   ├── calendar.py                   # Calendar MCP client
│   ├── calendar_server.py            # Calendar FastMCP stdio server
│   ├── email.py                      # Email MCP client
│   └── email_server.py               # Email FastMCP stdio server (APScheduler)
│
├── rag/                              # Supabase pgvector RAG Pipeline
│   ├── schema.sql                    # Supabase SQL schema & match_documents RPC
│   ├── embeddings.py                 # Gemini embedding-001 (768 dim)
│   ├── supabase_vectorstore.py       # Supabase client & isolated retrieval
│   ├── ingest.py                     # PDF text extraction & chunking
│   └── retriever.py                  # Isolated document retriever
│
├── backend/                          # FastAPI Backend
│   ├── main.py                       # FastAPI entrypoint & router configuration
│   └── api/
│       ├── agent.py                  # POST /api/agent & GET /api/scheduled-emails
│       ├── upload.py                 # POST /api/upload
│       ├── chat.py                   # POST /api/chat
│       └── documents.py              # GET/DELETE /api/documents
│
├── frontend/                         # React + Vite Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx           # Agents status & Scheduled Emails trigger
│   │   │   ├── ChatWindow.jsx        # Universal chat with suggestions
│   │   │   ├── ChatMessage.jsx       # Agent badges, citations & HITL confirmation card
│   │   │   ├── PDFUploader.jsx       # Drag & drop upload to Supabase
│   │   │   └── ScheduledEmailsModal.jsx # Scheduled email queue management
│   │   ├── App.jsx                   # Main orchestration state
│   │   └── index.css                 # Dark-mode styling system
│   └── vite.config.js                # Reverse proxy /api -> 127.0.0.1:8000
│
├── supervisor.py                     # LangGraph Supervisor routing engine
├── state.py                          # AgentState definition
└── test_full_system_e2e.py           # 100% passing end-to-end test suite
```

---

## 🚀 Running the Project

### 1. Backend Server
In the project root:
```powershell
.\.venv\Scripts\activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Backend API will be running on `http://127.0.0.1:8000` (docs at `http://127.0.0.1:8000/docs`).

### 2. Frontend Development Server
In the `frontend/` directory:
```powershell
cd frontend
npm run dev
```
Frontend will be running on `http://localhost:5173`.

---

## 🧪 Verification & Automated Testing

A comprehensive integration test suite is provided in [`test_full_system_e2e.py`](file:///d:/SMIT/LangGraph%20Multi-Agent%20System/test_full_system_e2e.py). It tests all sub-agents through the live frontend Vite proxy:

```powershell
.\.venv\Scripts\python test_full_system_e2e.py
```

### Test Suite Results:
- **Test 1: Health & Config Verification** — Verified live connection to Google Gemini & Supabase pgvector.
- **Test 2: Supabase Documents Listing** — Verified retrieval of indexed documents from Supabase.
- **Test 3: RAG Sub-Agent Retrieval & Citations** — Verified isolated chunk matching with page numbers.
- **Test 4: RAG Anti-Hallucination Compliance** — Verified strict refusal when knowledge is absent.
- **Test 5: GitHub MCP Sub-Agent Execution** — Verified stdio connection to `@modelcontextprotocol/server-github` and file retrieval.
- **Test 6: Google Calendar MCP Sub-Agent Execution** — Verified event retrieval and natural language scheduling.
- **Test 7: Email MCP HITL & Scheduler Verification** — Verified interception of unconfirmed sends, confirmed dispatch, and persistent SQLite job store query.
- **Final Result**: **`7/7 TESTS PASSED (100% SUCCESS)`**
