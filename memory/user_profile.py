"""UserProfileManager: Supabase CRUD for user profiles."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from memory.schemas import UserProfile

logger = logging.getLogger(__name__)


def _get_supabase_client() -> Any:
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


async def get_or_create_profile(user_id: str, role: str = "basic") -> UserProfile:
    """Load user profile from Supabase, or create a default one."""
    try:
        client = _get_supabase_client()
        result = (
            client.table("user_profiles")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if result.data:
            return UserProfile(**result.data)
    except KeyError:
        logger.warning("Supabase not configured — returning default profile")
        return UserProfile(user_id=user_id)
    except Exception:
        pass

    # Create default profile
    profile = UserProfile(user_id=user_id)
    try:
        client = _get_supabase_client()
        client.table("user_profiles").insert(
            profile.model_dump(mode="json", exclude={"created_at", "updated_at"})
        ).execute()
    except Exception as exc:
        logger.warning("Could not create user profile for %s: %s", user_id, exc)

    return profile


async def update_preferences(user_id: str, preferences: dict[str, Any]) -> None:
    """Merge new preferences into the user's profile."""
    try:
        client = _get_supabase_client()
        client.table("user_profiles").update(
            {"preferences": preferences, "updated_at": datetime.utcnow().isoformat()}
        ).eq("user_id", user_id).execute()
    except Exception as exc:
        logger.warning("Could not update preferences for %s: %s", user_id, exc)


async def increment_session_count(user_id: str) -> None:
    """Increment total_sessions counter for user."""
    try:
        client = _get_supabase_client()
        client.rpc(
            "increment_user_sessions",
            {"p_user_id": user_id, "p_last_active": datetime.utcnow().isoformat()},
        ).execute()
    except Exception as exc:
        logger.warning("Could not increment session count for %s: %s", user_id, exc)
