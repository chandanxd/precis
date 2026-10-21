"""
Précis: Session-Scoped Conversation History Manager.

Provides lightweight, in-memory, thread-safe session tracking for multi-turn
conversational context and contextual follow-ups.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock


@dataclass
class ChatMessage:
    """A single turn in a conversational session."""

    role: str  # "user" | "assistant"
    content: str
    timestamp: float
    # True for assistant turns answered from retrieved document facts.
    grounded: bool = False


class SessionManager:
    """
    Thread-safe, bounded in-memory store for session-scoped conversation history.

    Retains the most recent turns per session, with maximum session capacity
    and sliding-window turn pruning.
    """

    def __init__(
        self,
        max_sessions: int = 1000,
        max_turns_per_session: int = 20,
        session_ttl_seconds: float = 3600 * 4,
    ) -> None:
        self.max_sessions = max_sessions
        self.max_turns_per_session = max_turns_per_session
        self.session_ttl_seconds = session_ttl_seconds
        self._lock = Lock()
        self._sessions: OrderedDict[str, list[ChatMessage]] = OrderedDict()
        self._last_accessed: dict[str, float] = {}

    def get_history(
        self, session_id: str | None, max_turns: int = 6
    ) -> list[ChatMessage]:
        """Retrieve recent chat history for a session."""
        if not session_id or not session_id.strip():
            return []

        sid = session_id.strip()
        with self._lock:
            self._prune_expired()
            if sid not in self._sessions:
                return []
            self._sessions.move_to_end(sid)
            self._last_accessed[sid] = time.time()
            turns = self._sessions[sid]
            return list(turns[-max_turns:])

    def add_message(
        self,
        session_id: str | None,
        role: str,
        content: str,
        grounded: bool = False,
    ) -> None:
        """Record a user or assistant message to session history."""
        if not session_id or not session_id.strip() or not content.strip():
            return

        sid = session_id.strip()
        msg = ChatMessage(
            role=role,
            content=content.strip(),
            timestamp=time.time(),
            grounded=grounded,
        )

        with self._lock:
            self._prune_expired()
            if sid not in self._sessions:
                if len(self._sessions) >= self.max_sessions:
                    oldest_sid, _ = self._sessions.popitem(last=False)
                    self._last_accessed.pop(oldest_sid, None)
                self._sessions[sid] = []

            self._sessions[sid].append(msg)
            if len(self._sessions[sid]) > self.max_turns_per_session:
                self._sessions[sid] = self._sessions[sid][-self.max_turns_per_session:]

            self._sessions.move_to_end(sid)
            self._last_accessed[sid] = time.time()

    def clear_session(self, session_id: str) -> bool:
        """Clear history for a specific session."""
        sid = session_id.strip()
        with self._lock:
            if sid in self._sessions:
                del self._sessions[sid]
                self._last_accessed.pop(sid, None)
                return True
            return False

    def _prune_expired(self) -> None:
        """Prune sessions older than TTL (must be called with _lock held)."""
        now = time.time()
        expired_sids = [
            sid
            for sid, last_time in self._last_accessed.items()
            if (now - last_time) > self.session_ttl_seconds
        ]
        for sid in expired_sids:
            self._sessions.pop(sid, None)
            self._last_accessed.pop(sid, None)


# Global default session manager
session_manager = SessionManager()
