# LogicVault — Prototype Specification
> A living knowledge graph for software project reasoning, decisions, and institutional memory.

---

## Project Overview

**LogicVault** solves the institutional knowledge loss problem in software teams. When developers leave, join, or avoid "dumb questions," critical reasoning about *why* the software was built a certain way disappears. LogicVault captures, stores, and serves that reasoning layer — the layer that GitHub, Gitea Issues, and tickets never cover.

**Team:** Muhammad Umar (23I-0782), Muhammad Usman Al Haq (23I-0585), Shahmeer Atif (23I-0711)  
**University:** FAST NUCES, Islamabad  

**Goal for this prototype:** Demonstrate that the core system is implementable and feasible. The prototype must show: (1) knowledge ingestion from multiple sources, (2) storage in a knowledge graph, (3) AI chat grounded in that graph, and (4) invalidation flagging when code changes touch existing decisions.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        LogicVault                               │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   Ingestion  │    │  Knowledge   │    │   Chat / Query   │  │
│  │    Layer     │───▶│    Graph     │◀───│    Interface     │  │
│  │  (Agents)    │    │  (Neo4j)     │    │  (React + Groq)  │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│         │                   │                                   │
│         ▼                   ▼                                   │
│  ┌──────────────┐    ┌──────────────┐                          │
│  │    Gitea     │    │  Invalidation│                          │
│  │  Webhooks    │    │   Engine     │                          │
│  └──────────────┘    └──────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

**Four Layers:**
1. **Ingestion Layer** — Pulls data from Gitea, documents, tickets, and manual entries
2. **Knowledge Graph** — Neo4j AuraDB Free (cloud-hosted) stores nodes and reasoning edges
3. **AI Query Layer** — Groq API (free tier, llama-3.3-70b) answers questions grounded in the graph
4. **Chat Interface** — React standalone web app, the primary user-facing product

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend API | FastAPI (Python) | Fast, async, great for agent workers |
| Knowledge Graph DB | Neo4j AuraDB Free | Cloud-hosted, free, native graph queries |
| LLM | Groq API — llama-3.3-70b | Free tier, 70B model, fast inference |
| Git + Issues | Gitea (self-hosted on remote VM) | Free self-hosted, full API access |
| Frontend | React + Tailwind CSS | Component-based, easy to build chat UI |
| Document Parsing | LangChain document loaders | PDF, DOCX, plain text ingestion |
| Auth | Gitea OAuth2 | Reuse existing Gitea accounts |
| Deployment | Remote VM (backend) + Vercel/Netlify (frontend) | Free hosting |
| Environment | Python 3.11+, Node 18+ | Standard |

---

## Repository Structure

```
logicvault/
├── backend/
│   ├── main.py                    # FastAPI app entrypoint
│   ├── config.py                  # Env vars, settings
│   ├── requirements.txt
│   │
│   ├── graph/
│   │   ├── neo4j_client.py        # Neo4j AuraDB connection wrapper
│   │   ├── schema.py              # Node/edge type definitions
│   │   ├── queries.py             # Cypher query library
│   │   └── invalidation.py        # Invalidation detection logic
│   │
│   ├── agents/
│   │   ├── base_agent.py          # Abstract base class for agents
│   │   ├── document_agent.py      # Ingests uploaded docs/transcripts
│   │   ├── gitea_agent.py         # Pulls commits, PRs, issues from Gitea
│   │   ├── code_agent.py          # Analyzes code files, extracts component summaries
│   │   └── decision_agent.py      # Processes manual decision entries
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chat.py            # POST /chat — AI query endpoint
│   │   │   ├── decisions.py       # CRUD for decision nodes
│   │   │   ├── graph.py           # GET graph data for visualization
│   │   │   ├── ingest.py          # POST /ingest — trigger ingestion
│   │   │   └── webhooks.py        # POST /webhook/gitea — Gitea webhook receiver
│   │   └── middleware.py          # Auth middleware
│   │
│   └── services/
│       ├── groq_service.py        # Groq API wrapper
│       └── context_builder.py     # Builds context from graph for LLM prompts
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Chat.jsx           # Main AI chat interface
│   │   │   ├── Graph.jsx          # Knowledge graph visualization
│   │   │   ├── Decisions.jsx      # Browse/add decision entries
│   │   │   ├── Ingest.jsx         # Upload documents, trigger ingestion
│   │   │   └── Alerts.jsx         # Invalidation alerts dashboard
│   │   │
│   │   ├── components/
│   │   │   ├── ChatMessage.jsx    # Individual chat bubble
│   │   │   ├── DecisionCard.jsx   # Decision node display card
│   │   │   ├── AlertBanner.jsx    # Invalidation alert component
│   │   │   ├── GraphViewer.jsx    # Neo4j graph visualization (vis.js or react-force-graph)
│   │   │   ├── FileUploader.jsx   # Drag-and-drop document upload
│   │   │   └── Sidebar.jsx        # Navigation sidebar
│   │   │
│   │   ├── hooks/
│   │   │   ├── useChat.js         # Chat state and API calls
│   │   │   └── useGraph.js        # Graph data fetching
│   │   │
│   │   └── api/
│   │       └── client.js          # Axios API client, base URL config
│   │
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
│
├── .env.example                   # All required env vars listed here
├── docker-compose.yml             # Optional: run backend locally
└── README.md
```

---

## Environment Variables

Create a `.env` file in `backend/` based on `.env.example`:

```env
# Neo4j AuraDB (get from aura.neo4j.io free tier)
NEO4J_URI=neo4j+s://<your-aura-instance>.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<your-aura-password>

# Groq API (get from console.groq.com — free)
GROQ_API_KEY=<your-groq-api-key>
GROQ_MODEL=llama-3.3-70b-versatile

# Gitea (self-hosted on remote VM)
GITEA_BASE_URL=http://<your-vm-ip>:3000
GITEA_TOKEN=<gitea-personal-access-token>
GITEA_WEBHOOK_SECRET=<random-secret-string>

# App
SECRET_KEY=<random-string-for-jwt>
FRONTEND_URL=http://localhost:5173
```

---

## Knowledge Graph Schema

### Node Types

```cypher
// A software component (module, service, class, feature)
(:Component {
  id: string,              // UUID
  name: string,            // e.g., "AuthModule"
  type: string,            // "module" | "service" | "class" | "feature" | "api_endpoint"
  file_path: string,       // e.g., "src/auth/auth.service.ts"
  description: string,     // AI-generated or manually written summary
  language: string,        // "typescript" | "python" | etc.
  created_at: datetime,
  updated_at: datetime
})

// A human reasoning decision — the core of LogicVault
(:Decision {
  id: string,              // UUID
  title: string,           // Short label e.g., "PostgreSQL over MongoDB"
  reasoning: string,       // Full text of the why
  status: string,          // "active" | "invalidated" | "needs_review"
  source: string,          // "manual" | "document" | "ai_extracted"
  source_ref: string,      // File name, doc name, or "manual"
  created_by: string,      // Gitea username
  created_at: datetime,
  updated_at: datetime,
  invalidation_note: string  // Filled when status = "invalidated"
})

// A Gitea commit
(:Commit {
  id: string,              // Commit SHA
  message: string,
  author: string,
  timestamp: datetime,
  files_changed: [string]  // List of file paths changed
})

// A Gitea Issue or PR
(:Ticket {
  id: string,              // Gitea issue/PR number as string
  title: string,
  body: string,
  type: string,            // "issue" | "pull_request"
  status: string,          // "open" | "closed" | "merged"
  created_by: string,
  created_at: datetime,
  closed_at: datetime
})

// An ingested document (meeting transcript, Google Doc export, PDF)
(:Document {
  id: string,
  filename: string,
  file_type: string,       // "pdf" | "docx" | "txt" | "md"
  upload_date: datetime,
  processed: boolean,
  summary: string          // AI-generated summary
})
```

### Edge Types (Relationships)

```cypher
// Decision is about a Component
(:Decision)-[:ABOUT {confidence: float}]->(:Component)

// Component depends on another Component
(:Component)-[:DEPENDS_ON {description: string}]->(:Component)

// Decision was extracted from a Document
(:Decision)-[:EXTRACTED_FROM]->(:Document)

// Decision is linked to a Ticket
(:Decision)-[:REFERENCED_IN]->(:Ticket)

// Commit modified a Component
(:Commit)-[:MODIFIED]->(:Component)

// Commit invalidated a Decision (triggers needs_review flag)
(:Commit)-[:MAY_INVALIDATE {reason: string}]->(:Decision)

// Decision supersedes an older Decision
(:Decision)-[:SUPERSEDES]->(:Decision)

// Ticket is related to a Component
(:Ticket)-[:RELATES_TO]->(:Component)
```

---

## Agent Specifications

All agents inherit from `BaseAgent` and expose a single `run(payload)` method. They are triggered via API endpoints or webhooks, not on a scheduler. Keep agents stateless and independent.

### 1. DocumentAgent (`document_agent.py`)

**Trigger:** User uploads a file via `POST /ingest/document`

**Input:** File bytes + filename

**What it does:**
1. Parse the file using LangChain loaders (PDF → `PyPDFLoader`, DOCX → `Docx2txtLoader`, TXT/MD → plain read)
2. Split into chunks (1000 chars, 200 overlap) using `RecursiveCharacterTextSplitter`
3. Send chunks to Groq with this system prompt:
   ```
   You are extracting software decisions from a document.
   For each decision found, return JSON with: title, reasoning, related_components (list of component names mentioned).
   If no decisions are found in a chunk, return an empty list.
   Return ONLY valid JSON, no explanation.
   ```
4. For each extracted decision, create a `Decision` node in Neo4j with `source="document"`
5. Create a `Document` node and link decisions to it via `EXTRACTED_FROM`
6. Try to match `related_components` strings to existing `Component` nodes by name (fuzzy match), create `ABOUT` edges

**Output:** `{ decisions_created: int, document_id: string }`

---

### 2. GiteaAgent (`gitea_agent.py`)

**Trigger A:** `POST /ingest/gitea` (manual full sync for a repo)  
**Trigger B:** `POST /webhook/gitea` (real-time on push/PR events)

**Input:** Gitea repo owner + repo name (for manual sync) or webhook payload (for real-time)

**What it does — Commits:**
1. Fetch recent commits from Gitea API: `GET /repos/{owner}/{repo}/commits`
2. For each commit, create a `Commit` node
3. Fetch the diff: `GET /repos/{owner}/{repo}/git/commits/{sha}` — extract list of changed file paths
4. Match changed file paths to existing `Component` nodes (by `file_path` field)
5. Create `MODIFIED` edges between the commit and matched components
6. For each matched component, find all `Decision` nodes with `ABOUT` edges to it — set their status to `"needs_review"` and create `MAY_INVALIDATE` edges from the commit

**What it does — Issues/PRs:**
1. Fetch issues: `GET /repos/{owner}/{repo}/issues?type=issues`
2. Fetch PRs: `GET /repos/{owner}/{repo}/pulls`
3. Create `Ticket` nodes for each
4. Use Groq to extract any mentioned component names from ticket body, create `RELATES_TO` edges

**Gitea Webhook Handler:**
- On `push` event: run commit logic for the new commits in the payload
- On `pull_request` event (merged): run PR logic

---

### 3. CodeAgent (`code_agent.py`)

**Trigger:** `POST /ingest/code` with a repo reference

**Input:** Gitea repo owner + repo name

**What it does:**
1. Fetch the repo file tree: `GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=true`
2. Filter to code files only (`.py`, `.ts`, `.js`, `.java`, `.go`, `.cs` — configure which languages are active)
3. For each file (limit to files under 500 lines for the prototype — skip very large files):
   - Fetch file content: `GET /repos/{owner}/{repo}/raw/{filepath}`
   - Send to Groq with this prompt:
     ```
     Analyze this code file and return JSON:
     {
       "component_name": "short name for this module/class/service",
       "component_type": "module|service|class|feature|api_endpoint",
       "description": "1-2 sentence summary of what this does",
       "dependencies": ["list of other component names or modules this depends on"]
     }
     Return ONLY valid JSON.
     ```
4. Create or update `Component` nodes in Neo4j
5. Create `DEPENDS_ON` edges based on the `dependencies` list — match by component name

**Rate limiting note:** Add a 0.5s delay between Groq calls to stay within free tier limits. For the prototype, process a maximum of 50 files per run.

---

### 4. DecisionAgent (`decision_agent.py`)

**Trigger:** `POST /decisions` (user manually submits a decision from the UI)

**Input:** `{ title, reasoning, related_component_names: [], linked_ticket_ids: [] }`

**What it does:**
1. Create a `Decision` node with `source="manual"`, `status="active"`
2. Match `related_component_names` to existing `Component` nodes, create `ABOUT` edges
3. Match `linked_ticket_ids` to existing `Ticket` nodes, create `REFERENCED_IN` edges
4. Return the created decision node

---

## API Endpoints

### Chat

```
POST /api/chat
Body: { message: string, conversation_history: [{role, content}] }

Response: { reply: string, sources: [{type, id, title}] }
```

**How the chat endpoint works:**
1. Take the user's message
2. Use Groq to extract key entities (component names, decision topics) from the message
3. Query Neo4j: find `Component` and `Decision` nodes matching those entities
4. For each matched node, fetch its connected nodes (1-hop neighborhood)
5. Build a context string: format matched decisions and components as text
6. Send to Groq with system prompt:
   ```
   You are LogicVault, an AI assistant that answers questions about a software project.
   You have access to the project's knowledge graph which contains decisions, components, and their reasoning.
   
   KNOWLEDGE GRAPH CONTEXT:
   {context}
   
   Rules:
   - Only answer based on the provided context
   - If the context does not contain enough information, say so clearly
   - Always cite which Decision or Component your answer is based on
   - If a Decision has status "needs_review" or "invalidated", warn the user
   - Be direct and technical
   ```
7. Return the reply + source node references

---

### Decisions

```
GET    /api/decisions               # List all decisions (filter by status, component)
POST   /api/decisions               # Create a new decision manually
GET    /api/decisions/{id}          # Get single decision with full graph context
PATCH  /api/decisions/{id}          # Update decision (status, reasoning)
DELETE /api/decisions/{id}          # Delete decision
POST   /api/decisions/{id}/invalidate  # Mark as invalidated with a note
```

### Graph

```
GET /api/graph/overview             # All nodes + edges (paginated, limit 200 nodes for UI)
GET /api/graph/component/{id}       # Single component with its full neighborhood
GET /api/graph/decision/{id}        # Single decision with its full neighborhood
```

### Ingestion

```
POST /api/ingest/document           # Upload file, run DocumentAgent
POST /api/ingest/gitea              # Trigger full Gitea sync for a repo
POST /api/ingest/code               # Trigger CodeAgent for a repo
```

### Webhooks

```
POST /api/webhook/gitea             # Gitea webhook receiver (validate HMAC signature)
```

### Alerts

```
GET /api/alerts                     # Decisions with status "needs_review"
POST /api/alerts/{decision_id}/acknowledge   # Mark as reviewed (set back to "active")
```

---

## Frontend Pages

### 1. Chat Page (`/chat`) — PRIMARY PAGE

This is the hero feature. Design it like a clean developer chat tool (think Cursor's chat panel).

**Layout:**
- Left sidebar: navigation + recent conversations list
- Main area: chat messages
- Bottom: message input with Send button

**Features:**
- Send messages, receive AI replies
- Each reply shows "Sources" collapsed section — click to see which Decision/Component nodes were used
- If a source has `status: "needs_review"`, show a yellow warning badge on it: "⚠ This decision may be outdated"
- If a source has `status: "invalidated"`, show red badge: "✗ This decision has been invalidated"
- Conversation history maintained in component state (sent with each request)
- New chat button resets history

---

### 2. Knowledge Graph Page (`/graph`)

**Visual graph visualization** using `react-force-graph-2d` (free, npm package).

**Node colors:**
- Blue: Component nodes
- Green: Decision nodes (active)
- Yellow: Decision nodes (needs_review)
- Red: Decision nodes (invalidated)
- Gray: Commit nodes
- Purple: Ticket nodes

**Interactions:**
- Click a node → opens a side panel with full details
- Hover → shows name tooltip
- Filter by node type using checkboxes
- Search bar to highlight matching nodes

**Side panel on click:**
- Shows all fields of the node
- For Decision nodes: shows status, reasoning, related components
- "Chat about this" button → opens Chat page with the node's name pre-filled as context

---

### 3. Decisions Page (`/decisions`)

A list/table view of all Decision nodes.

**Features:**
- Table columns: Title, Status (badge), Related Components, Source, Created At
- Filter by status: All / Active / Needs Review / Invalidated
- Search by title or reasoning text
- Click a decision → open detail view (full reasoning, graph connections, history)
- "Add Decision" button → opens a form modal:
  - Title (text input)
  - Reasoning (textarea — large)
  - Related Components (multi-select from existing component names)
  - Linked Tickets (multi-select from existing ticket IDs + titles)
- On a decision detail: "Invalidate" button → asks for invalidation note → sets status

---

### 4. Ingest Page (`/ingest`)

**Two sections:**

**Section A — Upload Document:**
- Drag-and-drop file uploader (PDF, DOCX, TXT, MD)
- Shows upload progress
- After processing: shows how many decisions were extracted

**Section B — Gitea Sync:**
- Input: Gitea repo URL or owner/repo fields
- Buttons: "Sync Commits & Issues", "Analyze Code"
- Shows last sync timestamp
- Progress indicator while running

---

### 5. Alerts Page (`/alerts`)

Shows all decisions with `status: "needs_review"`.

**For each alert:**
- Decision title + reasoning preview
- Which commit triggered the flag + which files changed
- Which component is the link
- Buttons: "View Full Decision", "Mark as Reviewed", "Invalidate"

Badge count in sidebar navigation showing number of unreviewed alerts.

---

## Neo4j Connection (`neo4j_client.py`)

```python
from neo4j import GraphDatabase

class Neo4jClient:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
```

Use this client as a singleton (initialize once in `main.py`, pass via dependency injection in FastAPI).

---

## Groq Service (`groq_service.py`)

```python
from groq import Groq

class GroqService:
    def __init__(self, api_key, model="llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model

    def chat(self, messages: list, system_prompt: str = None, max_tokens: int = 1500) -> str:
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=0.3
        )
        return response.choices[0].message.content

    def extract_json(self, prompt: str, max_tokens: int = 800) -> str:
        """For agent extraction tasks — returns raw string, caller parses JSON."""
        return self.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
```

---

## Context Builder (`context_builder.py`)

This is critical — it builds the prompt context from graph data.

```python
def build_context_for_query(query: str, neo4j_client, groq_service) -> tuple[str, list]:
    """
    1. Extract entities from the user query using Groq
    2. Find matching nodes in Neo4j
    3. Fetch 1-hop neighborhood for each match
    4. Format as readable context text
    Returns: (context_string, source_nodes_list)
    """
    
    # Step 1: Extract what the user is asking about
    entity_extraction_prompt = f"""
    Extract component names, module names, or decision topics from this query.
    Return JSON: {{"entities": ["name1", "name2"]}}
    Query: {query}
    """
    # ... parse entities
    
    # Step 2: Cypher queries to find relevant nodes
    component_query = """
    MATCH (c:Component)
    WHERE toLower(c.name) CONTAINS toLower($name) 
       OR toLower(c.file_path) CONTAINS toLower($name)
    OPTIONAL MATCH (d:Decision)-[:ABOUT]->(c)
    OPTIONAL MATCH (c)-[:DEPENDS_ON]->(dep:Component)
    RETURN c, collect(d) as decisions, collect(dep) as dependencies
    LIMIT 5
    """
    
    decision_query = """
    MATCH (d:Decision)
    WHERE toLower(d.title) CONTAINS toLower($name)
       OR toLower(d.reasoning) CONTAINS toLower($name)
    OPTIONAL MATCH (d)-[:ABOUT]->(c:Component)
    RETURN d, collect(c) as components
    LIMIT 5
    """
    
    # Step 3: Format context
    # Return structured text + source list for citation in UI
```

---

## Invalidation Logic (`invalidation.py`)

Called by GiteaAgent after processing a commit.

```python
def check_invalidation(commit_sha: str, changed_files: list, neo4j_client):
    """
    For each changed file:
    1. Find Component nodes with matching file_path
    2. For each component, find all ACTIVE Decision nodes linked via ABOUT
    3. Set those decisions to status="needs_review"
    4. Create MAY_INVALIDATE edge from Commit to Decision
    """
    
    for file_path in changed_files:
        # Find component by file path
        query = """
        MATCH (c:Component {file_path: $file_path})
        MATCH (d:Decision)-[:ABOUT]->(c)
        WHERE d.status = 'active'
        SET d.status = 'needs_review', d.updated_at = datetime()
        WITH d
        MATCH (commit:Commit {id: $commit_sha})
        MERGE (commit)-[:MAY_INVALIDATE {reason: 'file modified: ' + $file_path}]->(d)
        RETURN d.id as decision_id, d.title as title
        """
        results = neo4j_client.run_query(query, {
            "file_path": file_path,
            "commit_sha": commit_sha
        })
        # Return list of flagged decisions for logging
```

---

## Gitea Webhook Setup Instructions

In your Gitea repository settings → Webhooks → Add Webhook:
- **Target URL:** `http://<your-vm-ip>:<backend-port>/api/webhook/gitea`
- **Content Type:** `application/json`
- **Secret:** matches `GITEA_WEBHOOK_SECRET` in your `.env`
- **Trigger events:** Push, Pull Request

In the webhook handler, validate the HMAC-SHA256 signature from the `X-Gitea-Signature` header before processing.

---

## Neo4j Setup (AuraDB Free)

1. Go to [aura.neo4j.io](https://aura.neo4j.io)
2. Create a free AuraDB instance (Free tier: 50k nodes, 175k relationships — sufficient for prototype)
3. Copy the connection URI, username, and password into `.env`
4. Run the schema initialization script on first boot:

```cypher
-- Create indexes for fast lookups (run once)
CREATE INDEX component_name IF NOT EXISTS FOR (c:Component) ON (c.name);
CREATE INDEX component_file IF NOT EXISTS FOR (c:Component) ON (c.file_path);
CREATE INDEX decision_status IF NOT EXISTS FOR (d:Decision) ON (d.status);
CREATE INDEX commit_sha IF NOT EXISTS FOR (c:Commit) ON (c.id);
CREATE INDEX ticket_id IF NOT EXISTS FOR (t:Ticket) ON (t.id);
```

---

## FastAPI App Entrypoint (`main.py`)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings
from graph.neo4j_client import Neo4jClient
from services.groq_service import GroqService
from api.routes import chat, decisions, graph, ingest, webhooks, alerts

# Shared service instances
neo4j_client: Neo4jClient = None
groq_service: GroqService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global neo4j_client, groq_service
    neo4j_client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    groq_service = GroqService(settings.GROQ_API_KEY)
    yield
    neo4j_client.close()

app = FastAPI(title="LogicVault API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(decisions.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
```

---

## Frontend API Client (`api/client.js`)

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: { 'Content-Type': 'application/json' }
});

export const chatAPI = {
  send: (message, history) => api.post('/chat', { message, conversation_history: history })
};

export const decisionsAPI = {
  list: (params) => api.get('/decisions', { params }),
  create: (data) => api.post('/decisions', data),
  get: (id) => api.get(`/decisions/${id}`),
  update: (id, data) => api.patch(`/decisions/${id}`, data),
  invalidate: (id, note) => api.post(`/decisions/${id}/invalidate`, { note })
};

export const graphAPI = {
  overview: () => api.get('/graph/overview'),
  component: (id) => api.get(`/graph/component/${id}`),
  decision: (id) => api.get(`/graph/decision/${id}`)
};

export const ingestAPI = {
  document: (formData) => api.post('/ingest/document', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  gitea: (owner, repo) => api.post('/ingest/gitea', { owner, repo }),
  code: (owner, repo) => api.post('/ingest/code', { owner, repo })
};

export const alertsAPI = {
  list: () => api.get('/alerts'),
  acknowledge: (id) => api.post(`/alerts/${id}/acknowledge`)
};
```

---

## Requirements (`backend/requirements.txt`)

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
python-dotenv==1.0.1
neo4j==5.20.0
groq==0.9.0
langchain==0.2.6
langchain-community==0.2.6
langchain-text-splitters==0.2.2
pypdf==4.2.0
python-docx==1.1.2
docx2txt==0.8
httpx==0.27.0
python-multipart==0.0.9
pydantic-settings==2.3.1
```

---

## Frontend `package.json` Dependencies

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.24.0",
    "axios": "^1.7.2",
    "react-force-graph-2d": "^1.25.5",
    "react-dropzone": "^14.2.3",
    "@heroicons/react": "^2.1.4"
  },
  "devDependencies": {
    "vite": "^5.3.1",
    "@vitejs/plugin-react": "^4.3.1",
    "tailwindcss": "^3.4.4",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.39"
  }
}
```

---

## Prototype Scope (What to Build First)

Build in this order — each milestone is a demo-able thing:

### Milestone 1 — Data Layer (Week 1-2)
- [ ] Neo4j AuraDB connected, schema initialized
- [ ] `neo4j_client.py` working with test queries
- [ ] Basic `Component` and `Decision` nodes can be created via Cypher
- [ ] FastAPI running with a health check endpoint

### Milestone 2 — Manual Decision Entry (Week 3-4)
- [ ] `DecisionAgent` working
- [ ] `POST /decisions` and `GET /decisions` endpoints working
- [ ] Basic React frontend with the Decisions page
- [ ] Can add and view decisions manually

### Milestone 3 — AI Chat (Week 5-6)
- [ ] `GroqService` and `context_builder.py` working
- [ ] `POST /chat` endpoint working
- [ ] React Chat page with message history
- [ ] AI answers questions based on manually entered decisions

### Milestone 4 — Document Ingestion (Week 7-8)
- [ ] `DocumentAgent` working
- [ ] File upload UI on Ingest page
- [ ] Meeting transcripts and docs automatically extract decisions

### Milestone 5 — Gitea Integration (Week 9-10)
- [ ] `GiteaAgent` working with Gitea API
- [ ] Commits, issues, PRs sync into graph
- [ ] `CodeAgent` analyzes code files and creates Component nodes

### Milestone 6 — Invalidation & Alerts (Week 11-12)
- [ ] Webhook receiver working
- [ ] Invalidation logic flags decisions on commit
- [ ] Alerts page shows flagged decisions
- [ ] Chat warns user when citing a "needs_review" decision

### Milestone 7 — Graph Visualization & Polish (Week 13-14)
- [ ] Graph visualization page working
- [ ] UI polish across all pages
- [ ] End-to-end demo flow working

---

## Demo Flow (For Supervisor Presentation)

1. Show an empty LogicVault for "Project X"
2. Upload a meeting transcript PDF — show decisions being extracted automatically
3. Add one manual decision: "We use JWT over sessions because the client wants a mobile app"
4. Sync Gitea repo — show components appearing in the graph
5. Open Graph page — visually show decisions linked to components
6. Open Chat — ask: "Why did we choose JWT?" → show AI answer citing the decision
7. Simulate a code change: push a commit that modifies the auth module
8. Open Alerts page — show the JWT decision is now flagged as "needs review"
9. Chat again about JWT — show the warning banner on the source

This 9-step flow proves every core feature works.

---

## Important Notes for the Agent Building This

1. **Keep agents simple and independent** — each agent does exactly one job, runs synchronously (no queues for the prototype), returns a result dict
2. **No authentication in the prototype** — skip JWT/OAuth for now, add a simple API key header check if needed, but don't block progress on auth
3. **Error handling matters** — Groq API calls can fail (rate limit). Wrap every Groq call in try/except. Log errors, don't crash
4. **Neo4j MERGE not CREATE** — use `MERGE` instead of `CREATE` for most nodes to avoid duplicates (Commits by SHA, Components by file_path, Tickets by id)
5. **The chat context window** — keep the context passed to Groq under 3000 tokens for the prototype. Limit graph traversal to 1 hop and max 10 nodes
6. **File upload size** — limit document uploads to 10MB in FastAPI settings
7. **Frontend state** — use React's built-in `useState` and `useEffect`. No Redux needed for this scale
8. **Graph visualization performance** — limit the overview graph to 200 nodes. Add a filter/search to reduce what's shown if the graph grows large
9. **Tailwind for styling** — use Tailwind utility classes throughout. Dark theme recommended (dark:bg-gray-900 etc.) — it looks professional for a dev tool
10. **CORS** — backend must have CORS configured for `http://localhost:5173` (Vite default) during development
