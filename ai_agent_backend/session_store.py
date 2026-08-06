from __future__ import annotations

from collections import deque
from threading import RLock
from typing import Any


class SessionStore:
    def __init__(self, max_messages: int = 20) -> None:
        self._max_messages = max_messages * 2  # Store both user and assistant messages
        self._sessions: dict[str, dict[str, Any]] = {}  # Enhanced session storage
        self._lock = RLock()

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id, {})
            history = session.get("history", deque(maxlen=self._max_messages))
            return list(history)

    def append_turn(self, session_id: str, user_message: str, assistant_message: str) -> None:
        with self._lock:
            session = self._sessions.setdefault(session_id, {
                "history": deque(maxlen=self._max_messages),
                "last_tool_results": [],
                "context_summary": None
            })
            session["history"].append({"role": "user", "content": user_message})
            session["history"].append({"role": "assistant", "content": assistant_message})

    def set_context_data(self, session_id: str, key: str, value: Any) -> None:
        """Store additional context data for the session."""
        with self._lock:
            session = self._sessions.setdefault(session_id, {
                "history": deque(maxlen=self._max_messages),
                "last_tool_results": [],
                "context_summary": None
            })
            session[key] = value

    def get_context_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """Retrieve context data for the session."""
        with self._lock:
            session = self._sessions.get(session_id, {})
            return session.get(key, default)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
