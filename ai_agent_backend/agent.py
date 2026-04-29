from __future__ import annotations

import asyncio
import difflib
import json
import logging
import re
import uuid
from dataclasses import dataclass
from threading import RLock
from typing import Any

from openai import APITimeoutError, OpenAI

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
You are StockQuery AI — an intelligent Inventory Intelligence Agent for a retail system.

Your job is to help users with:
- product availability
- stock levels
- pricing
- categories
- orders
- inventory insights

You are connected to tools that access a real SQLite database.

CORE RULES:
1. NEVER guess or hallucinate data.
2. ALWAYS use tools when the query involves inventory, products, stock, or orders.
3. ONLY answer based on tool results.
4. If no data is found, clearly say it is not available.
5. Do NOT repeat the same tool unnecessarily.
6. Do NOT call tools for greetings or casual messages.

GREETING BEHAVIOR:
If the user says hi, hello, or hlo, respond with:
"Hello! \U0001F44B I can help you with inventory, products, stock levels, and orders. What would you like to check?"
Do not call any tool.

INTENT HANDLING:
- Orders related queries should use list_orders() or list_orders_by_status() when a specific status is requested.
- Stock related queries should use get_low_stock_products() or list_out_of_stock_products() when appropriate.
- Cheapest product queries should use get_cheapest_product().
- All products queries should use list_products().
- Specific product queries should use query_inventory_db() or get_product_details().

REPEATED QUESTION FIX:
If the user asks the same kind of verified question repeatedly, avoid unnecessary repeat tool calls.
Reuse the latest verified context when it is still applicable, and provide a concise summarized answer.

RESPONSE FORMAT:
1. Call a tool when needed.
2. Then respond clearly and concisely using only verified results.
""".strip()

SAFE_INVENTORY_FALLBACK = (
    "I couldn't verify that request from the available tools. "
    "Try asking about a product's stock or price, inventory overview, categories, low-stock items, "
    "orders, or a specific product name."
)

SAFE_GENERAL_FALLBACK = (
    "I can help with verified inventory and knowledge-base questions only. "
    "Try asking about products, stock levels, categories, suppliers, orders, or knowledge-base content."
)

INVENTORY_OVERVIEW_PHRASES = (
    "inventory overview",
    "inventory summary",
    "overview of inventory",
    "summary of inventory",
    "inventory dashboard",
    "dashboard summary",
    "inventory stats",
    "inventory statistics",
)

TOTAL_VALUE_PHRASES = (
    "inventory value",
    "total inventory value",
    "inventory worth",
    "total stock value",
)

CATEGORY_LIST_PHRASES = (
    "what categories",
    "list categories",
    "show categories",
    "categories do we have",
    "available categories",
    "product categories",
    "inventory categories",
)

DETAIL_INTENT_PHRASES = (
    "tell me about",
    "details for",
    "product details",
    "describe",
    "more about",
    "price of",
    "cost of",
    "brand of",
    "supplier of",
    "warehouse location of",
    "where is",
    "location of",
    "what is the price of",
    "what's the price of",
    "what is the brand of",
    "what is the supplier of",
)

STOCK_INTENT_PHRASES = (
    "how many",
    "quantity",
    "stock of",
    "stock for",
    "do we have",
    "do you have",
    "available",
    "in stock",
    "availability",
)

CATALOG_SEARCH_HINTS = (
    "find",
    "search",
    "look up",
    "show",
    "list",
    "products",
    "items",
    "catalog",
    "brand",
    "supplier",
    "warehouse",
    "location",
)

ALL_PRODUCTS_PHRASES = (
    "show all products",
    "list all products",
    "show inventory",
    "what products do we have",
    "show all items",
    "all products",
)

OUT_OF_STOCK_PHRASES = (
    "out of stock",
    "out-of-stock",
    "zero stock",
    "no stock",
)

LOW_STOCK_PHRASES = (
    "low stock",
    "running low",
    "restock",
    "reorder",
)

CHEAPEST_PRODUCT_PHRASES = (
    "cheapest",
    "least expensive",
    "lowest price",
    "lowest priced",
)

ORDER_HINTS = (
    "order",
    "orders",
    "shipment",
    "shipments",
)

KNOWLEDGE_HINTS = (
    "policy",
    "policies",
    "manual",
    "guide",
    "documentation",
    "document",
    "return",
    "returns",
    "warranty",
    "procedure",
    "faq",
    "knowledge base",
)

ORDER_STATUS_KEYWORDS = {
    "pending": "Pending",
    "arrived": "Arrived",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
}

GREETING_MESSAGE = "Hello! \U0001F44B I can help you with inventory, products, stock levels, and orders. What would you like to check?"
GREETING_PATTERNS = (
    "hi",
    "hello",
    "hlo",
)


@dataclass(frozen=True)
class CachedRouteAnswer:
    tool_name: str
    arguments: dict[str, Any]
    summary: str
    rendered_response: str
    final_text: str


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
    max_retries=0,
    timeout=settings.llm_timeout_seconds,
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
        self._cached_route_answers: dict[str, dict[str, CachedRouteAnswer]] = {}
        self._cache_lock = RLock()

    async def stream_response(self, user_message: str, session_id: str) -> Any:
        question = user_message.strip()
        if self._is_greeting(question):
            async for event in self._stream_plain_response(question, session_id, GREETING_MESSAGE):
                yield event
            return

        history = self.sessions.get_history(session_id)
        routed_call = self._route_query(question)
        initial_routed_call = dict(routed_call) if routed_call is not None else None
        used_deterministic_route = routed_call is not None
        tool_executions: list[ToolExecution] = []
        llm_error: Exception | None = None

        cached_answer = self._get_cached_route_answer(session_id, routed_call)
        if cached_answer is not None:
            final_text = self._reuse_cached_answer(question, cached_answer)
            self.sessions.append_turn(session_id, question, final_text)
            yield format_sse({"type": "status", "content": "Reusing the latest verified result..."})
            for chunk in iter_text_chunks(final_text):
                yield format_sse({"type": "message", "content": chunk})
                await asyncio.sleep(0)
            yield format_sse({"type": "done"})
            return

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
        if used_deterministic_route and tool_executions:
            final_text = self._deterministic_response(question, tool_executions)
        else:
            for _ in range(4):
                try:
                    response = await asyncio.to_thread(
                        self.client.chat.completions.create,
                        model=settings.llm_model,
                        messages=messages,
                        tools=self.registry.openai_tools(),
                        temperature=0.0,
                    )
                except Exception as exc:  # pragma: no cover - depends on runtime LLM availability
                    llm_error = exc
                    if isinstance(exc, APITimeoutError):
                        logger.warning("LLM call timed out; using deterministic fallback.")
                    else:
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

        if used_deterministic_route and tool_executions and final_text and initial_routed_call is not None:
            self._store_cached_route_answer(
                session_id,
                initial_routed_call=initial_routed_call,
                tool_executions=tool_executions,
                final_text=final_text,
            )

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
        with self._cache_lock:
            self._cached_route_answers.pop(session_id, None)

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

    async def _stream_plain_response(self, question: str, session_id: str, final_text: str) -> Any:
        self.sessions.append_turn(session_id, question, final_text)
        yield format_sse({"type": "status", "content": "Preparing response..."})
        for chunk in iter_text_chunks(final_text):
            yield format_sse({"type": "message", "content": chunk})
            await asyncio.sleep(0)
        yield format_sse({"type": "done"})

    def _route_query(self, question: str) -> dict[str, Any] | None:
        lowered = question.lower().strip()
        if not lowered:
            return None

        if self._contains_fuzzy_phrase(question, INVENTORY_OVERVIEW_PHRASES):
            return {"name": "get_inventory_overview", "arguments": {}}

        if self._contains_fuzzy_phrase(question, TOTAL_VALUE_PHRASES):
            return {"name": "get_total_inventory_value", "arguments": {}}

        if self._contains_fuzzy_phrase(question, CATEGORY_LIST_PHRASES):
            return {"name": "list_product_categories", "arguments": {}}

        order_status = self._extract_order_status(lowered)
        if order_status and self._contains_fuzzy_token(question, ORDER_HINTS + ("restock",)):
            return {"name": "list_orders_by_status", "arguments": {"status": order_status}}

        if self._contains_fuzzy_token(question, ORDER_HINTS):
            return {"name": "list_orders", "arguments": {}}

        if self._is_global_products_request(question):
            return {"name": "list_products", "arguments": {}}

        if self._contains_fuzzy_phrase(question, OUT_OF_STOCK_PHRASES):
            return {"name": "list_out_of_stock_products", "arguments": {}}

        if self._contains_fuzzy_phrase(question, CHEAPEST_PRODUCT_PHRASES):
            return {"name": "get_cheapest_product", "arguments": {}}

        if self._contains_fuzzy_phrase(question, LOW_STOCK_PHRASES):
            return {
                "name": "get_low_stock_products",
                "arguments": {"threshold": self._extract_threshold(lowered) or settings.low_stock_threshold},
            }

        for category in db.get_product_categories():
            if self._contains_category_request(question, category):
                return {"name": "list_products_by_category", "arguments": {"category": category}}

        extracted_name = self._extract_product_name(question)
        if extracted_name:
            if self._contains_fuzzy_phrase(question, DETAIL_INTENT_PHRASES):
                return {"name": "get_product_details", "arguments": {"name": extracted_name}}

            if self._contains_fuzzy_phrase(question, STOCK_INTENT_PHRASES):
                if self._contains_fuzzy_token(question, ("products", "items", "brand", "supplier", "warehouse", "category")):
                    return {"name": "search_inventory_catalog", "arguments": {"query": question}}
                return {"name": "query_inventory_db", "arguments": {"name": extracted_name}}

            if self._contains_fuzzy_phrase(question, CATALOG_SEARCH_HINTS):
                return {"name": "search_inventory_catalog", "arguments": {"query": extracted_name}}

        product_candidate = self._find_product_candidate(question)
        if product_candidate is not None:
            return {"name": "get_product_details", "arguments": {"name": product_candidate["name"]}}

        if self._looks_inventory_query(question):
            if self._contains_fuzzy_phrase(question, CATALOG_SEARCH_HINTS):
                return {"name": "search_inventory_catalog", "arguments": {"query": question}}
            return None

        if self._looks_knowledge_query(question):
            return {"name": "search_knowledge_base", "arguments": {"query": question}}

        return None

    def _extract_product_name(self, question: str) -> str | None:
        cleaned = question.strip().rstrip("?.!")
        patterns = [
            r"^(tell me about|show details for|details for|product details for|describe)\s+",
            r"^(how many units of|how many of|how many|what is the stock of|stock of|stock for|availability of|availability for)\s+",
            r"^(what is the price of|what's the price of|price of|cost of|brand of|supplier of|warehouse location of|location of|where is)\s+",
            r"^(do we have|do you have|is there|show|find|search for|look up)\s+",
        ]
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+(do we have|available|in stock|right now)$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(any|the|a|an)\s+", "", cleaned, flags=re.IGNORECASE)
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
            if len(tool_executions) == 1:
                execution = tool_executions[0]
                lowered = user_message.lower()
                if (
                    any(keyword in lowered for keyword in ("how many", "count", "total"))
                    and execution.summary
                    and execution.rendered_response
                    and execution.summary != execution.rendered_response
                ):
                    return f"{execution.summary}\n{execution.rendered_response}"
            rendered = [execution.rendered_response for execution in tool_executions if execution.rendered_response]
            if rendered:
                return "\n\n".join(rendered)
        return self._safe_fallback(user_message)

    def _safe_fallback(self, user_message: str) -> str:
        if self._looks_inventory_query(user_message):
            return SAFE_INVENTORY_FALLBACK
        return SAFE_GENERAL_FALLBACK

    def _is_greeting(self, user_message: str) -> bool:
        normalized = re.sub(r"[^a-z]", "", user_message.lower())
        return normalized in GREETING_PATTERNS

    def _contains_fuzzy_phrase(self, user_message: str, phrases: tuple[str, ...], threshold: float = 0.84) -> bool:
        normalized = self._normalize_for_match(user_message)
        if not normalized:
            return False
        if any(phrase in normalized for phrase in phrases):
            return True

        tokens = normalized.split()
        for phrase in phrases:
            phrase_tokens = phrase.split()
            candidate_lengths = {len(phrase_tokens) - 1, len(phrase_tokens), len(phrase_tokens) + 1}
            for window_length in candidate_lengths:
                if window_length <= 0 or window_length > len(tokens):
                    continue
                for start in range(len(tokens) - window_length + 1):
                    window = " ".join(tokens[start : start + window_length])
                    if difflib.SequenceMatcher(None, window, phrase).ratio() >= threshold:
                        return True
        return False

    def _contains_fuzzy_token(self, user_message: str, terms: tuple[str, ...], threshold: float = 0.84) -> bool:
        normalized = self._normalize_for_match(user_message)
        if not normalized:
            return False
        tokens = normalized.split()
        for term in terms:
            if term in normalized:
                return True
            term_tokens = term.split()
            for token in tokens:
                for term_token in term_tokens:
                    if difflib.SequenceMatcher(None, token, term_token).ratio() >= threshold:
                        return True
        return False

    def _normalize_for_match(self, user_message: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s-]", " ", user_message.lower())).strip()

    def _contains_category_request(self, user_message: str, category: str) -> bool:
        normalized = self._normalize_for_match(user_message)
        category_normalized = self._normalize_for_match(category)
        if not normalized or not category_normalized:
            return False
        has_category_word = self._contains_fuzzy_token(
            user_message,
            ("category", "categories", "products", "items", "inventory", "show", "list", "filter"),
        )
        return has_category_word and (
            category_normalized in normalized
            or self._contains_fuzzy_phrase(user_message, (category_normalized,), threshold=0.9)
        )

    def _is_global_products_request(self, user_message: str) -> bool:
        if not self._contains_fuzzy_phrase(user_message, ALL_PRODUCTS_PHRASES):
            return False
        normalized = self._normalize_for_match(user_message)
        remaining = normalized
        for phrase in ALL_PRODUCTS_PHRASES:
            remaining = remaining.replace(phrase, " ")
        filler_tokens = {
            "all",
            "do",
            "have",
            "inventory",
            "items",
            "list",
            "please",
            "products",
            "show",
            "the",
            "we",
            "what",
        }
        residual_tokens = [token for token in remaining.split() if token not in filler_tokens]
        return not residual_tokens

    def _find_product_candidate(self, user_message: str) -> dict[str, Any] | None:
        normalized = self._normalize_for_match(user_message)
        if not normalized or self._contains_fuzzy_token(user_message, ORDER_HINTS):
            return None
        try:
            return db.find_product_candidate(user_message)
        except db.InventoryDataError:
            return None

    def _get_cached_route_answer(
        self,
        session_id: str,
        routed_call: dict[str, Any] | None,
    ) -> CachedRouteAnswer | None:
        if routed_call is None:
            return None
        signature = self._route_signature(routed_call)
        with self._cache_lock:
            return self._cached_route_answers.get(session_id, {}).get(signature)

    def _store_cached_route_answer(
        self,
        session_id: str,
        *,
        initial_routed_call: dict[str, Any],
        tool_executions: list[ToolExecution],
        final_text: str,
    ) -> None:
        if not tool_executions:
            return
        primary_execution = tool_executions[0]
        cached = CachedRouteAnswer(
            tool_name=primary_execution.tool_name,
            arguments=primary_execution.arguments,
            summary=primary_execution.summary,
            rendered_response=primary_execution.rendered_response,
            final_text=final_text,
        )
        signature = self._route_signature(initial_routed_call)
        with self._cache_lock:
            self._cached_route_answers.setdefault(session_id, {})[signature] = cached

    def _route_signature(self, routed_call: dict[str, Any]) -> str:
        return json.dumps(
            {
                "name": routed_call.get("name"),
                "arguments": routed_call.get("arguments", {}),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def _reuse_cached_answer(self, user_message: str, cached_answer: CachedRouteAnswer) -> str:
        lowered = user_message.lower()
        if "how many" in lowered or "count" in lowered or "total" in lowered:
            if cached_answer.summary and cached_answer.rendered_response:
                return f"{cached_answer.summary}\n{cached_answer.rendered_response}"
            return cached_answer.summary or cached_answer.final_text

        if any(keyword in lowered for keyword in ("remaining", "still", "again", "recent", "orders")):
            return f"Based on the latest verified result:\n{cached_answer.rendered_response}"

        return f"Based on the latest verified result:\n{cached_answer.final_text}"

    def _looks_inventory_query(self, user_message: str) -> bool:
        lowered = user_message.lower()
        keywords = (
            "available",
            "availability",
            "brand",
            "category",
            "categories",
            "cost",
            "dashboard",
            "details",
            "do you have",
            "do we have",
            "find",
            "inventory",
            "item",
            "items",
            "list",
            "location",
            "order",
            "orders",
            "inventory",
            "products",
            "product",
            "price",
            "quantity",
            "cheapest",
            "search",
            "shipment",
            "shipments",
            "show",
            "restock",
            "supplier",
            "out of stock",
            "low stock",
            "stock",
            "summary",
            "warehouse",
        )
        if any(keyword in lowered for keyword in keywords):
            return True
        if self._contains_fuzzy_phrase(
            user_message,
            OUT_OF_STOCK_PHRASES + LOW_STOCK_PHRASES + CHEAPEST_PRODUCT_PHRASES + INVENTORY_OVERVIEW_PHRASES,
        ):
            return True
        if self._contains_fuzzy_token(
            user_message,
            ("inventory", "stock", "product", "products", "orders", "order", "price", "quantity", "category"),
        ):
            return True
        return bool(
            re.search(
                r"^(do we have|do you have|is there|show|list|find|search|look up|tell me about|details for|price of|cost of|brand of|supplier of|warehouse location of|where is)\b",
                lowered,
            )
        )

    def _looks_knowledge_query(self, user_message: str) -> bool:
        lowered = user_message.lower()
        return any(keyword in lowered for keyword in KNOWLEDGE_HINTS)

    def _extract_order_status(self, lowered_question: str) -> str | None:
        for keyword, normalized_status in ORDER_STATUS_KEYWORDS.items():
            if keyword in lowered_question or self._contains_fuzzy_token(lowered_question, (keyword,), threshold=0.82):
                return normalized_status
        return None


stock_query_agent = StockQueryAgent(
    client=llm_client,
    registry=tool_registry,
    sessions=session_store,
)


async def stream_agent(user_message: str, session_id: str) -> Any:
    async for event in stock_query_agent.stream_response(user_message, session_id):
        yield event
