from __future__ import annotations

from collections import deque
from threading import RLock
from typing import Any


class SessionStore:
    def __init__(self, max_messages: int = 12) -> None:
        self._max_messages = max_messages * 2
        self._sessions: dict[str, deque[dict[str, Any]]] = {}
        self._lock = RLock()

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            history = self._sessions.get(session_id, deque())
            return list(history)

    def append_turn(self, session_id: str, user_message: str, assistant_message: str) -> None:
        with self._lock:
            history = self._sessions.setdefault(session_id, deque(maxlen=self._max_messages))
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": assistant_message})

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
