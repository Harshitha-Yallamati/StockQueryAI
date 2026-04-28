from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import database as db
from agent import stock_query_agent, stream_agent, tool_registry
from api_schemas import (
    AskRequest,
    DashboardStats,
    IngestRequest,
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    SessionClearResponse,
    ToolDescriptor,
)
from core_config import get_settings
from knowledge_tools import add_knowledge


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat/stream")
@app.post("/ask")
async def ask_question(req: AskRequest, request: Request):
    session_id = _resolve_session_id(request, req.session_id)
    logger.info("Received chat question for session %s", session_id)
    return StreamingResponse(
        stream_agent(req.question, session_id=session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat")
async def chat(req: AskRequest, request: Request):
    session_id = _resolve_session_id(request, req.session_id)
    logger.info("Received non-streaming chat question for session %s", session_id)

    answer_parts: list[str] = []
    tools_used: list[str] = []

    async for raw_event in stream_agent(req.question, session_id=session_id):
        payload = _parse_sse_payload(raw_event)
        if not payload:
            continue

        if payload.get("type") == "message":
            answer_parts.append(str(payload.get("content", "")))
            continue

        if payload.get("type") == "tool_call":
            tool_name = str(payload.get("name", "")).strip()
            if tool_name and tool_name not in tools_used:
                tools_used.append(tool_name)

    return {
        "answer": "".join(answer_parts).strip(),
        "session_id": session_id,
        "tools_used": tools_used,
    }


@app.delete("/api/chat/session", response_model=SessionClearResponse)
async def clear_chat_session(request: Request):
    session_id = _resolve_session_id(request, None)
    stock_query_agent.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/api/tools", response_model=list[ToolDescriptor])
def get_tool_descriptors():
    return tool_registry.descriptors()


@app.post("/api/knowledge/ingest")
@app.post("/ingest")
async def ingest_document(req: IngestRequest):
    try:
        result = add_knowledge(doc_id=req.doc_id, text=req.text, metadata=req.metadata)
        return {"status": "success", "message": f"Document {req.doc_id} embedded.", "result": result}
    except Exception as exc:
        logger.exception("Failed to ingest knowledge document")
        raise HTTPException(status_code=500, detail=f"Failed to ingest document: {exc}") from exc


@app.get("/api/dashboard/stats", response_model=DashboardStats)
def get_stats():
    return db.get_inventory_stats()


@app.get("/api/products", response_model=list[ProductResponse])
@app.get("/api/inventory", response_model=list[ProductResponse])
def get_products(category: str | None = None, out_of_stock: bool | None = None):
    return db.get_all_products(category=category, out_of_stock=out_of_stock)


@app.get("/api/products/{product_id}", response_model=ProductResponse)
@app.get("/api/product/{product_id}", response_model=ProductResponse)
def get_product(product_id: int):
    try:
        return db.get_product_by_id(product_id)
    except db.InventoryDataError as exc:
        raise _to_http_exception(exc) from exc


@app.post("/api/products", response_model=ProductResponse, status_code=201)
@app.post("/api/inventory", response_model=ProductResponse, status_code=201)
def add_product(payload: ProductCreate):
    try:
        return db.add_product(payload.model_dump())
    except db.InventoryDataError as exc:
        raise _to_http_exception(exc) from exc


@app.put("/api/products/{product_id}", response_model=ProductResponse)
@app.put("/api/inventory/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdate):
    try:
        return db.update_product(product_id, payload.model_dump(exclude_none=True))
    except db.InventoryDataError as exc:
        raise _to_http_exception(exc) from exc


@app.delete("/api/products/{product_id}")
@app.delete("/api/inventory/{product_id}")
def remove_product(product_id: int):
    try:
        db.delete_product(product_id)
        return {"status": "deleted", "id": product_id}
    except db.InventoryDataError as exc:
        raise _to_http_exception(exc) from exc


@app.get("/api/alerts", response_model=list[ProductResponse])
def get_alerts():
    try:
        return db.get_low_stock_products(settings.low_stock_threshold)
    except db.EmptyDatabaseError:
        return []
    except db.InventoryDataError as exc:
        raise _to_http_exception(exc) from exc


@app.get("/api/orders", response_model=list[OrderResponse])
def get_orders():
    return db.get_all_orders()


@app.post("/api/orders", response_model=OrderResponse, status_code=201)
def place_order_api(payload: OrderCreate):
    try:
        return db.place_order(payload.model_dump())
    except db.InventoryDataError as exc:
        raise _to_http_exception(exc) from exc


@app.put("/api/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status_api(order_id: int, payload: OrderStatusUpdate):
    try:
        return db.update_order_status(order_id, payload.status)
    except db.InventoryDataError as exc:
        raise _to_http_exception(exc) from exc


@app.get("/")
def health_check():
    try:
        stats = db.get_inventory_stats()
        db_status = "connected"
        product_count = stats["totalProducts"]
        status = "ok"
    except Exception:
        logger.exception("Health check failed to query inventory database")
        db_status = "unavailable"
        product_count = 0
        status = "degraded"

    return {
        "status": status,
        "db_status": db_status,
        "product_count": product_count,
        "llm_model": settings.llm_model,
        "version": settings.app_version,
    }


def _resolve_session_id(request: Request, body_session_id: str | None) -> str:
    return (
        body_session_id
        or request.headers.get("x-user-id")
        or request.headers.get("x-session-id")
        or "anonymous"
    )


def _parse_sse_payload(raw_event: Any) -> dict[str, Any] | None:
    if not isinstance(raw_event, str):
        return None

    for line in raw_event.splitlines():
        if not line.startswith("data: "):
            continue
        try:
            payload = json.loads(line[6:])
        except json.JSONDecodeError:
            logger.warning("Failed to decode SSE payload: %s", line)
            return None
        return payload if isinstance(payload, dict) else None

    return None


def _to_http_exception(exc: db.InventoryDataError) -> HTTPException:
    status_code = 400
    if exc.code in {"PRODUCT_NOT_FOUND", "ORDER_NOT_FOUND"}:
        status_code = 404
    elif exc.code in {"EMPTY_DATABASE"}:
        status_code = 404
    return HTTPException(
        status_code=status_code,
        detail={"code": exc.code, "message": str(exc)},
    )
