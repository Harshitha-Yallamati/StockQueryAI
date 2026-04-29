"""Model Context Protocol primitives for tool registration and HTTP JSON-RPC handling."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable


ToolHandler = Callable[..., dict[str, Any]]

JSON_RPC_VERSION = "2.0"
LATEST_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = (
    LATEST_PROTOCOL_VERSION,
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
)

MCP_METHOD_HEADER = "Mcp-Method"
MCP_NAME_HEADER = "Mcp-Name"
MCP_SESSION_HEADER = "Mcp-Session-Id"
MCP_PROTOCOL_HEADER = "MCP-Protocol-Version"

JSON_RPC_PARSE_ERROR = -32700
JSON_RPC_INVALID_REQUEST = -32600
JSON_RPC_METHOD_NOT_FOUND = -32601
JSON_RPC_INVALID_PARAMS = -32602
JSON_RPC_INTERNAL_ERROR = -32603

MCP_SERVER_NOT_INITIALIZED = -32000


class ToolArgumentError(ValueError):
    """Raised when tool arguments do not satisfy the registered input schema."""


@dataclass
class ToolExecution:
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    ok: bool
    summary: str
    rendered_response: str

    def to_call_tool_result(self) -> dict[str, Any]:
        return {
            "content": [
                {
                    "type": "text",
                    "text": self.rendered_response or json.dumps(self.result, ensure_ascii=False),
                }
            ],
            "structuredContent": self.result,
            "isError": not self.ok,
        }


@dataclass
class MCPResponse:
    status_code: int
    payload: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class MCPSession:
    session_id: str
    protocol_version: str
    client_capabilities: dict[str, Any]
    client_info: dict[str, Any]
    initialized: bool = False


class MCPTool:
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: ToolHandler,
        title: str | None = None,
    ) -> None:
        self.name = name
        self.title = title
        self.description = description
        self.input_schema = input_schema
        self.handler = handler

    def descriptor(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

    def mcp_descriptor(self) -> dict[str, Any]:
        descriptor = self.descriptor()
        if self.title:
            descriptor["title"] = self.title
        return descriptor

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    def normalize_arguments(self, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = arguments or {}
        properties = self.input_schema.get("properties", {})
        required = self.input_schema.get("required", [])

        normalized_arguments: dict[str, Any] = {}
        for key, value in arguments.items():
            if properties and key not in properties:
                continue
            try:
                normalized_arguments[key] = _coerce_value(value, properties.get(key, {}))
            except (TypeError, ValueError) as exc:
                raise ToolArgumentError(f"Invalid value supplied for '{key}'.") from exc

        missing = [field for field in required if normalized_arguments.get(field) in (None, "")]
        if missing:
            raise ToolArgumentError(f"Missing required argument(s): {', '.join(missing)}.")

        return normalized_arguments

    def execute(self, arguments: dict[str, Any]) -> ToolExecution:
        result = self.handler(**arguments)
        ok = bool(result.get("ok", False))
        summary = str(result.get("summary", "Tool executed."))
        rendered_response = str(result.get("rendered_response") or summary)
        return ToolExecution(
            tool_name=self.name,
            arguments=arguments,
            result=result,
            ok=ok,
            summary=summary,
            rendered_response=rendered_response,
        )

    def invoke(self, arguments: dict[str, Any] | None = None) -> ToolExecution:
        try:
            normalized_arguments = self.normalize_arguments(arguments)
        except ToolArgumentError as exc:
            message = str(exc)
            result = {
                "ok": False,
                "summary": message,
                "rendered_response": message,
                "error": {"code": "INVALID_ARGUMENTS", "message": message},
            }
            return ToolExecution(
                tool_name=self.name,
                arguments=arguments or {},
                result=result,
                ok=False,
                summary=message,
                rendered_response=message,
            )

        return self.execute(normalized_arguments)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}

    def register(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool

    def register_many(self, tools: list[MCPTool]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> MCPTool | None:
        return self._tools.get(name)

    def openai_tools(self) -> list[dict[str, Any]]:
        return [tool.to_openai_tool() for tool in self._tools.values()]

    def descriptors(self) -> list[dict[str, Any]]:
        return [tool.descriptor() for tool in self._tools.values()]

    def mcp_descriptors(self, cursor: str | None = None, page_size: int = 50) -> tuple[list[dict[str, Any]], str | None]:
        tools = [tool.mcp_descriptor() for tool in self._tools.values()]
        start = 0
        if cursor:
            try:
                start = int(cursor)
            except ValueError as exc:
                raise ToolArgumentError("Invalid pagination cursor.") from exc
            if start < 0 or start > len(tools):
                raise ToolArgumentError("Invalid pagination cursor.")

        end = start + page_size
        next_cursor = str(end) if end < len(tools) else None
        return tools[start:end], next_cursor

    def invoke(self, name: str, arguments: dict[str, Any] | None = None) -> ToolExecution:
        tool = self.get(name)
        if tool is None:
            message = f"Tool '{name}' is not registered."
            result = {
                "ok": False,
                "summary": message,
                "rendered_response": message,
                "error": {"code": "TOOL_NOT_FOUND", "message": message},
            }
            return ToolExecution(
                tool_name=name,
                arguments=arguments or {},
                result=result,
                ok=False,
                summary=message,
                rendered_response=message,
            )

        try:
            return tool.invoke(arguments)
        except Exception as exc:  # pragma: no cover - last-resort safety path
            message = f"Tool '{name}' failed safely: {exc}"
            result = {
                "ok": False,
                "summary": message,
                "rendered_response": message,
                "error": {"code": "TOOL_EXECUTION_FAILED", "message": message},
            }
            return ToolExecution(
                tool_name=name,
                arguments=arguments or {},
                result=result,
                ok=False,
                summary=message,
                rendered_response=message,
            )


class MCPServer:
    def __init__(
        self,
        registry: ToolRegistry,
        *,
        server_name: str,
        server_version: str,
        server_title: str | None = None,
        instructions: str | None = None,
        supported_protocol_versions: tuple[str, ...] = SUPPORTED_PROTOCOL_VERSIONS,
    ) -> None:
        self.registry = registry
        self.server_name = server_name
        self.server_version = server_version
        self.server_title = server_title
        self.instructions = instructions
        self.supported_protocol_versions = supported_protocol_versions
        self._sessions: dict[str, MCPSession] = {}
        self._lock = RLock()

    def handle_http_message(self, message: Any, headers: dict[str, str]) -> MCPResponse:
        if isinstance(message, list):
            return self._http_error_response(
                status_code=400,
                request_id=None,
                code=JSON_RPC_INVALID_REQUEST,
                message="Streamable HTTP requests must contain a single JSON-RPC message.",
            )

        if not isinstance(message, dict):
            return self._http_error_response(
                status_code=400,
                request_id=None,
                code=JSON_RPC_PARSE_ERROR,
                message="Request body must be a JSON object.",
            )

        if message.get("jsonrpc") != JSON_RPC_VERSION:
            return self._http_error_response(
                status_code=400,
                request_id=message.get("id"),
                code=JSON_RPC_INVALID_REQUEST,
                message="jsonrpc must be '2.0'.",
            )

        if "method" not in message:
            return self._http_error_response(
                status_code=400,
                request_id=message.get("id"),
                code=JSON_RPC_INVALID_REQUEST,
                message="JSON-RPC requests and notifications must include a method.",
            )

        method = str(message["method"])
        if "id" in message and message["id"] is None:
            return self._http_error_response(
                status_code=400,
                request_id=None,
                code=JSON_RPC_INVALID_REQUEST,
                message="Request ids must be omitted for notifications or be a string or integer.",
            )

        request_id = message.get("id")
        if request_id is not None and not isinstance(request_id, (str, int)):
            return self._http_error_response(
                status_code=400,
                request_id=None,
                code=JSON_RPC_INVALID_REQUEST,
                message="Request ids must be strings or integers.",
            )
        is_notification = request_id is None

        transport_error = self._validate_transport_headers(message, headers)
        if transport_error is not None:
            return transport_error

        session_header = headers.get(MCP_SESSION_HEADER.lower())
        session = self._get_session(session_header) if session_header else None

        if method == "initialize":
            if is_notification:
                return self._http_error_response(
                    status_code=400,
                    request_id=None,
                    code=JSON_RPC_INVALID_REQUEST,
                    message="initialize must be sent as a request.",
                )
            return self._handle_initialize(message)

        if session_header and session is None:
            return MCPResponse(status_code=404)

        if method == "notifications/initialized":
            if session is None:
                return MCPResponse(status_code=400)
            session.initialized = True
            return MCPResponse(status_code=202)

        if session is None:
            return MCPResponse(status_code=400)

        header_protocol_version = headers.get(MCP_PROTOCOL_HEADER.lower())
        if header_protocol_version:
            if header_protocol_version not in self.supported_protocol_versions:
                return MCPResponse(status_code=400)
            if header_protocol_version != session.protocol_version:
                return MCPResponse(status_code=400)

        if not session.initialized and method != "ping":
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=MCP_SERVER_NOT_INITIALIZED,
                message="MCP session has not completed the initialized handshake.",
            )

        if method == "tools/list":
            return self._handle_tools_list(message)
        if method == "tools/call":
            return self._handle_tools_call(message)
        if method == "ping":
            return self._jsonrpc_result_response(request_id, {})

        if is_notification:
            return MCPResponse(status_code=202)

        return self._jsonrpc_error_response(
            request_id=request_id,
            code=JSON_RPC_METHOD_NOT_FOUND,
            message=f"Method '{method}' is not supported.",
        )

    def terminate_session(self, session_id: str | None) -> bool:
        if not session_id:
            return False
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def has_session(self, session_id: str | None) -> bool:
        return self._get_session(session_id) is not None

    def _handle_initialize(self, message: dict[str, Any]) -> MCPResponse:
        request_id = message.get("id")
        params = message.get("params")
        if not isinstance(params, dict):
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INVALID_PARAMS,
                message="initialize params must be an object.",
            )

        requested_protocol = params.get("protocolVersion")
        if not isinstance(requested_protocol, str) or not requested_protocol.strip():
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INVALID_PARAMS,
                message="initialize requires a protocolVersion string.",
            )

        client_capabilities = params.get("capabilities")
        if not isinstance(client_capabilities, dict):
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INVALID_PARAMS,
                message="initialize requires capabilities to be an object.",
            )

        client_info = params.get("clientInfo")
        if not isinstance(client_info, dict):
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INVALID_PARAMS,
                message="initialize requires clientInfo to be an object.",
            )

        negotiated_protocol = (
            requested_protocol
            if requested_protocol in self.supported_protocol_versions
            else self.supported_protocol_versions[0]
        )

        session_id = uuid.uuid4().hex
        session = MCPSession(
            session_id=session_id,
            protocol_version=negotiated_protocol,
            client_capabilities=client_capabilities,
            client_info=client_info,
        )
        with self._lock:
            self._sessions[session_id] = session

        result = {
            "protocolVersion": negotiated_protocol,
            "capabilities": {
                "tools": {
                    "listChanged": False,
                }
            },
            "serverInfo": self._server_info(),
            "instructions": self.instructions
            or "Use tools to access verified inventory and knowledge-base data. Tool results are authoritative.",
        }
        return MCPResponse(
            status_code=200,
            payload={
                "jsonrpc": JSON_RPC_VERSION,
                "id": request_id,
                "result": result,
            },
            headers={
                MCP_SESSION_HEADER: session_id,
                MCP_PROTOCOL_HEADER: negotiated_protocol,
            },
        )

    def _handle_tools_list(self, message: dict[str, Any]) -> MCPResponse:
        request_id = message.get("id")
        params = message.get("params")
        cursor: str | None = None

        if params is not None:
            if not isinstance(params, dict):
                return self._jsonrpc_error_response(
                    request_id=request_id,
                    code=JSON_RPC_INVALID_PARAMS,
                    message="tools/list params must be an object when provided.",
                )
            raw_cursor = params.get("cursor")
            if raw_cursor is not None:
                cursor = str(raw_cursor)

        try:
            tools, next_cursor = self.registry.mcp_descriptors(cursor=cursor)
        except ToolArgumentError as exc:
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INVALID_PARAMS,
                message=str(exc),
            )

        result: dict[str, Any] = {"tools": tools}
        if next_cursor is not None:
            result["nextCursor"] = next_cursor
        return self._jsonrpc_result_response(request_id, result)

    def _handle_tools_call(self, message: dict[str, Any]) -> MCPResponse:
        request_id = message.get("id")
        params = message.get("params")
        if not isinstance(params, dict):
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INVALID_PARAMS,
                message="tools/call params must be an object.",
            )

        tool_name = params.get("name")
        if not isinstance(tool_name, str) or not tool_name.strip():
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INVALID_PARAMS,
                message="tools/call requires a tool name.",
            )

        raw_arguments = params.get("arguments")
        if raw_arguments is not None and not isinstance(raw_arguments, dict):
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INVALID_PARAMS,
                message="tools/call arguments must be an object when provided.",
            )

        tool = self.registry.get(tool_name)
        if tool is None:
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INVALID_PARAMS,
                message=f"Unknown tool '{tool_name}'.",
            )

        try:
            normalized_arguments = tool.normalize_arguments(raw_arguments)
            execution = tool.execute(normalized_arguments)
        except ToolArgumentError as exc:
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INVALID_PARAMS,
                message=str(exc),
            )
        except Exception as exc:  # pragma: no cover - safety path
            return self._jsonrpc_error_response(
                request_id=request_id,
                code=JSON_RPC_INTERNAL_ERROR,
                message=f"Tool '{tool_name}' execution failed.",
                data={"detail": str(exc)},
            )

        return self._jsonrpc_result_response(request_id, execution.to_call_tool_result())

    def _server_info(self) -> dict[str, Any]:
        info = {
            "name": self.server_name,
            "version": self.server_version,
        }
        if self.server_title:
            info["title"] = self.server_title
        return info

    def _validate_transport_headers(self, message: dict[str, Any], headers: dict[str, str]) -> MCPResponse | None:
        method = str(message["method"])
        method_header = headers.get(MCP_METHOD_HEADER.lower())
        if method_header and method_header != method:
            return MCPResponse(status_code=400)

        if method == "tools/call":
            params = message.get("params")
            body_name = params.get("name") if isinstance(params, dict) else None
            name_header = headers.get(MCP_NAME_HEADER.lower())
            if name_header and body_name and name_header != body_name:
                return MCPResponse(status_code=400)

        return None

    def _get_session(self, session_id: str | None) -> MCPSession | None:
        if not session_id:
            return None
        with self._lock:
            return self._sessions.get(session_id)

    def _jsonrpc_result_response(self, request_id: Any, result: dict[str, Any]) -> MCPResponse:
        return MCPResponse(
            status_code=200,
            payload={
                "jsonrpc": JSON_RPC_VERSION,
                "id": request_id,
                "result": result,
            },
        )

    def _jsonrpc_error_response(
        self,
        request_id: Any,
        *,
        code: int,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> MCPResponse:
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return MCPResponse(
            status_code=200,
            payload={
                "jsonrpc": JSON_RPC_VERSION,
                "id": request_id,
                "error": error,
            },
        )

    def _http_error_response(
        self,
        *,
        status_code: int,
        request_id: Any,
        code: int,
        message: str,
    ) -> MCPResponse:
        return MCPResponse(
            status_code=status_code,
            payload={
                "jsonrpc": JSON_RPC_VERSION,
                "id": request_id,
                "error": {
                    "code": code,
                    "message": message,
                },
            },
        )


def _coerce_value(value: Any, schema: dict[str, Any]) -> Any:
    value_type = schema.get("type")
    if value_type == "integer" and value is not None:
        return int(value)
    if value_type == "number" and value is not None:
        return float(value)
    if value_type == "boolean" and value is not None:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes"}
    if value_type == "string" and value is not None:
        return str(value).strip()
    return value
