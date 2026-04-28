# StockQuery AI

## Overview

StockQuery AI is a FastAPI backend for retail inventory workflows. It combines SQLite for structured inventory data, a custom MCP-inspired tool protocol, and an Ollama-compatible LLM agent for verified stock and product Q&A.

## Architecture

```text
User -> /ask -> StockQueryAgent -> ToolRegistry -> [8 MCPTools] -> SQLite
```

Knowledge-base questions are also supported through `search_knowledge_base`, which uses the Chroma-backed document store.

## Setup

```bash
git clone <repo-url>
cd StockQuery_AI
pip install -r requirements.txt
cp .env.example .env
python seed.py
uvicorn main:app --reload
```

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `STOCKQUERY_DB_PATH` | `<repo>/agent_inventory.db` | SQLite file path for inventory and order data. |
| `STOCKQUERY_CHROMA_PATH` | `<repo>/chroma_db` | Persistent Chroma directory for knowledge-base embeddings. |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible base URL, typically an Ollama endpoint. |
| `OPENAI_API_KEY` | `ollama` | API key sent to the OpenAI-compatible client. |
| `STOCKQUERY_LLM_MODEL` | `qwen2.5:1.5b` | Chat model used by the inventory agent. |
| `STOCKQUERY_LOW_STOCK_THRESHOLD` | `10` | Default threshold for low-stock alerts and tool routing. |
| `STOCKQUERY_SESSION_HISTORY_LIMIT` | `12` | Number of prior chat turns kept per session. |
| `STOCKQUERY_CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173,http://localhost:8080,http://localhost:8081` | Comma-separated frontend origins allowed by CORS. |

## API Routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Health summary with API status, DB status, product count, model, and version. |
| `POST` | `/api/chat` | Non-streaming chat endpoint that returns the final answer, session ID, and tools used. |
| `POST` | `/api/chat/stream` | Streaming SSE chat endpoint for inventory questions. |
| `POST` | `/ask` | Alias for the streaming SSE chat endpoint. |
| `DELETE` | `/api/chat/session` | Clear stored chat history for the resolved session. |
| `GET` | `/api/tools` | Return all registered MCP tool descriptors. |
| `POST` | `/api/knowledge/ingest` | Ingest a knowledge-base document into Chroma. |
| `POST` | `/ingest` | Alias for knowledge-base ingestion. |
| `GET` | `/api/dashboard/stats` | Return dashboard totals for products, value, and low-stock count. |
| `GET` | `/api/products` | List products, optionally filtered by category or stock state. |
| `GET` | `/api/inventory` | Alias for listing products. |
| `GET` | `/api/products/{product_id}` | Fetch one product by numeric ID. |
| `GET` | `/api/product/{product_id}` | Alias for fetching one product by ID. |
| `POST` | `/api/products` | Create a product record. |
| `POST` | `/api/inventory` | Alias for creating a product record. |
| `PUT` | `/api/products/{product_id}` | Update an existing product. |
| `PUT` | `/api/inventory/{product_id}` | Alias for updating an existing product. |
| `DELETE` | `/api/products/{product_id}` | Delete a product record. |
| `DELETE` | `/api/inventory/{product_id}` | Alias for deleting a product record. |
| `GET` | `/api/alerts` | List products at or below the configured low-stock threshold. |
| `GET` | `/api/orders` | List all purchase orders. |
| `POST` | `/api/orders` | Create a purchase order for a product. |
| `PUT` | `/api/orders/{order_id}/status` | Update an order status and restock inventory when marked arrived. |

## Example Queries

- `Show all products`
- `How many units of X?`
- `Tell me about Y`
- `Out of stock items`
- `Total inventory value`
- `Cheapest product`
- `Low stock items`

## MCP Tools

| Tool | Purpose |
| --- | --- |
| `query_inventory_db` | Get the exact stock quantity for one product. |
| `get_product_details` | Return the full verified record for one product. |
| `get_low_stock_products` | List products at or below a threshold. |
| `get_total_inventory_value` | Calculate total inventory value across all products. |
| `list_products` | List all products in inventory. |
| `list_out_of_stock_products` | List products with zero quantity. |
| `list_products_by_category` | List products within a specific category. |
| `get_cheapest_product` | Return the lowest-priced product in inventory. |
| `search_knowledge_base` | Search manuals, policies, and other ingested reference content. |
