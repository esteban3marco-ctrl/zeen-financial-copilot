"""ConversationMemoryManager: Supabase CRUD for conversations and messages."""
from __future__ import annotations

import logging
import os
from typing import Any

from typing import Literal, cast

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage

from agent_runtime.state import TraceMetadata
from memory.schemas import ConversationMemory, MessageRecord
from risk_gates.schemas import GateDecision

logger = logging.getLogger(__name__)


def _get_supabase_client() -> Any:
    """Lazy-init Supabase client to avoid import errors in tests."""
    from supabase import create_client
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def _message_to_record(
    message: AnyMessage,
    sequence_num: int,
    gate_decisions: dict[str, Any] | None = None,
) -> MessageRecord:
    """Convert a LangChain message to a Supabase-compatible MessageRecord."""
    _role: Literal["human", "ai", "tool", "system"]
    if isinstance(message, HumanMessage):
        _role = "human"
    elif isinstance(message, AIMessage):
        _role = "ai"
    elif isinstance(message, ToolMessage):
        _role = "tool"
    else:
        _role = "system"

    return MessageRecord(
        role=_role,
        content=str(message.content),
        tool_call_id=getattr(message, "tool_call_id", None),
        tool_name=getattr(message, "name", None),
        gate_decisions=gate_decisions,
        sequence_num=sequence_num,
    )


async def persist_turn(
    session_id: str,
    user_id: str,
    messages: list[AnyMessage],
    gate_decisions: dict[str, GateDecision],
    metadata: TraceMetadata,
) -> None:
    """Persist conversation turn to Supabase."""
    try:
        client = _get_supabase_client()
        gate_dict = {k: v.model_dump(mode="json") for k, v in gate_decisions.items()}

        # Upsert conversation row
        conv_data = {
            "session_id": session_id,
            "user_id": user_id,
            "turn_count": 1,  # incremented by Supabase trigger ideally
            "total_tokens": metadata.tokens_total,
            "status": "active",
        }
        client.table("conversations").upsert(
            conv_data, on_conflict="session_id"
        ).execute()

        # Get conversation_id
        result = (
            client.table("conversations")
            .select("id")
            .eq("session_id", session_id)
            .single()
            .execute()
        )
        conversation_id: str = result.data["id"]

        # Insert messages
        records = [
            _message_to_record(m, i, gate_dict).model_dump(
                mode="json", exclude={"embedding"}
            )
            | {"conversation_id": conversation_id, "session_id": session_id}
            for i, m in enumerate(messages)
        ]
        if records:
            client.table("messages").insert(records).execute()

        logger.info(
            "persist_turn: session=%s messages=%d tokens=%d",
            session_id,
            len(records),
            metadata.tokens_total,
        )
    except KeyError:
        logger.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY not set — skipping persistence")
    except Exception as exc:
        logger.error("Failed to persist conversation turn: %s", exc)


async def load_conversation(session_id: str) -> ConversationMemory | None:
    """Load a conversation and its messages from Supabase."""
    try:
        client = _get_supabase_client()
        result = (
            client.table("conversations")
            .select("*, messages(*)")
            .eq("session_id", session_id)
            .single()
            .execute()
        )
        if not result.data:
            return None

        data = result.data
        messages = [
            MessageRecord(**m)
            for m in sorted(data.get("messages", []), key=lambda x: x["sequence_num"])
        ]
        return ConversationMemory(
            conversation_id=data["id"],
            session_id=data["session_id"],
            user_id=data["user_id"],
            messages=messages,
            turn_count=data.get("turn_count", 0),
            total_tokens=data.get("total_tokens", 0),
            status=data.get("status", "active"),
        )
    except KeyError:
        logger.warning("Supabase not configured — cannot load conversation")
        return None
    except Exception as exc:
        logger.error("Failed to load conversation %s: %s", session_id, exc)
        return None
