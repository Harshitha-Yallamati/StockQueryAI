# StockQuery AI

StockQuery AI is a full-stack inventory assistant built with React, FastAPI, SQLite, and an LLM tool-calling backend. The project now uses a normalized product schema, a session-aware chat service, MCP-style tool registration, and a safer streaming contract between the UI and the agent.

## Architecture

### Frontend
- `src/pages/*`: dashboard, products, alerts, orders, auth, and chat views
- `src/contexts/AuthContext.tsx`: authenticated user state
- `src/contexts/ChatContext.tsx`: SSE chat client, per-user chat requests, tool-trace UI state
- `src/lib/api.ts`: typed frontend API client
- `src/lib/types.ts`: shared frontend data contracts

### Backend
- `ai_agent_backend/main.py`: FastAPI app and HTTP routes
- `ai_agent_backend/agent.py`: agent orchestration, tool loop, safe fallback logic, SSE events
- `ai_agent_backend/mcp.py`: MCP-style tool descriptors and registry
- `ai_agent_backend/inventory_tools.py`: inventory database tools exposed to the LLM
- `ai_agent_backend/knowledge_tools.py`: knowledge-base tools and ingestion helpers
- `ai_agent_backend/database.py`: schema migration, CRUD, order handling, and reporting
- `ai_agent_backend/session_store.py`: per-session conversation history
- `ai_agent_backend/api_schemas.py`: FastAPI request and response models
- `ai_agent_backend/core_config.py`: environment-driven configuration
- `ai_agent_backend/streaming.py`: SSE formatting helpers

## Normalized Schema

Products now use one consistent schema across backend and frontend:

```text
id
name
quantity
price
category
brand
supplier
warehouse_location
description
last_updated
```

Orders now return:

```text
id
product_id
name
quantity
total_cost
status
order_date
```

The backend still accepts legacy aliases like `product_name` and `stock_quantity` on input to ease migration, but all responses use the normalized schema.

## Chat and Tool Flow

1. The frontend sends a chat request to `POST /api/chat/stream` with `X-User-ID`.
2. The backend resolves a per-user session and loads recent chat history.
3. The agent either:
   - lets the LLM choose tools, or
   - uses a high-confidence deterministic route for obvious inventory intents.
4. Registered Python tools execute against SQLite or the knowledge base.
5. Tool results are appended back into the conversation.
6. The final assistant answer is generated from verified tool output, or a safe fallback is returned if verification is not possible.
7. The frontend renders streaming text plus visible tool traces.

## Supported Inventory Queries

- Show all products
- Show out-of-stock products
- Filter products by category
- Get the cheapest product
- Get low-stock products
- Get stock quantity for a specific product
- Get full product details
- Get total inventory value
- Search the knowledge base

## Local Development

### Frontend

```bash
npm install
npm run dev
```

### Backend

```bash
cd ai_agent_backend
python -m uvicorn main:app --reload --port 8000
```

### Optional environment variables

```bash
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
STOCKQUERY_LLM_MODEL=qwen2.5:1.5b
STOCKQUERY_LOW_STOCK_THRESHOLD=10
STOCKQUERY_SESSION_HISTORY_LIMIT=12
STOCKQUERY_CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

## Data Utilities

- `python ai_agent_backend/seed.py`: seed synthetic inventory data
- `python ai_agent_backend/seed_kaggle.py`: seed from the Kaggle-based CSV source

## Verification Notes

- Python backend modules compile successfully with `python -m compileall ai_agent_backend`
- FastAPI smoke checks pass for `/api/products`, `/api/tools`, and the new streaming event format
- TypeScript type-check passes with `node_modules\.bin\tsc.cmd -p tsconfig.app.json --noEmit`
- ESLint passes with warnings only
- `npm run build` may fail in some Windows sandboxed environments if the local `@swc/core` native binary cannot be loaded; this is an environment/runtime issue rather than an application type or lint failure
