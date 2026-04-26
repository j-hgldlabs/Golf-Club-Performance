from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from supabase import Client

from api.db import get_supabase

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _session_payload(resp) -> dict:
    user = resp.user
    role = (user.user_metadata or {}).get("role", "user")
    return {
        "access_token": resp.session.access_token,
        "refresh_token": resp.session.refresh_token,
        "expires_at": resp.session.expires_at,
        "email": user.email,
        "role": role,
    }


@router.post("/login")
async def login(body: LoginRequest, db: Client = Depends(get_supabase)):
    """Exchange email + password for a Supabase JWT."""
    try:
        resp = db.auth.sign_in_with_password({"email": body.email, "password": body.password})
        return _session_payload(resp)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: Client = Depends(get_supabase)):
    """Exchange a refresh token for a new access token."""
    try:
        resp = db.auth.refresh_session(body.refresh_token)
        return _session_payload(resp)
    except Exception:
        raise HTTPException(status_code=401, detail="Could not refresh session")
