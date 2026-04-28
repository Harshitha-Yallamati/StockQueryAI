"""Custom MCP-inspired tool protocol. Not the official MCP SDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


ToolHandler = Callable[..., dict[str, Any]]


@dataclass
class ToolExecution:
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    ok: bool
    summary: str
    rendered_response: str


class MCPTool:
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: ToolHandler,
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler

    def descriptor(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }

    def invoke(self, arguments: dict[str, Any] | None = None) -> ToolExecution:
        arguments = arguments or {}
        properties = self.input_schema.get("properties", {})
        required = self.input_schema.get("required", [])

        normalized_arguments: dict[str, Any] = {}
        for key, value in arguments.items():
            if properties and key not in properties:
                continue
            normalized_arguments[key] = _coerce_value(value, properties.get(key, {}))

        missing = [field for field in required if normalized_arguments.get(field) in (None, "")]
        if missing:
            message = f"Missing required argument(s): {', '.join(missing)}."
            result = {
                "ok": False,
                "summary": message,
                "rendered_response": message,
                "error": {"code": "INVALID_ARGUMENTS", "message": message},
            }
            return ToolExecution(
                tool_name=self.name,
                arguments=normalized_arguments,
                result=result,
                ok=False,
                summary=message,
                rendered_response=message,
            )

        result = self.handler(**normalized_arguments)
        ok = bool(result.get("ok", False))
        summary = str(result.get("summary", "Tool executed."))
        rendered_response = str(result.get("rendered_response") or summary)
        return ToolExecution(
            tool_name=self.name,
            arguments=normalized_arguments,
            result=result,
            ok=ok,
            summary=summary,
            rendered_response=rendered_response,
        )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}

    def register(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool

    def register_many(self, tools: list[MCPTool]) -> None:
        for tool in tools:
            self.register(tool)

    def openai_tools(self) -> list[dict[str, Any]]:
        return [tool.to_openai_tool() for tool in self._tools.values()]

    def descriptors(self) -> list[dict[str, Any]]:
        return [tool.descriptor() for tool in self._tools.values()]

    def invoke(self, name: str, arguments: dict[str, Any] | None = None) -> ToolExecution:
        tool = self._tools.get(name)
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
