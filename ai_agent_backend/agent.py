from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any

from openai import OpenAI

import database as db
from core_config import get_settings
from inventory_tools import build_inventory_tools
from knowledge_tools import build_knowledge_tools
from mcp import ToolExecution, ToolRegistry
from session_store import SessionStore
from streaming import format_sse, iter_text_chunks


logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """
You are StockQuery AI, a production inventory assistant.

Rules:
- Use tools for every inventory or knowledge-base fact.
- Never invent products, categories, prices, quantities, suppliers, or policies.
- The verified product schema is: id, name, quantity, price, category, brand, supplier, warehouse_location, description, last_updated.
- If a tool reports an error or no matching data, explain that clearly and do not guess.
- Supported query types include:
  - show all products
  - show out-of-stock products
  - filter products by category
  - get the cheapest product
  - get low-stock products
  - get product details
  - get stock quantity for a product
  - get total inventory value
  - search the knowledge base
- If the request is outside these capabilities, say so briefly and suggest a supported inventory query.
""".strip()

SAFE_INVENTORY_FALLBACK = (
    "I couldn't verify that request from the available tools. "
    "Try asking for all products, out-of-stock items, a product category, the cheapest product, "
    "low-stock products, or details for a specific product."
)

SAFE_GENERAL_FALLBACK = (
    "I can help with verified inventory and knowledge-base questions only. "
    "Try asking about products, stock levels, categories, cheapest items, or restocking alerts."
)


def _build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register_many(build_inventory_tools())
    registry.register_many(build_knowledge_tools())
    return registry


tool_registry = _build_registry()
session_store = SessionStore(max_messages=settings.session_history_limit)
llm_client = OpenAI(
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
)


class StockQueryAgent:
    def __init__(
        self,
        client: OpenAI,
        registry: ToolRegistry,
        sessions: SessionStore,
    ) -> None:
        self.client = client
        self.registry = registry
        self.sessions = sessions

    async def stream_response(self, user_message: str, session_id: str) -> Any:
        question = user_message.strip()
        history = self.sessions.get_history(session_id)
        routed_call = self._route_query(question)
        tool_executions: list[ToolExecution] = []
        llm_error: Exception | None = None

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": question},
        ]

        yield format_sse({"type": "status", "content": "Analyzing your request..."})

        if routed_call is not None:
            synthetic_call_id = f"route_{uuid.uuid4().hex}"
            yield format_sse(
                {
                    "type": "tool_call",
                    "call_id": synthetic_call_id,
                    "name": routed_call["name"],
                    "arguments": routed_call["arguments"],
                }
            )
            execution = self.registry.invoke(routed_call["name"], routed_call["arguments"])
            tool_executions.append(execution)
            yield format_sse(
                {
                    "type": "tool_result",
                    "call_id": synthetic_call_id,
                    "name": execution.tool_name,
                    "ok": execution.ok,
                    "summary": execution.summary,
                    "result": execution.result,
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": synthetic_call_id,
                            "type": "function",
                            "function": {
                                "name": routed_call["name"],
                                "arguments": json.dumps(routed_call["arguments"]),
                            },
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": synthetic_call_id,
                    "content": json.dumps(execution.result, ensure_ascii=False),
                }
            )
            routed_call = None

        final_text = ""
        for _ in range(4):
            try:
                response = self.client.chat.completions.create(
                    model=settings.llm_model,
                    messages=messages,
                    tools=self.registry.openai_tools(),
                    temperature=0.0,
                )
            except Exception as exc:  # pragma: no cover - depends on runtime LLM availability
                llm_error = exc
                logger.exception("LLM call failed safely")
                break

            message = response.choices[0].message
            if message.tool_calls:
                messages.append(self._assistant_message_from_response(message))
                for tool_call in message.tool_calls:
                    arguments = self._load_tool_arguments(tool_call.function.arguments)
                    yield format_sse(
                        {
                            "type": "tool_call",
                            "call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "arguments": arguments,
                        }
                    )
                    execution = self.registry.invoke(tool_call.function.name, arguments)
                    tool_executions.append(execution)
                    yield format_sse(
                        {
                            "type": "tool_result",
                            "call_id": tool_call.id,
                            "name": execution.tool_name,
                            "ok": execution.ok,
                            "summary": execution.summary,
                            "result": execution.result,
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(execution.result, ensure_ascii=False),
                        }
                    )
                continue

            if not tool_executions and routed_call is not None:
                synthetic_call_id = f"route_{uuid.uuid4().hex}"
                yield format_sse(
                    {
                        "type": "tool_call",
                        "call_id": synthetic_call_id,
                        "name": routed_call["name"],
                        "arguments": routed_call["arguments"],
                    }
                )
                execution = self.registry.invoke(routed_call["name"], routed_call["arguments"])
                tool_executions.append(execution)
                yield format_sse(
                    {
                        "type": "tool_result",
                        "call_id": synthetic_call_id,
                        "name": execution.tool_name,
                        "ok": execution.ok,
                        "summary": execution.summary,
                        "result": execution.result,
                    }
                )
                messages.append(
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": synthetic_call_id,
                                "type": "function",
                                "function": {
                                    "name": routed_call["name"],
                                    "arguments": json.dumps(routed_call["arguments"]),
                                },
                            }
                        ],
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": synthetic_call_id,
                        "content": json.dumps(execution.result, ensure_ascii=False),
                    }
                )
                routed_call = None
                continue

            final_text = self._finalize_response(
                response_text=message.content or "",
                user_message=question,
                tool_executions=tool_executions,
            )
            break

        if not final_text and not tool_executions and routed_call is not None:
            synthetic_call_id = f"route_{uuid.uuid4().hex}"
            yield format_sse(
                {
                    "type": "tool_call",
                    "call_id": synthetic_call_id,
                    "name": routed_call["name"],
                    "arguments": routed_call["arguments"],
                }
            )
            execution = self.registry.invoke(routed_call["name"], routed_call["arguments"])
            tool_executions.append(execution)
            yield format_sse(
                {
                    "type": "tool_result",
                    "call_id": synthetic_call_id,
                    "name": execution.tool_name,
                    "ok": execution.ok,
                    "summary": execution.summary,
                    "result": execution.result,
                }
            )

        if not final_text:
            final_text = self._deterministic_response(question, tool_executions)

        if not final_text:
            final_text = self._safe_fallback(question)

        self.sessions.append_turn(session_id, question, final_text)
        yield format_sse({"type": "status", "content": "Preparing verified response..."})

        for chunk in iter_text_chunks(final_text):
            yield format_sse({"type": "message", "content": chunk})
            await asyncio.sleep(0)

        if llm_error is not None:
            yield format_sse(
                {
                    "type": "warning",
                    "content": "LLM generation was unavailable, so a deterministic verified response was returned instead.",
                }
            )

        yield format_sse({"type": "done"})

    def clear_session(self, session_id: str) -> None:
        self.sessions.clear(session_id)

    def _assistant_message_from_response(self, message: Any) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in message.tool_calls or []
            ],
        }

    def _load_tool_arguments(self, raw_arguments: str | None) -> dict[str, Any]:
        if not raw_arguments:
            return {}
        try:
            data = json.loads(raw_arguments)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            logger.warning("Failed to decode tool arguments: %s", raw_arguments)
            return {}

    def _route_query(self, question: str) -> dict[str, Any] | None:
        lowered = question.lower().strip()

        if any(phrase in lowered for phrase in ("show all products", "list all products", "show inventory", "what products do we have", "show all items")):
            return {"name": "list_products", "arguments": {}}

        if "out of stock" in lowered or "out-of-stock" in lowered or "zero stock" in lowered:
            return {"name": "list_out_of_stock_products", "arguments": {}}

        if "cheapest" in lowered or "least expensive" in lowered or "lowest price" in lowered:
            return {"name": "get_cheapest_product", "arguments": {}}

        if "low stock" in lowered or "running low" in lowered or "restock" in lowered:
            return {
                "name": "get_low_stock_products",
                "arguments": {"threshold": self._extract_threshold(lowered) or settings.low_stock_threshold},
            }

        if "inventory value" in lowered or "total inventory value" in lowered:
            return {"name": "get_total_inventory_value", "arguments": {}}

        for category in db.get_product_categories():
            if category.lower() in lowered and any(
                token in lowered
                for token in ("category", "products", "show", "list", "filter", "inventory", "items")
            ):
                return {"name": "list_products_by_category", "arguments": {"category": category}}

        extracted_name = self._extract_product_name(question)
        if extracted_name:
            if any(
                phrase in lowered
                for phrase in ("tell me about", "details for", "product details", "describe", "more about")
            ):
                return {"name": "get_product_details", "arguments": {"product_name": extracted_name}}

            if any(
                phrase in lowered
                for phrase in ("how many", "quantity", "stock of", "stock for", "do we have", "available", "in stock")
            ):
                return {"name": "query_inventory_db", "arguments": {"product_name": extracted_name}}

        return None

    def _extract_product_name(self, question: str) -> str | None:
        cleaned = question.strip().rstrip("?.!")
        patterns = [
            r"^(tell me about|show details for|details for|product details for|describe)\s+",
            r"^(how many units of|how many of|how many|what is the stock of|stock of|stock for)\s+",
            r"^(do we have|is there|show)\s+",
        ]
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+(do we have|available|in stock)$", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()
        return cleaned or None

    def _extract_threshold(self, text: str) -> int | None:
        match = re.search(r"(\d+)", text)
        if match:
            return int(match.group(1))
        return None

    def _finalize_response(
        self,
        response_text: str,
        user_message: str,
        tool_executions: list[ToolExecution],
    ) -> str:
        cleaned = response_text.strip()
        if tool_executions:
            return cleaned or self._deterministic_response(user_message, tool_executions)

        if self._looks_inventory_query(user_message):
            return self._safe_fallback(user_message)

        return cleaned or SAFE_GENERAL_FALLBACK

    def _deterministic_response(
        self,
        user_message: str,
        tool_executions: list[ToolExecution],
    ) -> str:
        if tool_executions:
            rendered = [execution.rendered_response for execution in tool_executions if execution.rendered_response]
            if rendered:
                return "\n\n".join(rendered)
        return self._safe_fallback(user_message)

    def _safe_fallback(self, user_message: str) -> str:
        if self._looks_inventory_query(user_message):
            return SAFE_INVENTORY_FALLBACK
        return SAFE_GENERAL_FALLBACK

    def _looks_inventory_query(self, user_message: str) -> bool:
        lowered = user_message.lower()
        keywords = (
            "inventory",
            "stock",
            "product",
            "products",
            "category",
            "price",
            "quantity",
            "cheapest",
            "restock",
            "out of stock",
            "low stock",
        )
        return any(keyword in lowered for keyword in keywords)


stock_query_agent = StockQueryAgent(
    client=llm_client,
    registry=tool_registry,
    sessions=session_store,
)


async def stream_agent(user_message: str, session_id: str) -> Any:
    async for event in stock_query_agent.stream_response(user_message, session_id):
        yield event
