"""SessionMemoryManager: in-RAM context window and preference management."""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from agent_runtime.state import SessionMemory, ToolResult, UserPreference

logger = logging.getLogger(__name__)

_FINANCE_PREFERENCE_KEYWORDS: dict[str, str] = {
    "stock": "interest_area:equities",
    "crypto": "interest_area:crypto",
    "bond": "interest_area:fixed_income",
    "budget": "interest_area:budgeting",
    "tax": "interest_area:tax_planning",
    "retirement": "interest_area:retirement",
}


class SessionMemoryManager:
    """Manages in-RAM session memory for one active conversation."""

    def __init__(self, max_context_messages: int = 20) -> None:
        self._memory = SessionMemory(max_context_messages=max_context_messages)

    @property
    def memory(self) -> SessionMemory:
        return self._memory

    def add_message(self, message: AnyMessage) -> None:
        """Append message and trim context window to max size."""
        messages = list(self._memory.context_window_messages) + [message]
        if len(messages) > self._memory.max_context_messages:
            # Always keep system messages; trim from oldest human/ai messages
            messages = messages[-self._memory.max_context_messages:]
        self._memory = self._memory.model_copy(
            update={"context_window_messages": messages}
        )

    def add_tool_result(self, result: ToolResult) -> None:
        """Store tool result for in-session reference."""
        recent = list(self._memory.recent_tool_results) + [result]
        # Keep last 10 tool results in memory
        recent = recent[-10:]
        self._memory = self._memory.model_copy(
            update={"recent_tool_results": recent}
        )

    def detect_preferences(self, text: str) -> list[UserPreference]:
        """Detect financial preferences from message text."""
        detected: list[UserPreference] = []
        text_lower = text.lower()
        for keyword, preference in _FINANCE_PREFERENCE_KEYWORDS.items():
            if keyword in text_lower:
                detected.append(
                    UserPreference(key=preference.split(":")[0], value=preference.split(":")[1])
                )
        if detected:
            existing = list(self._memory.detected_preferences)
            existing_keys = {p.key for p in existing}
            new_prefs = [p for p in detected if p.key not in existing_keys]
            self._memory = self._memory.model_copy(
                update={"detected_preferences": existing + new_prefs}
            )
        return detected

    def increment_turn(self) -> None:
        self._memory = self._memory.model_copy(
            update={"turn_count": self._memory.turn_count + 1}
        )

    def get_context_for_llm(self) -> list[AnyMessage]:
        """Return messages suitable for LLM context window."""
        return list(self._memory.context_window_messages)
