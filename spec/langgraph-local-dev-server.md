# LangGraph Local Dev Server POC

## Overview

Move from `langgraph dev` (in-memory, ephemeral state) to `langgraph up` (full LangGraph Platform server in Docker) with persistent Postgres checkpoints, Redis for streaming/background tasks, and the complete Platform API surface.

Two approaches are documented:
- **Approach A (Managed):** `langgraph up` manages all containers — simplest path
- **Approach B (Manual Infra):** You control Postgres/Redis via `docker-compose.yml`, `langgraph up` connects to them

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 langgraph up                     │
│                                                  │
│  ┌──────────────┐  ┌──────────┐  ┌───────────┐  │
│  │ LangGraph    │  │ Postgres │  │   Redis   │  │
│  │ API Server   │──│ (pgvec)  │  │           │  │
│  │ :8123        │  │ :5433    │  │ (internal)│  │
│  └──────────────┘  └──────────┘  └───────────┘  │
│        │                │                        │
│   Full Platform    Checkpoints &                 │
│   REST API         State Persistence             │
└─────────────────────────────────────────────────┘
```

**Components:**
- **LangGraph API Server** — Full Platform server exposing REST API (threads, runs, assistants, crons, streaming)
- **PostgreSQL 16 + pgvector** — Persistent storage for checkpoints, thread state, assistant configs
- **Redis 7** — Streaming support and background task queuing

---

## Prerequisites

- Docker Desktop (running)
- Python 3.12+
- `uv` package manager
- Valid `LANGSMITH_API_KEY` (required by `langgraph up` for local dev)
- Valid `OPENAI_API_KEY` (OpenRouter key in `sk-or-v1-...` format is supported)

---

## Files Modified

| File                 | Change                                                                  |
| -------------------- | ----------------------------------------------------------------------- |
| `src/agent/graph.py` | Replaced stub with real LLM call using `ChatOpenAI` + `MessagesState`   |
| `pyproject.toml`     | Added `langchain-openai>=0.3.0` dependency                              |
| `langgraph.json`     | Added `python_version: "3.12"`                                          |
| `docker-compose.yml` | Updated for Approach B: pgvector image, named volume, Redis healthcheck |

---

## Implementation Details

### Graph: `src/agent/graph.py`

The graph was rewritten from a hardcoded-response stub to a real chat agent:

- **State:** Uses `MessagesState` from `langgraph.graph` which provides `messages: Annotated[list[AnyMessage], add_messages]`. The `add_messages` reducer appends new messages rather than replacing — the standard LangGraph chat pattern.
- **LLM:** Uses `ChatOpenAI` from `langchain-openai` with `base_url="https://openrouter.ai/api/v1"` to route through OpenRouter. Reads `OPENAI_API_KEY` from environment automatically.
- **Runtime Context:** The `Context` TypedDict exposes `model_name` (default: `gpt-4o-mini`) and `system_prompt` (default: `"You are a helpful assistant."`) as configurable parameters. These can be set per-assistant via the Platform API.
- **Node function:** `call_model` prepends the system prompt, calls `await model.ainvoke(messages)`, and returns the AI response.

### Dependencies: `pyproject.toml`

Added `langchain-openai>=0.3.0` to core dependencies. This brings in the `ChatOpenAI` class that returns `AIMessage` objects directly compatible with `MessagesState`'s `add_messages` reducer.

### LangGraph Config: `langgraph.json`

Added `"python_version": "3.12"` to match the local Python version. Without this, the Docker image defaults to Python 3.11. The rest of the config is unchanged:
- `"dependencies": ["."]` — installs from `pyproject.toml` in the Docker build
- `"graphs": {"agent": "./src/agent/graph.py:graph"}` — registers the graph as assistant `"agent"`
- `"env": ".env"` — injects environment variables into the server container

### Docker Compose: `docker-compose.yml`

Updated for Approach B compatibility:
- **Postgres image:** Changed from `postgres:16` to `pgvector/pgvector:pg16` (LangGraph requires the pgvector extension)
- **Postgres command:** Added `shared_preload_libraries=vector`
- **Volume:** Added named volume `pgdata` for data persistence across container restarts
- **Redis healthcheck:** Added `redis-cli ping` healthcheck

---

## Startup Guide

### Approach A — Managed (Recommended for first run)

`langgraph up` auto-provisions all three containers. This is the simplest path.

**1. Install dependencies**

```bash
uv sync
```

**2. Stop any existing Docker containers (avoid port conflicts)**

```bash
docker compose down
```

**3. Start the full stack**

```bash
langgraph up
```

Wait for the "Ready!" message. The server will be at `http://localhost:8123`.

**What happens under the hood:**
- Builds a Docker image from your project using `langgraph.json`
- Starts 3 containers:
  - `langgraph-api` on port **8123** (the API server)
  - `langgraph-postgres` (pgvector/pg16) on port **5433** (not 5432, to avoid conflicts)
  - `langgraph-redis` (internal, not exposed to host)
- Injects all `.env` variables into the server container
- Postgres data is stored in a Docker named volume (`langgraph-data`) that **survives restarts**

**4. Stop the server**

Press `Ctrl+C` in the terminal.

> **Warning:** Do NOT use `langgraph up --recreate` unless you want to destroy all persisted data. That flag deletes the Postgres volume.

---

### Approach B — Manual Infrastructure

You control Postgres/Redis via your own `docker-compose.yml`. The LangGraph server connects to your external Postgres.

**1. Install dependencies**

```bash
uv sync
```

**2. Start Postgres**

```bash
docker compose up -d postgres
```

Wait for healthy status:

```bash
docker compose ps
# postgres should show "healthy"
```

**3. Start the LangGraph server with external Postgres**

```bash
langgraph up --postgres-uri "postgres://langgraph_user:secure_password@host.docker.internal:5432/langgraph_db?sslmode=disable"
```

**Networking note:** `host.docker.internal` resolves to the host machine from inside Docker containers on macOS Docker Desktop. The `langgraph up` container can reach your Postgres container through the host's port 5432.

**Redis note:** The CLI has `--postgres-uri` but no `--redis-uri` flag. When you provide `--postgres-uri`, it skips creating a managed Postgres but **still creates a managed Redis**. You don't need to start your own Redis container.

**4. Stop everything**

```bash
# Stop the LangGraph server
# Ctrl+C in the langgraph up terminal

# Stop Postgres
docker compose down
```

---

## Verification

After either approach, the server is at `http://localhost:8123`.

### 1. Health check

```bash
curl -s http://localhost:8123/ok
```

### 2. List assistants (proves full Platform API)

```bash
curl -s -X POST http://localhost:8123/assistants/search \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

Expected: Returns a list containing the `"agent"` assistant.

### 3. Create a thread

```bash
curl -s -X POST http://localhost:8123/threads \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

Save the returned `thread_id`.

### 4. Invoke the graph (real LLM call)

```bash
THREAD_ID="<paste-thread-id>"

curl -s -X POST "http://localhost:8123/threads/${THREAD_ID}/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [{"role": "user", "content": "What is LangGraph in one sentence?"}]
    }
  }' | python3 -m json.tool
```

Expected: Returns graph output with an AI message from OpenAI via OpenRouter.

### 5. Verify thread state

```bash
curl -s "http://localhost:8123/threads/${THREAD_ID}/state" | python3 -m json.tool
```

Expected: Returns the full conversation (user message + AI response).

### 6. Persistence proof — restart and verify

```bash
# Stop the server (Ctrl+C), then restart:
langgraph up

# Retrieve the same thread:
curl -s "http://localhost:8123/threads/${THREAD_ID}/state" | python3 -m json.tool
```

Expected: Same state as before — messages survived the restart.

### 7. Checkpoint continuity — follow-up message

```bash
curl -s -X POST "http://localhost:8123/threads/${THREAD_ID}/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [{"role": "user", "content": "Can you elaborate on that?"}]
    }
  }' | python3 -m json.tool
```

Expected: AI references the prior exchange, proving full message history was loaded from Postgres.

### 8. Additional Platform API demonstrations

**List threads:**
```bash
curl -s -X POST http://localhost:8123/threads/search \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

**Get checkpoint history:**
```bash
curl -s "http://localhost:8123/threads/${THREAD_ID}/history" | python3 -m json.tool
```

**Create a custom assistant with different config:**
```bash
curl -s -X POST http://localhost:8123/assistants \
  -H "Content-Type: application/json" \
  -d '{
    "graph_id": "agent",
    "name": "GPT-4o Assistant",
    "config": {
      "configurable": {
        "model_name": "gpt-4o",
        "system_prompt": "You are a concise technical writer. Keep answers under 50 words."
      }
    }
  }' | python3 -m json.tool
```

---

## Success Criteria

| Criteria                | How to verify                                                                |
| ----------------------- | ---------------------------------------------------------------------------- |
| Persistent checkpoints  | Invoke graph → restart server → retrieve same thread state (Steps 4-6)       |
| Full Platform API       | List assistants, create threads, search threads, get history (Steps 2, 3, 8) |
| Real LLM calls          | Graph returns non-hardcoded AI responses via OpenRouter (Step 4)             |
| Configurable assistants | Create assistant with custom model/prompt via API (Step 8)                   |

---

## Troubleshooting

| Issue                                | Cause                                                | Fix                                                                                   |
| ------------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Server refuses to start              | Invalid/expired `LANGSMITH_API_KEY`                  | Verify at smith.langchain.com, update `.env`                                          |
| Port conflict on startup             | Existing containers using same ports                 | Run `docker compose down` before `langgraph up`                                       |
| LLM calls fail with auth error       | Wrong API key format                                 | Ensure `OPENAI_API_KEY` in `.env` is valid. OpenRouter keys start with `sk-or-v1-`    |
| Docker build fails                   | Missing system libraries                             | The `wolfi` base image handles this. If issues persist, check `langgraph.json` config |
| First build very slow                | Docker installing all Python deps                    | Normal — subsequent runs use Docker layer cache                                       |
| `host.docker.internal` not resolving | Not using Docker Desktop (e.g., native Linux Docker) | Use `--network host` or create a shared Docker network                                |
| State lost after restart             | Used `--recreate` flag                               | `--recreate` deletes the Postgres volume. Don't use it if preserving data             |

---

## Connecting to Postgres with DBeaver

You can inspect checkpoints, thread state, and other LangGraph tables directly in DBeaver.

### Approach A (Managed — `langgraph up` without flags)

The managed Postgres is exposed on **port 5433** (not 5432).

| Field              | Value              |
| ------------------ | ------------------ |
| Host               | `localhost`        |
| Port               | `5433`             |
| Database           | `postgres`         |
| Username           | `postgres`         |
| Password           | `postgres`         |
| SSL                | Disabled           |

JDBC URL: `jdbc:postgresql://localhost:5433/postgres`

### Approach B (Manual Infra — your own docker-compose)

Your Postgres is exposed on **port 5432** with custom credentials.

| Field              | Value              |
| ------------------ | ------------------ |
| Host               | `localhost`        |
| Port               | `5432`             |
| Database           | `langgraph_db`     |
| Username           | `langgraph_user`   |
| Password           | `secure_password`  |
| SSL                | Disabled           |

JDBC URL: `jdbc:postgresql://localhost:5432/langgraph_db`

### DBeaver Setup Steps

1. Open DBeaver → **Database** → **New Database Connection**
2. Select **PostgreSQL** → **Next**
3. Enter the connection details from the table above (pick Approach A or B)
4. Click **Test Connection** to verify (containers must be running)
5. Click **Finish**

### Tables to Explore

Once connected, look for these LangGraph tables:

| Table                    | Contents                                                  |
| ------------------------ | --------------------------------------------------------- |
| `checkpoints`            | Graph execution checkpoints (state at each step)          |
| `checkpoint_writes`      | Individual write operations within checkpoints            |
| `checkpoint_blobs`       | Serialized state blobs                                    |

You can query thread state directly, e.g.:

```sql
-- List all threads with their latest checkpoint
SELECT DISTINCT thread_id, created_at
FROM checkpoints
ORDER BY created_at DESC;
```
