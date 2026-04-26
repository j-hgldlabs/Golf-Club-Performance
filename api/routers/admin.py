from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from supabase import Client

from api.auth import require_admin
from api.db import get_supabase

router = APIRouter()


class InviteRequest(BaseModel):
    email: EmailStr


class RoleUpdate(BaseModel):
    email: EmailStr
    role: str  # "admin" | "user"


@router.get("/users")
async def list_users(
    admin=Depends(require_admin),
    db: Client = Depends(get_supabase),
):
    """Return all registered users. Admin only."""
    try:
        result = db.auth.admin.list_users()
        # supabase-py v2 may return a list directly or a paginated object
        user_list = result if isinstance(result, list) else getattr(result, "users", result)
        users = []
        for u in user_list:
            users.append({
                "id": str(u.id),
                "email": u.email,
                "role": (u.user_metadata or {}).get("role", "user"),
                "created_at": str(u.created_at) if u.created_at else None,
                "last_sign_in": str(u.last_sign_in_at) if u.last_sign_in_at else None,
            })
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invite")
async def invite_user(
    body: InviteRequest,
    admin=Depends(require_admin),
    db: Client = Depends(get_supabase),
):
    """Send a Supabase magic-link invite to a new user. Admin only."""
    try:
        db.auth.admin.invite_user_by_email(body.email)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not invite {body.email}: {e}")
    return {"invited": body.email}


@router.patch("/users/role")
async def update_role(
    body: RoleUpdate,
    admin=Depends(require_admin),
    db: Client = Depends(get_supabase),
):
    """Update a user's role in their metadata. Admin only."""
    # Look up user by email
    all_users = db.auth.admin.list_users()
    target = next((u for u in all_users if u.email == body.email), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"User {body.email} not found")

    db.auth.admin.update_user_by_id(
        target.id,
        {"user_metadata": {"role": body.role}},
    )
    return {"email": body.email, "role": body.role}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin=Depends(require_admin),
    db: Client = Depends(get_supabase),
):
    """Permanently delete a user and all their data. Admin only."""
    # Delete associated data first
    db.table("shots").delete().eq("user_id", user_id).execute()
    db.table("club_summaries").delete().eq("user_id", user_id).execute()
    db.table("sessions").delete().eq("user_id", user_id).execute()

    # Delete the auth user
    db.auth.admin.delete_user(user_id)

    return {"deleted": user_id}
