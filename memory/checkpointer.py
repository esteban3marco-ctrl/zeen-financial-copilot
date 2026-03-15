"""SupabaseCheckpointer: LangGraph checkpoint saver backed by Supabase."""
from __future__ import annotations

import logging
import os
from typing import Any, Iterator

logger = logging.getLogger(__name__)


def _get_supabase_client() -> Any:
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


class SupabaseCheckpointer:
    """
    Stores LangGraph checkpoints in conversations.checkpoint (JSONB).
    Implements the duck-typed checkpointer interface LangGraph expects.
    Each thread_id maps to a session_id in the conversations table.
    """

    def get(self, config: dict[str, Any]) -> dict[str, Any] | None:
        """Load checkpoint for the given thread_id."""
        thread_id: str = config.get("configurable", {}).get("thread_id", "")
        try:
            client = _get_supabase_client()
            result = (
                client.table("conversations")
                .select("checkpoint")
                .eq("session_id", thread_id)
                .single()
                .execute()
            )
            if result.data and result.data.get("checkpoint"):
                return result.data["checkpoint"]  # type: ignore[no-any-return]
        except Exception as exc:
            logger.warning("Checkpoint load failed for %s: %s", thread_id, exc)
        return None

    def put(
        self,
        config: dict[str, Any],
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist checkpoint for the given thread_id."""
        thread_id: str = config.get("configurable", {}).get("thread_id", "")
        try:
            client = _get_supabase_client()
            client.table("conversations").upsert(
                {
                    "session_id": thread_id,
                    "checkpoint": checkpoint,
                    "checkpoint_ts": metadata.get("created_at", ""),
                    "user_id": metadata.get("user_id", "anonymous"),
                },
                on_conflict="session_id",
            ).execute()
        except Exception as exc:
            logger.warning("Checkpoint save failed for %s: %s", thread_id, exc)
        return config

    def list(
        self,
        config: dict[str, Any] | None,
        *,
        filter: dict[str, Any] | None = None,
        before: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Minimal list implementation — returns empty iterator."""
        return iter([])
