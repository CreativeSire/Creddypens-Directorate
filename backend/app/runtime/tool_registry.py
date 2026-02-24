from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.runtime.hooks import RuntimeEvent, hook_bus
from app.runtime.tool_policy import tool_policy_service
from app.tools.document_search import doc_search
from app.tools.web_search import web_search
from app.tools.scheduling import scheduling_tool


@dataclass
class ToolCallContext:
    org_id: str
    session_id: str | None
    agent_code: str | None


class ToolRegistry:
    """Reusable custom tool runner with permissions + hooks."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {
            "web_search": self._run_web_search,
            "document_search": self._run_document_search,
            "check_availability": self._run_check_availability,
            "book_meeting": self._run_book_meeting,
        }

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def run(self, *, tool_name: str, context: ToolCallContext, args: dict | None = None) -> dict[str, Any]:
        if tool_name not in self._tools:
            return {"ok": False, "error": f"Unknown tool: {tool_name}"}
        args = args or {}
        allowed = tool_policy_service.is_allowed(
            org_id=context.org_id,
            agent_code=context.agent_code,
            tool_name=tool_name,
        )
        hook_bus.emit(
            RuntimeEvent(
                event_type="tool.pre_call",
                org_id=context.org_id,
                session_id=context.session_id,
                agent_code=context.agent_code,
                payload={"tool": tool_name, "allowed": allowed, "args": args},
            )
        )
        if not allowed:
            result = {"ok": False, "error": f"Tool blocked by policy: {tool_name}"}
            hook_bus.emit(
                RuntimeEvent(
                    event_type="tool.post_call",
                    org_id=context.org_id,
                    session_id=context.session_id,
                    agent_code=context.agent_code,
                    payload={"tool": tool_name, "result": result},
                )
            )
            return result
        try:
            payload = self._tools[tool_name](**args)
            result = {"ok": True, "data": payload}
        except Exception as e:
            result = {"ok": False, "error": str(e)}
        hook_bus.emit(
            RuntimeEvent(
                event_type="tool.post_call",
                org_id=context.org_id,
                session_id=context.session_id,
                agent_code=context.agent_code,
                payload={"tool": tool_name, "result": result},
            )
        )
        return result

    def _run_web_search(self, query: str, num_results: int = 5) -> dict[str, Any]:
        raw = web_search.search_sync(query=query, num_results=num_results, search_type="search")
        return {"raw": raw, "formatted": web_search.format_results(raw, max_results=3)}

    def _run_document_search(self, query: str, limit: int = 3) -> dict[str, Any]:
        rows = doc_search.search(query=query, limit=limit)
        return {"rows": rows, "formatted": doc_search.format_results(rows, max_content_length=350)}

    def _run_check_availability(self, date_str: str | None = None) -> dict[str, Any]:
        return scheduling_tool.check_availability(date_str=date_str)

    def _run_book_meeting(self, name: str, email: str, slot: str, date_str: str) -> dict[str, Any]:
        return scheduling_tool.book_meeting(name=name, email=email, slot=slot, date_str=date_str)


tool_registry = ToolRegistry()

