# StockQuery AI Backend

StockQuery AI Backend is a FastAPI service for verified inventory workflows. It combines:

- SQLite for product and order data
- A spec-conformant MCP JSON-RPC server in `mcp.py`
- An OpenAI-compatible chat client for tool-using answers
- ChromaDB for optional knowledge-base retrieval

The backend is designed to answer inventory questions without inventing facts. For common inventory queries, it routes directly to verified tools before or instead of relying on the model.

## Features

- Streaming and non-streaming chat endpoints
- Verified product lookups, stock checks, and inventory summaries
- Product CRUD endpoints
- Purchase order creation and status updates
- Low-stock alerts and dashboard stats
- Knowledge-base document ingestion and search
- Per-session chat memory with a configurable history limit
- Safe fallback behavior when the LLM is unavailable

## Architecture

```text
Client
  -> FastAPI (`main.py`)
  -> StockQueryAgent (`agent.py`)
  -> MCPServer + ToolRegistry (`mcp.py`)
  -> Inventory tools (`inventory_tools.py`) + Knowledge tools (`knowledge_tools.py`)
  -> SQLite (`agent_inventory.db`) + ChromaDB (`chroma_db`)
```

## Project Files

- `main.py`: FastAPI app and REST/SSE routes
- `agent.py`: tool-routing agent, OpenAI-compatible client, and fallback behavior
- `database.py`: SQLite schema migration and inventory/order data access
- `inventory_tools.py`: verified inventory tool handlers
- `knowledge_tools.py`: Chroma-backed ingest and retrieval helpers
- `api_schemas.py`: request and response models
- `seed.py`: resets and seeds demo inventory data

## Prerequisites

- Python 3.10 or newer
- An OpenAI-compatible LLM endpoint
- Ollama if you want to use the default local setup from `.env.example`

## Quick Start

All commands below assume you are running from the backend folder:

```powershell
cd ai_agent_backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python seed.py
uvicorn main:app --reload
```

On macOS or Linux, use `source .venv/bin/activate` and `cp .env.example .env`.

After startup:

- API base URL: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Configuration

The backend loads environment variables from `.env` with `python-dotenv`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `STOCKQUERY_DB_PATH` | `./agent_inventory.db` in `.env.example` | SQLite database for products and orders. |
| `STOCKQUERY_CHROMA_PATH` | `./chroma_db` in `.env.example` | Persistent ChromaDB directory for knowledge embeddings. |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible API base URL. |
| `OPENAI_API_KEY` | `ollama` | API key sent to the OpenAI-compatible client. |
| `STOCKQUERY_LLM_MODEL` | `qwen2.5:1.5b` | Chat model used by the agent. |
| `STOCKQUERY_LOW_STOCK_THRESHOLD` | `10` | Default threshold for low-stock alerts and routing. |
| `STOCKQUERY_SESSION_HISTORY_LIMIT` | `12` | Number of prior user/assistant turns retained per session. |
| `STOCKQUERY_CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173,http://localhost:8080,http://localhost:8081` | Comma-separated frontend origins allowed by CORS. |

Important:

- The sample `.env.example` uses relative paths.
- Run the backend from `ai_agent_backend` unless you convert those paths to absolute paths.
- If you do not have a compatible model running at `OPENAI_BASE_URL`, chat endpoints will still fail safely, but they cannot produce model-written responses.

## Runtime Behavior

- The app runs database initialization and schema migration automatically on startup.
- Common inventory prompts are routed directly to tools such as `list_products`, `get_low_stock_products`, and `query_inventory_db`.
- If the LLM call fails, the backend returns a deterministic verified response from tool output when possible.
- Session history is stored in memory only.
- MCP clients negotiate capabilities through `initialize` and `notifications/initialized` on `/mcp`.

Session resolution order for chat requests:

1. `session_id` in the request body
2. `x-user-id` header
3. `x-session-id` header
4. fallback to `anonymous`

## Data Model

### Product fields

- `id`
- `name`
- `quantity`
- `price`
- `category`
- `brand`
- `supplier`
- `warehouse_location`
- `description`
- `last_updated`

### Order fields

- `id`
- `product_id`
- `name`
- `quantity`
- `total_cost`
- `status`
- `order_date`

Order statuses must be one of:

- `Pending`
- `Arrived`
- `Cancelled`

When an order status changes from a non-arrived state to `Arrived`, the product quantity is incremented once.

Migration note: request payloads now accept only normalized product fields such as `name` and `quantity`. Legacy aliases were removed from API and tool inputs.

## API Routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Health summary with backend status, DB status, product count, model, and version. |
| `POST` | `/mcp` | JSON-RPC 2.0 MCP endpoint for `initialize`, `notifications/initialized`, `ping`, `tools/list`, and `tools/call`. |
| `GET` | `/mcp` | SSE keep-alive stream for an active MCP session. |
| `DELETE` | `/mcp` | Terminate an MCP session created during the MCP HTTP handshake. |
| `POST` | `/api/chat` | Non-streaming chat endpoint. Returns `answer`, `session_id`, and `tools_used`. |
| `POST` | `/api/chat/stream` | Streaming SSE chat endpoint. |
| `POST` | `/ask` | Alias for `/api/chat/stream`. |
| `DELETE` | `/api/chat/session` | Clear in-memory chat history for the resolved session. |
| `GET` | `/api/tools` | List registered tool descriptors. |
| `POST` | `/api/knowledge/ingest` | Ingest a document into ChromaDB. |
| `POST` | `/ingest` | Alias for `/api/knowledge/ingest`. |
| `GET` | `/api/dashboard/stats` | Return total products, total inventory value, and low-stock count. |
| `GET` | `/api/products` | List products, optionally filtered by `category` or `out_of_stock`. |
| `GET` | `/api/inventory` | Alias for `/api/products`. |
| `GET` | `/api/products/{product_id}` | Fetch one product by ID. |
| `GET` | `/api/product/{product_id}` | Alias for `/api/products/{product_id}`. |
| `POST` | `/api/products` | Create a product. |
| `POST` | `/api/inventory` | Alias for `/api/products`. |
| `PUT` | `/api/products/{product_id}` | Update a product. |
| `PUT` | `/api/inventory/{product_id}` | Alias for `/api/products/{product_id}`. |
| `DELETE` | `/api/products/{product_id}` | Delete a product. |
| `DELETE` | `/api/inventory/{product_id}` | Alias for `/api/products/{product_id}`. |
| `GET` | `/api/alerts` | List products at or below the configured low-stock threshold. |
| `GET` | `/api/orders` | List all purchase orders. |
| `POST` | `/api/orders` | Create a purchase order for a product. |
| `PUT` | `/api/orders/{order_id}/status` | Update order status and restock inventory when marked `Arrived`. |

## Example Requests

### Non-streaming chat

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"Show all products\",\"session_id\":\"demo-user\"}"
```

Example response shape:

```json
{
  "answer": "Inventory products\n- ...",
  "session_id": "demo-user",
  "tools_used": ["list_products"]
}
```

### Streaming chat

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What is the total inventory value?\"}"
```

SSE events may include:

- `status`
- `tool_call`
- `tool_result`
- `message`
- `warning`
- `done`

### Create a product

```bash
curl -X POST http://127.0.0.1:8000/api/products \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Logitech MX Master 3S\",
    \"quantity\": 25,
    \"price\": 99.99,
    \"category\": \"Accessories\",
    \"brand\": \"Logitech\",
    \"supplier\": \"Ingram Micro\",
    \"warehouse_location\": \"A-12\",
    \"description\": \"Wireless productivity mouse\"
  }"
```

### Create and receive an order

```bash
curl -X POST http://127.0.0.1:8000/api/orders \
  -H "Content-Type: application/json" \
  -d "{\"product_id\":1,\"quantity\":20}"
```

```bash
curl -X PUT http://127.0.0.1:8000/api/orders/1/status \
  -H "Content-Type: application/json" \
  -d "{\"status\":\"Arrived\"}"
```

### Ingest knowledge-base content

```bash
curl -X POST http://127.0.0.1:8000/api/knowledge/ingest \
  -H "Content-Type: application/json" \
  -d "{
    \"doc_id\": \"returns-policy\",
    \"text\": \"Returns are accepted within 30 days with proof of purchase.\",
    \"metadata\": {\"source\": \"policy_handbook\"}
  }"
```

### MCP initialize

```bash
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Method: initialize" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": 1,
    \"method\": \"initialize\",
    \"params\": {
      \"protocolVersion\": \"2025-11-25\",
      \"capabilities\": {},
      \"clientInfo\": {
        \"name\": \"demo-client\",
        \"version\": \"1.0.0\"
      }
    }
  }"
```

The response returns negotiated server capabilities plus an `Mcp-Session-Id` header for follow-up MCP requests.

## Supported Query Types

The agent is optimized for verified questions such as:

- Show all products
- Show out-of-stock products
- Show products in a category
- Get the cheapest product
- Get low-stock products
- Get product details
- Get stock quantity for a specific product
- Get total inventory value
- Search the knowledge base

Example prompts:

- `Show all products`
- `How many units of Sony Laptop AB-1200 do we have?`
- `Tell me about Logitech MX Master 3S`
- `List products in Electronics`
- `Which items are out of stock?`
- `What is the total inventory value?`
- `Show low stock items below 5`

## Registered Tools

`/api/tools` exposes these tool descriptors:

| Tool | Purpose |
| --- | --- |
| `query_inventory_db` | Get exact stock quantity for one product by name. |
| `get_product_details` | Return the full verified product record for one product. |
| `get_low_stock_products` | List products at or below a threshold. |
| `get_total_inventory_value` | Calculate total inventory value across all products. |
| `list_products` | List all inventory products. |
| `list_out_of_stock_products` | List products with zero quantity. |
| `list_products_by_category` | List products filtered by category. |
| `get_cheapest_product` | Return the lowest-priced product. |
| `search_knowledge_base` | Search ingested knowledge-base documents. |

## Utility Scripts

- `python seed.py`: clears `products` and `orders`, then inserts 200 demo products
- `python seed_rag.py`: pushes sample product summaries into ChromaDB
- `python verify_migration.py`: prints basic SQLite and ChromaDB verification details
- `python seed_kaggle.py`: imports a remote dataset into SQLite

Notes for optional scripts:

- `seed_kaggle.py` uses `pandas` and `requests`, which are not included in `requirements.txt`.
- `seed_kaggle.py` also requires network access to download the CSV.

## Troubleshooting

### Chat endpoint returns a safe fallback

Check that:

- your OpenAI-compatible endpoint is reachable
- the configured model exists
- the inventory database has data

Even when model generation fails, routed tool queries can still return verified deterministic responses.

### Knowledge-base features fail

Check that:

- `chromadb` installed successfully
- `STOCKQUERY_CHROMA_PATH` points to a writable directory
- the process can create or read the `inventory_knowledge` collection

### Paths resolve unexpectedly

If you changed the working directory, update `.env` to use absolute paths for:

- `STOCKQUERY_DB_PATH`
- `STOCKQUERY_CHROMA_PATH`
