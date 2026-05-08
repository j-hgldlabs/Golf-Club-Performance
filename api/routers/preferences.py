from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase import Client

from api.auth import get_current_user
from api.db import get_supabase

router = APIRouter()


class PreferencesBody(BaseModel):
    club_aliases: dict[str, str] = {}


@router.get("")
async def get_preferences(
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Return the authenticated user's preferences."""
    result = (
        db.table("user_preferences")
        .select("club_aliases")
        .eq("user_id", user.id)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return {"club_aliases": {}}
    return {"club_aliases": result.data.get("club_aliases") or {}}


@router.put("")
async def set_preferences(
    body: PreferencesBody,
    user=Depends(get_current_user),
    db: Client = Depends(get_supabase),
):
    """Upsert the authenticated user's preferences."""
    db.table("user_preferences").upsert(
        {"user_id": user.id, "club_aliases": body.club_aliases},
        on_conflict="user_id",
    ).execute()
    return {"club_aliases": body.club_aliases}
