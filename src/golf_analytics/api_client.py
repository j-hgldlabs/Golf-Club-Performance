from __future__ import annotations

import os

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _raise(r: requests.Response) -> None:
    """Raise with the FastAPI detail message, not just the HTTP status line."""
    if not r.ok:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise requests.HTTPError(f"{r.status_code}: {detail}", response=r)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login(email: str, password: str) -> dict:
    """Returns {access_token, refresh_token, expires_at, email, role}."""
    r = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
    if r.status_code == 401:
        raise ValueError("Invalid email or password")
    r.raise_for_status()
    return r.json()


def refresh_session(refresh_token: str) -> dict:
    """Exchange a refresh token for a new session. Returns same shape as login."""
    r = requests.post(f"{API_BASE}/auth/refresh", json={"refresh_token": refresh_token})
    _raise(r)
    return r.json()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

def list_sessions(token: str) -> list:
    r = requests.get(f"{API_BASE}/sessions/", headers=_h(token))
    r.raise_for_status()
    return r.json()


def upload_session(token: str, file_bytes: bytes, filename: str) -> dict:
    r = requests.post(
        f"{API_BASE}/sessions/upload",
        headers=_h(token),
        files={"file": (filename, file_bytes, "text/csv")},
    )
    r.raise_for_status()
    return r.json()


def delete_session(token: str, session_id: str) -> dict:
    r = requests.delete(f"{API_BASE}/sessions/{session_id}", headers=_h(token))
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def generate_analytics(token: str) -> dict:
    """Recompute all deliverables from the user's shots and cache in Supabase."""
    r = requests.post(f"{API_BASE}/analytics/generate", headers=_h(token))
    r.raise_for_status()
    return r.json()


def get_avg_carry(token: str) -> pd.DataFrame:
    """Compute avg_carry_yds table (base carry + wind adjustments) from the user's shots."""
    r = requests.get(f"{API_BASE}/analytics/avg-carry", headers=_h(token))
    r.raise_for_status()
    return pd.DataFrame(r.json())


def get_shots(token: str) -> pd.DataFrame:
    """All raw shots for the user, title-case columns (analytics-engine format)."""
    r = requests.get(f"{API_BASE}/analytics/shots", headers=_h(token))
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data) if data else pd.DataFrame()


def get_summary(token: str) -> pd.DataFrame:
    r = requests.get(f"{API_BASE}/analytics/summary", headers=_h(token))
    r.raise_for_status()
    return pd.DataFrame(r.json())


def get_carry_averages(token: str) -> pd.DataFrame:
    r = requests.get(f"{API_BASE}/analytics/carry-averages", headers=_h(token))
    r.raise_for_status()
    return pd.DataFrame(r.json())


def get_face_variance(token: str) -> pd.DataFrame:
    r = requests.get(f"{API_BASE}/analytics/face-variance", headers=_h(token))
    r.raise_for_status()
    return pd.DataFrame(r.json())


def get_shot_shapes(token: str) -> pd.DataFrame:
    r = requests.get(f"{API_BASE}/analytics/shot-shapes", headers=_h(token))
    r.raise_for_status()
    return pd.DataFrame(r.json())


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

def list_users(token: str) -> list:
    r = requests.get(f"{API_BASE}/admin/users", headers=_h(token))
    _raise(r)
    return r.json()


def invite_user(token: str, email: str) -> dict:
    r = requests.post(f"{API_BASE}/admin/invite", headers=_h(token), json={"email": email})
    _raise(r)
    return r.json()
