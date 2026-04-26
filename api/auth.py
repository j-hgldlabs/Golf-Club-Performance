from __future__ import annotations

import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from api.db import get_supabase

_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Client = Depends(get_supabase),
):
    """Verify the Supabase JWT and return the authenticated user."""
    token = credentials.credentials
    try:
        response = db.auth.get_user(token)
        if response.user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return response.user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")


def require_admin(user=Depends(get_current_user), db: Client = Depends(get_supabase)):
    """Allow only users with the admin role (set via Supabase user metadata)."""
    role = (user.user_metadata or {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
